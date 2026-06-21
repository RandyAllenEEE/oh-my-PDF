"""
Bookmark Service
Ported key logic from 'pdfdir' project to support handling PDF bookmarks (outlines).
"""

import re
import logging
import os
import copy
from pathlib import Path
from typing import Dict, Any, List, Optional
from pypdf import PdfReader, PdfWriter, PageObject
from pypdf.generic import Destination, Fit

logger = logging.getLogger("pdf_toolbox.bookmark_service")

# --- Logic from pdfdir/src/convert.py ---

# Pre-compile regex patterns to avoid recompilation on every call
_PAGE_NUM_PATTERNS_RAW = [
    r"((?<!-)-?\d+)",  # Support negative numbers
    r"\((\d+)\)",  # Support ()
    r"\[(\d+)\]",  # Support []
    r"\{(\d+)\}",  # Support {}
    r"\<(\d+)\>",  # Support <>
    r"（(\d+)）",  # Support（）
    r"【(\d+)】",  # Support【】
    r"「(\d+)」",  # Support「」
    r"《(\d+)》",  # Support《》
    r"(\d*)",  # Final pattern, without numbers
]

COMPILED_PAGE_NUM_PATTERNS = [
    re.compile(r"(.*?)%s$" % pat) for pat in _PAGE_NUM_PATTERNS_RAW
]

PREFIX_SPACE_PATTERN = re.compile(r"\s*")


def split_page_num(text):
    """split between title and page number"""
    con, num = "", 1
    for pat in COMPILED_PAGE_NUM_PATTERNS:
        res = pat.search(text)
        if res:
            con, num = res.groups()
            break
    if con:
        con = con.rstrip(" .-@\t")
    if num == "":
        num = 1
    return con, int(num)


def text_to_list(text):
    if isinstance(text, list):
        return text
    return text.splitlines()


def is_in(title, exp):
    try:
        return bool(re.match(exp, title)) if exp else False
    except re.error as e:
        logger.error("Check regex error! %s", e)
        return False


def check_level(
    title, level0, level1, level2, level3=None, level4=None, level5=None, other=0
):
    """check the level of this title"""
    ls = [level0, level1, level2, level3, level4, level5]
    for i in range(len(ls)):
        idx = len(ls) - 1 - i  # reserve match
        if is_in(title, ls[idx]):
            return idx
    # no level found
    return other


def generate_level_pattern_by_prefix_space(dir_list):
    """Generate regex pattern by prefix space in dir text"""
    level_patterns = [None, None, None, None, None, None]
    # All space count in dir text
    count_set = set()
    for d in dir_list:
        match = PREFIX_SPACE_PATTERN.match(d)
        if match:
            count_set.add(len(match.group(0)))
    space_count_list = sorted(count_set)
    max_level = 5
    i = 0
    while space_count_list:
        count = space_count_list.pop(0)
        level_patterns[i] = r"\s{" + str(count) + "}"
        i += 1
        if i > max_level:
            level_patterns[max_level] = r"\s{" + str(count) + ",}"
            break
    return level_patterns


def convert_dir_text(
    dir_text,
    offset=0,
    level0=None,
    level1=None,
    level2=None,
    level3=None,
    level4=None,
    level5=None,
    other=0,
    level_by_space=True,  # Default to True for simpler usage in Toolbox
    fix_non_seq=False,
):
    l0, l1, pagenum, index_dict = 0, 0, -float("inf"), {}
    l2, l3, l4 = 0, 0, 0
    dir_list = text_to_list(dir_text)

    # Auto-detect levels by indentation is usually what users want
    if level_by_space:
        level0, level1, level2, level3, level4, level5 = (
            generate_level_pattern_by_prefix_space(dir_list)
        )

    i = 0
    for di in dir_list:
        di = di.rstrip()
        if not di:
            continue  # Skip empty lines

        title, num = split_page_num(di)
        if num > pagenum or not fix_non_seq:
            pagenum = num
        index_dict[i] = {"title": title, "real_num": pagenum + offset, "num": pagenum}
        level = check_level(
            title, level0, level1, level2, level3, level4, level5, other=other
        )
        if level == 5 and i != l4:
            index_dict[i]["parent"] = l4
        elif level == 4 and i != l3:
            index_dict[i]["parent"] = l3
            l4 = i
        elif level == 3 and i != l2:
            index_dict[i]["parent"] = l2
            l3 = i
        elif level == 2 and i != l1:
            index_dict[i]["parent"] = l1
            l2 = i
        elif level == 1 and i != l0:
            index_dict[i]["parent"] = l0
            l1 = i
        elif level == 0:
            l0 = i
        index_dict[i]["title"] = title.lstrip()
        i += 1
    return index_dict


# --- Logic from pdfdir/src/pdf/pdf.py & bookmark.py ---


class PdfWrapper(object):
    """Wrapper around pypdf to handle bookmark operations"""

    def __init__(self, path, keep_outline=False):
        self.path = path
        self.reader = PdfReader(open(path, "rb"), strict=False)
        self.pages_num = self._get_pages_num(self.reader.pages)
        self._writer = None
        self.keep_outline = keep_outline

    @property
    def writer(self):
        if not self._writer:
            writer = PdfWriter()
            self.copy_reader_to_writer(
                self.reader, writer, keep_outline=self.keep_outline
            )
            if not self.keep_outline:
                # Remove existing outlines if we're overwriting
                # In newer pypdf, we can just clear it or skip import_outline
                pass
            self._writer = writer
        return self._writer

    @staticmethod
    def copy_reader_to_writer(reader, writer, keep_outline=False):
        # Modern pypdf append is more stable
        writer.append(reader, import_outline=keep_outline)
        return writer

    @staticmethod
    def _get_pages_num(pages):
        pages_num = {}
        # pypdf pages iteration
        for i, page in enumerate(pages):
            try:
                pages_num[page.indirect_ref.idnum] = (
                    i  # Use index as page number logic inside pypdf?
                )
                # Actually pypdf page numbers are 0-indexed.
                # The original code mapped idnum to page_number.
            except Exception as e:
                logger.error(e)
        return pages_num

    def add_bookmark(self, title, pagenum, parent=None):
        # pagenum is 0-indexed in add_outline_item
        return self.writer.add_outline_item(
            title, pagenum, parent=parent, fit=Fit.xyz()
        )

    def save_pdf(self, output_path):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        if os.path.exists(output_path):
            os.remove(output_path)
        with open(output_path, "wb") as out:
            self.writer.write(out)
        return output_path


def _apply_bookmarks_to_pdf(pdf_wrapper, index_dict):
    if not index_dict:
        return

    m = max(index_dict.keys())
    parent_dict = {}  # {parent index: IndirectObject}
    max_page_num = len(pdf_wrapper.reader.pages) - 1

    for i in range(m + 1):
        if i not in index_dict:
            continue
        value = index_dict[i]

        # Calculate target page index (0-based)
        # value['real_num'] is the physical page number (1-based) intended directly from user input + offset
        target_page_index = min(max(0, value.get("real_num", 1) - 1), max_page_num)

        inobject = pdf_wrapper.add_bookmark(
            value.get("title", ""),
            target_page_index,
            parent_dict.get(value.get("parent")),
        )
        parent_dict[i] = inobject


class BookmarkService:
    def __init__(self):
        pass

    def add_bookmarks(
        self, input_path: str, output_path: str, toc_text: str, page_offset: int = 0
    ):
        """
        Parse toc_text and apply bookmarks to the PDF at input_path.
        Save to output_path.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"File not found: {input_path}")

        # 1. Parse Directory Text
        index_dict = convert_dir_text(
            toc_text,
            offset=page_offset,
            level_by_space=True,  # Assuming indentation based hierarchy
        )

        # 2. Add Bookmarks
        # We generally overwrite existing bookmarks when using this tool
        pdf = PdfWrapper(input_path, keep_outline=False)

        _apply_bookmarks_to_pdf(pdf, index_dict)

        # 3. Save
        pdf.save_pdf(output_path)
        return output_path

    def extract_bookmarks(self, input_path: str) -> str:
        """
        Extract bookmarks from PDF at input_path and return as formatted text.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"File not found: {input_path}")

        reader = PdfReader(input_path)
        outline = reader.outline

        if not outline:
            return ""

        return self._outline_to_text(outline, reader)

    def _outline_to_text(self, outline, reader, level=0) -> str:
        text = []
        for item in outline:
            if isinstance(item, list):
                # This is a sub-level, passed recursively
                # use previously established level + 1?
                # pypdf outline structure: [Item, [Child, Child], Item]
                # Actually pypdf structure is: Item, Item, [Child, Child] (where list follows the parent)
                # But sometimes it's nested.
                # Wait, pypdf outline is a list of (Destination | List[Destination | List ...])
                # If it's a list, it's children of the *preceding* item.
                # So if I encounter a list, I should increment level for *that list*.
                pass
                # However, my recursive call logic below handles it if I just iterate.
                # But if I iterate, I need to know if the item is a list.
                # If it is a list, I recurse with level+1.
                text.append(self._outline_to_text(item, reader, level + 1))
            else:
                # Destination
                try:
                    title = item.title
                    page_num = reader.get_destination_page_number(item)
                    if page_num is None:
                        page_num = 0
                    else:
                        page_num += 1  # 1-based for user display

                    indent = " " * (4 * level)  # 4 spaces per level
                    text.append(f"{indent}{title} {page_num}")
                except Exception as e:
                    logger.warning(f"Failed to extract bookmark item: {e}")
                    continue

        return "\n".join(text)
