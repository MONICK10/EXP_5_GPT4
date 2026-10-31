"""Chunking Module - splits a long document into smaller parts so the LLM can read each one.

Example: 4500-character contract with max 2500 per chunk -> 2 chunks (split at paragraph breaks)
"""


def chunk(text, max_chars=2500):
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) > max_chars:
            chunks.append(cur)
            cur = ""
        cur = (cur + "\n\n" + p).strip()
    if cur:
        chunks.append(cur)
    return chunks
