#!/usr/bin/env python3
"""
md_to_docx.py

Convert a Markdown file to a .docx document.

Usage:
    python md_to_docx.py \
      --input CHUONG_4_DEMO_DANH_GIA_REVISED.md \
      --output CHUONG_4_DEMO_DANH_GIA_REVISED.docx

Strategy (tries in order):
1. pypandoc (preferred) -> requires pandoc installed on system and pypandoc package.
2. html2docx + markdown (convert md -> html -> docx).
3. Fallback: naive parser using python-docx to handle headings, paragraphs,
   ordered/unordered lists and code blocks (basic formatting).

If a required package is missing, the script prints instructions to install them.
"""
from __future__ import annotations
import argparse
import sys
import os
from pathlib import Path
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("md_to_docx")


def try_pypandoc(input_path: Path, output_path: Path) -> bool:
    try:
        import pypandoc  # type: ignore
    except Exception as e:
        logger.debug("pypandoc not available: %s", e)
        return False

    # pypandoc sometimes fails if pandoc binary is not installed
    try:
        logger.info("Converting using pypandoc (pandoc)...")
        pypandoc.convert_file(str(input_path), "docx", outputfile=str(output_path))
        logger.info("Wrote %s (via pypandoc)", output_path)
        return True
    except Exception as e:
        logger.warning("pypandoc conversion failed: %s", e)
        return False


def try_html2docx(input_path: Path, output_path: Path) -> bool:
    try:
        import markdown  # type: ignore
        from html2docx import html2docx  # type: ignore
    except Exception as e:
        logger.debug("html2docx or markdown not available: %s", e)
        return False

    try:
        logger.info("Converting using markdown -> html -> html2docx...")
        text = input_path.read_text(encoding="utf-8")
        html = markdown.markdown(text, extensions=["tables", "fenced_code", "codehilite"])
        # html2docx returns a docx binary string or writes to stream; use helper to write file
        docx_bytes = html2docx(html, title=input_path.stem)
        with open(output_path, "wb") as f:
            f.write(docx_bytes)
        logger.info("Wrote %s (via html2docx)", output_path)
        return True
    except Exception as e:
        logger.warning("html2docx conversion failed: %s", e)
        return False


def fallback_naive(input_path: Path, output_path: Path) -> bool:
    """
    Naive markdown -> docx converter using python-docx.
    Handles:
      - Headings: # .. ######
      - Unordered lists: lines starting with -, *, +
      - Ordered lists: lines starting with 1. 2. ...
      - Code blocks fenced with ```
      - Blank lines -> paragraph breaks
      - Inline code `...` and bold/italic are not rendered specially (kept verbatim)
      - Tables: will be emitted as simple paragraphs (no table conversion)
    This fallback does not require external non-standard binaries, but needs python-docx.
    """
    try:
        from docx import Document  # type: ignore
        from docx.shared import Pt  # type: ignore
    except Exception as e:
        logger.debug("python-docx not available: %s", e)
        return False

    logger.info("Using fallback naive converter with python-docx (basic formatting)...")
    text = input_path.read_text(encoding="utf-8").splitlines()

    doc = Document()
    in_code = False
    code_lines = []
    list_buffer = []
    list_type = None  # "ul" or "ol"

    def flush_list():
        nonlocal list_buffer, list_type
        if not list_buffer:
            return
        for idx, item in enumerate(list_buffer, start=1):
            p = doc.add_paragraph()
            if list_type == "ul":
                p.style = doc.styles["List Bullet"] if "List Bullet" in doc.styles else None
                p.add_run(item)
            else:
                # ordered
                p.style = doc.styles["List Number"] if "List Number" in doc.styles else None
                p.add_run(item)
        list_buffer = []
        list_type = None

    for raw in text:
        line = raw.rstrip("\n")
        if line.strip().startswith("```"):
            if not in_code:
                # enter code block
                flush_list()
                in_code = True
                code_lines = []
            else:
                # close code block
                in_code = False
                p = doc.add_paragraph()
                code_style = p.style
                run = p.add_run("\n".join(code_lines))
                run.font.name = "Courier New"
                run.font.size = Pt(9)
            continue

        if in_code:
            code_lines.append(line)
            continue

        # headings
        if line.startswith("#"):
            flush_list()
            hashes, _, rest = line.partition(" ")
            level = len(hashes)
            heading_text = rest.strip()
            if not heading_text:
                heading_text = hashes
            if level == 1:
                doc.add_heading(heading_text, level=1)
            elif level == 2:
                doc.add_heading(heading_text, level=2)
            elif level == 3:
                doc.add_heading(heading_text, level=3)
            else:
                # deeper headings -> use normal paragraph with bold
                p = doc.add_paragraph()
                run = p.add_run(heading_text)
                run.bold = True
            continue

        # unordered list
        stripped = line.lstrip()
        if stripped.startswith(("- ", "* ", "+ ")):
            prefix, item = stripped.split(" ", 1)
            if list_type is None:
                list_type = "ul"
            if list_type != "ul":
                flush_list()
                list_type = "ul"
            list_buffer.append(item.strip())
            continue

        # ordered list
        import re
        if re.match(r"^\s*\d+\.\s+", line):
            m = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
            if m:
                if list_type is None:
                    list_type = "ol"
                if list_type != "ol":
                    flush_list()
                    list_type = "ol"
                list_buffer.append(m.group(2).strip())
                continue

        # blank line
        if line.strip() == "":
            flush_list()
            # add paragraph break
            doc.add_paragraph()
            continue

        # tables (naive): detect pipes and header separator
        if "|" in line and not line.strip().startswith(">"):
            # treat as paragraph (so tables remain readable)
            flush_list()
            doc.add_paragraph(line)
            continue

        # normal paragraph
        flush_list()
        doc.add_paragraph(line)

    # flush at end
    flush_list()

    # save
    try:
        doc.save(str(output_path))
        logger.info("Wrote %s (via fallback python-docx)", output_path)
        return True
    except Exception as e:
        logger.error("Failed to save docx: %s", e)
        return False


def check_pandoc_installed() -> bool:
    # quick check for pandoc binary
    return shutil.which("pandoc") is not None


def main():
    parser = argparse.ArgumentParser(description="Convert Markdown to DOCX (tries multiple methods).")
    parser.add_argument("--input", "-i", required=True, help="Input markdown file path")
    parser.add_argument("--output", "-o", required=False, help="Output docx file path (optional)")
    parser.add_argument("--force-method", "-m", choices=["pypandoc", "html2docx", "fallback"],
                        help="Force conversion method")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file does not exist: %s", input_path)
        sys.exit(2)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".docx")

    # If output exists, warn and overwrite after confirmation
    if output_path.exists():
        logger.info("Output file %s already exists and will be overwritten.", output_path)

    methods = []
    if args.force_method:
        methods = [args.force_method]
    else:
        methods = ["pypandoc", "html2docx", "fallback"]

    success = False
    for method in methods:
        if method == "pypandoc":
            if not check_pandoc_installed():
                logger.debug("pandoc binary not found in PATH; skipping pypandoc method.")
                continue
            success = try_pypandoc(input_path, output_path)
        elif method == "html2docx":
            success = try_html2docx(input_path, output_path)
        elif method == "fallback":
            success = fallback_naive(input_path, output_path)
        if success:
            break

    if not success:
        logger.error(
            "Conversion failed. To improve results, install one of the following toolchains:\n\n"
            "- Pandoc + pypandoc (best):\n"
            "    1. Install pandoc: https://pandoc.org/installing.html\n"
            "    2. pip install pypandoc\n\n"
            "- html2docx + markdown (good for HTML->DOCX):\n"
            "    pip install markdown html2docx\n\n"
            "- python-docx (fallback, basic formatting):\n"
            "    pip install python-docx\n\n"
            "Then re-run this script. You may also force a method with --force-method.\n"
        )
        sys.exit(3)

    logger.info("Conversion finished successfully: %s", output_path)


if __name__ == "__main__":
    main()