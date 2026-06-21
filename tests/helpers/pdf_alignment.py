from __future__ import annotations

import shutil
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


PAGE_SIZE = (720, 480)
CUSTOM_BOXES = {
    "TOPLEFT": (0.18, 0.18, 0.45, 0.30),
    "BOTTOMRIGHT": (0.55, 0.60, 0.90, 0.76),
}


def has_ghostscript() -> bool:
    return bool(
        shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")
    )


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def scale_fraction_box(
    box: tuple[float, float, float, float], width: float, height: float
) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = box
    return x0 * width, y0 * height, x1 * width, y1 * height


def write_image_pdf(path: Path) -> None:
    image = Image.new("RGB", PAGE_SIZE, "white")
    draw = ImageDraw.Draw(image)
    for box in CUSTOM_BOXES.values():
        x0, y0, x1, y1 = scale_fraction_box(box, *PAGE_SIZE)
        draw.rectangle([x0, y0, x1, y1], outline="lightgray", width=2)
    image.save(path, "PDF", resolution=72.0)


def write_text_image_pdf(path: Path) -> dict[str, tuple[float, float, float, float]]:
    image = Image.new("RGB", PAGE_SIZE, "white")
    draw = ImageDraw.Draw(image)
    font = load_font(44)
    positions = {"ALPHA": (130, 95), "OMEGA": (430, 315)}
    expected: dict[str, tuple[float, float, float, float]] = {}

    for word, position in positions.items():
        draw.text(position, word, fill="black", font=font)
        expected[word] = draw.textbbox(position, word, font=font)

    image.save(path, "PDF", resolution=72.0)
    return expected


def expected_custom_boxes_for_pdf(
    pdf_path: Path,
) -> dict[str, tuple[float, float, float, float]]:
    with fitz.open(pdf_path) as doc:
        page_rect = doc[0].rect
        return {
            word: scale_fraction_box(box, page_rect.width, page_rect.height)
            for word, box in CUSTOM_BOXES.items()
        }


def assert_dual_layer_pdf_has_text_at(
    pdf_path: Path,
    expected_boxes: dict[str, tuple[float, float, float, float]],
    tolerance: float = 24.0,
) -> None:
    with fitz.open(pdf_path) as doc:
        assert len(doc) == 1
        page = doc[0]
        assert page.get_images(full=True), "expected the original image layer to remain"

        for word, expected in expected_boxes.items():
            rects = page.search_for(word)
            assert rects, f"expected searchable text for {word}"
            rect = rects[0]
            center_x = (rect.x0 + rect.x1) / 2
            center_y = (rect.y0 + rect.y1) / 2
            x0, y0, x1, y1 = expected

            assert x0 - tolerance <= center_x <= x1 + tolerance, (
                f"{word} x-center {center_x:.1f} outside expected " f"{x0:.1f}-{x1:.1f}"
            )
            assert y0 - tolerance <= center_y <= y1 + tolerance, (
                f"{word} y-center {center_y:.1f} outside expected " f"{y0:.1f}-{y1:.1f}"
            )
