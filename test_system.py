"""Comprehensive system test for the Islamic Chatbot.

Tests:
1. Translation (Hindi/Gujarati/Urdu → English)
2. Query classification (greeting vs needs RAG)
3. Query rewriting (follow-ups)
4. Retrieval (BM25, FAISS, hybrid)
5. Provider fallback (Gemini → Groq)
6. End-to-end chat flow
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def test_section(title: str):
    print(f"\n{BLUE}{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}{RESET}\n")

def test_result(name: str, passed: bool, details: str = ""):
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} | {name}")
    if details:
        print(f"      {details}")

# ============================================================================
# 1. TRANSLATION TESTS
# ============================================================================

def test_translation():
    test_section("1. QUERY TRANSLATION (Hindi/Gujarati -> English)")
    
    from rag.rewrite import translate_query_to_english
    
    test_cases = [
        ("kya mai muth maar sakta hoon", "masturbation", "Hindi"),
        ("mane kem khbr pade hu baaligh chu k nahi", "puberty", "Gujarati"),
        ("namaz ke liye wazu kaise karein", "wudu", "Hindi"),
        ("what is wudu", "wudu", "English (should pass through)"),
    ]
    
    for query, expected_keyword, lang in test_cases:
        try:
            translated = translate_query_to_english(query)
            passed = expected_keyword.lower() in translated.lower()
            test_result(
                f"{lang}: '{query[:40]}'",
                passed,
                f"-> '{translated}'" if passed else f"-> '{translated}' (expected '{expected_keyword}')"
            )
        except Exception as e:
            test_result(f"{lang}: '{query[:40]}'", False, f"Error: {str(e)}")

# ============================================================================
# 2. QUERY CLASSIFICATION TESTS
# ============================================================================

def test_classification():
    test_section("2. QUERY CLASSIFICATION (Greeting vs Needs RAG)")
    
    from rag.classify import classify_query, QueryIntent
    
    test_cases = [
        ("hello", QueryIntent.SKIP_RAG, "Greeting"),
        ("hellooo", QueryIntent.SKIP_RAG, "Greeting with extra letters"),
        ("salam", QueryIntent.SKIP_RAG, "Islamic greeting"),
        ("assalam alaikum", QueryIntent.SKIP_RAG, "Full Islamic greeting"),
        ("thank you", QueryIntent.SKIP_RAG, "Thanks"),
        ("hello what is wudu", QueryIntent.NEEDS_RAG, "Greeting + question"),
        ("what is wudu", QueryIntent.NEEDS_RAG, "Islamic question"),
        ("is music haram", QueryIntent.NEEDS_RAG, "Ruling question"),
    ]
    
    for query, expected, description in test_cases:
        result = classify_query(query)
        passed = result == expected
        test_result(
            f"{description}: '{query}'",
            passed,
            f"-> {result.name}" if passed else f"-> {result.name} (expected {expected.name})"
        )

# ============================================================================
# 3. QUERY REWRITING TESTS
# ============================================================================

def test_rewriting():
    test_section("3. QUERY REWRITING (Follow-up Expansion)")
    
    from rag.rewrite import rewrite_query
    
    # Test 1: Follow-up should be expanded
    history = [
        {"role": "user", "content": "Is abortion permissible?"},
        {"role": "assistant", "content": "Abortion is not permitted after implantation except when the mother's life is in danger..."}
    ]
    
    followup = "what about for women with health risks?"
    rewritten, was_rewritten = rewrite_query(followup, history)
    
    passed = was_rewritten and "abortion" in rewritten.lower() and "women" in rewritten.lower()
    test_result(
        "Follow-up expansion",
        passed,
        f"'{followup}' -> '{rewritten}'"
    )
    
    # Test 2: Self-contained query should pass through
    standalone = "What are the conditions for Friday prayer?"
    rewritten2, was_rewritten2 = rewrite_query(standalone, history)
    
    passed2 = not was_rewritten2 or rewritten2.lower() == standalone.lower()
    test_result(
        "Self-contained query (no change)",
        passed2,
        f"'{standalone}' -> '{rewritten2}'"
    )

# ============================================================================
# 4. RETRIEVAL TESTS
# ============================================================================

def test_retrieval():
    test_section("4. RETRIEVAL (BM25, FAISS, Hybrid)")
    
    from rag.retrieve import Retriever
    
    # Check if index exists
    if not os.path.exists("artifacts/chunks.sqlite"):
        test_result("Index file check", False, "Index not found at artifacts/")
        return
    
    retriever = Retriever()  # Uses default paths
    test_result("Index loading", True, f"{retriever.count} chunks loaded")
    
    test_cases = [
        ("masturbation allowed Islam", "Masturbation", "English query"),
        ("wudu ablution conditions", "wudu", "Prayer-related"),
        ("what breaks fast Ramadan", "fast", "Fasting-related"),
        ("marriage nikah conditions", "marriage", "Family law"),
    ]
    
    for query, expected_keyword, description in test_cases:
        try:
            hits = retriever.search(query, k=3, mode="hybrid")
            
            # Check if expected keyword appears in top results
            found = any(expected_keyword.lower() in hit.text.lower() for hit in hits)
            
            test_result(
                f"{description}: '{query}'",
                found and len(hits) > 0,
                f"-> {len(hits)} results, keyword {'found' if found else 'NOT FOUND'}"
            )
            
            if found and len(hits) > 0:
                print(f"      Top source: {hits[0].citation}")
        
        except Exception as e:
            test_result(f"{description}", False, f"Error: {str(e)}")

# ============================================================================
# 5. PROVIDER TESTS
# ============================================================================

def test_providers():
    test_section("5. LLM PROVIDER (Gemini key rotation, Groq fallback)")
    
    from rag.providers import call_generate, default_provider, AVAILABLE_PROVIDERS
    
    # Check configuration
    provider = default_provider()
    test_result("Default provider", True, f"Using: {provider}")
    
    # Check available providers
    for name, config in AVAILABLE_PROVIDERS.items():
        test_result(f"Provider config: {name}", True, config['label'])
    
    # Test simple generation
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'test successful' and nothing else."}
    ]
    
    try:
        result = call_generate(
            messages,
            provider=None,  # Use default
            max_tokens=50,
            temperature=0.3,
            reasoning_effort="low"
        )
        
        passed = len(result) > 0
        test_result(
            f"LLM generation ({provider})",
            passed,
            f"Response: '{result[:60]}...'" if len(result) > 60 else f"Response: '{result}'"
        )
    
    except Exception as e:
        error_msg = str(e)
        if "rate" in error_msg.lower():
            test_result(
                f"LLM generation ({provider})",
                False,
                f"{YELLOW}Rate limited - this is expected if quota exhausted{RESET}"
            )
        else:
            test_result(f"LLM generation ({provider})", False, f"Error: {error_msg}")

# ============================================================================
# 6. END-TO-END CHAT TEST
# ============================================================================

def test_end_to_end():
    test_section("6. END-TO-END CHAT (Full Pipeline)")
    
    # Import the main chat function
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # We'll test the pipeline components individually since we can't easily
    # test the FastAPI endpoint without starting the server
    
    from rag.classify import classify_query
    from rag.rewrite import translate_query_to_english, rewrite_query
    from rag.retrieve import Retriever
    
    # Load retriever
    try:
        retriever = Retriever()  # Uses default paths
    except Exception as e:
        test_result("Retriever initialization", False, f"Error: {e}")
        return
    
    test_cases = [
        ("kya muth maar sakta hoon", "masturbation", "Hindi query"),
        ("what breaks wudu", "wudu", "English query"),
        ("mane kem khbr pade baaligh chu", "puberty", "Gujarati query"),
    ]
    
    for query, expected_keyword, description in test_cases:
        print(f"\n{YELLOW}Testing: {description} - '{query}'{RESET}")
        
        # Step 1: Classify
        intent = classify_query(query)
        print(f"  1. Classification: {intent.name}")
        
        # Step 2: Translate
        translated = translate_query_to_english(query)
        print(f"  2. Translation: '{translated}'")
        
        # Step 3: Rewrite (no history for this test)
        rewritten, was_rewritten = rewrite_query(translated, [])
        print(f"  3. Rewrite: {'Yes' if was_rewritten else 'No'} - '{rewritten}'")
        
        # Step 4: Retrieve
        try:
            hits = retriever.search(rewritten, k=5, mode="hybrid")
            print(f"  4. Retrieval: {len(hits)} results")
            
            if hits:
                found = any(expected_keyword.lower() in hit.text.lower() for hit in hits)
                print(f"     -> Keyword '{expected_keyword}' {'FOUND' if found else 'NOT FOUND'}")
                print(f"     -> Top source: {hits[0].citation}")
                
                test_result(
                    f"Pipeline: {description}",
                    found and len(hits) > 0,
                    f"Retrieved {len(hits)} chunks with correct keyword"
                )
            else:
                test_result(f"Pipeline: {description}", False, "No results retrieved")
        
        except Exception as e:
            test_result(f"Pipeline: {description}", False, f"Retrieval error: {e}")

# ============================================================================
# 7. BOOKMARKS & UI FEATURES
# ============================================================================

def test_features():
    test_section("7. FEATURE AVAILABILITY CHECK")
    
    # Check if key files exist
    files_to_check = [
        ("frontend/components/saved-rulings.tsx", "Bookmarks UI"),
        ("frontend/components/message-actions.tsx", "Copy/Share/Bookmark actions"),
        ("frontend/components/source-cards.tsx", "Source citations display"),
        ("frontend/public/sitemap.xml", "SEO sitemap"),
        ("frontend/public/robots.txt", "SEO robots.txt"),
        ("frontend/public/llms.txt", "AI agent discovery"),
        ("rag/classify.py", "Query classifier"),
        ("rag/rewrite.py", "Query rewriter + translator"),
        ("rag/retrieve.py", "Retriever (BM25 + FAISS)"),
        ("rag/providers.py", "LLM provider with fallback"),
    ]
    
    for filepath, description in files_to_check:
        exists = os.path.exists(filepath)
        test_result(description, exists, filepath if exists else f"Missing: {filepath}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    print(f"\n{BLUE}{'='*70}")
    print(f"  SISTANI JURISPRUDENCE ASSISTANT - SYSTEM TEST")
    print(f"{'='*70}{RESET}")
    
    try:
        test_translation()
        test_classification()
        test_rewriting()
        test_retrieval()
        test_providers()
        test_end_to_end()
        test_features()
        
        print(f"\n{GREEN}{'='*70}")
        print(f"  TEST SUITE COMPLETED")
        print(f"{'='*70}{RESET}\n")
    
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}\n")
    except Exception as e:
        print(f"\n{RED}Fatal error: {e}{RESET}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
