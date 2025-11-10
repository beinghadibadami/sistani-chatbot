# sistani_rag_simple.py
"""
RAG chatbot for Sistani PDFs — No LangChain.
Steps:
  1) Put all PDFs in ./data/
  2) Run: python sistani_rag_simple.py --build  (to embed)
  3) Run: python sistani_rag_simple.py  (to chat)
"""

import os
import glob
import argparse
import pickle
from pathlib import Path
from tqdm.auto import tqdm

from groq import Groq

import PyPDF2
import faiss
import numpy as np
import requests

from dotenv import load_dotenv

load_dotenv()


# ---------- CONFIG ----------
DATA_DIR = "./data"
INDEX_FILE = "sistani_faiss_with_qna.index"
CHUNKS_FILE = "sistani_new_chunks.pkl"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 5
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = "openai/gpt-oss-120b"  # or any available Groq model
# Hugging Face Inference API (feature-extraction) for embeddings
HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://router.huggingface.co/hf-inference/models/BAAI/bge-small-en/pipeline/feature-extraction"
# ----------------------------

# ---------------- EMBEDDING VIA HF INFERENCE API ----------------
def _hf_embed_single(text: str) -> np.ndarray:
    """
    Get an embedding vector for a single text using HF Inference API.
    Handles both token-level outputs (applies mean pooling) and single-vector outputs.
    """
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN is not set in environment.")

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
    }
    resp = requests.post(HF_API_URL, headers=headers, json={"inputs": text})
    resp.raise_for_status()
    data = resp.json()

    # Possible shapes:
    # - [hidden] -> already pooled sentence embedding
    # - [[hidden], [hidden], ...] -> per-token embeddings, need mean-pooling
    if isinstance(data, list):
        if len(data) == 0:
            raise ValueError("Empty embedding returned from HF Inference API.")
        if isinstance(data[0], list):
            # token-level -> mean pool
            arr = np.array(data, dtype=np.float32)
            return arr.mean(axis=0)
        else:
            # already a vector
            return np.array(data, dtype=np.float32)
    else:
        # Unexpected shape
        raise ValueError(f"Unexpected embedding response format: {type(data)}")

def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Embed a list of texts. Returns a 2D numpy array (n_texts, dim).
    Sequential calls to keep API simple and robust.
    """
    vectors: list[np.ndarray] = []
    for t in tqdm(texts, desc="Embedding", leave=False):
        vectors.append(_hf_embed_single(t))
    # Ensure consistent dimension
    dims = {v.shape[0] for v in vectors}
    if len(dims) != 1:
        raise ValueError(f"Inconsistent embedding dims returned: {dims}")
    return np.stack(vectors, axis=0)
# ----------------------------

# ---------------- LOADING & CHUNKING ----------------
def load_pdf_text(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks

def build_embeddings():
    print("🔹 Preparing to build embeddings with Hugging Face Inference API...")

    all_chunks = []
    file_sources = []

    print(f"📄 Reading PDFs from {DATA_DIR} ...")
    for pdf_file in sorted(glob.glob(os.path.join(DATA_DIR, "*.pdf"))):
        print(f" - {Path(pdf_file).name}")
        pdf_text = load_pdf_text(pdf_file)
        chunks = chunk_text(pdf_text)
        all_chunks.extend(chunks)
        file_sources.extend([Path(pdf_file).name] * len(chunks))

    print(f"Total chunks: {len(all_chunks)}")

    print("🧠 Embedding chunks via HF Inference API...")
    embeddings = embed_texts(all_chunks)

    print("💾 Building FAISS index...")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, INDEX_FILE)
    with open(CHUNKS_FILE, "wb") as f:
        pickle.dump((all_chunks, file_sources), f)

    print("✅ Index + chunks saved.")

# ---------------- RETRIEVAL + LLM ----------------

def load_index():
    index = faiss.read_index(INDEX_FILE)
    with open(CHUNKS_FILE, "rb") as f:
        chunks, sources = pickle.load(f)
    # No local model; use HF API for embeddings
    return index, chunks, sources

def search_similar(query, index, chunks, sources, k=TOP_K):
    q_emb = embed_texts([query]).astype(np.float32)
    D, I = index.search(q_emb, k)
    results = []
    for idx in I[0]:
        results.append((chunks[idx], sources[idx]))
    return results

def generate_answer(context_chunks, question):
    context_text = "\n\n".join([f"Source: {src}\n{chunk}" for chunk, src in context_chunks])

    system_prompt = f"""
You are an Islamic scholar chatbot specializing in the rulings and teachings of Ayatullah al-Sistani.
Answer the question below using the provided context. Be respectful and scholarly.
If you cannot find the answer in the context, use your own knowledge about that topic and answer ONLY if you know , do not invent anything 
& when asked any question other than islamic like any general world question, say:
"I could not find any explicit ruling or reference in the available material." or "i cannot help you with that question please ask any relevant question" or something like that.
At the end, cite the source filenames(if used own knowledge then use those source names).

Context:
{context_text}

Question:
{question}

Answer:
"""

    client = Groq(api_key=GROQ_API_KEY)
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
        {
            "role": "user",
            "content": system_prompt
        }
        ],
        temperature=0,
        max_completion_tokens=8192,
        top_p=1,
        stream=False,
        stop=None
    )

    return completion.choices[0].message.content

# ---------------- CLI ----------------

# def interactive_cli():
#     index, chunks, sources, model = load_index()
#     print("\n🕌 Sistani RAG Chatbot ready. Type your questions (or 'exit').\n")
#     while True:
#         q = input("You: ").strip()
#         if q.lower() in ["exit", "quit"]:
#             break

#         top_chunks = search_similar(q, index, chunks, sources, model)
#         answer = generate_answer(top_chunks, q)
#         print("\nAssistant:\n")
#         print(answer)
#         print("\n---\n")

# ---------------- MAIN ----------------
# def main():
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--build", action="store_true", help="Build FAISS index")
    # args = parser.parse_args()

    # if args.build:
    #     build_embeddings()
    # else:
    #     if not os.path.exists(INDEX_FILE):
    #         print("❌ No index found. Run with --build first.")
    #         return
        # interactive_cli()

# if __name__ == "__main__":
#     main()
