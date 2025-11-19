"""A padded bounding box around a line of text.

A text element (presumably), an svg_ultralight BoundingBox around that element, and
padding on each side of that box. This is to simplify treating scaling and moving a
text element as if it were written on a ruled sheet of paper.

Padding represents the space between the direction-most point of the text and the
left margin, right margin, descent, and ascent of the text. Top and bottom padding
may be less than zero if the constructor used a `y_bounds_reference` argument, as
descenders and ascenders may extend below and above the bounds of that reference
character.

There is a getter and setter for each of the four padding values. These *do not* move
the text element. For instance, if you decrease the left padding, the left margin
will move, *not* the text element.

There is a getter and setter for each of x, cx, x2, y, cy, and y2. These *do* move
the element, but do not scale it. For instance, if you move the left margin (x value)
to the left, the right margin (and the text element with it) will move to the left.

There are getters and setters for width, height, and scale. These scale the text and
the padding values.

`set_width_preserve_sidebearings()`, `set_height_preserve_sidebearings(), and
`transform_preserve_sidebearings()` methods scale the text and the top and bottom
padding, but not the left or right padding. These also keep the text element anchored
on `x` and `y2`. These methods are useful for aligning text of different sizes on,
for instance, a business card so that Ls or Hs of different sizes line up vertically.

Building an honest instance of this class is fairly involved:

1. Create a left-aligned text element.

2. Create a BoundingBox around the left-aligned text element. The difference between
   0 and that BoundingBox's left edge is the left padding.

3. Create a right-aligned copy of the text element.

4. Create a BoundingBox around the right-aligned text element. The difference between
   the BoundingBox's right edge 0 is the right padding.

5. Use a BoundingBox around a "normal" capital (e.g. "M") to infer the baseline and
   capline and then calculate the top and bottom margins.

The padded text initializers in bounding_boxes.padded_text_initializers create
PaddedText instances with sensible defaults.

:author: Shay Hill
:created: 2021-11-28
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from paragraphs import par

from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.transformations import new_transformation_matrix, transform_element

if TYPE_CHECKING:
    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

_Matrix = tuple[float, float, float, float, float, float]

_no_line_gap_msg = par(
    """No line_gap defined. Line gap is an inherent font attribute defined within a
    font file. If this PaddedText instance was created with `pad_text` from reference
    elements, a line_gap was not defined. Reading line_gap from the font file
    requires creating a PaddedText instance with `pad_text_ft` or `pad_text_mixed`.
    You can set an arbitrary line_gap after init with `instance.line_gap = value`."""
)

_no_font_size_msg = par(
    """No font_size defined. Font size is an inherent font attribute defined within a
    font file or an argument passed to `pad_text`. Any instance created with a padded
    text initializer should have this property."""
)


class PaddedText(BoundElement):
    """A line of text with a bounding box and padding."""

    def __init__(
        self,
        elem: EtreeElement,
        bbox: BoundingBox,
        tpad: float,
        rpad: float,
        bpad: float,
        lpad: float,
        line_gap: float | None = None,
        font_size: float | None = None,
    ) -> None:
        """Initialize a PaddedText instance.

        :param elem: The text element.
        :param bbox: The bounding box around text element.
        :param tpad: Top padding.
        :param rpad: Right padding.
        :param bpad: Bottom padding.
        :param lpad: Left padding.
        :param line_gap: The line gap between this line of text and the next. This is
            an inherent font attribute sometimes defined within a font file.
        """
        self.elem = elem
        self.unpadded_bbox = bbox
        self.base_tpad = tpad
        self.rpad = rpad
        self.base_bpad = bpad
        self.lpad = lpad
        self._line_gap = line_gap
        self._font_size = font_size

    @property
    def tbox(self) -> BoundingBox:
        """Return the unpadded BoundingBox around the text element.

        Tight bbox or True bbox. An alias for unpadded_bbox.

        :return: The unpadded BoundingBox around the text element.
        """
        return self.unpadded_bbox

    @tbox.setter
    def tbox(self, value: BoundingBox) -> None:
        """Set the unpadded BoundingBox around the text element.

        :param value: The new unpadded BoundingBox.
        """
        self.unpadded_bbox = value

    @property
    def bbox(self) -> BoundingBox:
        """Return a BoundingBox around the margins and cap/baseline.

        :return: A BoundingBox around the margins and cap/baseline.

        This is useful for creating a merged bounding box with
        `svg_ultralight.BoundingBox.merged`. The merged bbox and merged_bbox
        attributes of multiple bounding boxes can be used to create a PaddedText
        instance around multiple text elements (a <g> elem).
        """
        return BoundingBox(
            self.x,
            self.y,
            self.width,
            self.height,
        )

    @bbox.setter
    def bbox(self, value: BoundingBox) -> None:
        """Set the bounding box of this PaddedText.

        :param value: The new bounding box.
        :effects: The text element is transformed to fit the new bounding box.
        """
        msg = "Cannot set bbox of PaddedText, use transform() instead."
        raise NotImplementedError(msg)

    def transform(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: tuple[float, float] | float | None = None,
        dx: float | None = None,
        dy: float | None = None,
        reverse: bool = False,
    ) -> None:
        """Transform the element and bounding box.

        :param transformation: a 6-tuple transformation matrix
        :param scale: a scaling factor
        :param dx: the x translation
        :param dy: the y translation
        :param reverse: Transform the element as if it were in a <g> element
            transformed by tmat.
        """
        tmat = new_transformation_matrix(transformation, scale=scale, dx=dx, dy=dy)
        self.unpadded_bbox.transform(tmat, reverse=reverse)
        _ = transform_element(self.elem, tmat, reverse=reverse)
        x_norm = pow(tmat[0] ** 2 + tmat[1] ** 2, 1 / 2)
        self.lpad *= x_norm
        self.rpad *= x_norm
        if self._line_gap or self._font_size:
            y_norm = pow(tmat[2] ** 2 + tmat[3] ** 2, 1 / 2)
            if self._line_gap:
                self._line_gap *= y_norm
            if self._font_size:
                self._font_size *= y_norm

    def transform_preserve_sidebearings(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: tuple[float, float] | float | None = None,
        dx: float | None = None,
        dy: float | None = None,
        reverse: bool = False,
    ) -> None:
        """Transform the element and bounding box preserving sidebearings.

        :param transformation: a 6-tuple transformation matrix
        :param scale: a scaling factor
        :param dx: the x translation
        :param dy: the y translation
        :param reverse: Transform the element as if it were in a <g> element
            transformed by tmat.
        """
        lpad = self.lpad
        rpad = self.rpad
        x = self.x
        y2 = self.y2
        self.transform(transformation, scale=scale, dx=dx, dy=dy, reverse=reverse)
        self.lpad = lpad
        self.rpad = rpad
        self.x = x
        self.y2 = y2

    @property
    def line_gap(self) -> float:
        """The line gap between this line of text and the next.

        :return: The line gap between this line of text and the next.
        """
        if self._line_gap is None:
            raise AttributeError(_no_line_gap_msg)
        return self._line_gap

    @line_gap.setter
    def line_gap(self, value: float) -> None:
        """Set the line gap between this line of text and the next.

        :param value: The new line gap.
        """
        self._line_gap = value

    @property
    def font_size(self) -> float:
        """The font size of this line of text.

        :return: The font size of this line of text.
        """
        if self._font_size is None:
            raise AttributeError(_no_font_size_msg)
        return self._font_size

    @font_size.setter
    def font_size(self, value: float) -> None:
        """Set the font size of this line of text.

        :param value: The new font size.
        """
        self.transform(scale=value / self.font_size)

    @property
    def leading(self) -> float:
        """The leading of this line of text.

        :return: The line gap plus the height of this line of text.
        """
        return self.height + self.line_gap

    @property
    def tpad(self) -> float:
        """The top padding of this line of text.

        :return: The scaled top padding of this line of text.
        """
        return self.base_tpad * self.tbox.scale[1]

    @tpad.setter
    def tpad(self, value: float) -> None:
        """Set the top padding of this line of text.

        :param value: The new top padding.
        """
        self.base_tpad = value / self.tbox.scale[1]

    @property
    def bpad(self) -> float:
        """The bottom padding of this line of text.

        :return: The scaled bottom padding of this line of text.
        """
        return self.base_bpad * self.tbox.scale[1]

    @bpad.setter
    def bpad(self, value: float) -> None:
        """Set the bottom padding of this line of text.

        :param value: The new bottom padding.
        """
        self.base_bpad = value / self.tbox.scale[1]

    @property
    def scale(self) -> tuple[float, float]:
        """Get scale of the bounding box.

        :return: uniform scale of the bounding box

        Use caution, the scale attribute can cause errors in intuition. Changing
        width or height will change the scale attribute, but not the x or y values.
        The scale setter, on the other hand, will work in the tradational manner.
        I.e., x => x*scale, y => y*scale, x2 => x*scale, y2 => y*scale, width =>
        width*scale, height => height*scale, scale => scale*scale. This matches how
        scale works in almost every other context.
        """
        xx, xy, yx, yy, *_ = self.tbox.transformation
        return math.sqrt(xx * xx + xy * xy), math.sqrt(yx * yx + yy * yy)

    @scale.setter
    def scale(self, value: tuple[float, float]) -> None:
        """Scale the bounding box by a uniform factor.

        :param value: new scale value

        Don't miss this! You are setting the scale, not scaling the scale! If you
        have a previously defined scale other than 1, this is probably not what you
        want. Most of the time, you will want to use the *= operator.

        `scale = 2` -> ignore whatever scale was previously defined and set scale to 2
        `scale *= 2` -> make it twice as big as it was.
        """
        new_scale = (
            value[0] / self.tbox.scale[0],
            value[1] / self.tbox.scale[1],
        )
        self.transform(scale=new_scale)

    @property
    def uniform_scale(self) -> float:
        """Get uniform scale of the bounding box.

        :return: uniform scale of the bounding box
        :raises ValueError: if the scale is non-uniform.
        """
        scale = self.scale
        if math.isclose(scale[0], scale[1]):
            return scale[0]
        msg = f"Non-uniform scale detected: sx={scale[0]}, sy={scale[1]}"
        raise ValueError(msg)

    @property
    def width(self) -> float:
        """The width of this line of text with padding.

        :return: The scaled width of this line of text with padding.
        """
        return self.tbox.width + self.lpad + self.rpad

    @width.setter
    def width(self, value: float) -> None:
        """Scale to padded_width = width without scaling padding.

        :param width: The new width of this line of text.
        :effects: the text_element bounding box is scaled to width - lpad - rpad.

        Svg_Ultralight BoundingBoxes preserve x and y when scaling. This is
        consistent with how rectangles, viewboxes, and anything else defined by x, y,
        width, height behaves in SVG. This is unintuitive for text, because the
        baseline is near y2 (y + height) not y. So, we preserve baseline (alter y
        *and* y2) when scaling.
        """
        self.transform(scale=value / self.width)

    def set_width_preserve_sidebearings(self, value: float) -> None:
        """Set the width of this line of text without scaling sidebearings.

        :param value: The new width of this line of text.
        :effects: the text_element bounding box is scaled to width - lpad - rpad.
        """
        no_margins_old = self.tbox.width
        no_margins_new = value - self.lpad - self.rpad
        scale = no_margins_new / no_margins_old
        self.transform_preserve_sidebearings(scale=scale)

    @property
    def height(self) -> float:
        """The height of this line of text with padding.

        :return: The scaled height of this line of text with padding.
        """
        return self.tbox.height + self.tpad + self.bpad

    @height.setter
    def height(self, value: float) -> None:
        """Scale to height without scaling padding.

        :param height: The new height of this line of text.
        :effects: the text_element bounding box is scaled to height - tpad - bpad.
        """
        scale = value / self.height
        self.transform(scale=scale)

    def set_height_preserve_sidebearings(self, value: float) -> None:
        """Set the height of this line of text without scaling sidebearings.

        :param value: The new height of this line of text.
        :effects: the text_element bounding box is scaled to height - tpad - bpad.
        """
        self.transform_preserve_sidebearings(scale=value / self.height)

    @property
    def x(self) -> float:
        """The left margin of this line of text.

        :return: The left margin of this line of text.
        """
        return self.tbox.x - self.lpad

    @x.setter
    def x(self, value: float) -> None:
        """Set the left margin of this line of text.

        :param value: The left margin of this line of text.
        """
        self.transform(dx=value + self.lpad - self.tbox.x)

    @property
    def cx(self) -> float:
        """The horizontal center of this line of text.

        :return: The horizontal center of this line of text.
        """
        return self.x + self.width / 2

    @cx.setter
    def cx(self, value: float) -> None:
        """Set the horizontal center of this line of text.

        :param value: The horizontal center of this line of text.
        """
        self.x += value - self.cx

    @property
    def x2(self) -> float:
        """The right margin of this line of text.

        :return: The right margin of this line of text.
        """
        return self.tbox.x2 + self.rpad

    @x2.setter
    def x2(self, value: float) -> None:
        """Set the right margin of this line of text.

        :param value: The right margin of this line of text.
        """
        self.transform(dx=value - self.rpad - self.tbox.x2)

    @property
    def y(self) -> float:
        """The top of this line of text.

        :return: The top of this line of text.
        """
        return self.tbox.y - self.tpad

    @y.setter
    def y(self, value: float) -> None:
        """Set the top of this line of text.

        :param value: The top of this line of text.
        """
        self.transform(dy=value + self.tpad - self.tbox.y)

    @property
    def cy(self) -> float:
        """The horizontal center of this line of text.

        :return: The horizontal center of this line of text.
        """
        return self.y + self.height / 2

    @cy.setter
    def cy(self, value: float) -> None:
        """Set the horizontal center of this line of text.

        :param value: The horizontal center of this line of text.
        """
        self.y += value - self.cy

    @property
    def y2(self) -> float:
        """The bottom of this line of text.

        :return: The bottom of this line of text.
        """
        return self.tbox.y2 + self.bpad

    @y2.setter
    def y2(self, value: float) -> None:
        """Set the bottom of this line of text.

        :param value: The bottom of this line of text.
        """
        self.transform(dy=value - self.bpad - self.tbox.y2)
