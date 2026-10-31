"""Genera los PDF del dataset (data/*.pdf) a partir de los textos de scripts/fuentes_pdf/*.md.

Por que existe: la consigna pide que la metadata incluya la PAGINA de origen. Los .md no tienen paginas
(se indexan como pagina 1), asi que parte del dataset son PDF reales de varias paginas.

Uso (solo hace falta si queres regenerar los PDF; ya estan en data/):
    pip install reportlab
    python scripts/generar_pdfs.py

Formato de las fuentes: Markdown simple (# titulo, ## seccion, - lista, > nota, **negrita**) y la marca
<!-- salto --> para forzar un salto de pagina.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "scripts" / "fuentes_pdf"
DESTINO = RAIZ / "data"
SALTO = "<!-- salto -->"


def _inline(texto: str) -> str:
    """Escapa XML y convierte **negrita** a <b>."""
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)


def construir(fuente: Path, destino: Path) -> int:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=estilos["Title"], fontSize=18, leading=22, alignment=TA_LEFT, spaceAfter=10)
    seccion = ParagraphStyle("s", parent=estilos["Heading2"], fontSize=13, leading=16, spaceBefore=12, spaceAfter=4)
    cuerpo = ParagraphStyle("c", parent=estilos["BodyText"], fontSize=11, leading=15, spaceAfter=6)
    nota = ParagraphStyle("n", parent=cuerpo, fontName="Helvetica-Oblique", textColor=colors.HexColor("#555555"))
    item = ParagraphStyle("i", parent=cuerpo, leftIndent=14, bulletIndent=2, spaceAfter=3)

    historia: list = []
    for linea in fuente.read_text(encoding="utf-8").split("\n"):
        linea = linea.rstrip()
        if not linea:
            historia.append(Spacer(1, 2))
        elif linea == SALTO:
            historia.append(PageBreak())
        elif linea.startswith("## "):
            historia.append(Paragraph(_inline(linea[3:]), seccion))
        elif linea.startswith("# "):
            historia.append(Paragraph(_inline(linea[2:]), titulo))
        elif linea.startswith("> "):
            historia.append(Paragraph(_inline(linea[2:]), nota))
        elif linea.startswith("- "):
            historia.append(Paragraph(_inline(linea[2:]), item, bulletText="•"))
        else:
            historia.append(Paragraph(_inline(linea), cuerpo))

    documento = SimpleDocTemplate(
        str(destino), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        title=fuente.stem, author="Mercado Austral S.A. (documento ficticio)",
    )
    documento.build(historia)
    return len(re.findall(re.escape(SALTO), fuente.read_text(encoding="utf-8"))) + 1


def main() -> int:
    try:
        import reportlab  # noqa: F401
    except ImportError:
        print("Falta reportlab: pip install reportlab", file=sys.stderr)
        return 1
    fuentes = sorted(FUENTES.glob("*.md"))
    if not fuentes:
        print(f"No hay fuentes en {FUENTES}", file=sys.stderr)
        return 1
    DESTINO.mkdir(exist_ok=True)
    for fuente in fuentes:
        destino = DESTINO / f"{fuente.stem}.pdf"
        paginas = construir(fuente, destino)
        print(f"{destino.relative_to(RAIZ)}  ({paginas} paginas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
