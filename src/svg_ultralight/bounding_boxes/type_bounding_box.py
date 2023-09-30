"""Bounding box classes for SVG elements.

:author: Shay Hill
:created: 2022-12-09
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
from svg_ultralight.string_conversion import format_number


@dataclass
class BoundingBox(SupportsBounds):
    """Mutable bounding box object for svg_ultralight.

    :param x: left x value
    :param y: top y value
    :param width: width of the bounding box
    :param height: height of the bounding box

    The below optional parameters, in addition to the required parameters, capture
    the entire state of a BoundingBox instance.  They could be used to make a copy or
    to initialize a transformed box with the same transform_string as another box.
    Under most circumstances, they will not be used.

    :param scale: scale of the bounding box
    :param translation_x: x translation of the bounding box
    :param translation_y: y translation of the bounding box

    Functions that return a bounding box will return a BoundingBox instance. This
    instance can be transformed (uniform scale and translate only). Transformations
    will be combined and scored to be passed to new_element as a transform value.

    Define the bbox with x=, y=, width=, height=

    Transform the BoundingBox by setting these variables. Each time you set x, cx,
    x2, y, cy, y2, width, or height, private transformation values (_scale,
    _transform_x, and _transform_y) will be updated.

    The ultimate transformation can be accessed through ``.transformation_string``.
    So the workflow will look like :

        1. Get the bounding box of an svg element
        2. Update the bounding box x, y, width, and height
        3. Transform the original svg element with
            update_element(elem, transform=bbox.transform_string)
        4. The transformed element will lie in the transformed BoundingBox

    In addition to x, y, width, and height, x2 and y2 can be set to establish the
    right x value or bottom y value.

    The point of all of this is to simplify stacking and aligning elements. To stack:

        ```
        elem_a = new_element(*args)
        bbox_a = get_bounding_box(elem_a)

        elem_b = new_element(*args)
        bbox_b = get_bounding_box(elem_b)

        # align at same x
        bbox_b.x = bbox_a.x

        # make the same width
        bbox_b.width = bbox_a.width

        # stack a on top of b
        bbox_a.y2 = bbox_b.y

        update_element(elem_a, transform=bbox_a.transform_string)
        update_element(elem_b, transform=bbox_b.transform_string)
    """

    _x: float
    _y: float
    _width: float
    _height: float
    _scale: float = 1.0
    _translation_x: float = 0.0
    _translation_y: float = 0.0

    @property
    def scale(self) -> float:
        """Read-only scale.

        :return: uniform scale of the bounding box

        Use caution, the scale attribute can cause errors in intuition. Changing
        width or height will change the scale attribute, but not the x or y values.
        The scale setter, on the other hand, will work in the tradational manner.
        I.e., x => x*scale, y => y*scale, x2 => x*scale, y2 => y*scale, width =>
        width*scale, height => height*scale, scale => scale*scale. This matches how
        scale works in almost every other context.
        """
        return self._scale

    @scale.setter
    def scale(self, value: float) -> None:
        """Scale the bounding box by a uniform factor.

        :param value: new scale value

        Don't miss this! You are setting the scale, not scaling the scale! If you
        have a previously defined scale other than 1, this is probably not what you
        want. Most of the time, you will want to use the *= operator.

        `scale = 2` -> ignore whatever scale was previously defined and set scale to 2
        `scale *= 2` -> make it twice as big as it was.
        """
        self._scale = value

    @property
    def x(self) -> float:
        """Return x left value of bounding box.

        :return: internal _x value transformed by scale and translation
        """
        return (self._translation_x + self._x) * self._scale

    @x.setter
    def x(self, value: float) -> None:
        """Update transform values (do not alter self._x).

        :param value: new x value after transformation
        """
        self._add_transform(1, value - self.x, 0)

    @property
    def cx(self) -> float:
        """Center x value.

        :return: midpoint of transformed x and x2
        """
        return self.x + self.width / 2

    @cx.setter
    def cx(self, value: float):
        """Center x value.

        :param value: new center x value after transformation
        """
        self._add_transform(1, value - self.cx, 0)

    @property
    def x2(self) -> float:
        """Return x right value of bounding box.

        :return: transformed x + transformed width
        """
        return self.x + self.width

    @x2.setter
    def x2(self, value: float) -> None:
        """Update transform values (do not alter self._x2).

        :param value: new x2 value after transformation
        """
        self._add_transform(1, value - self.x2, 0)

    @property
    def y(self) -> float:
        """Return y top value of bounding box.

        :return: internal _y value transformed by scale and translation
        """
        return (self._translation_y + self._y) * self._scale

    @y.setter
    def y(self, value: float) -> None:
        """Update transform values (do not alter self._y).

        :param value: new y value after transformation
        """
        self._add_transform(1, 0, value - self.y)

    @property
    def cy(self) -> float:
        """Center y value.

        :return: midpoint of transformed y and y2
        """
        return self.y + self.height / 2

    @cy.setter
    def cy(self, value: float):
        """Center y value.

        :param value: new center y value after transformation
        """
        self._add_transform(1, 0, value - self.cy)

    @property
    def y2(self) -> float:
        """Return y bottom value of bounding box.

        :return: transformed y + transformed height
        """
        return self.y + self.height

    @y2.setter
    def y2(self, value: float) -> None:
        """Update transform values (do not alter self._y).

        :param value: new y2 value after transformation
        """
        self.y = value - self.height

    @property
    def width(self) -> float:
        """Width of transformed bounding box.

        :return: internal _width value transformed by scale
        """
        return self._width * self._scale

    @width.setter
    def width(self, value: float) -> None:
        """Update transform values, Do not alter self._width.

        :param value: new width value after transformation

        Here transformed x and y value will be preserved. That is, the bounding box
        is scaled, but still anchored at (transformed) self.x and self.y
        """
        current_x = self.x
        current_y = self.y
        self._scale *= value / self.width
        self.x = current_x
        self.y = current_y

    @property
    def height(self) -> float:
        """Height of transformed bounding box.

        :return: internal _height value transformed by scale
        """
        return self._height * self._scale

    @height.setter
    def height(self, value: float) -> None:
        """Update transform values, Do not alter self._height.

        :param value: new height value after transformation

        Here transformed x and y value will be preserved. That is, the bounding box
        is scaled, but still anchored at (transformed) self.x and self.y
        """
        self.width = value * self.width / self.height

    def _add_transform(self, scale: float, translation_x: float, translation_y: float):
        """Transform the bounding box by updating the transformation attributes.

        :param scale: scale factor
        :param translation_x: x translation
        :param translation_y: y translation

        Transformation attributes are _translation_x, _translation_y, and _scale
        """
        self._translation_x += translation_x / self._scale
        self._translation_y += translation_y / self._scale
        self._scale *= scale

    @property
    def transform_string(self) -> str:
        """Transformation property string value for svg element.

        :return: string value for an svg transform attribute.

        Use with
        ``update_element(elem, transform=bbox.transform_string)``
        """
        scale, trans_x, trans_y = (
            format_number(x)
            for x in (self._scale, self._translation_x, self._translation_y)
        )
        return f"scale({scale}) translate({trans_x} {trans_y})"

    def merge(self, *others: BoundingBox) -> BoundingBox:
        """Create a bounding box around all other bounding boxes.

        :param others: one or more bounding boxes to merge with self
        :return: a bounding box around self and other bounding boxes
        :raises DeprecationWarning:
        """
        warnings.warn(
            "Method a.merge(b, c) is deprecated. "
            + "Use classmethod BoundingBox.merged(a, b, c) instead.",
            category=DeprecationWarning,
            stacklevel=1,
        )
        return BoundingBox.merged(self, *others)

    @classmethod
    def merged(cls, *bboxes: SupportsBounds) -> BoundingBox:
        """Create a bounding box around all other bounding boxes.

        :param bboxes: one or more bounding boxes
        :return: a bounding box encompasing all bboxes args
        :raises ValueError: if no bboxes are given

        This can be used to repace a bounding box after the element it bounds has
        been transformed with instance.transform_string.
        """
        if not bboxes:
            msg = "At least one bounding box is required"
            raise ValueError(msg)
        min_x = min(x.x for x in bboxes)
        max_x = max(x.x + x.width for x in bboxes)
        min_y = min(x.y for x in bboxes)
        max_y = max(x.y + x.height for x in bboxes)
        return BoundingBox(min_x, min_y, max_x - min_x, max_y - min_y)
