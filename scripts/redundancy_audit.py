#!/usr/bin/env python3
"""REDUNDANCY-AUDIT engine: find near-duplicate claims across chapters and sections.

WHY THIS EXISTS
---------------
On 2026-07-26 four separate redundancies were found by hand, none by any script:
§3.7 and §5.2 restated the same three design limits; the Introduction and §5.1
both opened "The contribution rests on..."; §4.6 stated "renders the performer
public and the reflective observer private" three times in one paragraph; and
§4.4's closing gloss repeated the line that ended the same section. A marker
reads redundancy as padding. No string audit looked for it.

METHOD
------
Sentences are labelled with their section, normalised, and compared pairwise.
Two similarity signals must agree, which keeps the false-positive rate low:
  - token-set Jaccard (catches reordering and rewording)
  - difflib sequence ratio (catches near-verbatim restatement)
Cross-section pairs are reported as REDUNDANT; same-section pairs as ECHO.
Openings are checked separately: two sections opening on the same formula is a
distinct and more visible defect than a repeated claim buried mid-paragraph.

Exit 0 always by default (this is an advisory audit; judgement is required on
each hit). Use --strict to fail when anything is reported.
"""
import argparse, difflib, os, re, sys, unicodedata

STOP = set("""a an the and or but of to in on for with as at by from that this these those it its
is are was were be been being has have had do does did not no so than then there their they them
he she his her him we us our you your i me my which who whom what when where how why if while
about into over under again further once more most other some such only own same can will just""".split())


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    for a, b in (("’","'"),("‘","'"),("“",'"'),("”",'"'),("–","-"),("—","-"),("…"," ")):
        s = s.replace(a, b)
    s = re.sub(r"\(§?[^)]{0,60}\)", " ", s)      # drop citations and cross-refs
    s = re.sub(r"§\s*\d+(\.\d+)*", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def content_words(s):
    return [w for w in norm(s).split() if w not in STOP and len(w) > 2]


def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa or sb) else 0.0


def read_docx_sections(path):
    from docx import Document
    doc = Document(path)
    out, section = [], "(front matter)"
    started = False
    for p in doc.paragraphs:
        t = p.text.strip()
        st = p.style.name
        if st.startswith("Heading"):
            if t.startswith("Chapter 1."):
                started = True
            if t == "Bibliography":
                break
            section = t
            continue
        if not started or not t:
            continue
        if t.startswith("“"):          # block quotes are participants', not the author's
            continue
        for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z“])", t):
            if len(content_words(sent)) >= 7:
                out.append((section, sent.strip()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--jaccard", type=float, default=0.45)
    ap.add_argument("--ratio", type=float, default=0.48)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    sents = read_docx_sections(a.target)
    print(f"[REDUNDANCY-AUDIT] {len(sents)} author sentences across "
          f"{len(set(s for s, _ in sents))} sections (block quotes excluded)")

    cw = [content_words(s) for _, s in sents]
    cross, echo = [], []
    for i in range(len(sents)):
        if not cw[i]:
            continue
        for j in range(i + 1, len(sents)):
            if not cw[j]:
                continue
            jc = jaccard(cw[i], cw[j])
            if jc < a.jaccard:
                continue
            rt = difflib.SequenceMatcher(None, norm(sents[i][1]), norm(sents[j][1])).ratio()
            if rt < a.ratio:
                continue
            (echo if sents[i][0] == sents[j][0] else cross).append((jc, rt, sents[i], sents[j]))

    # section openings sharing a formula
    firsts, opens = {}, []
    for sec, sent in sents:
        firsts.setdefault(sec, sent)
    secs = list(firsts.items())
    for i in range(len(secs)):
        for j in range(i + 1, len(secs)):
            w1, w2 = content_words(secs[i][1])[:6], content_words(secs[j][1])[:6]
            if w1 and jaccard(w1, w2) >= 0.5:
                opens.append((secs[i], secs[j]))

    def dump(label, items, fmt):
        if not items:
            return
        print(f"\n[REDUNDANCY-AUDIT] {label}: {len(items)}")
        for it in sorted(items, key=lambda x: -x[0])[:40] if fmt else items:
            print_item(it, fmt)

    def print_item(it, scored):
        if scored:
            jc, rt, (s1, t1), (s2, t2) = it
            print(f"  jaccard={jc:.2f} ratio={rt:.2f}")
            print(f"    [{s1}] {t1[:150]}")
            print(f"    [{s2}] {t2[:150]}")
        else:
            (s1, t1), (s2, t2) = it
            print(f"    [{s1}] opens: {t1[:110]}")
            print(f"    [{s2}] opens: {t2[:110]}")

    dump("CROSS-SECTION REDUNDANCY", cross, True)
    dump("SAME-SECTION ECHO", echo, True)
    dump("SECTIONS OPENING ON THE SAME FORMULA", opens, False)

    total = len(cross) + len(echo) + len(opens)
    if total == 0:
        print("\n[REDUNDANCY-AUDIT] clean: no near-duplicate claims found.")
        return 0
    print(f"\n[REDUNDANCY-AUDIT] {total} candidate(s) for review. "
          f"Each needs judgement: a deliberate Introduction-to-Conclusion pickup is not a defect; "
          f"the same limit stated twice as if new is.")
    return 1 if a.strict else 0


if __name__ == "__main__":
    sys.exit(main())
