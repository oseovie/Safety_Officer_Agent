"""Minimal PDF export for the safety risk register.

This intentionally avoids third-party packages so the app remains easy to run.
"""

from __future__ import annotations

from textwrap import wrap


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN = 44
LINE_HEIGHT = 14
MAX_TEXT_WIDTH = 92


def pdf_escape(text: object) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def add_line(pages: list[list[str]], text: object = "", size: int = 10) -> None:
    if not pages:
        pages.append([])
    pages[-1].append((str(text), size))
    max_lines = int((PAGE_HEIGHT - (MARGIN * 2)) / LINE_HEIGHT)
    if len(pages[-1]) >= max_lines:
        pages.append([])


def add_wrapped(pages: list[list[str]], label: str, value: object, size: int = 10) -> None:
    text = f"{label}: {value}"
    lines = wrap(text, width=MAX_TEXT_WIDTH) or [text]
    for line in lines:
        add_line(pages, line, size)


def build_pdf(risks: list[dict[str, object]]) -> bytes:
    pages: list[list[str]] = [[]]
    add_line(pages, "Safety Risk Register", 18)
    add_line(pages, "Generated from the local risk management engine.", 10)
    add_line(pages)

    if not risks:
        add_line(pages, "No risks logged.", 11)

    for index, risk in enumerate(risks, start=1):
        add_line(pages, f"{index}. {risk.get('task', '')}", 13)
        add_wrapped(pages, "ID", risk.get("id", ""))
        add_wrapped(pages, "Status", risk.get("status", ""))
        add_wrapped(pages, "Hazard", risk.get("hazard", ""))
        add_wrapped(pages, "People at risk", risk.get("people_at_risk", ""))
        add_wrapped(pages, "Location", risk.get("location", ""))
        add_wrapped(pages, "Category", risk.get("category", ""))
        add_wrapped(
            pages,
            "Initial risk",
            f"{risk.get('initial_score', '')}/25 ({risk.get('initial_level', '')})",
        )
        add_wrapped(
            pages,
            "Residual risk",
            f"{risk.get('residual_score', '')}/25 ({risk.get('residual_level', '')})",
        )
        add_wrapped(pages, "Owner", risk.get("owner", ""))
        add_wrapped(pages, "Due", risk.get("due_at", ""))
        add_wrapped(
            pages,
            "Verification",
            risk.get("verification_note") or risk.get("verification_required", ""),
        )
        add_line(pages)

    objects: list[bytes] = []
    catalog_id = 1
    pages_id = 2
    font_id = 3
    page_ids: list[int] = []

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for page in pages:
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_ids.append(page_id)

        stream_lines = ["BT", f"/F1 10 Tf", f"{MARGIN} {PAGE_HEIGHT - MARGIN} Td"]
        current_size = 10
        first_line = True
        for text, size in page:
            if size != current_size:
                stream_lines.append(f"/F1 {size} Tf")
                current_size = size
            if first_line:
                first_line = False
            else:
                stream_lines.append(f"0 -{LINE_HEIGHT} Td")
            stream_lines.append(f"({pdf_escape(text)}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("utf-8")

        objects.append(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("utf-8")
        )
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("utf-8")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)
