import json
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()


ROOT = Path(__file__).resolve().parents[1]

CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
INDEX_DIR = ROOT / "data" / "vector_store" / "faiss_aha"


def build_faiss_index():
    #load chunks (JSONL)
    chunks = []
    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    print("Loaded chunks:", len(chunks), "from", CHUNKS_PATH)

    embedder = OpenAIEmbeddings(model="text-embedding-3-small")

    docs = []
    for ch in chunks:
        doc = Document(
            page_content=ch["text"],
            metadata={
                "chunk_id": ch["chunk_id"],
                "source_id": ch["source_id"],
                "source_url": ch["source_url"],
                "section": ch["section"],
                "subsection": ch["subsection"],
            },
        )
        docs.append(doc)

    db = FAISS.from_documents(docs, embedder)
    db.save_local(str(INDEX_DIR))
    print("Saved index to:", INDEX_DIR)
    return INDEX_DIR


if __name__ == "__main__":
    build_faiss_index()
