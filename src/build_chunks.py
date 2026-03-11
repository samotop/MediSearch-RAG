from pathlib import Path
from bs4 import BeautifulSoup
import json
from chunking import make_chunks_from_blocks

ROOT = Path(__file__).resolve().parents[1]

SOURCES = [
    {"source_id": 1, "url": "https://www.ahajournals.org/doi/10.1161/HYP.0000000000000238", "file": "HYP.0000000000000238.html"},
    {"source_id": 2, "url": "https://www.ahajournals.org/doi/10.1161/CIRCRESAHA.121.318083", "file": "CIRCRESAHA.121.318083.html"},
    {"source_id": 3, "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001341", "file": "CIR.0000000000001341.html"},
]


def build_chunks_jsonl():
    all_blocks = []

    for src in SOURCES:
        path = ROOT / "data" / "raw" / "scraped" / src["file"]

        html = path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "lxml")

        source_id = src["source_id"]
        source_url = src["url"]

        h1 = soup.select_one("#pb-page-content main article header h1")
        doc_title = h1.get_text(strip=True) if h1 else "Unknown title"

        doc_blocks = []

        abstract_container = soup.select_one("#abstract > div")
        if abstract_container is not None:
            doc_blocks.append({
                "type": "heading_h2",
                "section": "Abstract",
                "subsection": None,
                "text": "Abstract",
                "source_id": source_id,
                "source_url": source_url,
                "doc_title": doc_title,
            })

            abs_paras = abstract_container.select('div[role="paragraph"]')
            if abs_paras:
                for el in abs_paras:
                    t = el.get_text(strip=True)
                    if t:
                        doc_blocks.append({
                            "type": "paragraph",
                            "section": "Abstract",
                            "subsection": None,
                            "text": t,
                            "source_id": source_id,
                            "source_url": source_url,
                            "doc_title": doc_title,
                        })
            else:
                t = abstract_container.get_text(strip=True)
                if t:
                    doc_blocks.append({
                        "type": "paragraph",
                        "section": "Abstract",
                        "subsection": None,
                        "text": t,
                        "source_id": source_id,
                        "source_url": source_url,
                        "doc_title": doc_title,
                    })

        container = soup.select_one("#bodymatter .core-container")
        if container is None:
            for b in doc_blocks:
                b["missing_body"] = True
            print(f"[WARN] Missing container for source_id={source_id} url={source_url}")
            continue

        current_h2 = "PREAMBLE"
        current_h3 = None

        for el in container.find_all(["h2", "h3", "div"], recursive=True):

            if el.name == "h2":
                current_h2 = el.get_text(strip=True)
                current_h3 = None
                doc_blocks.append({
                    "type": "heading_h2",
                    "section": current_h2,
                    "subsection": None,
                    "text": current_h2,
                    "source_id": source_id,
                    "source_url": source_url,
                    "doc_title": doc_title,
                })
                continue

            if el.name == "h3":
                current_h3 = el.get_text(strip=True)
                doc_blocks.append({
                    "type": "heading_h3",
                    "section": current_h2,
                    "subsection": current_h3,
                    "text": current_h3,
                    "source_id": source_id,
                    "source_url": source_url,
                    "doc_title": doc_title,
                })
                continue

            if el.name == "div" and el.get("role") == "paragraph":
                if el.find_parent("figure") is not None:
                    continue

                text = el.get_text(strip=True)
                if text:
                    doc_blocks.append({
                        "type": "paragraph",
                        "section": current_h2,
                        "subsection": current_h3,
                        "text": text,
                        "source_id": source_id,
                        "source_url": source_url,
                        "doc_title": doc_title,
                    })

        print(f"blocks (source_id={source_id}):", len(doc_blocks))
        all_blocks.extend(doc_blocks)

    print("ALL blocks:", len(all_blocks))

    chunks = make_chunks_from_blocks(all_blocks, chunk_token_limit=280, overlap_paragraphs=1)

    out_path = ROOT / "data" / "processed" / "chunks.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", ) as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

    print("Saved chunks to:", out_path)

    # quick check
    from collections import Counter
    print("chunk source_id counts:", Counter(ch["source_id"] for ch in chunks))

    return out_path


if __name__ == "__main__":
    build_chunks_jsonl()