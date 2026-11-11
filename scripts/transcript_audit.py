#!/usr/bin/env python3
"""TRANSCRIPT-AUDIT engine: check every participant quotation in the dissertation
against the interview transcript it claims to come from.

WHY THIS EXISTS
---------------
The six standing audits check WIKI quotes against SOURCE PDFs. None of them ever
touched `interviews/`, which sits outside `wiki/`. On 2026-07-26 a 41-agent pass
found a quotation attributed to a participant that appears NOWHERE in his record
(a quotation that appears in no transcript) plus four fidelity defects, after six consecutive
"clean" six-script audits. String-level and anchor-level audits cannot see what a
quotation does to its source. This can.

WHAT IT CLASSIFIES
------------------
  VERBATIM          exact contiguous match in the attributed speaker's transcript
  ELIDED-MARKED     the span carries an ellipsis and each fragment is verbatim
  ELIDED-UNMARKED   every word is present in order, but words were dropped silently
  ALTERED           the words are mostly present but reordered or reworded
  WRONG-SPEAKER     verbatim, but in a DIFFERENT participant's transcript
  NOT-IN-CORPUS     not in any transcript  <-- the fabrication signal
  NOT-PARTICIPANT   no participant attribution (study's own terms, UI labels,
                    researcher field notes); reported for completeness, never failed

Exit 0 when nothing worse than ELIDED-MARKED is present.
Exit 1 on NOT-IN-CORPUS or WRONG-SPEAKER (hard defects).
Exit 1 on ELIDED-UNMARKED / ALTERED too, unless --lenient.
"""
import argparse, os, re, sys, unicodedata

# --- normalisation -----------------------------------------------------------
PUNCT_MAP = {
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": " ", " ": " ",
}
# transcripts are ASR-normalised; these classes are declared in the draft's
# methodology as silently correctable, so the audit must not flag them.
ASR_EQUIV = [
    (r"\bdownloads\b", "downvotes"),
    (r"\bdoes does\b", "does"),
    (r"\bAmerican does\b", "America does"),
]
FILLER = r"\b(?:um|uh|erm|like,|in like|you know|i mean|sort of|kind of)\b"
CENSOR = [("sh\\*ts", "shits"), ("f\\*\\*\\*ing", "fucking"), ("sh\\*t", "shit")]


BRACKET_INSERT = re.compile(r"\[(?!…|\.\.\.)[^\]]{1,40}\]")


def norm(s, drop_filler=True):
    s = unicodedata.normalize("NFKC", s)
    # [square brackets] are the scholarly marker for an editorial insertion: the
    # source did NOT contain them. Drop them before matching, so a properly
    # bracketed repair passes and an UNbracketed one still fails.
    s = BRACKET_INSERT.sub(" ", s)
    for a, b in PUNCT_MAP.items():
        s = s.replace(a, b)
    for a, b in CENSOR:
        s = re.sub(a, b, s, flags=re.I)
    for pat, rep in ASR_EQUIV:
        s = re.sub(pat, rep, s, flags=re.I)
    s = s.lower()
    if drop_filler:
        s = re.sub(FILLER, " ", s)
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    # apostrophes used as quote marks are punctuation; apostrophes inside a word
    # are not. Keep don't / it's, drop 'libtard'.
    s = re.sub(r"(?<![a-z])'|'(?![a-z])", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def is_subsequence(needle_words, hay_words):
    """Are all needle words present, in order, inside hay (gaps allowed)?"""
    it = iter(hay_words)
    return all(w in it for w in needle_words)


def overlap(a_words, b_words):
    if not a_words:
        return 0.0
    sa = set(a_words)
    return len(sa & set(b_words)) / len(sa)


# --- corpus ------------------------------------------------------------------
def load_transcripts(interviews_dir):
    out = {}
    pseudo = {}
    bank = os.path.join(interviews_dir, "Quote Bank - Cross-Participant (running).md")
    if os.path.exists(bank):
        txt = open(bank, encoding="utf-8", errors="replace").read()
        # the map lives on one declared line; parsing the whole file over-matches
        # (it picked up "Al", "Discord" and "Western" on 2026-07-26)
        line = ""
        for ln in txt.split("\n"):
            if "Pseudonyms" in ln and re.search(r"P0?1\s", ln):
                line = ln
                break
        for pid, name in re.findall(r"\b(P\d{2})\s+([A-Z][a-z]+)", line or ""):
            pseudo.setdefault(name, pid)
    if not pseudo:
        sys.stderr.write("[TRANSCRIPT-AUDIT] could not read the pseudonym map\n")
        return {}, {}
    for name, pid in pseudo.items():
        fp = os.path.join(interviews_dir, f"Interviewee Transcript - {pid}.md")
        if os.path.exists(fp):
            out[name] = norm(open(fp, encoding="utf-8", errors="replace").read())
    return out, pseudo


# --- document readers --------------------------------------------------------
def read_docx(path):
    from docx import Document
    doc = Document(path)
    return [p.text for p in doc.paragraphs]


def read_md(path):
    return open(path, encoding="utf-8", errors="replace").read().split("\n")


# --- the check ---------------------------------------------------------------
QUOTE_RE = re.compile("“(.+?)”", re.S)
ELLIPSIS_SPLIT = re.compile(r"\[…\]|\[\.\.\.\]|…|\.\.\.")


def audit_paragraphs(paras, transcripts, min_words=4):
    names = sorted(transcripts, key=len, reverse=True)
    findings = []
    for idx, text in enumerate(paras):
        if not text or "“" not in text:
            continue
        here = [n for n in names if re.search(r"\b" + re.escape(n) + r"\b", text)]
        m = re.search(r"[–—-]\s*(" + "|".join(names) + r")\s*$", text.strip())
        attributed = m.group(1) if m else None
        stripped = text.strip()
        # A block quote is one quotation that may itself contain quoted material.
        # Regex-scanning it for inner spans splits it at the nested quote marks
        # and produces false ALTERED verdicts, so take the paragraph whole.
        if attributed and stripped.startswith("“"):
            inner = stripped[1:stripped.rfind("”")] if "”" in stripped else stripped[1:]
            spans = [inner]
        else:
            spans = [q.group(1) for q in QUOTE_RE.finditer(text)]
        for span in spans:
            if len(norm(span).split()) < min_words:
                continue
            marked = bool(ELLIPSIS_SPLIT.search(span))
            frags = [f for f in ELLIPSIS_SPLIT.split(span)
                     if len(norm(f).split()) >= min_words] or [span]
            cands = [attributed] if attributed else here
            cands = [c for c in cands if c]
            if not cands:
                findings.append((idx, "NOT-PARTICIPANT", None, span, ""))
                continue
            best = None
            for c in cands:
                hay = transcripts.get(c, "")
                hw = hay.split()
                verdicts = []
                for f in frags:
                    nf = norm(f)
                    fw = nf.split()
                    if nf in hay:
                        verdicts.append("V")
                    elif is_subsequence(fw, hw):
                        verdicts.append("E")
                    elif overlap(fw, hw) >= 0.75:
                        verdicts.append("A")
                    else:
                        verdicts.append("X")
                if all(v == "V" for v in verdicts):
                    best = (c, "ELIDED-MARKED" if marked else "VERBATIM", "")
                    break
                worst = "X" if "X" in verdicts else ("A" if "A" in verdicts else "E")
                lbl = {"E": "ELIDED-UNMARKED", "A": "ALTERED", "X": "NOT-IN-CORPUS"}[worst]
                detail = "; ".join(f.strip()[:90] for f, v in zip(frags, verdicts) if v != "V")
                if best is None or lbl == "ELIDED-UNMARKED":
                    best = (c, lbl, detail)
            who, verdict, detail = best
            if verdict == "NOT-IN-CORPUS":
                for other, hay in transcripts.items():
                    if other in cands:
                        continue
                    if all(norm(f) in hay for f in frags):
                        verdict, detail = "WRONG-SPEAKER", f"verbatim in {other}, attributed to {who}"
                        break
            findings.append((idx, verdict, who, span, detail))
    return findings


HARD = {"NOT-IN-CORPUS", "WRONG-SPEAKER"}
SOFT = {"ELIDED-UNMARKED", "ALTERED"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+", help=".docx or .md files to audit")
    ap.add_argument("--interviews", required=True)
    ap.add_argument("--lenient", action="store_true", help="do not fail on soft defects")
    ap.add_argument("--show-ok", action="store_true")
    ap.add_argument("--accept", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     "transcript-audit.accept.txt"),
                    help="file of reviewed-and-accepted renderings (recorded, not hidden)")
    a = ap.parse_args()

    accepted = []
    if os.path.exists(a.accept):
        for ln in open(a.accept, encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                accepted.append(ln)

    transcripts, pseudo = load_transcripts(a.interviews)
    if not transcripts:
        print("[TRANSCRIPT-AUDIT] no transcripts loaded; cannot run.")
        return 2
    print(f"[TRANSCRIPT-AUDIT] {len(transcripts)} transcripts loaded "
          f"({', '.join(sorted(transcripts))})")

    totals = {}
    hard_hits, soft_hits = [], []
    if accepted:
        print(f"[TRANSCRIPT-AUDIT] {len(accepted)} reviewed-and-accepted rendering(s) on file")
    for t in a.targets:
        if not os.path.exists(t):
            print(f"  ! missing target: {t}")
            continue
        paras = read_docx(t) if t.lower().endswith(".docx") else read_md(t)
        found = audit_paragraphs(paras, transcripts)
        counts = {}
        for idx, verdict, who, span, detail in found:
            if verdict in (HARD | SOFT) and any(x in span for x in accepted):
                verdict = "ACCEPTED"
            counts[verdict] = counts.get(verdict, 0) + 1
            totals[verdict] = totals.get(verdict, 0) + 1
            if verdict in HARD or verdict in SOFT:
                (hard_hits if verdict in HARD else soft_hits).append(
                    (os.path.basename(t), idx, verdict, who, span, detail))
            elif a.show_ok:
                print(f"    ok  [{verdict}] {who}: {span[:70]}")
        print(f"  {os.path.basename(t)}: " +
              ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    for label, hits in (("HARD DEFECTS", hard_hits), ("SOFT DEFECTS", soft_hits)):
        if hits:
            print(f"\n[TRANSCRIPT-AUDIT] {label}: {len(hits)}")
            for f, idx, verdict, who, span, detail in hits:
                print(f"  {verdict}  {f} para {idx}  attributed={who}")
                print(f"     quote : {span[:150]}")
                if detail:
                    print(f"     detail: {detail[:200]}")

    n_hard = sum(totals.get(k, 0) for k in HARD)
    n_soft = sum(totals.get(k, 0) for k in SOFT)
    if n_hard:
        print(f"\n[TRANSCRIPT-AUDIT] FAIL: {n_hard} hard defect(s). "
              f"A NOT-IN-CORPUS result means the quotation is in no transcript.")
        return 1
    if n_soft and not a.lenient:
        print(f"\n[TRANSCRIPT-AUDIT] FAIL: {n_soft} soft defect(s) "
              f"(unmarked elision or altered wording). Mark the elision or restore the words.")
        return 1
    print("\n[TRANSCRIPT-AUDIT] clean: every participant quotation resolves to its transcript.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
