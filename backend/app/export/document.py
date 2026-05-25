from __future__ import annotations

import re
from io import BytesIO

_LONG_TOKEN = re.compile(r"\S{56,}")


def _break_long_tokens(text: str, n: int = 55) -> str:
    def rep(m: re.Match[str]) -> str:
        s = m.group(0)
        return " ".join(s[i : i + n] for i in range(0, len(s), n))

    return _LONG_TOKEN.sub(rep, text)


def _is_stage(line: str) -> bool:
    return line.startswith("[") and line.endswith("]") and not line.startswith("[SEGMEN")


def build_docx(title: str, body: str, sources: str, meta_lines: list[str]) -> bytes:
    from docx import Document

    doc = Document()
    doc.add_heading(title, level=0)
    for m in meta_lines:
        doc.add_paragraph(m)
    doc.add_paragraph("")
    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[SEGMEN"):
            doc.add_heading(line.strip("[]"), level=2)
        elif _is_stage(line):
            p = doc.add_paragraph(line)
            p.runs[0].italic = True
        else:
            doc.add_paragraph(line)
    if sources:
        doc.add_page_break()
        doc.add_heading("Sumber dan Bukti", level=1)
        for raw in sources.split("\n"):
            if raw.strip():
                doc.add_paragraph(raw)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()


def build_pdf(title: str, body: str, sources: str, meta_lines: list[str]) -> bytes:
    from fpdf.enums import XPos, YPos
    from fpdf.fpdf import FPDF

    def enc(text: str) -> str:
        return _break_long_tokens(text).encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()

    def cell(text: str, size: int, style: str = "") -> None:
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(0, 6, enc(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    cell(title, 16, "B")
    for m in meta_lines:
        cell(m, 9)
    cell(body, 11)
    if sources:
        pdf.add_page()
        cell("Sumber dan Bukti", 13, "B")
        cell(sources, 9)
    return bytes(pdf.output())  # type: ignore[arg-type]
