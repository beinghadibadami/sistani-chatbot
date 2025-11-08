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
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import requests

from dotenv import load_dotenv

load_dotenv()


# ---------- CONFIG ----------
DATA_DIR = "./data"
INDEX_FILE = "sistani_faiss_with_qna.index"
CHUNKS_FILE = "sistani_new_chunks.pkl"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 5
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = "openai/gpt-oss-120b"  # or any available Groq model
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
    print("🔹 Loading embedding model...")
    model = SentenceTransformer(EMBED_MODEL)

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

    print("🧠 Embedding chunks...")
    embeddings = model.encode(all_chunks, show_progress_bar=True, convert_to_numpy=True)

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
    model = SentenceTransformer(EMBED_MODEL)
    return index, chunks, sources, model

def search_similar(query, index, chunks, sources, model, k=TOP_K):
    q_emb = model.encode([query], convert_to_numpy=True)
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
