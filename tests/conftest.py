"""Configuración de pytest: el proyecto se importa desde la raíz del repo."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _synthetic_pdf(lines):
    instructions = []
    for x, y, text in lines:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        instructions.append(f"BT /F1 9 Tf {x} {y} Td ({escaped}) Tj ET")
    stream = "\n".join(instructions).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
        + stream + b"\nendstream",
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    result.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(result)


@pytest.fixture
def synthetic_pdfs(tmp_path):
    """Create two fictional bank statements with real PDF structure."""
    bac = _synthetic_pdf([
        (40, 760, "BAC CREDOMATIC"),
        (40, 740, "Fecha de Corte 28-OCT-2026"),
        (78, 700, "****-****-****-4521"),
        (85, 680, "1000000000"),
        (182, 680, "OCT/10"),
        (227, 680, "UBER TRIP"),
        (440, 680, "125.00"),
    ])
    ficohsa = _synthetic_pdf([
        (40, 760, "BANCO FICOHSA"),
        (40, 740, "Periodo del 01/10/2026 al 28/10/2026"),
        (40, 720, "123456XXXXXX8932"),
        (124, 700, "MOVIMIENTO DE CUENTA"),
        (124, 680, "- TOTAL DE PAGOS Y CREDITOS"),
        (124, 660, "+ TOTAL DE FINANCIAMIENTOS"),
        (30, 640, "10/10/2026"),
        (92, 640, "111"),
        (124, 640, "PEDIDOS YA"),
        (385, 640, "L75.00"),
    ])
    files = [tmp_path / "bac.pdf", tmp_path / "ficohsa.pdf"]
    for path, content in zip(files, (bac, ficohsa), strict=True):
        path.write_bytes(content)
    return files
