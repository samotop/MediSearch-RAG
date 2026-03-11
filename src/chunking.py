import tiktoken


def get_encoder(model="gpt-4o-mini"):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text, enc) -> int:
    return len(enc.encode(text))


def make_chunks_from_blocks(blocks, model="gpt-4o-mini", chunk_token_limit=280,
                            overlap_paragraphs=1):
    enc = get_encoder(model)

    chunks = []
    buffer_texts = []
    buffer_blocks = []
    buffer_tokens = 0

    current_meta = None  # (source_id, section, subsection)

    #Boolean: shows if overlap paragraph was left in buffer after flush
    just_left_overlap = False

    def flush(limit_flush=False):
        nonlocal buffer_texts, buffer_blocks, buffer_tokens, just_left_overlap

        if not buffer_texts:
            return

        first = buffer_blocks[0]
        chunk_text = "\n".join(buffer_texts).strip()

        chunks.append({
            "chunk_id": f"{first['source_id']}:{len(chunks) + 1}",
            "text": chunk_text,
            "source_id": first["source_id"],
            "source_url": first.get("source_url"),
            "doc_title": first.get("doc_title"),
            "section": first.get("section"),
            "subsection": first.get("subsection"),
            "token_count": count_tokens(chunk_text, enc),
        })

        if limit_flush and overlap_paragraphs > 0 and len(buffer_texts) > overlap_paragraphs:
            # ponecháme posledné N odsekov ako overlap
            buffer_texts = buffer_texts[-overlap_paragraphs:]
            buffer_blocks = buffer_blocks[-overlap_paragraphs:]
            just_left_overlap = True  # v buffri je len overlap (kým nepribudne nový odstavec)
        else:
            buffer_texts, buffer_blocks = [], []
            just_left_overlap = False

        buffer_tokens = count_tokens("\n".join(buffer_texts), enc) if buffer_texts else 0

    for b in blocks:
        if b.get("type") != "paragraph":
            continue

        meta = (b["source_id"], b["section"], b.get("subsection"))
        if current_meta is None:
            current_meta = meta

        # Zmena sekcie/podsekcie: flush bez overlapu
        if meta != current_meta and buffer_texts:
            if just_left_overlap:
                buffer_texts = []
                buffer_blocks = []
                buffer_tokens = 0
                just_left_overlap = False
                current_meta = meta
            else:
                flush(limit_flush=False)
                current_meta = meta

        text = b["text"].strip()
        if not text:
            continue

        t_tokens = count_tokens(text, enc)

        # Prípad: jeden odsek je dlhší ako limit -> "single long paragraph"
        if t_tokens > chunk_token_limit:
            # 1) Nechceme vytvárať medzichunk len z overlapa.
            #    Ak v buffri je len ponechaný overlap (a nič nové), neflushujeme ho samostatne.
            if buffer_texts and not just_left_overlap:
                # v buffri je reálny obsah (nie iba overlap po limit-flushi) -> uzavri ho bez overlapa
                flush(limit_flush=False)

            # 2) Ulož single-long paragraf ako samostatný chunk
            buffer_texts = [text]
            buffer_blocks = [b]
            buffer_tokens = t_tokens
            flush(limit_flush=False)  # typicky sa po 1 odseku overlap neponechá (podľa podmienky vo flush)

            current_meta = meta
            just_left_overlap = False  # práve sme uložili single-long chunk
            continue

        # Bežný prípad: nový odsek by prešvihol limit s aktuálnym buffrom -> limit flush s overlapom
        if buffer_tokens + t_tokens > chunk_token_limit and buffer_texts:
            flush(limit_flush=True)
            # Po tomto kroku môže zostať v buffri iba overlap; to si pamätáme v just_left_overlap (nastavené vo flush)

        # Pridáme nový odsek do buffra (tým pádom už overlap nie je "sám")
        buffer_texts.append(text)
        buffer_blocks.append(b)
        buffer_tokens += t_tokens
        just_left_overlap = False

    # Záver – zabránenie vytvorenia chunku iba z overlapa na konci
    # ADDED: Finálna kontrola, aby sa neuložil samostatný "overlap-only" chunk
    if buffer_texts:
        if just_left_overlap:
            # ADDED: Ak je v buffri iba overlap, na konci ho zahodíme a neflushujeme
            buffer_texts = []
            buffer_blocks = []
            buffer_tokens = 0
            just_left_overlap = False
        else:
            flush(limit_flush=False)

    return chunks
