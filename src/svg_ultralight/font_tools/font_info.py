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

import math
import functools as ft
import itertools as it
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from fontTools.ttLib import TTFont

from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.constructors import new_element
from svg_ultralight.string_conversion import format_attr_dict, format_number, encode_to_css_class_name
from fontTools.ttLib import TTFont
import fontTools.ttLib.tables.otTables as otTables
from contextlib import suppress
from fontTools.ttLib import TTFont
# from fontTools.ttLib.tables._g_p_o_s import GPOS

if TYPE_CHECKING:
    import os

    from fontTools.ttLib.tables._g_l_y_f import Glyph


# def extract_kerning(font_path):
def extractKerningFromGPOS(gpos, font):
    """
    Extract kerning information from a font's GPOS table using fontTools.
    
    Args:
        font_path (str): Path to the font file (TTF or OTF).
    
    Returns:
        dict: Dictionary of kerning pairs and their values.
    """
    # Load the font
    # font = TTFont(font_path)
    
    # Check if GPOS table exists
    if 'GPOS' not in font:
        return {}
    
    gpos = font['GPOS']
    kerning_pairs = {}
    
    # Get the GPOS table's lookup list
    lookup_list = gpos.table.LookupList.Lookup if gpos.table.LookupList else []
    
    for lookup in lookup_list:
        # Check for PairPos (kerning) lookups (Type 2)
        if lookup.LookupType == 2:
            for subtable in lookup.SubTable:
                if hasattr(subtable, 'PairSet'):
                    # Handle PairPos Format 1 (pair adjustment)
                    for pair_set, first_glyph in zip(subtable.PairSet, subtable.Coverage.glyphs):
                        for pair_value_record in pair_set.PairValueRecord:
                            second_glyph = pair_value_record.SecondGlyph
                            # Get kerning value (XAdvance or Value1)
                            value = pair_value_record.Value1.XAdvance if pair_value_record.Value1 else 0
                            kerning_pairs[(first_glyph, second_glyph)] = value
                elif hasattr(subtable, 'Class1Record'):
                    # Handle PairPos Format 2 (class-based kerning)
                    first_classes = subtable.ClassDef1.classDefs
                    second_classes = subtable.ClassDef2.classDefs
                    for glyph1, class1 in first_classes.items():
                        for glyph2, class2 in second_classes.items():
                            try:
                                value_record = subtable.Class1Record[class1].Class2Record[class2]
                                value = value_record.Value1.XAdvance if value_record.Value1 else 0
                                if value != 0:
                                    kerning_pairs[(glyph1, glyph2)] = value
                            except IndexError:
                                continue
    
    font.close()
    return kerning_pairs


# def extractKerningFromGPOS(gpos, font):
#     kernings = []
#     for lookup in gpos.table.LookupList.Lookup:
#         # LookupType 2 is Pair Adjustment
#         if lookup.LookupType == 2:
#             for subtable in lookup.SubTable:
#                 if isinstance(subtable, otTables.PairPos):
#                     for pairSet in subtable.PairSet:
#                         breakpoint()
#                         firstGlyph = font.getGlyphName(pairSet.Glyph)
#                         for pairValueRecord in pairSet.PairValueRecord:
#                             secondGlyph = font.getGlyphName(pairValueRecord.SecondGlyph)
#                             value = pairValueRecord.Value1.XAdvance
#                             kernings.append((firstGlyph, secondGlyph, value))
#     return kernings

# def extractKerningFromGPOS(gpos):
#    kernings = []
#    for lookup in gpos.table.LookupList.Lookup:
#        if lookup.LookupType == 2:  # LookupType 2 is Pair Adjustment
#            for subtable in lookup.SubTable:
#                if isinstance(subtable, otTables.PairPos):
#                    for pairSet in subtable.PairSet:
#                        for pairValueRecord in pairSet.PairValueRecord:
#                            firstGlyph = font.getGlyphName(pairSet.Glyph)
#                            secondGlyph = font.getGlyphName(pairValueRecord.SecondGlyph)
#                            value = pairValueRecord.Value1.XAdvance
#                            kernings.append((firstGlyph, secondGlyph, value))
#    return kernings



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

        # with suppress (KeyError, AttributeError):
        #     return extractKerningFromGPOS(self.font["GPOS"], self.font)
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

    @ft.cached_property
    def glyf(self) -> dict[str, Glyph]:
        """Get the glyph table for the font.

        :return: The glyph table for the font.
        :raises ValueError: If the font does not have a 'glyf' table.
        """
        try:
            glyf = cast("dict[str, Glyph]", self.font["glyf"])
            return dict(glyf)
        except KeyError as e:
            msg = f"Font '{self.path}' does not have a 'glyf' table: {e}"
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

    def get_glyph(self, char: str) -> Glyph:
        """Get the glyph name for a character in the font.

        :param char: The character to get the glyph for.
        :return: The glyph name for the character.
        :raises ValueError: If the character is not found in the font.
        """
        name = self.get_glyph_name(char)
        return self.glyf[name]

    def get_char_bounds_using_pen(self, char: str) -> tuple[int, int, int, int]:

        from fontTools.pens.ttGlyphPen import TTGlyphPen
        from fontTools.pens.boundsPen import BoundsPen

        glyph_set = self.font.getGlyphSet()

        # Get the glyph name for the character
        glyph_name = self.font.getBestCmap().get(ord(char))

        # Create a pen to compute the bounding box
        bounds_pen = BoundsPen(glyph_set)

        # Draw the glyph outline with the bounds pen
        _ = glyph_set[glyph_name].draw(bounds_pen)

        # Get the bounding box
        pen_bounds = bounds_pen.bounds
        if pen_bounds is None:
            return 0, 0, 0, 0
        xMin, yMin, xMax, yMax = pen_bounds
        return xMin, yMin, xMax, yMax

    def get_char_bounds(self, char: str) -> tuple[int, int, int, int]:
        """Get the bounds of a glyph in the font.

        :param char: The character to get the bounds for.
        :return: A tuple of (xmin, ymin, xmax, ymax) for the glyph.
        """
        return self.get_char_bounds_using_pen(char)
        glyph = self.get_glyph(char)
        try:
            return glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax
        except AttributeError:
            return 0, 0, 0, 0

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
        bounds = [self.get_char_bounds_using_pen(c) for c in text]
        # aaa = [self.get_char_bounds_using_pen(c) for c in text]
        # if aaa != bounds:
        #     breakpoint()
        total_advance = sum(hmtx_table[n][0] for n in names[:-1])
        aaa = sum(hmtx_table[n][0] for n in names)
        total_kern = sum(self.kern_table.get((x, y), 0) for x, y in it.pairwise(names))
        min_xs, min_ys, max_xs, max_ys = zip(*bounds)
        min_x = min_xs[0]
        min_y = min(min_ys)

        last_char_width = max_xs[-1] - min_xs[-1]
        max_x = total_advance + max_xs[-1] + total_kern
        # max_x = aaa + total_kern - self.get_rsb(text[-1]) - min_x
        max_y = max(max_ys)

        # italic_angle = self.font["post"].italicAngle
        # x_height = self.font["OS/2"].sxHeight
        # slant = math.tan(math.radians(-italic_angle))
        # x_offset = (x_height / 2) * slant
        # min_x += x_offset
        # breakpoint()
        # max_x += x_offset
        return min_x, min_y, max_x, max_y

    def get_text_bounds2(self, text: str) -> tuple[int, int, int, int]:
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
        bounds = [self.get_char_bounds_using_pen(c) for c in text]
        total_advance = sum(hmtx_table[n][0] for n in names[:-1])
        total_kern = sum(self.kern_table.get((x, y), 0) for x, y in it.pairwise(names))
        min_xs, min_ys, max_xs, max_ys = zip(*bounds)
        min_x = min_xs[0]
        min_y = min(min_ys)
        max_x = total_advance + max_xs[-1] + total_kern
        max_y = max(max_ys)
        return min_x, min_y, max_x, max_y

    def get_rsb(self, char: str) -> float:
        """Return the right side bearing of a character."""
        glyph_name = self.get_glyph_name(char)
        glyph_metrics = self.get_glyph(char)
        glyph_width = glyph_metrics.xMax - glyph_metrics.xMin

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
    def font_tools_bounds(self) -> tuple[float, float, float, float]:
        """Return bounds of a string as xmin, ymin, xmax, ymax.

        :param font_path: path to a TTF font file
        :param text: a string to get the bounding box for

        These bounds are in Cartesian coordinates, not translated to SVGs screen
        coordinates, and not x, y, width, height.
        """
        kern_table = self.font.kern_table
        hmtx_table = cast("dict[str, tuple[int, int]]", self.font.font["hmtx"])

        names = [self.font.get_glyph_name(c) for c in self.text]
        bounds = [self.font.get_char_bounds(c) for c in self.text]
        total_advance = sum(hmtx_table[n][0] for n in names[:-1])
        total_kern = sum(kern_table.get((x, y), 0) for x, y in it.pairwise(names))
        min_xs, min_ys, max_xs, max_ys = zip(*bounds)
        min_x = min_xs[0]
        min_y = min(min_ys)
        max_x = total_advance + max_xs[-1] + total_kern
        max_y = max(max_ys)
        return min_x, min_y, max_x, max_y

    @property
    def bbox(self) -> BoundingBox:
        """Return the bounding box of the text.

        :return: A BoundingBox in svg coordinates.
        """
        min_x, min_y, max_x, max_y = (
            x * self.scale for x in self.font.get_text_bounds(self.text)
        )
        width = max_x - min_x
        height = max_y - min_y
        return BoundingBox(min_x, -max_y, width, height)

    @property
    def bbox_old(self) -> BoundingBox:
        """Return the bounding box of the text.

        :return: A BoundingBox in svg coordinates.
        """
        min_x, min_y, max_x, max_y = (
            x * self.scale for x in self.font.get_text_bounds2(self.text)
        )
        width = max_x - min_x
        height = max_y - min_y
        return BoundingBox(min_x, -max_y, width, height)

    @property
    def lsb(self):
        hmtx = cast("dict[str, tuple[int, int]]", self.font.font["hmtx"])
        _, lsb = hmtx.metrics[self.font.get_glyph_name(self.text[0])]
        return lsb * self.scale

    @property
    def left_side_bearing(self) -> float:
        """Return the left side bearing of the first glyph in the text."""
        if not self.text:
            return 0.0

        hmtx_table = cast("dict[str, tuple[int, int]]", self.font.font["hmtx"])
        aaa = hmtx_table[self.font.get_glyph_name(self.text[0])][1] * self.scale

        # glyph_metrics = self.font.get_glyph(self.text[0])
        # bbb = glyph_metrics.xMin * self.scale
        ccc = self.font.get_char_bounds_using_pen(self.text[0])[0] * self.scale
        return ccc
        # if aaa != bbb or aaa != ccc:
        #     breakpoint()
        return glyph_metrics.xMin * self.scale

    @property
    def right_side_bearing(self) -> float:
        """Return the right side bearing of the last glyph in the text."""
        if not self.text:
            return 0.0
        glyph_name = self.font.get_glyph_name(self.text[-1])
        # glyph_metrics = self.font.get_glyph(self.text[-1])
        bounds = self.font.get_char_bounds_using_pen(self.text[-1])
        # glyph_width = glyph_metrics.xMax - glyph_metrics.xMin
        glyph_width = bounds[2] - bounds[0]

        hmtx = cast("dict[str, tuple[int, int]]", self.font.font["hmtx"])
        advance, lsb = hmtx[glyph_name]
        return (advance - (lsb + glyph_width)) * self.scale

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
        return self.right_side_bearing

    @property
    def bpad(self) -> float:
        """Return the bottom padding for the text."""
        return self.descent - self.bbox.y2

    @property
    def lpad(self) -> float:
        """Return the left padding for the text.

        This is the left side bearing of the first glyph in the text.
        """
        return self.left_side_bearing


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
    font_size: float = 12,
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


def new_padded_text(
    font: str | os.PathLike[str],
    text: str,
    font_size: float = 12,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
    **attributes: str | float,
) -> tuple[PaddedText, FTTextInfo]:
    """Create a new PaddedTExt instance.

    :param text: the text of the text element.
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
    :param attributes: additional attributes to set on the text element.
    :return: a PaddedText instance and a FTTextInfo instance which contains some
        useful information, notably line_gap and line_height.
    """
    attributes_ = format_attr_dict(**attributes)
    attributes_["font-size"] = attributes_.get("font-size", format_number(font_size))
    attributes_["class"] = encode_to_css_class_name(Path(font).name)

    elem = new_element("text", text=text, **attributes_)
    info = get_padded_text_info(
        font, text, font_size, ascent, descent, y_bounds_reference=y_bounds_reference
    )
    return (
        PaddedText(elem, info.bbox, info.tpad, info.rpad, info.bpad, info.lpad),
        info,
    )


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


# from svg_ultralight.string_conversion import encode_to_css_class_name


# import base64


# def infer_font_format(font: str | os.PathLike[str]) -> str:
#     with open(font, "rb") as f:
#         file_header = f.read(4)

#     # Maps file header bytes to font format names
#     font_formats = {
#         b"\x00\x01\x00\x00": "ttf",  # TTF (TrueType Font)
#         b"OTTO": "otf",  # OTF (OpenType Font)
#         b"wOFF": "woff",  # WOFF (Web Open Font Format)
#         b"wOF2": "woff2",  # WOFF2 (Web Open Font Format 2)
#     }

#     # Returning the detected format
#     return font_formats.get(file_header, "unknown")


# def encode_font_to_base64(font_path: str | os.PathLike[str]) -> str:
#     with open(font_path, "rb") as font_file:
#         font_data = font_file.read()
#     base64_encoded_font = base64.b64encode(font_data).decode("utf-8")
#     return base64_encoded_font


# def create_font_data_url(font_path: str | os.PathLike[str]) -> str:
#     # Determine the font format
#     font_format = infer_font_format(font_path)
#     if font_format == "unknown":
#         raise ValueError(f"Unsupported font format for file: {font_path}")

#     # Encode the font file in Base64
#     base64_data = encode_font_to_base64(font_path)

#     # Construct the data URL
#     data_url = (
#         f"url(data:font/{font_format};base64,{base64_data}) format('{font_format}')"
#     )
#     return data_url


# aaa, inf = new_padded_text(font, "ascii")
# font_path = WindowsPath('C:/Windows/Fonts/AGENCYB.TTF')
# text = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!"#$%&\'()*+,-./:;<=>?'
# aaa, inf = new_padded_text(font_path, text)
# aaa, inf = new_padded_text(font_path, text)
# aaa, inf = new_padded_text(font_path, text)
# aaa, inf = new_padded_text(font_path, text)
# aaa, inf = new_padded_text(font_path, text)
# aaa, inf = new_padded_text(font_path, text)
# breakpoint()

# from lxml.etree import _Element as EtreeElement  # pyright: ignore[reportPrivateUsage]

# def _create_svg_font_class(path: str | os.PathLike[str], *, embed: bool = False) -> tuple[str, str]:
#     """Create a css class for the font.

#     :param path_to_font: path to a ttf or otf file
#     :param embed: if True, will embed the font in a data url, otherwise will just
#         reference the font file.
#     :return: a css class name for the font, e.g., "AgencyFB-Bold"
#     """
#     class_name = encode_to_css_class_name(Path(path).name)
#     if embed:
#         src = create_font_data_url(path)
#     else:
#         src = f"url('{path}')"
#     lines = [
#         "@font-face {",
#         f"  font-family: '{class_name}';",
#         f"  src: {src};",
#         "}",
#         f".{class_name} {{",
#         f"  font-family: '{class_name}';",
#         "}",
#     ]
#     return class_name, "\n".join(lines)

# def _add_svg_font_class(root: EtreeElement, font: str | os.PathLike[str], embed: bool = False) -> None:
#     """Add a css class for the font to the root element."""
#     # attempt to find an existing style element in the root element
#     existing_style = root.find("style")
#     if existing_style is not None:
#         lines = existing_style.text.splitlines()
#     else:
#         lines = []
#     class_name, css = _create_svg_font_class(font)

#     style_elem = new_element("style", type="text/css", text=css)
#     root.append(style_elem)
#     # root.set("class", class_name)


def get_western_utf8() -> str:
    """Return a string of the commonly used Western UTF-8 character set."""
    western = (
        string.ascii_lowercase
        + string.ascii_uppercase
        + string.digits
        + string.punctuation
        + " "
    )
    return western
    return western + "áÁéÉíÍóÓúÚñÑäÄëËïÏöÖüÜçÇàÀèÈìÌòÒùÙâÂêÊîÎôÔûÛãÃõÕåÅæÆøØœŒßÿŸ"


if __name__ == "__main__":
    import string

    _WESTERN_CHARS = get_western_utf8()

    from svg_ultralight.constructors import new_element
    from svg_ultralight.main import new_svg_root
    from svg_ultralight.font_tools.font_css import add_svg_font_class
    from svg_ultralight import pad_bbox, new_svg_root_around_bounds, write_root, new_bbox_rect, write_svg
    from lxml import etree
    from svg_ultralight.query import pad_text
    from pathlib import WindowsPath
    font = Path("C:/Windows/Fonts/bahnschrift.ttf")
    font = Path('C:/Windows/Fonts/Amasis MT Pro Black Italic.ttf')
    font = Path('C:/Windows/Fonts/AGENCYB.TTF')
    font = Path('C:/Windows/Fonts/Amasis MT Pro Black Italic.ttf')
    font = Path('C:/Windows/Fonts/SitkaVF-Italic.ttf')
    font = Path('C:/Windows/Fonts/Aptos-Black-Italic.ttf')
    font = Path('C:/Windows/Fonts/HelveticaNeue-Bold.otf')
    font = Path('C:/Windows/Fonts/marlett.ttf')
    font = Path('C:/Windows/Fonts/HelveticaNeue-Medium.otf')
# Failed on unpadded bbox y values HelveticaNeue-Medium.otf

    INKSCAPE = Path(r"C:\Program Files\Inkscape\bin\inkscape")

    text = "abcdefghijklmnopqrstuvwxyzABCD"
    text = "|eCD|"
    text = _WESTERN_CHARS[:-91] 
    # text = "ff"
    font_size = 12
    font_attributes = get_svg_font_attributes(font)
    text_elem = new_element("text", text=text, **font_attributes, font_size=font_size)
    pa = pad_text(INKSCAPE, text_elem)

    root = new_svg_root_around_bounds(pad_bbox(pa.bbox, 10))
    css_class = add_svg_font_class(root, font)
    pb, info = new_padded_text(font, text, font_size, y_bounds_reference="M", fill="green")

    root.append(new_bbox_rect(pa.unpadded_bbox, fill="none", stroke_width=0.07, stroke="red"))
    root.append(new_bbox_rect(pb.unpadded_bbox, fill="none", stroke_width=0.05, stroke="blue"))
    # root.append(new_bbox_rect(pa.bbox, fill="none", stroke_width=0.07, stroke="red"))
    # root.append(new_bbox_rect(pb.bbox, fill="none", stroke_width=0.05, stroke="blue"))
    root.append(pa.elem)
    root.append(pb.elem)

    breakpoint()




    _ = write_svg("temp.svg", root)
    # _ = write_root(INKSCAPE, "temp.svg", root)




    # aaa = _create_svg_font_class(font, embed=True)
    # # aaa = create_font_data_url(font)
    # # breakpoint()
