"""A padded bounding box around a line of text.

A text element (presumably), an svg_ultralight BoundingBox around that element, and
padding on each side of that box. This is to simplify treating scaling and moving a
text element as if it were written on a ruled sheet of paper.

Padding represents the left margin, right margin, baseline, and capline of the text.
Baseling and capline padding will often be less than zero, as descenders and
ascenders will extend below the baseline and above the capline.

There is a getter and setter for each of the four padding values. These *do not* move
the text element. For instance, if you decrease the left padding, the left margin
will move, *not* the text element.

_There is a getter and setter for each of lmargin, rmargin, baseline, and capline.
These *do* move the element, but do not scale it. For instance, if you move the
leftmargin to the left, the right margin (and the text element with it) will move to
the left.

There is a getter and setter for padded_width and padded_height. These scale the
element and the top and bottom padding, but *not* the left and right padding. This is
one of two quirks which make this PaddedText class different from a generalized
padded bounding box.

1. As above, the left and right padding are not scaled with the text element, the top
and bottom padding are. This preserves but does not exaggerate the natural
sidebearings of the text element.  This lack of scaling will be pronounced if
adjacent padded lines are scaled to dramatically different sizes. The idea is to
scale each PaddedText as little as possible to match widths (or any other
relationship) then scale the resulting transformed text elements another way. For
instance, create multiple PaddedText instances, scale their padded_width atributes to
match, then put the resulting elements in a <g> element and scale the <g> element to
the ultimate desired size.

2. The left margin and baseline (*bottom* and left) do not move when the height or
width is changed. This is in contrast to an InkScape rect element, which, when the
width or height is changed, preserve the *top* and left boundaries.

Building an honest instance of this class is fairly involved:

1. Create a left-aligned text element.

2. Create a BoundingBox around the left-aligned text element. The difference between
   0 and that BoundingBox's left edge is the left padding.

3. Create a right-aligned copy of the text element.

4. Create a BoundingBox around the right-aligned text element. The difference between
   the BoundingBox's right edge 0 is the right padding.

5. Use a BoundingBox around a "normal" capital (e.g. "M") to infer the baseline and
   capline and then calculate the top and bottom margins.

There is a function to do this is `svg_ultralight.query.py` with sensible defaults.

A lot can be done with a dishonest instance of this class. For instance, you could
align and scale text while preserving left margin. The capline would scale with the
height or width, so a left margin and capline (assume baseline is zero) would be
enough to lay out text on a business card.

:author: Shay Hill
:created: 2021-11-28
"""

from __future__ import annotations

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
    ) -> None:
        """Initialize a PaddedText instance.

        :param elem: The text element.
        :param bbox: The bounding box around text element.
        :param tpad: Top padding.
        :param rpad: Right padding.
        :param bpad: Bottom padding.
        :param lpad: Left padding.
        """
        self.elem = elem
        self.unpadded_bbox = bbox
        self.base_tpad = tpad
        self.rpad = rpad
        self.base_bpad = bpad
        self.lpad = lpad
        self._line_gap = line_gap

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
    ):
        """Transform the element and bounding box.

        :param transformation: a 6-tuple transformation matrix
        :param scale: a scaling factor
        :param dx: the x translation
        :param dy: the y translation
        """
        tmat = new_transformation_matrix(transformation, scale=scale, dx=dx, dy=dy)
        self.unpadded_bbox.transform(tmat)
        _ = transform_element(self.elem, tmat)

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
        return self.base_tpad * self.unpadded_bbox.scale[1]

    @tpad.setter
    def tpad(self, value: float) -> None:
        """Set the top padding of this line of text.

        :param value: The new top padding.
        """
        self.base_tpad = value / self.unpadded_bbox.scale[1]

    @property
    def bpad(self) -> float:
        """The bottom padding of this line of text.

        :return: The scaled bottom padding of this line of text.
        """
        return self.base_bpad * self.unpadded_bbox.scale[1]

    @bpad.setter
    def bpad(self, value: float) -> None:
        """Set the bottom padding of this line of text.

        :param value: The new bottom padding.
        """
        self.base_bpad = value / self.unpadded_bbox.scale[1]

    @property
    def width(self) -> float:
        """The width of this line of text with padding.

        :return: The scaled width of this line of text with padding.
        """
        return self.unpadded_bbox.width + self.lpad + self.rpad

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
        y2 = self.y2

        no_margins_old = self.unpadded_bbox.width
        no_margins_new = value - self.lpad - self.rpad
        scale = no_margins_new / no_margins_old
        self.transform(scale=(scale, scale))

        self.y2 = y2

    @property
    def height(self) -> float:
        """The height of this line of text with padding.

        :return: The scaled height of this line of text with padding.
        """
        return self.unpadded_bbox.height + self.tpad + self.bpad

    @height.setter
    def height(self, value: float) -> None:
        """Scale to height without scaling padding.

        :param height: The new height of this line of text.
        :effects: the text_element bounding box is scaled to height - tpad - bpad.
        """
        y2 = self.y2
        scale = value / self.height
        self.transform(scale=(scale, scale))
        self.y2 = y2

    @property
    def x(self) -> float:
        """The left margin of this line of text.

        :return: The left margin of this line of text.
        """
        return self.unpadded_bbox.x - self.lpad

    @x.setter
    def x(self, value: float) -> None:
        """Set the left margin of this line of text.

        :param value: The left margin of this line of text.
        """
        self.transform(dx=value + self.lpad - self.unpadded_bbox.x)

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
        return self.unpadded_bbox.x2 + self.rpad

    @x2.setter
    def x2(self, value: float) -> None:
        """Set the right margin of this line of text.

        :param value: The right margin of this line of text.
        """
        self.transform(dx=value - self.rpad - self.unpadded_bbox.x2)

    @property
    def y(self) -> float:
        """The top of this line of text.

        :return: The top of this line of text.
        """
        return self.unpadded_bbox.y - self.tpad

    @y.setter
    def y(self, value: float) -> None:
        """Set the top of this line of text.

        :param value: The top of this line of text.
        """
        self.transform(dy=value + self.tpad - self.unpadded_bbox.y)

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
        return self.unpadded_bbox.y2 + self.bpad

    @y2.setter
    def y2(self, value: float) -> None:
        """Set the bottom of this line of text.

        :param value: The bottom of this line of text.
        """
        self.transform(dy=value - self.bpad - self.unpadded_bbox.y2)

    lmargin = x
    rmargin = x2
    capline = y
    baseline = y2
