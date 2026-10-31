"""Input Module - accepts a legal document as an uploaded file (.txt/.pdf/.docx) or pasted text."""
import os

ALLOWED = (".txt", ".pdf", ".docx")
TYPES = ["Auto-detect", "Employment Agreement", "Non-Disclosure Agreement", "Rental Agreement",
         "Service Agreement", "Sales Agreement", "Loan Agreement", "Other"]
ANALYSIS = ["Complete", "Summary", "Clauses", "Obligations"]


def from_upload(file_storage, folder):
    name = os.path.basename(file_storage.filename or "")
    if not name.lower().endswith(ALLOWED):
        raise ValueError("Upload a .txt, .pdf or .docx file.")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    file_storage.save(path)
    return path, name
