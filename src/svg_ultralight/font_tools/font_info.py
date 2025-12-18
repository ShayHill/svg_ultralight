"""Use fontTools to extract some font information and remove the problematic types.

Svg_Ultralight uses Inkscape command-line calls to find binding boxes, rasterize
images, and convert font objects to paths. This has some nice advantages:

- it's free

- ensures Inkscape compatibility, so you can open the results and edit them in
  Inkscape

- is much easier to work with than Adobe Illustrator's scripting

... and a couple big disadvantages:

- Inkscape will not read local font files without encoding them.

- Inkscape uses Pango for text layout.

Pango is a Linux / GTK library. You can get it working on Windows with some work, but
it's definitely not a requirement I want for every project that uses Svg_Ultralight.

This means I can only infer Pango's text layout by passing reference text elements to
Inkscape and examining the results. That's not terribly, but it's slow and does not
reveal line_gap, line_height, true ascent, or true descent, which I often want for
text layout.

FontTools is a Pango-like library that can get *similar* results. Maybe identical
results you want to re-implement Pango's text layout. I have 389 ttf and otf fonts
installed on my system.

- for 361 of 389, this module apears to lay out text exactly as Pango.

- 17 of 389 raise an error when trying to examine them. Some of these are only issues
  with the test text, which may include characters not in the font.

- 7 of 389 have y-bounds differences from Pango, but the line_gap values may still be
  useful.

- 4 of 389 have x-bounds differences from Pango.

I have provided the `check_font_tools_alignment` function to check an existing font
for compatilibilty with Inkscape's text layout. If that returns (NO_ERROR, None),
then a font object created with

```
new_element("text", text="abc", **get_svg_font_attributes(path_to_font))
```

... will lay out the element exactly as Inkscape would *if* Inkscape were able to
read locally linked font files.

Advantages to using fontTools do predict how Inkscape will lay out text:

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
  attributes that `pad_text_inkscape` would through Inkscape.

See the padded_text_initializers module for how to create a PaddedText instance using
fontTools and this module.

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
import weakref
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from paragraphs import par
from svg_path_data import format_svgd_shortest, get_cpts_from_svgd, get_svgd_from_cpts
from typing_extensions import Self

from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.constructors.new_element import new_element, new_sub_element
from svg_ultralight.strings import svg_matrix

if TYPE_CHECKING:
    import os
    from collections.abc import Iterator

    from lxml.etree import _Element as EtreeElement

    from svg_ultralight.attrib_hints import ElemAttrib

logging.getLogger("fontTools").setLevel(logging.ERROR)


DATA_TEXT_ESCAPE_CHARS = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&apos;",
    "{": "&#123",  # valid, but stops MS File Explorer from thumbnailing an svg
    "}": "&#125",  # valid, but stops MS File Explorer from thumbnailing an svg
}


def _sanitize_svg_data_text(text: str) -> str:
    """Sanitize a string for use in an SVG data-text attribute.

    :param text: The input string to sanitize.
    :return: The sanitized string with XML characters escaped.
    """
    for char, escape_seq in DATA_TEXT_ESCAPE_CHARS.items():
        text = text.replace(char, escape_seq)
    return text


def _get_gpos_kerning(font: TTFont) -> dict[tuple[str, str], int]:
    """Extract kerning pairs from the GPOS table of a font.

    :param font: A fontTools TTFont object.
    :return: A dictionary mapping glyph pairs to their kerning values.
    :raises ValueError: If the font does not have a GPOS table.

    This is the more elaborate kerning that is used in OTF fonts and some TTF fonts.
    It has several flavors, I'm only implementing glyph-pair kerning (Format 1),
    because I don't have fonts to test anything else.
    """
    if "GPOS" not in font:
        msg = "Font does not have a GPOS table."
        raise ValueError(msg)

    gpos = font["GPOS"].table
    kern_table: dict[tuple[str, str], int] = {}

    type2_lookups = (x for x in gpos.LookupList.Lookup if x.LookupType == 2)
    subtables = list(it.chain(*(x.SubTable for x in type2_lookups)))
    for subtable in (x for x in subtables if x.Format == 1):  # glyph-pair kerning
        for pair_set, glyph1 in zip(
            subtable.PairSet, subtable.Coverage.glyphs, strict=True
        ):
            for pair_value in pair_set.PairValueRecord:
                glyph2 = pair_value.SecondGlyph
                value1 = pair_value.Value1
                xadv = getattr(value1, "XAdvance", None)
                xpla = getattr(value1, "XPlacement", None)
                value = xadv or xpla or 0
                if value != 0:  # only record non-zero kerning values
                    kern_table[(glyph1, glyph2)] = value

    for subtable in (x for x in subtables if x.Format == 2):  # class-based kerning
        defs1 = subtable.ClassDef1.classDefs
        defs2 = subtable.ClassDef2.classDefs
        record1 = subtable.Class1Record
        defs1 = {k: v for k, v in defs1.items() if v < len(record1)}
        for (glyph1, class1), (glyph2, class2) in it.product(
            defs1.items(), defs2.items()
        ):
            class1_record = record1[class1]
            if class2 < len(class1_record.Class2Record):
                value1 = class1_record.Class2Record[class2].Value1
                xadv = getattr(value1, "XAdvance", None)
                xpla = getattr(value1, "XPlacement", None)
                value = xadv or xpla or 0
                if value != 0:
                    kern_table[(glyph1, glyph2)] = value

    return kern_table


_XYTuple = tuple[float, float]


def _split_into_quadratic(*pts: _XYTuple) -> Iterator[tuple[_XYTuple, _XYTuple]]:
    """Connect a series of points with quadratic bezier segments.

    :param points: a series of at least two (x, y) coordinates.
    :return: an iterator of ((x, y), (x, y)) quadatic bezier control points (the
        second and third points)

    This is part of connecting a (not provided) current point to the last input
    point. The other input points will be control points of a series of quadratic
    Bezier curves. New Bezier curve endpoints will be created between these points.

    given (B, C, D, E) (with A as the not-provided current point):
    - [A,  B, bc][1:]
    - [bc, C, cd][1:]
    - [cd, D,  E][1:]
    """
    if len(pts) < 2:
        msg = "At least two points are required."
        raise ValueError(msg)
    for prev_cp, next_cp in it.pairwise(pts[:-1]):
        xs, ys = zip(prev_cp, next_cp, strict=True)
        midpnt = sum(xs) / 2, sum(ys) / 2
        yield prev_cp, midpnt
    yield pts[-2], pts[-1]


class PathPen(BasePen):
    """A pen to collect svg path data commands from a glyph."""

    def __init__(self, glyph_set: Any) -> None:
        """Initialize the PathPen with a glyph set.

        :param glyph_set: TTFont(path).getGlyphSet()
        """
        super().__init__(glyph_set)
        self._cmds: list[str] = []

    @property
    def svgd(self) -> str:
        """Return an svg path data string for the glyph."""
        if not self._cmds:
            return ""
        svgd = " ".join(self._cmds)
        return "M" + svgd[1:]

    @property
    def cpts(self) -> list[list[tuple[float, float]]]:
        """Return as a list of lists of Bezier control points."""
        return get_cpts_from_svgd(" ".join(self._cmds))

    def moveTo(self, pt: tuple[float, float]) -> None:
        """Move the current point to a new location."""
        self._cmds.extend(("M", *map(str, pt)))

    def lineTo(self, pt: tuple[float, float]) -> None:
        """Add a line segment to the path."""
        self._cmds.extend(("L", *map(str, pt)))

    def curveTo(self, *pts: tuple[float, float]) -> None:
        """Add a series of cubic bezier segments to the path."""
        if len(pts) > 3:
            msg = par(
                """I'm uncertain how to decompose these points into cubics (if the
                goal is to match font rendering in Inkscape and elsewhere. There is
                function, decomposeSuperBezierSegment, in fontTools, but I cannot
                find a reference for the algorithm. I'm hoping to run into one in a
                font file so I have a test case."""
            )
            raise NotImplementedError(msg)
        self._cmds.extend(("C", *map(str, it.chain(*pts))))

    def qCurveTo(self, *pts: tuple[float, float]) -> None:
        """Add a series of quadratic bezier segments to the path."""
        for q_pts in _split_into_quadratic(*pts):
            self._cmds.extend(("Q", *map(str, it.chain(*q_pts))))

    def closePath(self) -> None:
        """Close the current path."""
        self._cmds.append("Z")


class FTFontInfo:
    """Hide all the type kludging necessary to use fontTools."""

    def __new__(cls, font: str | os.PathLike[str] | Self) -> Self:
        """Create a new FTFontInfo instance as a context manager."""
        if isinstance(font, FTFontInfo):
            return font
        instance = super().__new__(cls)
        _ = weakref.finalize(instance, instance.__close__)
        return instance

    def __init__(self, font: str | os.PathLike[str] | Self) -> None:
        """Initialize the SUFont with a path to a TTF font file."""
        if self is font:
            return
        if isinstance(font, FTFontInfo):
            msg = "Unexpected Error, should have been caught in __new__."
            raise TypeError(msg)
        self._ttfont_local_to_instance = True
        self._path = Path(font)
        if not self.path.exists():
            msg = f"Font file '{self.path}' does not exist."
            raise FileNotFoundError(msg)
        self._font = TTFont(self.path)

    def __close__(self) -> None:
        """Close the font file."""
        self._font.close()

    def maybe_close(self) -> None:
        """Close the TTFont instance if it is was opened by this instance."""
        if self._ttfont_local_to_instance:
            self.__close__()

    def __enter__(self) -> Self:
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Exit the context manager."""
        del exc_type, exc_value, traceback
        self.maybe_close()

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
        try:
            kern_tables = cast(
                "list[dict[tuple[str, str], int]]",
                [x.kernTable for x in self.font["kern"].kernTables],
            )
            kern = dict(x for d in reversed(kern_tables) for x in d.items())
        except (KeyError, AttributeError):
            kern = {}
        with suppress(Exception):
            kern.update(_get_gpos_kerning(self.font))

        return kern

    @property
    def ascent(self) -> int:
        """Get the ascent for the font.

        :return: The ascent for the font.
        """
        with suppress(KeyError, AttributeError):
            return self.font["os2"].sTypoAscender
        with suppress(KeyError, AttributeError):
            return self.font["hhea"].ascent
        msg = f"Failed to find ascent for font '{self.path}'."
        raise AttributeError(msg)

    @property
    def descent(self) -> int:
        """Get the descent for the font.

        :return: The descent for the font.
        """
        with suppress(KeyError, AttributeError):
            return self.font["os2"].sTypoDescender
        with suppress(KeyError, AttributeError):
            return self.font["hhea"].descent
        msg = f"Failed to find descent for font '{self.path}'."
        raise AttributeError(msg)

    @property
    def line_gap(self) -> int:
        """Get the cap height for the font.

        :return: The (often 0) line gap for the font.
        """
        with suppress(KeyError, AttributeError):
            return self.font["os2"].sTypoLineGap
        with suppress(KeyError, AttributeError):
            return self.font["hhea"].lineGap
        return 0

    @property
    def cap_height(self) -> int:
        """Get the cap height for the font.

        :return: The cap height for the font.
        """
        with suppress(KeyError, AttributeError):
            return self.font["os2"].sCapHeight
        return self.get_char_bounds("H")[3]

    @property
    def x_height(self) -> int:
        """Get the x-height for the font.

        :return: The x-height for the font.
        """
        with suppress(KeyError, AttributeError):
            return self.font["os2"].sxHeight  # rare
        return self.get_char_bounds("x")[3]

    def try_glyph_name(self, char: str) -> str | None:
        """Try to get the glyph name for a character in the font.

        :param char: The character to get the glyph name for.
        :return: The glyph name for the character, or None if not found.
        """
        ord_char = ord(char)
        char_map = cast("dict[int, str]", self.font.getBestCmap())
        if ord_char in char_map:
            return char_map[ord_char]
        return None

    def get_glyph_name(self, char: str) -> str:
        """Get the glyph name for a character in the font.

        :param char: The character to get the glyph name for.
        :return: The glyph name for the character.
        :raises ValueError: If the character is not found in the font.
        """
        ord_char = self.try_glyph_name(char)
        if ord_char is None:
            msg = f"Character '{char}' not found in font '{self.path}'."
            raise ValueError(msg)
        return ord_char

    def get_char_svgd(self, char: str, dx: float = 0) -> str:
        """Return the svg path data for a glyph.

        :param char: The character to get the svg path data for.
        :param dx: An optional x translation to apply to the glyph.
        :return: The svg path data for the character.
        """
        glyph_name = self.get_glyph_name(char)
        glyph_set = self.font.getGlyphSet()
        path_pen = PathPen(glyph_set)
        _ = glyph_set[glyph_name].draw(path_pen)
        svgd = path_pen.svgd
        if not dx or not svgd:
            return format_svgd_shortest(svgd)
        cpts = get_cpts_from_svgd(svgd)
        for i, curve in enumerate(cpts):
            cpts[i][:] = [(x + dx, y) for x, y in curve]
        svgd = format_svgd_shortest(get_svgd_from_cpts(cpts))
        return "M" + svgd[1:]

    def get_char_bounds(self, char: str) -> tuple[int, int, int, int]:
        """Return the min and max x and y coordinates of a glyph.

        There are two ways to get the bounds of a glyph, using an object from
        font["glyf"] or this awkward-looking method. Most of the time, they are the
        same, but when they disagree, this method is more accurate. Additionally,
        some fonts do not have a glyf table, so this method is more robust.
        """
        glyph_name = self.get_glyph_name(char)
        glyph_set = self.font.getGlyphSet()
        bounds_pen = BoundsPen(glyph_set)
        _ = glyph_set[glyph_name].draw(bounds_pen)
        pen_bounds = cast("None | tuple[int, int, int, int]", bounds_pen.bounds)
        if pen_bounds is None:
            return 0, 0, 0, 0
        x_min, y_min, x_max, y_max = pen_bounds
        return x_min, y_min, x_max, y_max

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
        hmtx = cast("dict[str, tuple[int, int]]", self.font["hmtx"])

        names = [self.get_glyph_name(c) for c in text]
        bounds = [self.get_char_bounds(c) for c in text]
        total_advance = sum(hmtx[n][0] for n in names[:-1])
        total_kern = sum(self.kern_table.get((x, y), 0) for x, y in it.pairwise(names))
        min_xs, min_ys, max_xs, max_ys = zip(*bounds, strict=True)
        min_x = min_xs[0]
        min_y = min(min_ys)

        max_x = total_advance + max_xs[-1] + total_kern
        max_y = max(max_ys)
        return min_x, min_y, max_x, max_y

    def get_text_svgd_by_char(self, text: str, dx: float = 0) -> Iterator[str]:
        """Return an iterator of svg path data for each character in a string.

        :param text: The text to get the svg path data for.
        :param dx: An optional x translation to apply to the entire text.
        :return: An iterator of svg path data for each character in the text.
        """
        hmtx = cast("dict[str, tuple[int, int]]", self.font["hmtx"])
        char_dx = dx
        for c_this, c_next in it.pairwise(text):
            this_name = self.get_glyph_name(c_this)
            next_name = self.get_glyph_name(c_next)
            yield self.get_char_svgd(c_this, char_dx)
            char_dx += hmtx[this_name][0]
            char_dx += self.kern_table.get((this_name, next_name), 0)
        yield self.get_char_svgd(text[-1], char_dx)

    def get_text_svgd(self, text: str, dx: float = 0) -> str:
        """Return the svg path data for a string.

        :param text: The text to get the svg path data for.
        :param dx: An optional x translation to apply to the entire text.
        :return: The svg path data for the text.
        """
        return "".join(self.get_text_svgd_by_char(text, dx))

    def get_text_svgds(self, text: str, dx: float = 0) -> list[tuple[str, str]]:
        """Return a list of svg path data for each character in a string.

        :param text: The text to get the svg path data for.
        :param dx: An optional x translation to apply to the entire text.
        :return: A list of svg path data for each character in the text.
        """
        hmtx = cast("dict[str, tuple[int, int]]", self.font["hmtx"])
        svgds: list[tuple[str, str]] = []
        for c_this, c_next in it.pairwise(text):
            this_name = self.get_glyph_name(c_this)
            next_name = self.get_glyph_name(c_next)
            svgd = self.get_char_svgd(c_this)
            tmat = "" if dx == 0 else f"matrix(1 0 0 1 {dx} 0)"
            svgds.append((svgd, tmat))
            dx += hmtx[this_name][0]
            dx += self.kern_table.get((this_name, next_name), 0)
        svgd = self.get_char_svgd(text[-1])
        tmat = "" if dx == 0 else f"matrix(1 0 0 1 {dx} 0)"
        svgds.append((svgd, tmat))
        return svgds

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
        hmtx = cast("Any", self.font["hmtx"])
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
    ) -> None:
        """Initialize the SUText with text, a SUFont instance, and font size."""
        self._font = FTFontInfo(font)
        self._text = text

    def __close__(self) -> None:
        """Close the font file."""
        self._font.maybe_close()

    def __enter__(self) -> Self:
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Exit the context manager."""
        del exc_type, exc_value, traceback
        self.__close__()

    @property
    def font(self) -> FTFontInfo:
        """Return the font information."""
        return self._font

    @property
    def text(self) -> str:
        """Return the text."""
        return self._text

    def new_element(self, **attributes: ElemAttrib) -> EtreeElement:
        """Return an svg text element with the appropriate font attributes."""
        matrix_vals = (1, 0, 0, -1, 0, 0)
        attributes["transform"] = svg_matrix(matrix_vals)
        data_text = _sanitize_svg_data_text(self.text)
        group = new_element("g", data_text=data_text, **attributes)
        for i, (svgd, tmat) in enumerate(self.font.get_text_svgds(self.text)):
            if not svgd:
                continue
            data_text = _sanitize_svg_data_text(self.text[i])
            if not tmat:
                _ = new_sub_element(group, "path", data_text=data_text, d=svgd)
                continue
            _ = new_sub_element(
                group, "path", data_text=data_text, d=svgd, transform=tmat
            )
        return group

    @property
    def bbox(self) -> BoundingBox:
        """Return the bounding box of the text.

        :return: A BoundingBox in svg coordinates.
        """
        return self.font.get_text_bbox(self.text)

    @property
    def tpad(self) -> float:
        """Return the top padding for the text."""
        return self.font.ascent + self.bbox.y

    @property
    def rpad(self) -> float:
        """Return the right padding for the text.

        This is the right side bearing of the last glyph in the text.
        """
        return self.font.get_rsb(self.text[-1])

    @property
    def bpad(self) -> float:
        """Return the bottom padding for the text."""
        return -self.font.descent - self.bbox.y2

    @property
    def lpad(self) -> float:
        """Return the left padding for the text.

        This is the left side bearing of the first glyph in the text.
        """
        return self.font.get_lsb(self.text[0])

    @property
    def padding(self) -> tuple[float, float, float, float]:
        """Return the padding for the text as a tuple of (top, right, bottom, left)."""
        return self.tpad, self.rpad, self.bpad, self.lpad


# ===================================================================================
#   Infer svg font attributes from a ttf or otf file
# ===================================================================================

# This is the record nameID that most consistently reproduces the desired font
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
