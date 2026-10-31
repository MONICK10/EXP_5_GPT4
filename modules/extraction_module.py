"""Extraction Module - reads the document and pulls out its text.

.txt -> read directly,  .pdf -> pypdf,  .docx -> python-docx
"""


def extract(path):
    p = path.lower()
    if p.endswith(".txt"):
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    if p.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    if p.endswith(".docx"):
        import docx
        return "\n".join(par.text for par in docx.Document(path).paragraphs)
    raise ValueError("Unsupported file type.")
