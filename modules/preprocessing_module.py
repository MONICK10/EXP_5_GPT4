"""Preprocessing Module - cleans the text and finds basic facts with rules (regex).

Example: "Rs. 50,000 per month"  -> amount found
         "01-07-2026"            -> date found
"""
import re

DOC_TYPES = {
    "Non-Disclosure Agreement": ["non-disclosure", "confidential information", "nda"],
    "Employment Agreement": ["employment agreement", "employee", "employer"],
    "Rental Agreement": ["rental agreement", "tenant", "landlord", "owner", "rent"],
    "Service Agreement": ["service agreement", "service provider", "services"],
    "Loan Agreement": ["loan agreement", "borrower", "lender"],
    "Sales Agreement": ["sale agreement", "purchaser", "seller", "buyer"],
}


def clean(text):
    before = len(text)
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)          # many spaces -> one space
    text = re.sub(r"\n\s*\n+", "\n\n", text)     # many blank lines -> one
    text = re.sub(r"(?im)^\s*page \d+( of \d+)?\s*$", "", text)  # page numbers
    text = text.strip()
    return text, before - len(text)


def detect_type(text):
    t = text.lower()
    scores = {k: sum(t.count(w) for w in words) for k, words in DOC_TYPES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Other"


def rule_facts(text):
    dates = re.findall(r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b", text)
    amounts = re.findall(r"(?:Rs\.?|INR|₹)\s?[\d,]+(?:\.\d+)?", text)
    durations = re.findall(r"\b(?:\w+\s)?\(\d+\)\s(?:days?|months?|years?)", text)
    return {"dates": list(dict.fromkeys(dates)), "amounts": list(dict.fromkeys(amounts)),
            "durations": list(dict.fromkeys(durations))}


def preprocess(raw):
    text, removed = clean(raw)
    words = len(text.split())
    return {"text": text, "chars": len(text), "words": words, "pages": max(1, round(words / 400)),
            "removed_chars": removed, "doc_type": detect_type(text), "facts": rule_facts(text)}
