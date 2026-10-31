"""Save Module - saves the structured legal analysis report as a .txt file."""
import os
import re
from datetime import datetime

FOLDER = os.path.join(os.path.dirname(__file__), "..", "saved")


def save(d):
    a = d.get("analysis", {})
    lines = ["LEGAL DOCUMENT ANALYSIS", "-" * 50, f"Generated : {datetime.now():%d-%m-%Y %H:%M:%S}",
             "Prepared by: Monick S (URK23CS1167)", f"Document  : {d.get('file_name', 'Pasted text')}",
             f"Document Type: {d.get('doc_type', '')}", "",
             "Parties:", *[f"  - {p}" for p in a.get("parties", [])],
             f"\nPurpose: {a.get('purpose', '')}", f"Duration: {a.get('duration', '')}",
             "\nPayment:", *[f"  - {p}" for p in a.get("payment_terms", [])],
             "\nKey Obligations:", *[f"  - {o.get('party', '')}: {o.get('obligation', '')}" for o in a.get("obligations", [])],
             "\nTermination:", *[f"  - {t}" for t in a.get("termination", [])],
             f"\nConfidentiality: {a.get('confidentiality', '')}", f"Governing Law: {a.get('governing_law', '')}",
             "\nImportant Dates:", *[f"  - {x.get('date')}: {x.get('event')}" for x in a.get("important_dates", [])],
             "\nPotentially Important Clauses:", *[f"  - {c['name']} ({c.get('importance', '')}): {c.get('explanation', '')}"
                                                   for c in d.get("clauses", [])],
             "\nSummary:", d.get("summary", ""), "",
             "Disclaimer: AI-generated analysis for understanding only. Not legal advice."]
    os.makedirs(FOLDER, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", d.get("doc_type", "document").lower()).strip("_")
    path = os.path.join(FOLDER, f"analysis_{slug}_{datetime.now():%Y%m%d_%H%M%S}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return {"file": os.path.abspath(path), "size": os.path.getsize(path)}
