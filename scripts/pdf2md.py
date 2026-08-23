#!/usr/bin/env python3
"""Extract text from arXiv PDFs into Markdown files (for KB upload)."""

import sys
import os


def extract_with_pdfplumber(path):
    import pdfplumber
    parts = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            parts.append(f"\n\n<!-- PAGE {i} -->\n\n{text}")
    return "".join(parts)


def extract_with_pdfminer(path):
    from pdfminer.high_level import extract_text
    return extract_text(path)


def main():
    pdfs = sys.argv[1:]
    out_dir = "kb/md"
    os.makedirs(out_dir, exist_ok=True)
    for pdf in pdfs:
        name = os.path.splitext(os.path.basename(pdf))[0]
        try:
            text = extract_with_pdfplumber(pdf)
            if len(text.strip()) < 500:
                text = extract_with_pdfminer(pdf)
            out = os.path.join(out_dir, f"{name}.md")
            with open(out, "w", encoding="utf-8") as f:
                f.write(f"# {name}\n\n{text}")
            print(f"{name}: {len(text)} chars -> {out}")
        except Exception as e:
            print(f"{name}: FAILED {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
