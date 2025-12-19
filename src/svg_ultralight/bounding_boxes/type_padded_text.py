"""A padded bounding box around a line of text.

An element, an svg_ultralight BoundingBox around that element, and padding on each
side of that box. This is to simplify treating scaling and moving a text element as
if it were written on a ruled sheet of paper.

Padding represents the space between the direction-most point of the text and the
left margin, right margin, descent, and ascent of the text. Top and bottom padding
may be less than zero if the constructor `pad_text_inkscape` is used with a
`y_bounds_reference` argument, as descenders and ascenders may extend below and above
the bounds of that reference character.

There are three families of transformations: padding, handles, and size.

There is a getter and setter for each of the four padding values. These *do not* move
the text element. For instance, if you decrease the left padding, the left margin
will move, *not* the text element.

There is a getter and setter for each of many handles (x, cx, x2, y, cy, and y2 are
the most common). These *do* move the element, but do not scale it. For instance, if
you move the left margin (x value) to the left, the right margin (and the text
element with it) will move to the left.

There are getters and setters for width, height, scale, cap_height, and x_height.
These scale the text and the padding values.

`set_width_preserve_sidebearings()`, `set_height_preserve_sidebearings(), and
`transform_preserve_sidebearings()` methods scale the text and the top and bottom
padding, but not the left or right padding. These also keep the text element anchored
on `x` and `y2`. These methods are useful for aligning text of different sizes on,
for instance, a business card so that Ls or Hs of different sizes line up vertically.

The padded text initializers in bounding_boxes.padded_text_initializers create
PaddedText instances.

:author: Shay Hill
:created: 2021-11-28
"""

from __future__ import annotations

import dataclasses
import math
from typing import TYPE_CHECKING

from lxml import etree

from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.constructors.new_element import new_element_union
from svg_ultralight.transformations import new_transformation_matrix, transform_element

if TYPE_CHECKING:
    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

    from svg_ultralight.attrib_hints import ElemAttrib

_Matrix = tuple[float, float, float, float, float, float]


@dataclasses.dataclass
class FontMetrics:
    """Font metrics."""

    _font_size: float
    _ascent: float
    _descent: float
    _cap_height: float
    _x_height: float
    _line_gap: float
    _scalar: float = dataclasses.field(default=1.0, init=False)

    def scale(self, scalar: float) -> None:
        """Scale the font metrics by a scalar.

        :param scalar: The scaling factor.
        """
        self._scalar *= scalar

    @property
    def font_size(self) -> float:
        """The font size."""
        return self._font_size * self._scalar

    @property
    def ascent(self) -> float:
        """Return the ascent."""
        return self._ascent * self._scalar

    @property
    def descent(self) -> float:
        """Return the descent."""
        return self._descent * self._scalar

    @property
    def cap_height(self) -> float:
        """Return the cap height."""
        return self._cap_height * self._scalar

    @property
    def x_height(self) -> float:
        """Return the x height."""
        return self._x_height * self._scalar

    @property
    def line_gap(self) -> float:
        """Return the line gap."""
        return self._line_gap * self._scalar


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
        metrics: FontMetrics | None = None,
    ) -> None:
        """Initialize a PaddedText instance.

        :param elem: The text element.
        :param bbox: The bounding box around text element.
        :param tpad: Top padding.
        :param rpad: Right padding.
        :param bpad: Bottom padding.
        :param lpad: Left padding.
        :param metrics: The font metrics for this line of text (inferred from a font):
        """
        self.elem = elem
        self.unpadded_bbox = bbox
        self._tpad = tpad
        self._rpad = rpad
        self._bpad = bpad
        self._lpad = lpad
        self._metrics = metrics

    @property
    def metrics(self) -> FontMetrics:
        """The font metrics for this PaddedText.

        :return: The font metrics for this PaddedText.
        """
        if self._metrics is None:
            msg = "No font metrics defined for this PaddedText."
            raise AttributeError(msg)
        return self._metrics

    @property
    def tbox(self) -> BoundingBox:
        """Return the unpadded BoundingBox around the text element.

        Tight bbox or True bbox. An alias for unpadded_bbox.

        :return: The unpadded BoundingBox around the text element.
        """
        return self.unpadded_bbox

    @property
    def bbox(self) -> BoundingBox:
        """Return a BoundingBox around the margins and ascent/descent.

        :return: A BoundingBox around the margins and ascentf/descent.

        This is useful for creating a merged bounding box with
        `svg_ultralight.BoundingBox.merged`. The merged bbox and merged_bbox
        attributes of multiple bounding boxes can be used to create a PaddedText
        instance around multiple text elements (a <g> elem).
        """
        return BoundingBox(
            self.tbox.x - self.lpad,
            self.tbox.y - self.tpad,
            self.tbox.width + self.lpad + self.rpad,
            self.tbox.height + self.tpad + self.bpad,
        )

    @bbox.setter
    def bbox(self, value: BoundingBox) -> None:
        """Forbid setting the bbox directly."""
        del value
        msg = "Cannot set bbox."
        raise AttributeError(msg)

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
        self.tbox.transform(tmat, reverse=reverse)
        _ = transform_element(self.elem, tmat, reverse=reverse)
        if self._metrics:
            y_norm = pow(tmat[2] ** 2 + tmat[3] ** 2, 1 / 2)
            self._metrics.scale(y_norm)

    @property
    def caps_bbox(self) -> BoundingBox:
        """The bounding box around the capital letters.

        :return: The bounding box around the capital letters.

        This is for passing into BoundUnion or new_svg_root_around_bounds to treat
        text elements as if they dot have ascenders or descenders. This is useful
        when, for instance, stacking text elements vertically with non-text elements,
        where few or no descenders will make the text look misaligned.
        """
        return BoundingBox(self.x, self.capline, self.width, self.metrics.cap_height)

    @property
    def caps_blem(self) -> BoundElement:
        """The BoundElement around the capital letters.

        :return: The BoundElement around the capital letters.

        This is for passing into BoundUnion or new_svg_root_around_bounds to treat
        text elements as if they dot have ascenders or descenders. This is useful
        when, for instance, stacking text elements vertically with non-text elements,
        where few or no descenders will make the text look misaligned.
        """
        return BoundElement(self.elem, self.caps_bbox)

    @property
    def caps_cy(self) -> float:
        """The vertical center of the capital letters.

        :return: The cap height of this line of text.
        """
        return (self.baseline + self.capline) / 2

    @caps_cy.setter
    def caps_cy(self, value: float) -> None:
        """Set the vertical center of the capital letters.

        :param value: The new cap height y value.
        """
        dy = value - self.caps_cy
        self.transform(dy=dy)

    @property
    def tx(self) -> float:
        """The x value of the tight element bounding box.

        :return: The x value of the tight element bounding box.
        """
        return self.tbox.x

    @tx.setter
    def tx(self, value: float) -> None:
        """Set the x value of the tight element bounding box.

        :param value: The new x value of the tight element bounding box.
        """
        self.transform(dx=value - self.tbox.x)

    @property
    def tx2(self) -> float:
        """The x2 value of the tight element bounding box.

        :return: The x2 value of the tight element bounding box.
        """
        return self.tbox.x2

    @tx2.setter
    def tx2(self, value: float) -> None:
        """Set the x2 value of the tight element bounding box.

        :param value: The new x2 value of the tight element bounding box.
        """
        self.transform(dx=value - self.tbox.x2)

    @property
    def ty(self) -> float:
        """The y value of the tight element bounding box.

        :return: The y value of the tight element bounding box.
        """
        return self.tbox.y

    @ty.setter
    def ty(self, value: float) -> None:
        """Set the y value of the tight element bounding box.

        :param value: The new y value of the tight element bounding box.
        """
        self.transform(dy=value - self.tbox.y)

    @property
    def ty2(self) -> float:
        """The y2 value of the tight element bounding box.

        :return: The y2 value of the tight element bounding box.
        """
        return self.tbox.y2

    @ty2.setter
    def ty2(self, value: float) -> None:
        """Set the y2 value of the tight element bounding box.

        :param value: The new y2 value of the tight element bounding box.
        """
        self.transform(dy=value - self.tbox.y2)

    @property
    def twidth(self) -> float:
        """The width of the tight element bounding box.

        :return: The width of the tight element bounding box.
        """
        return self.tbox.width

    @twidth.setter
    def twidth(self, value: float) -> None:
        """Set the width of the tight element bounding box.

        :param value: The new width of the tight element bounding box.
        """
        self.transform(scale=value / self.tbox.width)

    @property
    def theight(self) -> float:
        """The height of the tight element bounding box.

        :return: The height of the tight element bounding box.
        """
        return self.tbox.height

    @theight.setter
    def theight(self, value: float) -> None:
        """Set the height of the tight element bounding box.

        :param value: The new height of the tight element bounding box.
        """
        self.transform(scale=value / self.tbox.height)

    @property
    def font_size(self) -> float:
        """The font size of this line of text.

        :return: The font size of this line of text.
        """
        return self.metrics.font_size

    @font_size.setter
    def font_size(self, value: float) -> None:
        """Set the font size of this line of text.

        :param value: The new font size.
        """
        self.transform(scale=value / self.font_size)

    @property
    def baseline(self) -> float:
        """The y value of the baseline for the font.

        :return: The baseline y value of this line of text.
        """
        return self.y2 + self.metrics.descent

    @baseline.setter
    def baseline(self, value: float) -> None:
        """Set the y value of the baseline for the font.

        :param value: The new baseline y value.
        """
        dy = value - self.baseline
        self.transform(dy=dy)

    @property
    def capline(self) -> float:
        """The y value of the top of flat-topped capital letters for the font.

        :return: The capline y value of this line of text.
        """
        return self.baseline - self.metrics.cap_height

    @capline.setter
    def capline(self, value: float) -> None:
        """Set the capline y value for the font.

        :param value: The new capline y value.
        """
        dy = value - self.capline
        self.transform(dy=dy)

    @property
    def xline(self) -> float:
        """The y value of the x-height for the font.

        :return: The xline y value of this line of text.
        """
        return self.baseline - self.metrics.x_height

    @xline.setter
    def xline(self, value: float) -> None:
        """Set the xline y value for the font.

        :param value: The new xline y value.
        """
        dy = value - self.xline
        self.transform(dy=dy)

    @property
    def ascent(self) -> float:
        """The ascent of this line of text.

        :return: The ascent of this line of text.
        """
        return self.metrics.ascent

    @property
    def descent(self) -> float:
        """The descent of this line of text.

        :return: The descent of this line of text.
        """
        return self.metrics.descent

    @property
    def cap_height(self) -> float:
        """The cap height of this line of text.

        :return: The cap height of this line of text.
        """
        return self.metrics.cap_height

    @cap_height.setter
    def cap_height(self, value: float) -> None:
        """Set the cap height of this line of text.

        :param value: The new cap height.
        """
        self.transform(scale=value / self.cap_height)

    @property
    def x_height(self) -> float:
        """The x height of this line of text.

        :return: The x height of this line of text.
        """
        return self.metrics.x_height

    @x_height.setter
    def x_height(self, value: float) -> None:
        """Set the x height of this line of text.

        :param value: The new x height.
        """
        self.transform(scale=value / self.x_height)

    @property
    def headroom(self) -> float:
        """The headroom of this line of text.

        :return: The scaled headroom of this line of text.
        """
        return self.ascent - self.x_height

    @property
    def line_gap(self) -> float:
        """The line gap of this line of text.

        :return: The line gap of this line of text.
        """
        return self.metrics.line_gap

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
        return self._tpad * self.tbox.scale[1]

    @tpad.setter
    def tpad(self, value: float) -> None:
        """Set the top padding of this line of text.

        :param value: The new top padding.
        """
        self._tpad = value / self.tbox.scale[1]

    @property
    def rpad(self) -> float:
        """The right padding of this line of text.

        :return: The scaled right padding of this line of text.
        """
        return self._rpad * self.tbox.scale[0]

    @rpad.setter
    def rpad(self, value: float) -> None:
        """Set the right padding of this line of text.

        :param value: The new right padding.
        """
        self._rpad = value / self.tbox.scale[0]

    @property
    def bpad(self) -> float:
        """The bottom padding of this line of text.

        :return: The scaled bottom padding of this line of text.
        """
        return self._bpad * self.tbox.scale[1]

    @bpad.setter
    def bpad(self, value: float) -> None:
        """Set the bottom padding of this line of text.

        :param value: The new bottom padding.
        """
        self._bpad = value / self.tbox.scale[1]

    @property
    def lpad(self) -> float:
        """The left padding of this line of text.

        :return: The scaled left padding of this line of text.
        """
        return self._lpad * self.tbox.scale[0]

    @lpad.setter
    def lpad(self, value: float) -> None:
        """Set the left padding of this line of text.

        :param value: The new left padding.
        """
        self._lpad = value / self.tbox.scale[0]

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

        Preserve x for the common use case when multiple PaddedText instances are
        created. (They will all have x=0 and baseline=0.) Do not lose x alignment
        when the sidebearings are preserved.
        """
        tmat = new_transformation_matrix(transformation, scale=scale, dx=dx, dy=dy)
        x_norm = pow(tmat[0] ** 2 + tmat[1] ** 2, 1 / 2)
        self.transform(tmat, reverse=reverse)
        x = self.x
        self._lpad /= x_norm
        self._rpad /= x_norm
        self.x = x

    def set_width_preserve_sidebearings(self, value: float) -> None:
        """Set the width of this line of text without scaling sidebearings.

        :param value: The new width of this line of text.
        :effects: the text_element bounding box is scaled to width - lpad - rpad.
        """
        no_margins_old = self.tbox.width
        no_margins_new = value - self._lpad - self._rpad
        scale = no_margins_new / no_margins_old
        self.transform_preserve_sidebearings(scale=scale)

    def set_height_preserve_sidebearings(self, value: float) -> None:
        """Set the height of this line of text without scaling sidebearings.

        :param value: The new height of this line of text.
        :effects: the text_element bounding box is scaled to height - tpad - bpad.
        """
        self.transform_preserve_sidebearings(scale=value / self.height)


def new_empty_padded_union(*plems: PaddedText) -> PaddedText:
    """Use the new_padded_union mechanic to create an empty PaddedText instance.

    This is useful for mocking the bounding boxes and attributes of a PaddedText
    union without moving the elements into that union.
    """
    bbox = BoundingBox.union(*(t.bbox for t in plems))
    tbox = BoundingBox.union(*(t.tbox for t in plems))
    tpad = tbox.y - bbox.y
    rpad = bbox.x2 - tbox.x2
    bpad = bbox.y2 - tbox.y2
    lpad = tbox.x - bbox.x
    min_font_size = min(t.font_size for t in plems)
    max_y_extent = max(t.y2 for t in plems)
    min_y_extent = min(t.y for t in plems)
    min_caps_extent = min(t.capline for t in plems)
    min_x_extent = min(t.xline for t in plems)
    min_line_gap = min(t.metrics.line_gap for t in plems)
    baseline = max(t.baseline for t in plems)
    metrics = FontMetrics(
        min_font_size,
        baseline - min_y_extent,
        baseline - max_y_extent,
        baseline - min_caps_extent,
        baseline - min_x_extent,
        min_line_gap,
    )
    return PaddedText(etree.Element("g"), tbox, tpad, rpad, bpad, lpad, metrics)


def new_padded_union(*plems: PaddedText, **attributes: ElemAttrib) -> PaddedText:
    """Create a new PaddedText instance that is the union of multiple PaddedText.

    :param plems: The PaddedText instances to union.
    :return: A new PaddedText instance that is the union of the input instances.

    `.metrics` should be straghtforward. Ascent is the highest ascent any member,
    descent is the lowest descent, etc. (SVG uses a right-handed coordinate system,
    so higher y values are lower on the screen, and the 'highest' ascent is actually
    the lowest y value.) The metric values and handles will be appropriate for
    treating a stack (or bundle) of text elements as a single line of text.
    """
    union = new_empty_padded_union(*plems)
    union.elem = new_element_union(*(t.elem for t in plems), **attributes)
    return union
