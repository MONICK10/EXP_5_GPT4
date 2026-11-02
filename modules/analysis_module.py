"""Analysis Module - sends each chunk to the LLM, combines the results, and writes a summary.

Chunk 1 -> JSON,  Chunk 2 -> JSON  ->  merged structured analysis  ->  final summary
"""
import json
import re

from llm import as_list, ask, ask_json

from .prompt_module import FIELDS, chunk_prompt, summary_prompt


def _strip_preamble(text):
    """Drop an opening line like 'Here is a plain-English summary of the Agreement:'."""
    text = text.strip()
    first, sep, rest = text.partition("\n")
    if sep and first.rstrip().endswith(":") and len(first.split()) <= 20:
        return rest.strip()
    return re.sub(r"^here(?:'s| is)[^:]{0,100}:\s*", "", text, flags=re.I).strip()


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


DATE_RE = re.compile(r"\b\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}\b")
MONTH = ("january|february|march|april|may|june|july|august|september|october|november|december")
WORD_DATE_RE = re.compile(rf"\b(?:\d{{1,2}}\s+(?:{MONTH})|(?:{MONTH})\s+\d{{1,2}})\,?\s+\d{{4}}\b", re.I)


def _parts(text):
    """'15-06-2026' -> frozenset({15, 6, 2026}), so a reformatted date still matches."""
    return frozenset(int(x) for x in re.split(r"[-/.]", text))


def _only_real_dates(dates, source):
    """Keep an entry only if it is a real calendar date that is printed in the document.

    Two things are filtered out here, because a record must show extracted facts only:
      * dates the model worked out itself (a probation or renewal date that is not written down)
      * values that are not dates at all, such as "30 days" or "immediately without notice"
    """
    printed = {_parts(m) for m in DATE_RE.findall(source)}
    printed_words = {m.lower() for m in WORD_DATE_RE.findall(source)}
    kept = []
    for d in dates:
        raw = str(d.get("date", "")).strip()
        m = DATE_RE.search(raw)
        w = WORD_DATE_RE.search(raw)
        if m and _parts(m.group()) in printed:
            kept.append(d)
        elif w and w.group().lower() in printed_words:
            kept.append(d)
    return kept


ROLE_RE = re.compile(r"\b(Employer|Employee|Landlord|Tenant|Lessor|Lessee|Discloser|Disclosing Party|"
                     r"Recipient|Receiving Party|Service Provider|Client|Lender|Borrower|Seller|Buyer|"
                     r"Purchaser|Company|Contractor|Consultant)\b")
DEFINED_RE = re.compile(r"referred to as the\s*[\"'“]([A-Za-z ]+)[\"'”]")


def _role_names(source):
    """'Nimbus Softech Private Limited, ... referred to as the "Employer"' -> {'employer': 'Nimbus ...'}

    The name is read per paragraph, because the party block always opens with the party's name.
    """
    out = {}
    for para in re.split(r"\n\s*\n", source):
        m = DEFINED_RE.search(para)
        if not m:
            continue
        name = para.strip().split(",")[0].strip()
        if name and name[0].isupper() and len(name) < 80:
            out[m.group(1).strip().lower()] = name
    return out


def _sentences(source):
    # do not split inside "Rs. 50,000", "No." or "Mr. Karthik"
    parts = re.split(r"(?<=[.;])(?<!Rs\.)(?<!No\.)(?<!Mr\.)(?<!Ms\.)(?<!Mrs\.)\s+|\n", source)
    return [s.strip() for s in parts if len(s.strip()) > 25]


# the role that owes a duty is the one in front of "shall"/"must"/"hereby"
DOER_RE = re.compile(rf"{ROLE_RE.pattern}\s+(?:shall|must|hereby|agrees|undertakes|will|is required to)", re.I)
GIVES = re.compile(r"^\W*(pay|provide|grant|appoint|reimburse|issue|confirm|deliver|assign to the Employee)\b", re.I)
RECEIVES = re.compile(r"\b(shall receive|shall be entitled|shall be eligible|is entitled|is eligible)\b", re.I)


def _actor_role(sentence, obligation):
    """Which role actually owes this duty.

    "after leaving the Employer, the Employee shall not solicit"  -> Employee (not Employer)
    "The Employee shall receive a gross salary" + duty "pay ..."  -> the other side, the Employer
    """
    m = DOER_RE.search(sentence) or ROLE_RE.search(sentence)
    if not m:
        return ""
    role = m.group(1)
    # a benefit written from the receiver's side is really the counterparty's duty to give
    if GIVES.search(obligation) and RECEIVES.search(sentence):
        pair = {"employee": "Employer", "employer": "Employee", "tenant": "Landlord", "landlord": "Tenant",
                "lessee": "Lessor", "lessor": "Lessee", "borrower": "Lender", "lender": "Borrower",
                "buyer": "Seller", "seller": "Buyer", "purchaser": "Seller"}
        role = pair.get(role.lower(), role)
    return role


def _fix_obligation_parties(obligations, source):
    """Decide who owes each obligation from the document, not from the model's guess.

    The 3B model often flips this ("the Employee assigns IP to the Employer" came back as the
    Employer's duty). In legal prose the party that must act is the subject, so it is the first
    role word of the sentence the obligation came from. That is what we use.
    """
    sents = _sentences(source)
    names = _role_names(source)
    fixed = []
    for o in obligations:
        text = str(o.get("obligation", "")).strip()
        if not text:
            continue
        words = {w for w in re.findall(r"[a-z]{4,}", text.lower())}
        best, score = "", 0.0
        for s in sents:
            sw = {w for w in re.findall(r"[a-z]{4,}", s.lower())}
            overlap = len(words & sw) / max(len(words), 1)
            if overlap > score:
                best, score = s, overlap
        party = o.get("party", "")
        if score >= 0.5:  # confident we found the sentence this obligation came from
            role = _actor_role(best, text)
            if role:
                party = names.get(role.lower(), role)
            # Quote the contract instead of the model's paraphrase. Llama 3.2 keeps flipping the
            # direction ("assigns to the Employee" for an assignment TO the Employer), and a legal
            # record must not contain a reversed term.
            text = re.sub(r"^\d+(\.\d+)*\s*", "", best).strip()
        fixed.append({"party": str(party), "obligation": text, "_key": (party, frozenset(words))})
    # drop duplicates: the two chunks often report the same duty in slightly different words
    out, seen = [], []
    for f in fixed:
        party, words = f.pop("_key")
        if any(p == party and len(words & w) / max(len(words | w), 1) > 0.6 for p, w in seen):
            continue
        seen.append((party, words))
        out.append(f)
    return out


def _drop_invented_dates(items, source):
    """Remove list entries that quote a calendar date the document does not contain.

    Example: the model once returned "12-06-2027" as a termination term. The contract says
    30-06-2027, so that entry is dropped rather than printed into the record.
    """
    printed = {_parts(m) for m in DATE_RE.findall(source)}
    kept = []
    for it in items:
        text = str(it)
        found = DATE_RE.findall(text)
        if found and any(_parts(f) not in printed for f in found):
            continue
        if found and not re.sub(DATE_RE, "", text).strip(" .,;-"):
            continue  # a bare date on its own is not a term
        kept.append(it)
    return kept


def analyze(chunks, doc_type, analysis_type="Complete"):
    results, prompts = [], []
    for i, c in enumerate(chunks, 1):
        p = chunk_prompt(c, i, len(chunks), doc_type)
        prompts.append(p)
        results.append(ask_json(p, temperature=0.1, default={}) or {})
    merged = _merge(results)
    source = "\n".join(chunks)
    merged["important_dates"] = _only_real_dates(merged["important_dates"], source)
    merged["obligations"] = _fix_obligation_parties(merged["obligations"], source)
    for k in ("termination", "payment_terms"):
        merged[k] = _drop_invented_dates(merged[k], source)
    summary = _strip_preamble(ask(summary_prompt(doc_type, json.dumps(merged, indent=1), analysis_type),
                                  temperature=0.3))
    return {"analysis": merged, "summary": summary, "prompt": prompts[0], "n_chunks": len(chunks)}
