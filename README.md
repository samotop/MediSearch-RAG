# Mini-MediSearch (RAG)

This project is a small “MediSearch-like” system in Python.

It:
1) scrapes HTML from the provided AHA sources (Playwright),
2) parses the HTML into structured blocks and creates chunks,
3) builds a FAISS vector index (OpenAI embeddings),
4) answers user questions using only retrieved chunks and provides inline citations like **[1]**, **[2]**, ...

## Sources
The system is built from these three sources:
- https://www.ahajournals.org/doi/10.1161/HYP.0000000000000238
- https://www.ahajournals.org/doi/10.1161/CIRCRESAHA.121.318083
- https://www.ahajournals.org/doi/10.1161/CIR.0000000000001341

## Requirements
- Python 3.11 recommended
- An OpenAI API key

## Important (Python version)
Please use Python **3.11** (recommended) or 3.12.
If you have multiple Pythons installed, make sure your virtual environment uses Python 3.11.
Using Python 3.13 may cause Playwright/greenlet import errors.


## Setup

### 1) Create and activate a virtual environment

Windows (PowerShell):
```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
```

macOS/Linux:
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Install Playwright browsers
Basic installation (all browsers):
```bash
python -m playwright install
```

Optionally only Chromium (useful for CI):
```bash
python -m playwright install chromium
```

### 4) Configure API key
Create (or open) a `.env` file in the project root and paste your API key:
```env
OPENAI_API_KEY="your_api_key_here"
```

Alternatively, you can set the key only for the current shell session:
- Windows (PowerShell):
  ```powershell
  $env:OPENAI_API_KEY = "your_api_key_here"
  ```
- macOS/Linux (bash/zsh):
  ```bash
  export OPENAI_API_KEY="your_api_key_here"
  ```

## Run
Run the main entrypoint:

```bash
python src/main.py
```

On the first run, it will automatically:
- scrape the HTML into `data/raw/scraped/`
- build chunks into `data/processed/chunks.jsonl`
- build the FAISS index into `data/vector_store/faiss_aha/`

On subsequent runs, it reuses cached files and only starts the interactive Q&A loop.

### Embeddings model
This project uses the OpenAI embeddings model `text-embedding-3-small` (see `src/embeddings.py`).
Ensure your account has access and sufficient quota for this model.

## Usage
After startup you can type a question, for example:
- What lifestyle changes are recommended to lower blood pressure, and what evidence is cited?
- What are the key recommendations for managing elevated inpatient blood pressure?

The answer includes inline citations like **[1]**, **[2]**, etc., and the terminal prints the mapping of sources used.

## Refresh / Rebuild cache
If you want to force a fresh scrape and re-index, delete the following artifacts and then run `python src/main.py` again:
- `data/raw/scraped/*.html`
- `data/processed/chunks.jsonl`
- `data/vector_store/faiss_aha/` (entire directory)

## Project structure (key files)
- `src/main.py` – orchestrates the full pipeline and runs interactive Q&A
- `src/scrape_website_data.py` – Playwright scraping into `data/raw/scraped/`
- `src/build_chunks.py` – HTML -> blocks -> `chunks.jsonl` (includes Abstract)
- `src/chunking.py` – chunking logic (token-based chunk limits + overlap)
- `src/embeddings.py` – builds FAISS index from `chunks.jsonl`
- `src/llm_answer.py` – retrieval + prompt assembly + LLM answer with citations
- `data/` – cached HTML, chunks, and FAISS index

## Notes
- The system is instructed to answer using **only** retrieved SOURCES.
- If the SOURCES do not contain enough information, it should say so explicitly.
- The first run can take longer due to scraping and indexing.
- On the first run, the scraper may take longer on some articles.  
  This is expected: the Playwright script includes small random delays and basic “human-like” interactions 
  (mouse moves/scrolling) to reduce the chance of being blocked.  

### Playwright behavior
- The scraper runs in a visible browser window (headed mode) by default (`scrape_website_data(headed=True)`).
- If you prefer headless mode, you can change the call in code to `scrape_website_data(headed=False)` (see `src/scrape_website_data.py`).

## Troubleshooting
- ImportError (greenlet/Playwright) on Python 3.13: please use Python 3.11 or 3.12.
- Missing OPENAI_API_KEY: set it in `.env` or export it in your shell (see Setup → Configure API key).
- Playwright cannot find browsers: run `python -m playwright install` (or `python -m playwright install chromium`).
- Scraping timeouts or occasional blocking: try again later. The script uses small random delays and human-like interactions to lower blocking risk; temporary site issues or network conditions may still cause timeouts.