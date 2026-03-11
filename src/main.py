import os
from pathlib import Path
from scrape_website_data import scrape_website_data
from build_chunks import build_chunks_jsonl
from embeddings import build_faiss_index
from llm_answer import answer_question


ROOT = Path(__file__).resolve().parents[1]

RAW_SCRAPED_DIR = ROOT / "data" / "raw" / "scraped"
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
INDEX_DIR = ROOT / "data" / "vector_store" / "faiss_aha"
INDEX_FAISS = INDEX_DIR / "index.faiss"
INDEX_PKL = INDEX_DIR / "index.pkl"


def has_scraped_html() -> bool:
    return RAW_SCRAPED_DIR.exists() and any(RAW_SCRAPED_DIR.glob("*.html"))


def has_faiss_index() -> bool:
    return INDEX_FAISS.exists() and INDEX_PKL.exists()


def ensure_pipeline() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY. Set it in env or in a .env file.")

    # SCRAPE
    if not has_scraped_html():
        print("[STEP] Scraping HTML...")
        scrape_website_data(headed=True)
        print("[OK] HTML scraped.")
    else:
        print("[SKIP] HTML already exists.")

    # BUILD CHUNKS
    if not CHUNKS_PATH.exists():
        print("[STEP] Building chunks.jsonl...")
        build_chunks_jsonl()
        print("[OK] chunks.jsonl built.")
    else:
        print("[SKIP] chunks.jsonl already exists.")

    # BUILD INDEX
    if not has_faiss_index():
        print("[STEP] Building FAISS index...")
        build_faiss_index()
        print("[OK] FAISS index built.")
    else:
        print("[SKIP] FAISS index already exists.")


def main() -> None:
    ensure_pipeline()

    print("\nReady. Ask a question (empty = exit):")
    while True:
        question = input("> ").strip()
        if not question:
            break

        print("\nSearching relevant passages...")
        print("Generating answer...\n")

        answer, used_docs = answer_question(question, top_k=12)

        print(answer.strip())

        print("\nSOURCES USED:")
        for i, doc in enumerate(used_docs, start=1):
            url = doc.metadata.get("source_url") or ""
            section = doc.metadata.get("section") or ""
            subsection = doc.metadata.get("subsection")

            if subsection:
                print(f"[{i}] {url} | {section} | {subsection}")
            else:
                print(f"[{i}] {url} | {section}")

        print("\nAsk another question (empty = exit):")


if __name__ == "__main__":
    main()