"""Clause Module - finds important clauses with keywords, then the LLM explains each in simple words.

Example: sentence with "terminate" + "notice" -> Termination clause
"""
import re

from llm import ask_json

CLAUSES = {
    "Confidentiality": ["confidential", "non-disclosure", "not disclose"],
    "Payment": ["salary", "rent", "payment", "fee", "rs.", "deposit", "invoice"],
    "Termination": ["terminate", "termination", "notice"],
    "Liability": ["liable", "liability", "damages", "indemn"],
    "Intellectual Property": ["intellectual property", "ownership", "licence", "license", "assigns"],
    "Dispute Resolution": ["arbitration", "dispute", "jurisdiction"],
    "Governing Law": ["governed by", "governing law", "laws of"],
    "Non-Solicitation / Non-Compete": ["solicit", "non-compete", "compete"],
}


def find(text):
    # split into sentences, but not after "Rs." ; skip ALL-CAPS headings
    sentences = [s.strip() for s in re.split(r"(?<=[.;])(?<!Rs\.)\s+|\n", text)]
    sentences = [s for s in sentences if len(s) > 25 and not s.isupper()]
    found = {}
    for name, words in CLAUSES.items():
        scored = [(sum(w in s.lower() for w in words), s) for s in sentences]
        hits = [s for n, s in sorted(scored, key=lambda x: -x[0]) if n > 0]
        if hits:
            found[name] = hits[:2]
    return found


def explain(found, doc_type):
    if not found:
        return []
    listing = "\n".join(f"{k}: {' '.join(v)}" for k, v in found.items())
    d = ask_json(f"These clauses come from a {doc_type}:\n{listing}\n\n"
                 "For each clause name, explain it in one simple sentence and rate its importance for the reader.\n"
                 'Return JSON: {"clauses": [{"name": "...", "explanation": "...", "importance": "High|Medium|Low"}]}',
                 default={}) or {}
    llm = {c.get("name"): c for c in d.get("clauses", []) if isinstance(c, dict)}
    return [{"name": k, "text": v[0], "explanation": llm.get(k, {}).get("explanation", ""),
             "importance": llm.get(k, {}).get("importance", "Medium")} for k, v in found.items()]
