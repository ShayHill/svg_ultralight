"""Use fontTools to extract some font information and remove the problematic types.

This module is an alternative to the query module's `pad_text`. `pad_text` uses
Inkscape to inspect reference characters and create a PaddedText instance that can be
stacked and aligned similarly to how a word processor would stack and align text. For
instance, the string `gg` is treated as if it were the same height as the string
`Hh`, even though the `g` descends below the baseline and the `H` does not.

`new_padded_text` will do the same, but in a more sophisticated, if less reliable,
way. `new_padded_text` and its helper classes use fontTools to inspect the font file
and extract the values needed for a PaddedText instance. This has advantages and
disadvantages:

Advantages:
- does not require Inkscape to be installed.
- knows the actual ascent and descent of the font, not just inferences based on
  reference characters
- provides the line_gap and line_height, which Inkscape cannot
- much faster

Disadvantages:
- will fail for some fonts that do not have the necessary tables
- will not reflect any layout nuances that Inkscape might apply to the text
- does not adjust for font-weight and other characteristics that Inkscape *might*
- matching the specification of a font file to svg's font-family, font-style,
  font-weight, and font-stretch isn't always straightforward. It's worth a visual
  test to see how well your bounding boxes fit if you're using an unfamiliar font.
- does not support `font-variant`, `font-kerning`, `text-anchor`, and other
  attributes that `pad_text` would through Inkscape.

Will attempt to mimic `pad_text` output if a `y_bounds_reference` is provided. If
given, will calculate tpad and bpad the same way as `pad_text` does, using the y
extents of the reference character.

If no `y_bounds_reference` is provided, will center text between the max descent and
max ascent, which will be a big change from `pad_text` and which might be undesirable
for vertically centering all-caps text with no descenders. To center between baseline
and ascent, pass `descent` = 0 and let the module calculate the ascent from the font
file. Or pass a tall character like "}" as a `y_bounds_reference`.

The helper classes FTFontInfo and FTTextInfo are unfortunate noise to keep most of
the type kludging inside this module.

:author: Shay Hill
:created: 2025-05-31
"""

# pyright: reportUnknownMemberType = false
# pyright: reportPrivateUsage = false
# pyright: reportAttributeAccessIssue = false
# pyright: reportUnknownArgumentType = false
# pyright: reportUnknownVariableType = false
# pyright: reportUnknownParameterType = false
# pyright: reportMissingTypeStubs = false

from __future__ import annotations

import functools as ft
import itertools as it
import logging
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.font_tools.globs import DEFAULT_FONT_SIZE

if TYPE_CHECKING:
    import os


logging.getLogger("fontTools").setLevel(logging.ERROR)


class FTFontInfo:
    """Hide all the type kludging necessary to use fontTools."""

    def __init__(self, font_path: str | os.PathLike[str]) -> None:
        """Initialize the SUFont with a path to a TTF font file."""
        self._path = Path(font_path)
        if not self.path.exists():
            msg = f"Font file '{self.path}' does not exist."
            raise FileNotFoundError(msg)
        self._font = TTFont(self.path)

    @property
    def path(self) -> Path:
        """Return the path to the font file."""
        return self._path

    @property
    def font(self) -> TTFont:
        """Return the fontTools TTFont object."""
        return self._font

    @ft.cached_property
    def units_per_em(self) -> int:
        """Get the units per em for the font.

        :return: The units per em for the font. For a ttf, this will usually
            (always?) be 2048.
        :raises ValueError: If the font does not have a 'head' table or 'unitsPerEm'
            attribute.
        """
        try:
            maybe_units_per_em = cast("int | None", self.font["head"].unitsPerEm)
        except (KeyError, AttributeError) as e:
            msg = (
                f"Font '{self.path}' does not have"
                + " 'head' table or 'unitsPerEm' attribute: {e}"
            )
            raise ValueError(msg) from e
        if maybe_units_per_em is None:
            msg = f"Font '{self.path}' does not have 'unitsPerEm' defined."
            raise ValueError(msg)
        return maybe_units_per_em

    @ft.cached_property
    def kern_table(self) -> dict[tuple[str, str], int]:
        """Get the kerning pairs for the font.

        :return: A dictionary mapping glyph pairs to their kerning values.
        :raises ValueError: If the font does not have a 'kern' table.

        I haven't run across a font with multiple kern tables, but *if* a font had
        multiple tables and *if* the same pair were defined in multiple tables, this
        method would give precedence to the first occurrence. That behavior is copied
        from examples found online.
        """
        with suppress(KeyError, AttributeError):
            kern_tables = cast(
                "list[dict[tuple[str, str], int]]",
                [x.kernTable for x in self.font["kern"].kernTables],
            )
            return dict(x for d in reversed(kern_tables) for x in d.items())
        return {}

    @ft.cached_property
    def hhea(self) -> Any:
        """Get the horizontal header table for the font.

        :return: The horizontal header table for the font.
        :raises ValueError: If the font does not have a 'hhea' table.
        """
        try:
            return cast("Any", self.font["hhea"])
        except KeyError as e:
            msg = f"Font '{self.path}' does not have a 'hhea' table: {e}"
            raise ValueError(msg) from e

    def get_glyph_name(self, char: str) -> str:
        """Get the glyph name for a character in the font.

        :param char: The character to get the glyph name for.
        :return: The glyph name for the character.
        :raises ValueError: If the character is not found in the font.
        """
        ord_char = ord(char)
        char_map = cast("dict[int, str]", self.font.getBestCmap())
        if ord_char in char_map:
            return char_map[ord_char]
        msg = f"Character '{char}' not found in font '{self.path}'."
        raise ValueError(msg)

    def get_char_bounds(self, char: str) -> tuple[int, int, int, int]:
        """Return the min and max x and y coordinates of a glyph.

        There are two ways to get the bounds of a glyph, using an object from
        font["glyf"] or this awkward-looking method. Most of the time, they are the
        same, but when they disagree, this method is more accurate. Additionally,
        some fonts do not have a glyf table, so this method is more robust.
        """
        glyph_set = self.font.getGlyphSet()
        glyph_name = self.font.getBestCmap().get(ord(char))
        bounds_pen = BoundsPen(glyph_set)
        _ = glyph_set[glyph_name].draw(bounds_pen)

        pen_bounds = cast("None | tuple[int, int, int, int]", bounds_pen.bounds)
        if pen_bounds is None:
            return 0, 0, 0, 0
        xMin, yMin, xMax, yMax = pen_bounds
        return xMin, yMin, xMax, yMax

    def get_char_bbox(self, char: str) -> BoundingBox:
        """Return the BoundingBox of a character svg coordinates.

        Don't miss: this not only converts min and max x and y to x, y, width,
        height; it also converts from Cartesian coordinates (+y is up) to SVG
        coordinates (+y is down).
        """
        min_x, min_y, max_x, max_y = self.get_char_bounds(char)
        return BoundingBox(min_x, -max_y, max_x - min_x, max_y - min_y)

    def get_text_bounds(self, text: str) -> tuple[int, int, int, int]:
        """Return bounds of a string as xmin, ymin, xmax, ymax.

        :param font_path: path to a TTF font file
        :param text: a string to get the bounding box for

        The max x value of a string is the sum of the hmtx advances for each glyph
        with some adjustments:

        * The rightmost glyph's actual width is used instead of its advance (because
          no space is added after the last glyph).
        * The kerning between each pair of glyphs is added to the total advance.

        These bounds are in Cartesian coordinates, not translated to SVGs screen
        coordinates, and not x, y, width, height.
        """
        hmtx_table = cast("dict[str, tuple[int, int]]", self.font["hmtx"])

        names = [self.get_glyph_name(c) for c in text]
        bounds = [self.get_char_bounds(c) for c in text]
        total_advance = sum(hmtx_table[n][0] for n in names[:-1])
        total_kern = sum(self.kern_table.get((x, y), 0) for x, y in it.pairwise(names))
        min_xs, min_ys, max_xs, max_ys = zip(*bounds)
        min_x = min_xs[0]
        min_y = min(min_ys)

        max_x = total_advance + max_xs[-1] + total_kern
        max_y = max(max_ys)
        return min_x, min_y, max_x, max_y

    def get_text_bbox(self, text: str) -> BoundingBox:
        """Return the BoundingBox of a string svg coordinates.

        Don't miss: this not only converts min and max x and y to x, y, width,
        height; it also converts from Cartesian coordinates (+y is up) to SVG
        coordinates (+y is down).
        """
        min_x, min_y, max_x, max_y = self.get_text_bounds(text)
        return BoundingBox(min_x, -max_y, max_x - min_x, max_y - min_y)

    def get_lsb(self, char: str) -> float:
        """Return the left side bearing of a character."""
        hmtx = cast("dict[str, tuple[int, int]]", self.font["hmtx"])
        _, lsb = hmtx.metrics[self.get_glyph_name(char)]
        return lsb

    def get_rsb(self, char: str) -> float:
        """Return the right side bearing of a character."""
        glyph_name = self.get_glyph_name(char)
        glyph_width = self.get_char_bbox(char).width
        hmtx = cast("dict[str, tuple[int, int]]", self.font["hmtx"])
        advance, lsb = hmtx[glyph_name]
        return advance - (lsb + glyph_width)


class FTTextInfo:
    """Scale the fontTools font information for a specific text and font size."""

    def __init__(
        self,
        font: str | os.PathLike[str] | FTFontInfo,
        text: str,
        font_size: float,
        ascent: float | None = None,
        descent: float | None = None,
    ) -> None:
        """Initialize the SUText with text, a SUFont instance, and font size."""
        if isinstance(font, FTFontInfo):
            self._font = font
        else:
            self._font = FTFontInfo(font)
        self._text = text.rstrip(" ")
        self._font_size = font_size
        self._ascent = ascent
        self._descent = descent

    @property
    def font(self) -> FTFontInfo:
        """Return the font information."""
        return self._font

    @property
    def text(self) -> str:
        """Return the text."""
        return self._text

    @property
    def font_size(self) -> float:
        """Return the font size."""
        return self._font_size

    @property
    def scale(self) -> float:
        """Return the scale factor for the font size.

        :return: The scale factor for the font size.
        """
        return self.font_size / self.font.units_per_em

    @property
    def bbox(self) -> BoundingBox:
        """Return the bounding box of the text.

        :return: A BoundingBox in svg coordinates.
        """
        bbox = self.font.get_text_bbox(self.text)
        bbox.transform(scale=self.scale)
        return BoundingBox(*bbox.values())

    @property
    def ascent(self) -> float:
        """Return the ascent of the font."""
        if self._ascent is None:
            self._ascent = self.font.hhea.ascent * self.scale
        return self._ascent

    @property
    def descent(self) -> float:
        """Return the descent of the font."""
        if self._descent is None:
            self._descent = self.font.hhea.descent * self.scale
        return self._descent

    @property
    def line_gap(self) -> float:
        """Return the height of the capline for the font."""
        return self.font.hhea.lineGap * self.scale

    @property
    def line_spacing(self) -> float:
        """Return the line spacing for the font."""
        return self.descent + self.ascent + self.line_gap

    @property
    def tpad(self) -> float:
        """Return the top padding for the text."""
        return self.ascent + self.bbox.y

    @property
    def rpad(self) -> float:
        """Return the right padding for the text.

        This is the right side bearing of the last glyph in the text.
        """
        return self.font.get_rsb(self.text[-1]) * self.scale

    @property
    def bpad(self) -> float:
        """Return the bottom padding for the text."""
        return self.descent - self.bbox.y2

    @property
    def lpad(self) -> float:
        """Return the left padding for the text.

        This is the left side bearing of the first glyph in the text.
        """
        return self.font.get_lsb(self.text[0]) * self.scale

    @property
    def padding(self) -> tuple[float, float, float, float]:
        """Return the padding for the text as a tuple of (top, right, bottom, left)."""
        return self.tpad, self.rpad, self.bpad, self.lpad


def get_font_size_given_height(font: str | os.PathLike[str], height: float) -> float:
    """Return the font size that would give the given line height.

    :param font: path to a font file.
    :param height: desired line height in pixels.

    Where line height is the distance from the longest possible descender to the
    longest possible ascender.
    """
    font_info = FTFontInfo(font)
    units_per_em = font_info.units_per_em
    if units_per_em <= 0:
        msg = f"Font '{font}' has invalid units per em: {units_per_em}"
        raise ValueError(msg)
    line_height = font_info.hhea.ascent - font_info.hhea.descent
    return height / line_height * units_per_em


def get_padded_text_info(
    font: str | os.PathLike[str],
    text: str,
    font_size: float = DEFAULT_FONT_SIZE,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
) -> FTTextInfo:
    """Return a FTTextInfo object for the given text and font.

    :param font: path to a font file.
    :param text: the text to get the information for.
    :param font_size: the font size to use.
    :param ascent: the ascent of the font. If not provided, it will be calculated
        from the font file.
    :param descent: the descent of the font. If not provided, it will be calculated
        from the font file.
    :param y_bounds_reference: optional character or string to use as a reference
        for the ascent and descent. If provided, the ascent and descent will be the y
        extents of the capline reference. This argument is provided to mimic the
        behavior of the query module's `pad_text` function. `pad_text` does no
        inspect font files and relies on Inkscape to measure reference characters.
    :return: A FTTextInfo object with the information necessary to create a
        PaddedText instance: bbox, tpad, rpad, bpad, lpad.
    """
    font_info = FTFontInfo(font)
    if y_bounds_reference:
        capline_info = FTTextInfo(font_info, y_bounds_reference, font_size)
        ascent = -capline_info.bbox.y
        descent = capline_info.bbox.y2

    return FTTextInfo(font_info, text, font_size, ascent, descent)


# ===================================================================================
#   Infer svg font attributes from a ttf or otf file
# ===================================================================================

# This is the record nameID that most consistently reproduce the desired font
# characteristics in svg.
_NAME_ID = 1
_STYLE_ID = 2

# Windows
_PLATFORM_ID = 3


def _get_font_names(
    path_to_font: str | os.PathLike[str],
) -> tuple[str | None, str | None]:
    """Get the family and style of a font from a ttf or otf file path.

    :param path_to_font: path to a ttf or otf file
    :return: One of many names of the font (e.g., "HelveticaNeue-CondensedBlack") or
        None and a style name (e.g., "Bold") as a tuple or None. This seems to be the
        convention that semi-reliably works with Inkscape.

    These are loosely the font-family and font-style, but they will not usually work
    in Inkscape without some transation (see translate_font_style).
    """
    font = TTFont(path_to_font)
    name_table = cast("Any", font["name"])
    font.close()
    family = None
    style = None
    for i, record in enumerate(name_table.names):
        if record.nameID == _NAME_ID and record.platformID == _PLATFORM_ID:
            family = record.toUnicode()
            next_record = (
                name_table.names[i + 1] if i + 1 < len(name_table.names) else None
            )
            if (
                next_record is not None
                and next_record.nameID == _STYLE_ID
                and next_record.platformID == _PLATFORM_ID
            ):
                style = next_record.toUnicode()
            break
    return family, style


_FONT_STYLE_TERMS = [
    "italic",
    "oblique",
]
_FONT_WEIGHT_MAP = {
    "ultralight": "100",
    "demibold": "600",
    "light": "300",
    "bold": "bold",
    "black": "900",
}
_FONT_STRETCH_TERMS = [
    "ultra-condensed",
    "extra-condensed",
    "semi-condensed",
    "condensed",
    "normal",
    "semi-expanded",
    "extra-expanded",
    "ultra-expanded",
    "expanded",
]


def _translate_font_style(style: str | None) -> dict[str, str]:
    """Translate the myriad font styles retured by ttLib into valid svg styles.

    :param style: the style string from a ttf or otf file, extracted by
        _get_font_names(path_to_font)[1].
    :return: a dictionary with keys 'font-style', 'font-weight', and 'font-stretch'

    Attempt to create a set of svg font attributes that will reprduce a desired ttf
    or otf font.
    """
    result: dict[str, str] = {}
    if style is None:
        return result
    style = style.lower()
    for font_style_term in _FONT_STYLE_TERMS:
        if font_style_term in style:
            result["font-style"] = font_style_term
            break
    for k, v in _FONT_WEIGHT_MAP.items():
        if k in style:
            result["font-weight"] = v
            break
    for font_stretch_term in _FONT_STRETCH_TERMS:
        if font_stretch_term in style:
            result["font-stretch"] = font_stretch_term
            break
    return result


def get_svg_font_attributes(path_to_font: str | os.PathLike[str]) -> dict[str, str]:
    """Attempt to get svg font attributes (font-family, font-style, etc).

    :param path_to_font: path to a ttf or otf file
    :return: {'font-family': 'AgencyFB-Bold'}
    """
    svg_font_attributes: dict[str, str] = {}
    family, style = _get_font_names(path_to_font)
    if family is None:
        return svg_font_attributes
    svg_font_attributes["font-family"] = family
    svg_font_attributes.update(_translate_font_style(style))
    return svg_font_attributes
