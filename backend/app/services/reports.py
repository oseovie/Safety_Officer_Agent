from io import BytesIO

from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def build_pdf_report(title: str, rows: list[dict[str, object]]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle(title)
    pdf.drawString(72, 740, title)
    y = 710
    for row in rows[:40]:
        pdf.drawString(72, y, f"{row.get('title', row.get('id'))} | {row.get('status', '')} | {row.get('risk_level', '')}")
        y -= 18
        if y < 72:
            pdf.showPage()
            y = 740
    pdf.save()
    return buffer.getvalue()


def build_excel_report(rows: list[dict[str, object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Safety Records"
    headers = ["id", "title", "location", "status", "risk_level", "created_at"]
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header, "") for header in headers])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
