"""Export a generated quest to a printable PDF.

Hybrid layout: title strip followed by cut-out task cards for the hunters
(no answers, no hints, packed tallest-first to save paper), and a
game-master cheat sheet with answers and hint bullets at the end.
Pure helper module: no Streamlit calls here so it stays testable and
reusable.
"""

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import cast

from fpdf import FPDF
from fpdf.enums import MethodReturnValue
from PIL import Image

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Pixels per mm at 96 dpi, to convert PIL pixel sizes to PDF millimetres.
PX_PER_MM = 96 / 25.4

# Task image box: fit inside, never upscale, always centered.
MAX_IMG_W = 140.0
MAX_IMG_H = 85.0
CARD_PAD = 3.0
CARD_GAP = 6.0

MUTED = (100, 100, 100)
FAINT = (130, 130, 130)


@dataclass
class QuestStop:
    number: int
    clue_word: str
    image: Image.Image
    hints: list[str] = field(default_factory=list)
    task_name: str = ""


@dataclass
class _Buffers:
    items: list[BytesIO] = field(default_factory=list)


class _QuestPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*FAINT)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _setup_fonts(pdf: FPDF) -> tuple[str, str, str]:
    """Return (body_font, heading_font, heading_style)."""
    try:
        pdf.add_font("DejaVu", "", _ASSETS_DIR / "DejaVuSans.ttf")
        body_font = "DejaVu"
    except (FileNotFoundError, RuntimeError):
        body_font = "Helvetica"  # latin-1 only, fallback if font missing
    try:
        pdf.add_font("Montserrat", "", _ASSETS_DIR / "Montserrat[wght].ttf")
        heading_font, heading_style = "Montserrat", ""
    except (FileNotFoundError, RuntimeError):
        heading_font, heading_style = "Helvetica", "B"
    return body_font, heading_font, heading_style


def _measure(pdf: FPDF, text: str) -> float:
    """Height in mm the text would occupy, without rendering anything."""
    return float(
        cast(
            float,
            pdf.multi_cell(
                w=0,
                text=text,
                dry_run=True,
                output=MethodReturnValue.HEIGHT,
                new_x="LMARGIN",
                new_y="NEXT",
            ),
        )
    )


def _fit_inside(w_mm: float, h_mm: float) -> tuple[float, float]:
    scale = min(MAX_IMG_W / w_mm, MAX_IMG_H / h_mm, 1.0)
    return w_mm * scale, h_mm * scale


def _scaled_size(img: Image.Image) -> tuple[float, float]:
    return _fit_inside(img.width / PX_PER_MM, img.height / PX_PER_MM)


def build_quest_pdf(stops: list[QuestStop], title: str = "Your hunt") -> bytes:
    """Render title strip + packed cut-out cards + game-master cheat sheet."""
    pdf = _QuestPDF(orientation="P", unit="mm", format="A4")
    body_font, heading_font, heading_style = _setup_fonts(pdf)
    body_bold_style = "B" if body_font == "Helvetica" else ""
    pdf.set_auto_page_break(True, margin=20)
    pdf.set_margins(15, 15, 15)
    buffers = _Buffers()
    total = len(stops)
    last_num = max((s.number for s in stops), default=None)

    # --- Title strip (not a cover page): tasks start right below ---
    pdf.add_page()
    pdf.set_font(heading_font, heading_style, 20)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(
        w=0, text=f"{title} — {total} stops",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font(body_font, "", 10)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        w=0,
        text=(
            "\nSolve each to find the next.\n"
            "Last answer shows where the prize is hiding.\n"
            "Cut along the dashed lines."
        ),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(6)

    # --- Hunter cards: packed flow, tallest-first print order ---
    ordered = sorted(stops, key=lambda s: _scaled_size(s.image)[1], reverse=True)
    for stop in ordered:
        w_mm, h_mm = _scaled_size(stop.image)
        if stop.number == last_num and total > 1:
            label = f"Stop {stop.number} of {total} → prize"
        else:
            label = f"Stop {stop.number} of {total}"
        pdf.set_font(heading_font, heading_style, 10)
        pdf.set_text_color(*MUTED)
        label_h = _measure(pdf, label)
        card_h = CARD_PAD + label_h + 3 + h_mm + CARD_PAD
        if pdf.get_y() > pdf.t_margin and pdf.will_page_break(card_h + CARD_GAP):
            pdf.add_page()
        card_top = pdf.get_y()
        pdf.set_y(card_top + CARD_PAD)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            w=0, text=label, align="C", new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(3)
        buf = BytesIO()
        stop.image.save(buf, format="PNG")
        buf.seek(0)
        buffers.items.append(buf)  # keep alive until output() embeds them
        x = pdf.l_margin + (pdf.epw - w_mm) / 2
        y = pdf.get_y()
        pdf.image(buf, x=x, y=y, w=w_mm, h=h_mm)
        card_bottom = y + h_mm + CARD_PAD
        pdf.set_dash_pattern(dash=2, gap=2)
        pdf.rect(
            pdf.l_margin, card_top,
            pdf.epw, card_bottom - card_top, style="D",
        )
        pdf.set_dash_pattern()
        pdf.set_y(card_bottom + CARD_GAP)

    # --- Game-master cheat sheet ---
    pdf.add_page()
    pdf.set_font(heading_font, heading_style, 16)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(
        w=0, text="Solutions and possible hints.", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font(body_font, "", 10)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        w=0,
        text=(
            "\nFor the game master only. Don't show the hunters.\n"
            "You don't have to use these — give as many or as few as you like."
        ),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(4)
    for stop in sorted(stops, key=lambda s: s.number):
        if stop.task_name:
            cheat_title = f"Stop {stop.number} — {stop.clue_word} ({stop.task_name})"
        else:
            cheat_title = f"Stop {stop.number} — {stop.clue_word}"
        pdf.set_font(body_font, body_bold_style, 11)
        pdf.set_text_color(0, 0, 0)
        block = _measure(pdf, cheat_title) + 2
        pdf.set_font(body_font, "", 10)
        pdf.set_text_color(0, 0, 0)
        block += sum(_measure(pdf, f"- {h}") for h in stop.hints)
        block += len(stop.hints) * 1 + 8
        if pdf.get_y() > pdf.t_margin and pdf.will_page_break(block):
            pdf.add_page()
        pdf.set_font(body_font, body_bold_style, 11)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(
            w=0, text=cheat_title, new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(2)
        pdf.set_font(body_font, "", 9.5)
        pdf.set_text_color(*MUTED)
        pdf.ln(1)
        pdf.set_font(body_font, "", 10)
        pdf.set_text_color(0, 0, 0)
        for h in stop.hints:
            pdf.multi_cell(
                w=0, text=f"- {h}", new_x="LMARGIN", new_y="NEXT",
            )
            pdf.ln(1)
        pdf.ln(8)

    return bytes(pdf.output())
