from pathlib import Path

from pypdf import PdfWriter

from src.services.bookmark_service import (
    BookmarkService,
    convert_dir_text,
    split_page_num,
)


def write_sample_pdf(path: Path, pages: int = 2) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as output:
        writer.write(output)


def test_split_page_num_supports_at_separator():
    title, page = split_page_num("Chapter One @ 12")

    assert title == "Chapter One"
    assert page == 12


def test_convert_dir_text_uses_indentation_and_offset():
    toc = "Intro @ 1\n    Child @ 2"

    result = convert_dir_text(toc, offset=1)

    assert result[0]["title"] == "Intro"
    assert result[0]["real_num"] == 2
    assert result[1]["title"] == "Child"
    assert result[1]["parent"] == 0
    assert result[1]["real_num"] == 3


def test_add_and_extract_bookmarks_round_trip(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"
    write_sample_pdf(input_pdf, pages=2)

    service = BookmarkService()
    service.add_bookmarks(
        str(input_pdf),
        str(output_pdf),
        "Intro @ 1\n    Child @ 2",
    )

    extracted = service.extract_bookmarks(str(output_pdf))

    assert output_pdf.exists()
    assert "Intro 1" in extracted
    assert "    Child 2" in extracted
