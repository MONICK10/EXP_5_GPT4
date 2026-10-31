"""
Ex. No. 5 - Automated Legal Document Analyzer using GPT-4 style LLM (Llama 3.2 via Ollama)
Monick S - URK23CS1167

Run:  python app.py    then open  http://localhost:5005
"""
import os

from flask import Flask, jsonify, render_template, request

from llm import LLMError, status
from modules import (analysis_module, chunking_module, clause_module, extraction_module, input_module,
                     preprocessing_module, save_module)

BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(BASE, "samples")
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


@app.errorhandler(LLMError)
def llm_error(e):
    return jsonify(error=str(e)), 503


@app.errorhandler(ValueError)
def bad_input(e):
    return jsonify(error=str(e)), 400


@app.get("/")
def home():
    return render_template("index.html", exp_no=5, title="LexiScan AI – Legal Document Analyzer",
                           samples=sorted(os.listdir(SAMPLES)), types=input_module.TYPES, analysis=input_module.ANALYSIS)


@app.get("/api/status")
def api_status():
    return jsonify(status())


@app.post("/api/extract")
def api_extract():
    """Input -> Extraction -> Preprocessing -> Chunking"""
    f = request.files.get("file")
    sample = request.form.get("sample")
    if f and f.filename:
        path, name = input_module.from_upload(f, os.path.join(BASE, "uploads"))
        raw = extraction_module.extract(path)
    elif sample:
        name = os.path.basename(sample)
        raw = extraction_module.extract(os.path.join(SAMPLES, name))
    else:
        raw, name = request.form.get("text", ""), "Pasted text"
    if len(raw.strip()) < 50:
        raise ValueError("Document text is empty or too short.")
    pre = preprocessing_module.preprocess(raw)
    chosen = request.form.get("doc_type", "Auto-detect")
    if chosen != "Auto-detect":
        pre["doc_type"] = chosen
    chunks = chunking_module.chunk(pre["text"], int(request.form.get("chunk_size", 2500)))
    return jsonify(file_name=name, raw_preview=raw[:1500], chunks=chunks, **pre)


@app.post("/api/analyze")
def api_analyze():
    d = request.get_json()
    return jsonify(analysis_module.analyze(d["chunks"], d["doc_type"], d.get("analysis_type", "Complete")))


@app.post("/api/clauses")
def api_clauses():
    d = request.get_json()
    return jsonify(clauses=clause_module.explain(clause_module.find(d["text"]), d["doc_type"]))


@app.post("/api/save")
def api_save():
    return jsonify(save_module.save(request.get_json()))


if __name__ == "__main__":
    app.run(port=5005, debug=False)
