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

There is a getter and setter for each of lmargin, rmargin, baseline, and capline.
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

from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox

if TYPE_CHECKING:
    from lxml.etree import _Element as EtreeElement  # type: ignore


class PaddedText(SupportsBounds):
    """A line of text with a bounding box and padding."""

    def __init__(
        self,
        elem: EtreeElement,
        bbox: BoundingBox,
        tpad: float,
        rpad: float,
        bpad: float,
        lpad: float,
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
        self.bbox = bbox
        self.base_tpad = tpad
        self.rpad = rpad
        self.base_bpad = bpad
        self.lpad = lpad

    @property
    def padded_bbox(self) -> BoundingBox:
        """Return a BoundingBox around the margins and cap/baseline.

        :return: A BoundingBox around the margins and cap/baseline.

        This is useful for creating a merged bounding box with
        `svg_ultralight.BoundingBox.merged`. The merged bbox and merged_bbox
        attributes of multiple bounding boxes can be used to create a PaddedText
        instance around multiple text elements (a <g> elem).
        """
        return BoundingBox(
            self.lmargin, self.capline, self.padded_width, self.padded_height
        )

    def _update(self, attrib: str, value: float) -> None:
        """Update bbox attribute and keep elem synced."""
        setattr(self.bbox, attrib, value)
        self.elem.attrib["transform"] = self.bbox.transform_string

    @property
    def tpad(self) -> float:
        """The top padding of this line of text.

        :return: The scaled top padding of this line of text.
        """
        return self.base_tpad * self.bbox.scale

    @tpad.setter
    def tpad(self, value: float) -> None:
        """Set the top padding of this line of text.

        :param value: The new top padding.
        """
        self.base_tpad = value / self.bbox.scale

    @property
    def bpad(self) -> float:
        """The bottom padding of this line of text.

        :return: The scaled bottom padding of this line of text.
        """
        return self.base_bpad * self.bbox.scale

    @bpad.setter
    def bpad(self, value: float) -> None:
        """Set the bottom padding of this line of text.

        :param value: The new bottom padding.
        """
        self.base_bpad = value / self.bbox.scale

    @property
    def lmargin(self) -> float:
        """The left margin of this line of text.

        :return: The left margin of this line of text.
        """
        return self.bbox.x - self.lpad

    @lmargin.setter
    def lmargin(self, value: float) -> None:
        """Set the left margin of this line of text.

        :param value: The left margin of this line of text.
        """
        self._update("x", value + self.lpad)

    @property
    def rmargin(self) -> float:
        """The right margin of this line of text.

        :return: The right margin of this line of text.
        """
        return self.bbox.x2 + self.rpad

    @rmargin.setter
    def rmargin(self, value: float) -> None:
        """Set the right margin of this line of text.

        :param value: The right margin of this line of text.
        """
        self._update("x2", value - self.rpad)

    @property
    def capline(self) -> float:
        """The top of this line of text.

        :return: The top of this line of text.
        """
        return self.bbox.y - self.tpad

    @capline.setter
    def capline(self, value: float) -> None:
        """Set the top of this line of text.

        :param value: The top of this line of text.
        """
        self._update("y", value + self.tpad)

    @property
    def baseline(self) -> float:
        """The bottom of this line of text.

        :return: The bottom of this line of text.
        """
        return self.bbox.y2 + self.bpad

    @baseline.setter
    def baseline(self, value: float) -> None:
        """Set the bottom of this line of text.

        :param value: The bottom of this line of text.
        """
        self._update("y2", value - self.bpad)

    @property
    def padded_width(self) -> float:
        """The width of this line of text with padding.

        :return: The scaled width of this line of text with padding.
        """
        return self.bbox.width + self.lpad + self.rpad

    @padded_width.setter
    def padded_width(self, width: float) -> None:
        """Scale to padded_width = width without scaling padding.

        :param width: The new width of this line of text.
        :effects: the text_element bounding box is scaled to width - lpad - rpad.

        Svg_Ultralight BoundingBoxes preserve x and y when scaling. This is
        consistent with how rectangles, viewboxes, and anything else defined by x, y,
        width, height behaves in SVG. This is unintuitive for text, because the
        baseline is near y2 (y + height) not y. So, we preserve baseline (alter y
        *and* y2) when scaling.
        """
        baseline = self.baseline
        self._update("width", width - self.lpad - self.rpad)
        self.baseline = baseline

    @property
    def padded_height(self) -> float:
        """The height of this line of text with padding.

        :return: The scaled height of this line of text with padding.
        """
        return self.bbox.height + self.tpad + self.bpad

    @padded_height.setter
    def padded_height(self, height: float) -> None:
        """Scale to padded_height = height without scaling padding.

        :param height: The new height of this line of text.
        :effects: the text_element bounding box is scaled to height - tpad - bpad.
        """
        self.padded_width *= height / self.padded_height

    @property
    def x(self) -> float:
        """The left margin of this line of text.

        :return: The left margin of this line of text.
        """
        return self.lmargin

    @x.setter
    def x(self, value: float) -> None:
        """Set the left margin of this line of text.

        :param value: The new left margin of this line of text.
        """
        self.lmargin = value

    @property
    def x2(self) -> float:
        """The right margin of this line of text.

        :return: The right margin of this line of text.
        """
        return self.rmargin

    @x2.setter
    def x2(self, value: float) -> None:
        """Set the right margin of this line of text.

        :param value: The new right margin of this line of this text.
        """
        self.rmargin = value

    @property
    def y(self) -> float:
        """The capline of this line of text.

        :return: The capline of this line of text.
        """
        return self.capline

    @y.setter
    def y(self, value: float) -> None:
        """Set the capline of this line of text.

        :param value: The new capline of this line of text.
        """
        self.capline = value

    @property
    def y2(self) -> float:
        """The baseline of this line of text.

        :return: The baseline of this line of text.
        """
        return self.baseline

    @y2.setter
    def y2(self, value: float) -> None:
        """Set the baseline of this line of text.

        :param value: The new baseline of this line of text.
        """
        self.baseline = value

    @property
    def width(self) -> float:
        """The width of this line of text with padding.

        :return: The scaled width of this line of text with padding.
        """
        return self.padded_width

    @width.setter
    def width(self, value: float) -> None:
        """Scale to width without scaling padding.

        :param value: The new width of this line of text.
        :effects: the text_element bounding box is scaled to width - lpad - rpad.

        Svg_Ultralight BoundingBoxes preserve x and y when scaling. This is
        consistent with how rectangles, viewboxes, and anything else defined by x, y,
        width, height behaves in SVG. This is unintuitive for text, because the
        baseline is near y2 (y + height) not y. So, we preserve baseline (alter y
        *and* y2) when scaling.
        """
        baseline = self.baseline
        self.padded_width = value
        self.baseline = baseline

    @property
    def height(self) -> float:
        """The height of this line of text with padding.

        :return: The scaled height of this line of text with padding.
        """
        return self.padded_height

    @height.setter
    def height(self, value: float) -> None:
        """Scale to height without scaling padding.

        :param value: The new height of this line of text.
        :effects: the text_element bounding box is scaled to height - tpad - bpad.
        """
        self.padded_height = value

    @property
    def cx(self) -> float:
        """The x coordinate of the center between margins.

        :return: the x coordinate of the center between margins
        """
        return self.lmargin + self.padded_width / 2

    @cx.setter
    def cx(self, value: float):
        """Set the x coordinate of the center between margins.

        :param value: the new x coordinate of the center between margins
        """
        self.lmargin = value - self.padded_width / 2

    @property
    def cy(self) -> float:
        """The y coordinate of the center between baseline and capline.

        :return: the y coordinate of the center between baseline and capline
        """
        return self.capline + self.padded_height / 2

    @cy.setter
    def cy(self, value: float):
        """Set the y coordinate of the center between baseline and capline.

        :param value: the new y coordinate of the center between baseline and capline
        """
        self.capline = value - self.padded_height / 2

    @property
    def scale(self) -> float:
        """The scale of the text element.

        :return: the scale of the text element
        """
        return self.bbox.scale

    @scale.setter
    def scale(self, value: float):
        """Set the scale of the text element.

        :param value: the new scale of the text element
        """
        self.bbox.scale = value
