"""Analysis Module - sends each chunk to the LLM, combines the results, and writes a summary.

Chunk 1 -> JSON,  Chunk 2 -> JSON  ->  merged structured analysis  ->  final summary
"""
import json

from llm import as_list, ask, ask_json

from .prompt_module import FIELDS, chunk_prompt, summary_prompt


def _merge(results):
    out = {"parties": [], "purpose": "", "duration": "", "payment_terms": [], "obligations": [],
           "termination": [], "confidentiality": "", "governing_law": "", "important_dates": []}
    for r in results:
        for k in ("parties", "payment_terms", "termination"):
            for v in as_list(r.get(k)):
                if v not in out[k]:
                    out[k].append(v)
        for k in ("purpose", "duration", "confidentiality", "governing_law"):
            v = r.get(k)
            if isinstance(v, list):
                v = "; ".join(map(str, v))
            if v and not out[k]:
                out[k] = str(v)
        for o in r.get("obligations") or []:
            if isinstance(o, dict) and o.get("obligation"):
                out["obligations"].append({"party": str(o.get("party", "")), "obligation": str(o["obligation"])})
            elif isinstance(o, str):
                out["obligations"].append({"party": "", "obligation": o})
        for d in r.get("important_dates") or []:
            if isinstance(d, dict) and d.get("date"):
                out["important_dates"].append({"date": str(d["date"]), "event": str(d.get("event", ""))})
    return out


def analyze(chunks, doc_type, analysis_type="Complete"):
    results, prompts = [], []
    for i, c in enumerate(chunks, 1):
        p = chunk_prompt(c, i, len(chunks), doc_type)
        prompts.append(p)
        results.append(ask_json(p, temperature=0.1, default={}) or {})
    merged = _merge(results)
    summary = ask(summary_prompt(doc_type, json.dumps(merged, indent=1), analysis_type), temperature=0.3)
    return {"analysis": merged, "summary": summary, "prompt": prompts[0], "n_chunks": len(chunks)}
