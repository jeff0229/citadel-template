#!/usr/bin/env python3
"""
Build a CV or cover letter PDF from markdown.

Usage:
    python3 scripts/build.py data/master_cv.md            # CV margins
    python3 scripts/build.py drafts/letter.md --letter    # letter margins, justified

Strips the tailoring blockquote and everything from "## Source notes" onward,
so working notes never reach the render.

Requires: wkhtmltopdf, python3, pypdf (for verify.py).
    sudo apt install wkhtmltopdf poppler-utils
    pip install pypdf pillow
"""

import re
import html
import json
import sys
import subprocess
from pathlib import Path

# Your contact details, used to turn the email and LinkedIn text in the header into live links.
# Copy data/profile.example.json to data/profile.json and fill it in (profile.json is git-ignored).
_PROFILE = Path(__file__).resolve().parent.parent / "data" / "profile.json"
if not _PROFILE.exists():
    _PROFILE = _PROFILE.with_name("profile.example.json")
PROFILE = json.loads(_PROFILE.read_text(encoding="utf-8")) if _PROFILE.exists() else {}
EMAIL = PROFILE.get("email", "you@example.com")
LINKEDIN = PROFILE.get("linkedin", "linkedin.com/in/your-handle/")
NAME = PROFILE.get("name", "Your Name")

CV_MARGINS = ["--margin-top", "13mm", "--margin-bottom", "12mm",
              "--margin-left", "14mm", "--margin-right", "14mm"]
LETTER_MARGINS = ["--margin-top", "16mm", "--margin-bottom", "14mm",
                  "--margin-left", "18mm", "--margin-right", "18mm"]

CSS = """  @page { size: A4; margin: %(page_margin)s; }
  * { box-sizing: border-box; }
  /* 2026-09-06: Arial, matching the exemplar CV and the safest font for ATS
     parsing. This supersedes the Carlito choice below, which was made only to
     escape a Calibri defect. Arial escapes it too and was verified to extract
     cleanly in the same test. Do NOT put Calibri back at the front.
     Original note: Carlito first, not Calibri. Metric-compatible, and on Windows the Calibri
     render breaks the PDF text layer: pypdf and pdftotext both read the contact
     line as "yourna me@exam ple.com", which is what an ATS would parse.
     Verified 2026-09-04 on wkhtmltopdf 0.12.6-1 win64 and headless Edge. */
  body { font-family: Arial,"Liberation Sans","Helvetica Neue",Helvetica,sans-serif;
         font-size: 9.5pt; line-height: 1.32; color:#1a1a1a; margin:0; padding:0;
         text-align: %(align)s; }
  h1 { font-size: 15pt; font-weight: bold; margin: 0 0 2px 0; letter-spacing: 0.3px;
       text-align: %(headalign)s; }
  h2 { font-size: 10pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.6px;
       border-bottom: 1px solid #9a9a9a; padding-bottom: 2px; margin: 10px 0 5px 0;
       page-break-after: avoid; text-align: left; }
  h3 { font-size: 9.8pt; margin: 9px 0 4px 0; color:#333; page-break-after: avoid; text-align: left; }
  p { margin: 0 0 5px 0; }
  p.contact, p.meta { font-size: 9pt; color:#3d3d3d; margin: 0 0 2px 0; text-align: %(headalign)s; }
  p.meta { margin-bottom: 4px; }
  p.role { margin: 7px 0 1px 0; page-break-after: avoid; text-align: left;
           display: block; overflow: hidden; }
  p.role .date { float: right; font-weight: normal; color:#3d3d3d; }
  p.scope { margin: 0 0 3px 0; color:#2a2a2a; text-align: left; }
  ul { margin: 2px 0 5px 0; padding-left: 14px; page-break-inside: avoid; text-align: left;
       list-style-type: disc; }
  li { margin: 0 0 2px 0; }
  a { color: #1a4f8a; text-decoration: underline; }
  em { font-style: italic; }
  div.keep { page-break-inside: avoid; }
  ul.split { margin-bottom: 0; }
  ul.cont { margin-top: 0; page-break-inside: auto; }
  li { page-break-inside: avoid; }"""


# 2026-09-10: letters were rendering in CV typography, 9.5pt at 1.32 line height,
# which crammed a 240-word letter into the top 43 per cent of an A4 page and read
# as cramped. A letter is a reading document, not a scanning document. The ladder
# below runs loosest first; build.py steps down a rung at a time until the letter
# fits one page, so a short letter breathes and a long one still fits without
# anyone hand-tuning CSS. CV metrics are untouched.
LETTER_STEPS = [
    (11.2, 1.55, 13, 17),
    (11.0, 1.48, 11, 16.5),
    (10.7, 1.42, 10, 16),
    (10.4, 1.36, 9, 15.5),
    (10.1, 1.30, 8, 15),
]


def letter_css(step):
    size, leading, gap, h1 = step
    return """
  body { font-size: %spt; line-height: %s; }
  h1 { font-size: %spt; margin: 0 0 4px 0; }
  p { margin: 0 0 %spx 0; }
  p.contact, p.meta { font-size: 10pt; margin: 0 0 3px 0; }
""" % (size, leading, h1, gap)


def inline(t):
    t = html.escape(t)
    # Markdown links. Added 2026-09-04: only the email and LinkedIn hyperlinks
    # were special-cased below, so any other [text](url) rendered as literal
    # brackets in the PDF. Runs before emphasis so link text can carry bold.
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\g<2>">\g<1></a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return t


def md_to_html(body_md):
    # 2026-10-10: two-page CVs left a role heading, or a section heading, alone at
    # the foot of page 1 with its bullets on page 2. This engine's old WebKit
    # ignores page-break-after: avoid, but honours page-break-inside: avoid on a
    # block. So each section heading travels in one div with its first entry, and
    # every later entry (role line, scope line, bullets) gets a div of its own.
    # Only the heading and the first KEEP_BULLETS bullets are held together: the
    # rest continue in a list that may break across pages, because holding a
    # nine-bullet entry whole pushed it off page 1 and left a third of the page
    # blank. A single-page document renders exactly as before.
    KEEP_BULLETS = 2
    out, in_ul = [], False
    in_block, block_has_role = False, False
    bullets, cont = 0, False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def close_block():
        nonlocal in_block, block_has_role
        if in_block:
            out.append("</div>")
            in_block, block_has_role = False, False

    def open_block():
        nonlocal in_block, bullets, cont
        out.append('<div class="keep">')
        in_block, bullets, cont = True, 0, False

    for ln in body_md.split("\n"):
        s = ln.rstrip()
        if s.startswith("### "):
            close_ul(); out.append("<h3>%s</h3>" % inline(s[4:])); continue
        if s.startswith("## "):
            close_ul(); close_block(); open_block()
            out.append("<h2>%s</h2>" % inline(s[3:])); continue
        if s.startswith("# "):
            close_ul(); close_block(); out.append("<h1>%s</h1>" % inline(s[2:])); continue
        if s.startswith("**"):
            # a role line starts a new entry, unless it is the first entry under
            # a section heading, which shares the heading's div
            close_ul()
            if not (in_block and not block_has_role):
                close_block(); open_block()
            block_has_role = True
        if s.startswith("- "):
            if not in_ul:
                out.append('<ul class="cont">' if cont else "<ul>"); in_ul = True
            out.append("<li>%s</li>" % inline(s[2:]))
            bullets += 1
            if in_block and bullets == KEEP_BULLETS:
                # end the kept block here, and continue the same list outside it
                last_ul = max(i for i, x in enumerate(out) if x == "<ul>")
                out[last_ul] = '<ul class="split">'
                close_ul(); close_block(); cont = True
            continue
        if s.strip() in ("", "---"):
            close_ul(); cont = False; continue
        close_ul()
        if s.startswith("**") and " | " in s:
            # "**Role, Employer** | Oct 2024 to Jun 2025" renders as a single row
            # with the date right-aligned, matching the exemplar CV. Added
            # 2026-09-06: dates previously ran inline after the title and wrapped,
            # which is the main thing that made the layout look unconsidered.
            title, _, date = s.partition(" | ")
            out.append('<p class="role">%s<span class="date">%s</span></p>'
                       % (inline(title), inline(date.strip())))
            continue
        if s.startswith("**"):
            out.append('<p class="role">%s</p>' % inline(s))
            continue
        out.append("<p%s>%s</p>" % (' class="scope"' if out and 'class="role"' in out[-1] else "", inline(s)))
    close_ul()
    close_block()
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    src = Path(sys.argv[1])
    is_letter = "--letter" in sys.argv
    md = src.read_text(encoding="utf-8")

    # style gate: fail loudly rather than shipping a violation
    if "\u2014" in md or ";" in md.split("## Source notes")[0]:
        print("WARNING: em dash or semicolon found in the body. Fix before shipping.")

    body_md = md.split("\n---\n\n## Source notes")[0]
    body_md = re.split(r"\n#+ Source notes", body_md)[0]
    body_md = "\n".join(l for l in body_md.split("\n") if not l.startswith("> "))

    doc = md_to_html(body_md)

    doc = doc.replace(EMAIL, '<a href="mailto:%s">%s</a>' % (EMAIL, EMAIL), 1)
    doc = doc.replace(LINKEDIN, '<a href="https://www.%s">LinkedIn</a>' % LINKEDIN.replace("https://", "").replace("www.", ""), 1)
    # The header styling used to key on literal strings (a city name, a visa
    # line). A CV worded differently silently lost its centred contact styling
    # and rendered left-aligned while every other document was centred. The header
    # block is defined by POSITION, not by its wording: it is the paragraphs
    # immediately following the H1, however they are worded.
    lines = doc.split("\n")
    seen_h1, styled = False, 0
    for i, ln in enumerate(lines):
        if ln.startswith("<h1>"):
            seen_h1 = True
            continue
        if not seen_h1:
            continue
        if ln.startswith("<p>") and styled < 2:
            lines[i] = ln.replace("<p>", '<p class="%s">' % ("contact" if styled == 0 else "meta"), 1)
            styled += 1
            continue
        if ln.strip():
            break
    doc = "\n".join(lines)

    css = CSS % {
        "page_margin": "16mm 18mm" if is_letter else "14mm 17mm",
        # 2026-09-06: letters are LEFT-ALIGNED, not justified, and this is not a
        # style preference. Justifying text in wkhtmltopdf 0.12.6 win64 makes it
        # substitute ligature glyphs whose ToUnicode mapping is wrong, so the PDF
        # text layer comes out corrupted: "production" extracts as "produc8on",
        # "committee" as "commi;ee", "written" as "wri;en". Measured on identical
        # content: justified gave 14 ti->8 and 3 tt->; errors, left-aligned gave
        # zero. pdftotext recovers, pypdf does not, and an ATS may use either,
        # so the keywords these applications are screened on are at risk.
        # Suppressing ligatures in CSS does not help: font-variant-ligatures and
        # font-feature-settings are both ignored by this engine's old WebKit.
        # Justified text is cosmetic. A parseable text layer is not.
        "align": "left",
        # header block centred to match the exemplar; body stays left for parsing
        "headalign": "left" if is_letter else "center",
    }

    # The document title used to be hard-coded to the author's name, which lands in the
    # PDF metadata Title field. That silently defeats a name-blind CV, where the
    # entire point is that no identifier reaches the sifter. The title now comes
    # from the document's own H1, so an anonymised CV headed "Curriculum Vitae"
    # stays anonymous. Falls back to the name for every ordinary document.
    m_title = re.search(r"^# (.+)$", body_md, re.MULTILINE)
    doc_title = m_title.group(1).strip() if m_title else NAME

    out_html = src.with_suffix(".html")
    out_pdf = src.with_suffix(".pdf")

    margins = LETTER_MARGINS if is_letter else CV_MARGINS

    def render(extra_css=""):
        out_html.write_text(
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            "<title>" + html.escape(doc_title) + "</title>\n<style>\n"
            + css + extra_css
            + "\n</style>\n</head>\n<body>\n\n" + doc + "\n\n</body>\n</html>\n",
            encoding="utf-8")
        subprocess.run(
            ["wkhtmltopdf", "--enable-local-file-access", "--page-size", "A4"]
            + margins
            + ["--print-media-type", "--disable-smart-shrinking",
               str(out_html), str(out_pdf)],
            check=True)

    if is_letter:
        from pypdf import PdfReader
        for i, step in enumerate(LETTER_STEPS):
            render(letter_css(step))
            if len(PdfReader(str(out_pdf)).pages) == 1:
                print("letter typography: %spt / %s leading (rung %d of %d)"
                      % (step[0], step[1], i + 1, len(LETTER_STEPS)))
                break
        else:
            print("WARNING: letter runs over one page at the tightest rung. Cut words.")
    else:
        render()

    print("built %s and %s" % (out_html, out_pdf))
    print("now run: python3 scripts/verify.py %s" % out_pdf)


if __name__ == "__main__":
    main()
