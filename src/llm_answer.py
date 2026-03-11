import os
from pathlib import Path
import tiktoken
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
load_dotenv()


# Paths
ROOT = Path(__file__).resolve().parents[1]
INDEX_DIR = ROOT / "data" / "vector_store" / "faiss_aha"

MODEL = "gpt-4o-mini"
MAX_CONTEXT_TOKENS = 1600
RELEVANCE_SCORE_THRESHOLD = 1.5


def get_encoder(model=MODEL):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text, enc):
    return len(enc.encode(text))


def load_vectorstore():
    embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    return FAISS.load_local(str(INDEX_DIR), embedder, allow_dangerous_deserialization=True)


def retrieve(db, query, k=12):
    return db.similarity_search_with_score(query, k=k)


def build_context_with_budget(ranked, question, model=MODEL, max_tokens=MAX_CONTEXT_TOKENS):

    enc = get_encoder(model)

    system_prompt = (
        "You are a medical QA assistant.\n"
        "Answer the user's question using ONLY the provided SOURCES.\n"
        "Cite sources inline using [1], [2], ... exactly matching the source numbers.\n"
        "Every sentence with a factual claim MUST have at least one citation.\n"
        "Do NOT mention specific drugs, doses, or thresholds unless they appear in the SOURCES.\n"
        "If the SOURCES do not contain enough information, say so explicitly.\n"
        "Do NOT use outside knowledge.\n"
    )

    header = "SOURCES:\n"
    footer = f"\nQUESTION:\n{question}\n\nANSWER:\n"

    base_prompt = system_prompt + "\n" + header + footer
    base_tokens = count_tokens(base_prompt, enc)

    used_docs = []
    source_lines = []

    reserve = 50
    budget = max_tokens - base_tokens - reserve
    if budget <= 0:
        return header + footer, []

    for idx, (doc, score) in enumerate(ranked, start=1):
        url = doc.metadata.get("source_url", "")
        section = doc.metadata.get("section", "")
        subsection = doc.metadata.get("subsection", None)
        title = doc.metadata.get("doc_title", "")

        loc = section if not subsection else f"{section} > {subsection}"
        label = f"[{idx}] {title} | {loc} | {url}".strip()

        block = f"{label}\n{doc.page_content.strip()}\n\n"
        block_tokens = count_tokens(block, enc)

        if block_tokens <= budget:
            source_lines.append(block)
            used_docs.append(doc)
            budget -= block_tokens
        else:
            break

    context_text = header + "".join(source_lines) + footer
    return context_text, used_docs


def answer_question(question: str, top_k: int = 12):
    db = load_vectorstore()

    ranked = retrieve(db, question, k=top_k)

    # RELEVANCE GATE
    if not ranked:
        return "Not enough information in the provided sources.", []

    best_score = ranked[0][1]
    if best_score > RELEVANCE_SCORE_THRESHOLD:
        return "Not enough information in the provided sources.", []

    context_text, used_docs = build_context_with_budget(ranked, question)

    llm = ChatOpenAI(model=MODEL, temperature=0)

    messages = [
        SystemMessage(content="You must follow the citation rules. Every factual sentence must have [n] citations."),
        HumanMessage(content=context_text),
    ]

    result = llm.invoke(messages)
    answer = result.content
    return answer, used_docs


def main():
    question = "What does the AHA statement say about alcohol consumption and blood pressure changes over time?"

    answer, used_docs = answer_question(question, top_k=12)

    print("\n" + "=" * 80)
    print(answer.strip())
    print("\n" + "=" * 80)
    print("\nSOURCES USED:")
    for i, doc in enumerate(used_docs, start=1):
        url = doc.metadata.get("source_url") or ""
        section = doc.metadata.get("section") or ""
        subsection = doc.metadata.get("subsection")

        if subsection:
            print(f"[{i}] {url} | {section} | {subsection}")
        else:
            print(f"[{i}] {url} | {section}")


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY. Set it in env or in a .env file.")
    main()
