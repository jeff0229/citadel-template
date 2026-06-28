"""Extract plain text from .docx and .pptx without pandoc/python-pptx.

Both formats are zip archives of XML. We pull text runs (<w:t> for docx,
<a:t> for pptx) and emit one text file per source. Slide boundaries
preserved for pptx via blank-line separators.
"""

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def extract_docx(path: Path) -> str:
    out: list[str] = []
    with zipfile.ZipFile(path) as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
        for para in tree.iter(f"{W_NS}p"):
            buf: list[str] = []
            for t in para.iter(f"{W_NS}t"):
                if t.text:
                    buf.append(t.text)
            line = "".join(buf).strip()
            if line:
                out.append(line)
    return "\n\n".join(out)


def extract_pptx(path: Path) -> str:
    out: list[str] = []
    with zipfile.ZipFile(path) as z:
        slides = sorted(
            n for n in z.namelist()
            if n.startswith("ppt/slides/slide") and n.endswith(".xml")
        )
        for slide_path in slides:
            slide_no = slide_path.split("slide")[-1].split(".")[0]
            with z.open(slide_path) as f:
                tree = ET.parse(f)
            buf: list[str] = []
            for t in tree.iter(f"{A_NS}t"):
                if t.text:
                    buf.append(t.text.strip())
            slide_text = "\n".join(b for b in buf if b)
            if slide_text:
                out.append(f"=== SLIDE {slide_no} ===\n{slide_text}")
    return "\n\n".join(out)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: extract_office.py <input.docx|.pptx> <output.txt>")
        return 2
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2])
    suffix = inp.suffix.lower()
    if suffix == ".docx":
        text = extract_docx(inp)
    elif suffix == ".pptx":
        text = extract_pptx(inp)
    else:
        print(f"unsupported: {suffix}")
        return 2
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
