"""Prompt Module - builds the structured prompt: Role, Task, Information to extract, Constraint, Output format."""

FIELDS = ["parties", "purpose", "duration", "payment_terms", "obligations", "termination", "confidentiality",
          "governing_law", "important_dates"]


def chunk_prompt(chunk, i, n, doc_type):
    return (
        "ROLE: You are a legal document analysis assistant.\n"
        f"TASK: Read part {i} of {n} of a {doc_type} and extract key information.\n"
        "CONSTRAINT: Use ONLY information present in this text. Do not invent facts. Use [] or \"\" if not present.\n"
        "OUTPUT FORMAT: JSON with keys:\n"
        '{"parties": ["..."], "purpose": "", "duration": "", "payment_terms": ["..."], '
        '"obligations": [{"party": "...", "obligation": "..."}], "termination": ["..."], '
        '"confidentiality": "", "governing_law": "", "important_dates": [{"date": "...", "event": "..."}]}\n\n'
        f"TEXT:\n{chunk}"
    )


def summary_prompt(doc_type, notes, analysis_type):
    focus = {"Summary": "a clear plain-English summary",
             "Clauses": "a summary that focuses on the key clauses and risks",
             "Obligations": "a summary that focuses on what each party must do",
             "Complete": "a complete plain-English summary"}[analysis_type]
    return (
        "ROLE: You are a legal document analysis assistant explaining contracts to non-lawyers.\n"
        f"TASK: Using the extracted notes from a {doc_type}, write {focus} in 5-7 sentences, "
        "then a line 'Points to check before signing:' with 3 short bullets.\n"
        "CONSTRAINT: Use only these notes. Do not give legal advice.\n\n"
        f"NOTES:\n{notes}"
    )
