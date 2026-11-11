#!/usr/bin/env python3
"""
Verify a built PDF before it goes out.

Usage:
    python3 scripts/verify.py data/master_cv.pdf

Checks, in the order they matter:
  1. Page count
  2. Live link annotations. Visual inspection does not prove a link exists.
  3. Style violations in the extracted text: em dashes, semicolons
  4. Source note leakage
  5. Known stale strings that have crept back in before
  6. ATS text order, first lines as a parser sees them
  7. Page fill percentage, target 98

Requires: pypdf, pillow, poppler-utils (pdftotext, pdftoppm)
"""

import sys
import glob
import os
import subprocess
import tempfile

from pypdf import PdfReader
from PIL import Image

STALE = [
    # Strings that must never reach a rendered PDF: wrong dates, retired claims, old wording.
    # Add one line whenever verified_facts.md corrects something. Examples:
    "Sep 2020 to Jun 2023",   # a wrong education date that kept coming back
    "eligible to work",        # old right-to-work wording
]


def main():
    path = sys.argv[1]
    reader = PdfReader(path)
    print("pages: %d" % len(reader.pages))

    links = 0
    for i, page in enumerate(reader.pages):
        for annot in (page.get("/Annots") or []):
            uri = annot.get_object().get("/A", {}).get("/URI")
            if uri:
                links += 1
                print("  link p%d: %s" % (i + 1, uri))
    if links == 0:
        print("  FAIL: no live links found. Email and LinkedIn must be clickable.")

    text = "".join(p.extract_text() or "" for p in reader.pages)

    for bad, label in [("\u2014", "em dash"), (";", "semicolon")]:
        if bad in text:
            print("  FAIL: %s in rendered text" % label)

    if "Source notes" in text:
        print("  FAIL: source notes leaked into the render")

    for s in STALE:
        if s in text:
            print("  FAIL: stale string present: %s" % s)

    print("\nATS text order, first 14 lines:")
    out = subprocess.run(["pdftotext", "-layout", path, "-"],
                         capture_output=True, text=True).stdout
    for line in out.split("\n")[:14]:
        print("  " + line)

    print("\npage fill:")
    with tempfile.TemporaryDirectory() as td:
        prefix = os.path.join(td, "pg")
        subprocess.run(["pdftoppm", "-png", "-r", "105", path, prefix], check=True)
        for f in sorted(glob.glob(prefix + "*.png")):
            im = Image.open(f).convert("L")
            w, h = im.size
            px = im.load()
            last = 0
            for y in range(h):
                for x in range(w):
                    if px[x, y] < 200:
                        last = y
                        break
            print("  %s %.1f%%" % (os.path.basename(f), 100 * last / h))


if __name__ == "__main__":
    main()
