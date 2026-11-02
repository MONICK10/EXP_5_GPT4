"""Prompt Module - builds the structured prompt: Role, Task, Information to extract, Constraint, Output format."""

FIELDS = ["parties", "purpose", "duration", "payment_terms", "obligations", "termination", "confidentiality",
          "governing_law", "important_dates"]


def chunk_prompt(chunk, i, n, doc_type):
    return (
        "ROLE: You are a legal document analysis assistant.\n"
        f"TASK: Read part {i} of {n} of a {doc_type} and extract key information.\n"
        "CONSTRAINT: Use ONLY information present in this text. Do not invent facts. Use [] or \"\" if not present.\n"
        "RULES:\n"
        "- important_dates: include every calendar date that is PRINTED in the text (such as 01-07-2026), "
        "copied exactly, with what happens on it. Never calculate, guess or infer a date that is not "
        "printed - a probation or renewal date you worked out yourself must NOT be listed. "
        "A notice period such as \"30 days\" is NOT a date: put it in termination, not here.\n"
        "- governing_law: the law or country the contract is governed by, for example "
        "\"the laws of India\". Look for the words \"governed by\".\n"
        "- parties: give the actual names only, not role words like \"Employee\" on their own.\n"
        "- obligations: attribute each duty to the party named as the DOER of that sentence, never to "
        "the other side. Check the subject of the sentence before you answer:\n"
        "    \"the Employee shall devote full working time\" -> the Employee's duty.\n"
        "    \"the Employee hereby assigns to the Employer all rights in intellectual property\" -> "
        "the Employee's duty (the Employee gives, the Employer receives).\n"
        "    \"the Employer shall pay a gross salary\" -> the Employer's duty.\n"
        "  Inside the obligation text keep the role words exactly as the document writes them "
        "(\"to the Employer\", \"by the Employee\"). Never swap them round and never replace a role "
        "word with a person's or company's name.\n"
        "  Do not list the same duty twice.\n"
        "OUTPUT FORMAT: JSON with keys:\n"
        '{"parties": ["..."], "purpose": "", "duration": "", "payment_terms": ["..."], '
        '"obligations": [{"party": "...", "obligation": "..."}], "termination": ["..."], '
        '"confidentiality": "", "governing_law": "", "important_dates": [{"date": "...", "event": "..."}]}\n\n'
        f"TEXT:\n{chunk}\n\n"
        "Remember: list every date that is printed above, copied exactly, and invent nothing. "
        "Return only the JSON."
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
        "CONSTRAINT: Use only these notes. Do not give legal advice. "
        "Start directly with the summary - do not write an introduction line such as "
        "'Here is a summary'. Write every date exactly as it appears in the notes "
        "(for example 01-07-2026); never convert it to another format or another day.\n\n"
        f"NOTES:\n{notes}"
    )
