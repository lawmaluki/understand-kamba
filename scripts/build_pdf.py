"""
Render a docs/*.md file to a styled A4 PDF (headings, paragraphs, bullet and
numbered lists, tables, code blocks, **bold**). Needs reportlab and Windows'
Segoe UI / Consolas fonts (the PDF's standard fonts can't show ĩ and ũ).

    python scripts/build_pdf.py docs/DOCUMENTATION.md docs/Understand-Kamba-Documentation.pdf
"""
import re
import sys
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, KeepTogether, ListFlowable, ListItem, Paragraph,
                                Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle)

SRC, OUT = sys.argv[1], sys.argv[2]
with open(SRC, encoding="utf-8") as _f:
    DOC_TITLE = next(line[2:].strip() for line in _f if line.startswith("# "))

FONTS = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("UI", rf"{FONTS}\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("UI-Bold", rf"{FONTS}\segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("UI-Semi", rf"{FONTS}\seguisb.ttf"))
pdfmetrics.registerFont(TTFont("Mono", rf"{FONTS}\consola.ttf"))
pdfmetrics.registerFontFamily("UI", normal="UI", bold="UI-Bold", italic="UI", boldItalic="UI-Bold")

INK, MUTED, LINE = colors.HexColor("#171717"), colors.HexColor("#525252"), colors.HexColor("#E5E5E5")
BUTTER, BUTTER_50, BUTTER_700 = colors.HexColor("#F8E27A"), colors.HexColor("#FEFBEA"), colors.HexColor("#8C6B12")
CODE_BG = colors.HexColor("#F5F5F4")

body = ParagraphStyle("body", fontName="UI", fontSize=10, leading=15, textColor=INK, spaceAfter=6)
title = ParagraphStyle("title", parent=body, fontName="UI-Semi", fontSize=26, leading=31, spaceAfter=8)
subtitle = ParagraphStyle("subtitle", parent=body, fontSize=12, leading=17, textColor=MUTED, spaceAfter=4)
meta = ParagraphStyle("meta", parent=body, fontSize=9, textColor=MUTED, spaceAfter=14)
h2 = ParagraphStyle("h2", parent=body, fontName="UI-Semi", fontSize=16, leading=21, spaceBefore=16, spaceAfter=6)
h3 = ParagraphStyle("h3", parent=body, fontName="UI-Semi", fontSize=12, leading=16, spaceBefore=10, spaceAfter=4)
cell = ParagraphStyle("cell", parent=body, fontSize=8.5, leading=12, spaceAfter=0)
cell_head = ParagraphStyle("cellhead", parent=cell, fontName="UI-Bold")
code = ParagraphStyle("code", fontName="Mono", fontSize=8.5, leading=12, textColor=INK)


def inline(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(text))


def table(rows: list[list[str]], width: float) -> Table:
    ncols = len(rows[0])
    # Each column at least as wide as its longest unbreakable word; spare width goes to wordier columns.
    min_w = [max(pdfmetrics.stringWidth(w, "UI-Bold", 8.5) for r in rows for w in (r[i].split() or [""])) + 13
             for i in range(ncols)]
    lengths = [max(len(r[i]) for r in rows) for i in range(ncols)]
    spare = max(width - sum(min_w), 0)
    col_w = [m + spare * n / sum(lengths) for m, n in zip(min_w, lengths)]
    col_w = [c * width / sum(col_w) for c in col_w]
    data = [[Paragraph(inline(c), cell_head if ri == 0 else cell) for c in r] for ri, r in enumerate(rows)]
    t = Table(data, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BUTTER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BUTTER_50]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def code_block(lines: list[str], width: float) -> Table:
    t = Table([[Preformatted("\n".join(lines), code)]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG), ("LINEBEFORE", (0, 0), (0, -1), 2, BUTTER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def parse(md: str, width: float) -> list:
    story, lines, i = [], md.splitlines(), 0
    pending = []  # headings and "Request:"-style lead-ins, kept on the same page as what follows
    seen_subtitle = False

    def add(flowable, keep_with_next=False):
        pending.append(flowable)
        if keep_with_next:
            return
        if len(pending) > 1 and isinstance(flowable, Table) and flowable.wrap(width, 10**6)[1] > 60 * mm:
            story.append(CondPageBreak(55 * mm))  # long table: may split, but starts where a few rows fit
            story.extend(pending)
        else:
            story.append(KeepTogether(pending[:]) if len(pending) > 1 else flowable)
        pending.clear()

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("```"):
            block, i = [], i + 1
            while not lines[i].startswith("```"):
                block.append(lines[i]); i += 1
            i += 1
            add(code_block(block, width)); story.append(Spacer(1, 6))
        elif line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), title)); i += 1
        elif line.startswith(("## ", "### ")):
            add(Paragraph(inline(line.split(" ", 1)[1]), h2 if line.startswith("## ") else h3), keep_with_next=True)
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            add(table(rows, width)); story.append(Spacer(1, 8))
        elif line.startswith("- ") or re.match(r"\d+\. ", line):
            numbered = not line.startswith("- ")
            items = []
            while i < len(lines) and (re.match(r"\d+\. ", lines[i]) if numbered else lines[i].startswith("- ")):
                items.append(ListItem(Paragraph(inline(lines[i].split(" ", 1)[1]), body), leftIndent=14))
                i += 1
            add(ListFlowable(items, bulletType="1" if numbered else "bullet", bulletFontName="UI-Semi",
                             bulletColor=BUTTER_700, leftIndent=16, bulletFontSize=10))
            story.append(Spacer(1, 4))
        else:
            para = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"(#|- |\||```|\d+\. )", lines[i]):
                para.append(lines[i]); i += 1
            text = " ".join(para)
            if not seen_subtitle:
                add(Paragraph(inline(text), subtitle)); seen_subtitle = True
            elif text.startswith(("Last updated", "Date:")):
                add(Paragraph(inline(text), meta))
            else:
                add(Paragraph(inline(text), body), keep_with_next=text.endswith(":"))
    story.extend(pending)
    return story


def decorate(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(BUTTER)
    canvas.rect(0, h - 5, w, 5, stroke=0, fill=1)
    canvas.setFont("UI", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 12 * mm, DOC_TITLE)
    canvas.drawRightString(w - doc.rightMargin, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm,
                        bottomMargin=22 * mm, title=DOC_TITLE, author="Lawrence Maluki")
with open(SRC, encoding="utf-8") as f:
    doc.build(parse(f.read(), doc.width), onFirstPage=decorate, onLaterPages=decorate)
print("wrote", OUT)
