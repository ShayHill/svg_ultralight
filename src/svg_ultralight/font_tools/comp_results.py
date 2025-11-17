"""Compare results between Inkscape and fontTools.

Function `check_font_tools_alignment` will let you know if it's relatively safe to
use `pad_text_mix` or `pad_text_ft`, which improve `pad_text` by assigning `line_gap`
values to the resulting PaddedText instance and by aligning with the actual descent
and ascent of a font instead of by attempting to infer these from a referenve string.

See Enum `FontBboxError` for the possible error codes and their meanings returned by
`check_font`.

You can use `draw_comparison` to debug or explore differences between fontTools and
Inkscape.

:author: Shay Hill
:created: 2025-06-08
"""

from __future__ import annotations

import enum
import itertools as it
import string
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from svg_ultralight.bounding_boxes.bound_helpers import new_bbox_rect, pad_bbox
from svg_ultralight.bounding_boxes.padded_text_initializers import (
    DEFAULT_Y_BOUNDS_REFERENCE,
    pad_text,
    pad_text_ft,
)
from svg_ultralight.constructors import new_element
from svg_ultralight.font_tools.font_info import FTFontInfo, get_svg_font_attributes
from svg_ultralight.inkscape import write_root
from svg_ultralight.root_elements import new_svg_root_around_bounds

if TYPE_CHECKING:
    import os
    from collections.abc import Iterator

    from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox


class FontBboxError(enum.Enum):
    """Classify the type of error between Inkscape and fontTools bounding boxes.

    INIT: Use `pad_text`.

    FontTools failed to run. This can happen with fonts that, inentionally or
    not, do not have the required tables or character sets to build a bounding box
    around the TEXT_TEXT. You can only use the `pad_text` PaddedText constructor.
    This font may work with other or ascii-only text.

    ELEM_Y: Use `pad_text` or `pad_text_mix` with cautions.

    The y coordinate of the element bounding box is off by more than 1% of
    the height. This error matters, because the y coordinates are used by
    `pad_bbox_ft` and `pad_bbox_mix`. You can use either of these functions with a
    y_bounds_reference element and accept some potential error in `line_gap` or
    explicitly pass `ascent` and `descent` values to `pad_text_ft` or `pad_text_mix`.

    SAFE_ELEM_X: Use `pad_text_mix`.

    The y bounds are accurate, but the x coordinate of the element
    bounding box is off by more than 1%. This is called "safe" because it is not used
    by pad_bbox_mix, but you cannot use `pad_text_ft` without expecting BoundingBox
    inaccuracies.

    LINE_Y: Use `pad_text` or `pad_text_mix` with caution.

    All of the above match, but the y coordinate of the line bounding box
    (the padded bounding box) is off by more than 1% of the height. This error
    matters as does ELEM_Y, but it does not exist for any font on my system. Fonts
    without ELEM_Y errors should not have LINE_Y errors.

    SAFE_LINE_X: Use `pad_text_mix`.

    All of the above match, but the x coordinate of the line bounding
    box (the padded bounding box) is off by more than 1%. This is safe or unsafe as
    SAFE_ELEM_X, but also does not exist for any font on my system.

    NO_ERROR: Use `pad_text_ft`.

    No errors were found. The bounding boxes match within 1% of the height.
    You can use `pad_text_ft` to get the same result as `pad_text` or `pad_text_mix`
    without the delay caused by an Inkscape call.
    """

    INIT = enum.auto()
    ELEM_Y = enum.auto()
    SAFE_ELEM_X = enum.auto()
    LINE_Y = enum.auto()
    SAFE_LINE_X = enum.auto()
    NO_ERROR = enum.auto()


# ===================================================================================
#   Produce some commonly used Western UTF-8 characters for test text.
# ===================================================================================


def _get_western_utf8() -> str:
    """Return a string of the commonly used Western UTF-8 character set."""
    western = " ".join(
        [
            string.ascii_lowercase,
            string.ascii_uppercase,
            string.digits,
            string.punctuation,
            "áÁéÉíÍóÓúÚñÑäÄëËïÏöÖüÜçÇàÀèÈìÌòÒùÙâÂêÊîÎôÔûÛãÃõÕåÅæÆøØœŒßÿŸ",
        ]
    )
    return western + " "


DEFAULT_TEST_TEXT = _get_western_utf8()


def _format_bbox_error(
    bbox_a: BoundingBox, bbox_b: BoundingBox
) -> tuple[int, int, int, int]:
    """Return the difference between two bounding boxes as a percentage of height."""
    width = bbox_a.width
    height = bbox_a.height
    diff = (
        bbox_b.x - bbox_a.x,
        bbox_b.y - bbox_a.y,
        bbox_b.width - bbox_a.width,
        bbox_b.height - bbox_a.height,
    )
    scaled_diff = (
        x / y for x, y in zip(diff, (height, height, width, height), strict=True)
    )
    dx, dy, dw, dh = (int(x * 100) for x in scaled_diff)
    return dx, dy, dw, dh


def check_font_tools_alignment(
    inkscape: str | os.PathLike[str],
    font: str | os.PathLike[str],
    text: str | None = None,
) -> tuple[FontBboxError, tuple[int, int, int, int] | None]:
    """Return an error code and the difference b/t Inkscape and fontTools bboxes.

    :param inkscape: path to an Inkscape executable
    :param font_path: path to the font file
    :return: a tuple of the error code and the percentage difference between the
        bounding boxes as a tuple of (dx, dy, dw, dh) or (error, None) if there was
        an error initializing fontTools.
    """
    if text is None:
        text = DEFAULT_TEST_TEXT
    try:
        svg_attribs = get_svg_font_attributes(font)
        text_elem = new_element("text", **svg_attribs, text=text)
        rslt_pt = pad_text(inkscape, text_elem)
        rslt_ft = pad_text_ft(
            font,
            text,
            y_bounds_reference=DEFAULT_Y_BOUNDS_REFERENCE,
        )
    except Exception:
        return FontBboxError.INIT, None

    error = _format_bbox_error(rslt_pt.tbox, rslt_ft.tbox)
    if error[1] or error[3]:
        return FontBboxError.ELEM_Y, error
    if error[0] or error[2]:
        return FontBboxError.SAFE_ELEM_X, error

    error = _format_bbox_error(rslt_pt.bbox, rslt_ft.bbox)
    if error[1] or error[3]:
        return FontBboxError.LINE_Y, error
    if error[0] or error[2]:
        return FontBboxError.SAFE_LINE_X, error

    return FontBboxError.NO_ERROR, None


def draw_comparison(
    inkscape: str | os.PathLike[str],
    output: str | os.PathLike[str],
    font: str | os.PathLike[str],
    text: str | None = None,
) -> None:
    """Draw a font in Inkscape and fontTools.

    :param inkscape: path to an Inkscape executable
    :param output: path to the output SVG file
    :param font: path to the font file
    :param text: the text to render. If None, the font name will be used.
    :effect: Writes an SVG file to the output path.

    Compare the rendering and bounding boxes of a font in Inkscape and fontTools. The
    bounding boxes drawn will always be accurate, but some fonts will not render the
    Inkscape version in a browser. Conversely, Inskcape will not render the fontTools
    version in Inkscape, because Inkscape does not read locally linked fonts. It
    usually works, and it a good place to start if you'd like to compare fontTools
    and Inkscape results.
    """
    if text is None:
        text = Path(font).stem
    font_size = 12
    font_attributes = get_svg_font_attributes(font)
    text_elem = new_element(
        "text",
        text=text,
        **font_attributes,
        font_size=font_size,
        fill="none",
        stroke="green",
        stroke_width=0.1,
    )
    padded_pt = pad_text(inkscape, text_elem)
    padded_ft = pad_text_ft(
        font,
        text,
        font_size,
        y_bounds_reference=DEFAULT_Y_BOUNDS_REFERENCE,
        fill="none",
        stroke="orange",
        stroke_width=0.1,
    )

    root = new_svg_root_around_bounds(pad_bbox(padded_pt.bbox, 1))
    root.append(
        new_bbox_rect(padded_pt.tbox, fill="none", stroke_width=0.07, stroke="red")
    )
    root.append(
        new_bbox_rect(padded_ft.tbox, fill="none", stroke_width=0.05, stroke="blue")
    )
    root.append(padded_pt.elem)
    root.append(padded_ft.elem)
    _ = sys.stdout.write(f"{Path(font).stem} comparison drawn at {output}.\n")
    _ = write_root(inkscape, Path(output), root)


def _iter_fonts(*fonts_dirs: Path) -> Iterator[Path]:
    """Yield a path to each ttf and otf file in the given directories.

    :param fonts_dir: directory to search for ttf and otf files, multiple ok
    :yield: paths to ttf and otf files in the given directories

    A helper function for _test_every_font_on_my_system.
    """
    if not fonts_dirs:
        return
    head, *tail = fonts_dirs
    ttf_files = head.glob("*.[tt][tt][ff]")
    otf_files = head.glob("*.[oO][tT][fF]")
    yield from it.chain(ttf_files, otf_files)
    yield from _iter_fonts(*tail)


def _test_every_font_on_my_system(
    inkscape: str | os.PathLike[str],
    font_dirs: list[Path],
    text: str | None = None,
) -> None:
    """Test every font on my system."""
    if not Path(inkscape).with_suffix(".exe").exists():
        _ = sys.stdout.write(f"Inkscape not found at {inkscape}\n")
        return
    font_dirs = [x for x in font_dirs if x.exists()]
    if not font_dirs:
        _ = sys.stdout.write("No font directories found.\n")
        return

    counts = dict.fromkeys(FontBboxError, 0)
    for font_path in _iter_fonts(*font_dirs):
        error, diff = check_font_tools_alignment(inkscape, font_path, text)
        counts[error] += 1
        if error is not FontBboxError.NO_ERROR:
            _ = sys.stdout.write(f"Error with {font_path.name}: {error.name} {diff}\n")
    for k, v in counts.items():
        _ = sys.stdout.write(f"{k.name}: {v}\n")


if __name__ == "__main__":
    _INKSCAPE = Path(r"C:\Program Files\Inkscape\bin\inkscape")
    _FONT_DIRS = [
        Path(r"C:\Windows\Fonts"),
        Path(r"C:\Users\shaya\AppData\Local\Microsoft\Windows\Fonts"),
    ]
    _test_every_font_on_my_system(_INKSCAPE, _FONT_DIRS)

    font = Path(r"C:\Windows\Fonts\arial.ttf")
    font = Path("C:/Windows/Fonts/Aptos-Display-Bold.ttf")
    info = FTFontInfo(font)
    draw_comparison(_INKSCAPE, "temp.svg", font, "AApple")
