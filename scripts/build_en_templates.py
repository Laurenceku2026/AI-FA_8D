"""Sync blank English 8D template from the authoritative local English_Example_8D.xlsx."""
from __future__ import annotations

import os

from openpyxl import load_workbook

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(HERE, "templates")
SOURCE = os.path.join(
    r"C:\Users\Laurence\Technical\Project\SaaS\DFSS Report Template",
    "AI-FA",
    "English_Example_8D.xlsx",
)
DEST = os.path.join(TEMPLATES, "English_Example_8D.xlsx")
CONTENT_ROWS = (9, 12, 15, 18, 19, 20, 21, 24, 27, 30, 33)


def build_blank_english_template(source: str = SOURCE, dest: str = DEST) -> None:
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    wb = load_workbook(source)
    ws = wb.active
    ws._images = []
    for row in CONTENT_ROWS:
        ws.cell(row, 1).value = None
        ws.cell(row, 1).number_format = "General"
    for addr in ("B6", "D6", "G6", "B7", "D7", "G7"):
        ws[addr].value = None
    for row in (34, 35):
        ws.row_dimensions[row].height = 30.0
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    wb.save(dest)


if __name__ == "__main__":
    build_blank_english_template()
    print("Wrote", DEST)
