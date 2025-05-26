"""Bounding box classes for SVG elements.

:author: Shay Hill
:created: 2022-12-09
"""

from __future__ import annotations

import dataclasses
import math

from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
from svg_ultralight.string_conversion import format_number
from svg_ultralight.transformations import mat_apply, mat_dot, new_transformation_matrix

_Matrix = tuple[float, float, float, float, float, float]


@dataclasses.dataclass
class BoundingBox(SupportsBounds):
    """Mutable bounding box object for svg_ultralight.

    :param x: left x value
    :param y: top y value
    :param width: width of the bounding box
    :param height: height of the bounding box

    The below optional parameter, in addition to the required parameters, captures
    the entire state of a BoundingBox instance. It could be used to make a copy or
    to initialize a transformed box with the same transform_string as another box.
    Under most circumstances, it will not be used.

    :param _transformation: transformation matrix

    Functions that return a bounding box will return a BoundingBox instance. This
    instance can be transformed (uniform scale and translate only). Transformations
    will be combined and scored to be passed to new_element as a transform value.

    Define the bbox with x=, y=, width=, height=

    Transform the BoundingBox by setting these variables. Each time you set x, cx,
    x2, y, cy, y2, width, or height, private transformation value _transformation
    will be updated.

    The ultimate transformation can be accessed through ``.transform_string``.
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
    _transformation: _Matrix = (1, 0, 0, 1, 0, 0)

    def _get_input_corners(
        self,
    ) -> tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ]:
        """Get the input corners of the bounding box.

        :return: four corners counter-clockwise starting at top left
        """
        x2 = self._x + self._width
        y2 = self._y + self._height
        return (self._x, self._y), (x2, self._y), (x2, y2), (self._x, y2)

    def _get_transformed_corners(
        self,
    ) -> tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ]:
        """Get the transformed corners of the bounding box.

        :return: four corners counter-clockwise starting at top left, transformed by
            self._transformation
        """
        c0, c1, c2, c3 = (
            mat_apply(self._transformation, c) for c in self._get_input_corners()
        )
        return c0, c1, c2, c3

    def _scale_scale_by_uniform_scalar(self, scalar: float) -> None:
        """Scale the bounding box uniformly by a factor.

        :param scale: scale factor
        Unlike self.scale, this does not set the scale, but scales the scale. So if
        the current scale is (2, 6), and you call this with a scalar of 2, the new
        scale will be (4, 12).
        """
        self.transform(scale=(scalar, scalar))

    @property
    def transformation(self) -> _Matrix:
        """Return transformation matrix.

        :return: transformation matrix
        """
        return self._transformation

    def transform(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: tuple[float, float] | None = None,
        dx: float | None = None,
        dy: float | None = None,
    ):
        """Transform the bounding box by updating the transformation attribute.

        :param transformation: 2D transformation matrix
        :param scale: scale factor
        :param dx: x translation
        :param dy: y translation

        All parameters are optional. Scale, dx, and dy are optional and applied after
        the transformation matrix if both are given. This shouldn't be necessary in
        most cases, the four parameters are there to allow transformation arguments
        to be passed in a variety of ways. Scale, dx, and dy are the sensible values
        to pass "by hand". The transformation matrix is the sensible argument to pass
        when applying a transformation from another bounding box instance.
        """
        tmat = new_transformation_matrix(transformation, scale=scale, dx=dx, dy=dy)
        self._transformation = mat_dot(tmat, self.transformation)

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
        xx, xy, yx, yy, *_ = self.transformation
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
        new_scale = value[0] / self.scale[0], value[1] / self.scale[1]
        self.transform(scale=new_scale)

    @property
    def x(self) -> float:
        """Return x left value of bounding box.

        :return: internal _x value transformed by scale and translation
        """
        return min(x for x, _ in self._get_transformed_corners())

    @x.setter
    def x(self, value: float) -> None:
        """Update transformation values (do not alter self._x).

        :param value: new x value after transformation
        """
        self.transform(dx=value - self.x)

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
        self.x += value - self.cx

    @property
    def x2(self) -> float:
        """Return x right value of bounding box.

        :return: transformed x + transformed width
        """
        return max(x for x, _ in self._get_transformed_corners())

    @x2.setter
    def x2(self, value: float) -> None:
        """Update transformation values (do not alter self._x2).

        :param value: new x2 value after transformation
        """
        self.x += value - self.x2

    @property
    def y(self) -> float:
        """Return y top value of bounding box.

        :return: internal _y value transformed by scale and translation
        """
        return min(y for _, y in self._get_transformed_corners())

    @y.setter
    def y(self, value: float) -> None:
        """Update transformation values (do not alter self._y).

        :param value: new y value after transformation
        """
        self.transform(dy=value - self.y)

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
        self.y += value - self.cy

    @property
    def y2(self) -> float:
        """Return y bottom value of bounding box.

        :return: transformed y + transformed height
        """
        return max(y for _, y in self._get_transformed_corners())

    @y2.setter
    def y2(self, value: float) -> None:
        """Update transformation values (do not alter self._y).

        :param value: new y2 value after transformation
        """
        self.y += value - self.y2

    @property
    def width(self) -> float:
        """Width of transformed bounding box.

        :return: internal _width value transformed by scale
        """
        return self.x2 - self.x

    @width.setter
    def width(self, value: float) -> None:
        """Update transformation values, Do not alter self._width.

        :param value: new width value after transformation

        Here transformed x and y value will be preserved. That is, the bounding box
        is scaled, but still anchored at (transformed) self.x and self.y
        """
        current_x = self.x
        current_y = self.y
        self._scale_scale_by_uniform_scalar(value / self.width)
        self.x = current_x
        self.y = current_y

    @property
    def height(self) -> float:
        """Height of transformed bounding box.

        :return: internal _height value transformed by scale
        """
        return self.y2 - self.y

    @height.setter
    def height(self, value: float) -> None:
        """Update transformation values, Do not alter self._height.

        :param value: new height value after transformation

        Here transformed x and y value will be preserved. That is, the bounding box
        is scaled, but still anchored at (transformed) self.x and self.y
        """
        self.width = value * self.width / self.height

    @property
    def transform_string(self) -> str:
        """Transformation property string value for svg element.

        :return: string value for an svg transformation attribute.

        Use with
        ``update_element(elem, transform=bbox.transform_string)``
        """
        return f"matrix({' '.join(map(format_number, self.transformation))})"

    def merge(self, *others: BoundingBox) -> BoundingBox:
        """Create a bounding box around all other bounding boxes.

        :param others: one or more bounding boxes to merge with self
        :return: a bounding box around self and other bounding boxes
        :raises DeprecationWarning:
        """
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


class HasBoundingBox(SupportsBounds):
    """A parent class for BoundElement and others that have a bbox attribute."""

    def __init__(self, bbox: BoundingBox) -> None:
        """Initialize the HasBoundingBox instance."""
        self.bbox = bbox

    @property
    def transformation(self) -> _Matrix:
        """The transformation matrix of the bounding box."""
        return self.bbox.transformation

    def transform(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: tuple[float, float] | None = None,
        dx: float | None = None,
        dy: float | None = None,
    ):
        """Transform the element and bounding box.

        :param transformation: a 6-tuple transformation matrix
        :param scale: a scaling factor
        :param dx: the x translation
        :param dy: the y translation
        """
        self.bbox.transform(transformation, scale=scale, dx=dx, dy=dy)

    @property
    def scale(self) -> tuple[float, float]:
        """The scale of the bounding box.

        :return: the scale of the bounding box
        """
        xx, xy, yx, yy, *_ = self.bbox.transformation
        return math.sqrt(xx * xx + xy * xy), math.sqrt(yx * yx + yy * yy)

    @scale.setter
    def scale(self, value: tuple[float, float]):
        """Set the scale of the bounding box.

        :param value: the scale of the bounding box
        """
        self.transform(scale=(value[0] / self.scale[0], value[1] / self.scale[1]))

    @property
    def x(self) -> float:
        """The x coordinate of the left edge of the bounding box.

        :return: the x coordinate of the left edge of the bounding box
        """
        return self.bbox.x

    @x.setter
    def x(self, value: float):
        """Set the x coordinate of the left edge of the bounding box.

        :param value: the new x coordinate of the left edge of the bounding box
        """
        self.transform(dx=value - self.x)

    @property
    def x2(self) -> float:
        """The x coordinate of the right edge of the bounding box.

        :return: the x coordinate of the right edge of the bounding box
        """
        return self.bbox.x2

    @x2.setter
    def x2(self, value: float):
        """Set the x coordinate of the right edge of the bounding box.

        :param value: the new x coordinate of the right edge of the bounding box
        """
        self.x += value - self.x2

    @property
    def cx(self) -> float:
        """The x coordinate of the center of the bounding box.

        :return: the x coordinate of the center of the bounding box
        """
        return self.bbox.cx

    @cx.setter
    def cx(self, value: float):
        """Set the x coordinate of the center of the bounding box.

        :param value: the new x coordinate of the center of the bounding box
        """
        self.x += value - self.cx

    @property
    def y(self) -> float:
        """The y coordinate of the top edge of the bounding box.

        :return: the y coordinate of the top edge of the bounding box
        """
        return self.bbox.y

    @y.setter
    def y(self, value: float):
        """Set the y coordinate of the top edge of the bounding box.

        :param value: the new y coordinate of the top edge of the bounding box
        """
        self.transform(dy=value - self.y)

    @property
    def y2(self) -> float:
        """The y coordinate of the bottom edge of the bounding box.

        :return: the y coordinate of the bottom edge of the bounding box
        """
        return self.bbox.y2

    @y2.setter
    def y2(self, value: float):
        """Set the y coordinate of the bottom edge of the bounding box.

        :param value: the new y coordinate of the bottom edge of the bounding box
        """
        self.y += value - self.y2

    @property
    def cy(self) -> float:
        """The y coordinate of the center of the bounding box.

        :return: the y coordinate of the center of the bounding box
        """
        return self.bbox.cy

    @cy.setter
    def cy(self, value: float):
        """Set the y coordinate of the center of the bounding box.

        :param value: the new y coordinate of the center of the bounding box
        """
        self.y += value - self.cy

    @property
    def width(self) -> float:
        """The width of the bounding box.

        :return: the width of the bounding box
        """
        return self.bbox.width

    @width.setter
    def width(self, value: float):
        """Set the width of the bounding box.

        :param value: the new width of the bounding box
        """
        current_x = self.x
        current_y = self.y
        self.transform(scale=(value / self.width, value / self.width))
        self.x = current_x
        self.y = current_y

    @property
    def height(self) -> float:
        """The height of the bounding box.

        :return: the height of the bounding box
        """
        return self.bbox.height

    @height.setter
    def height(self, value: float):
        """Set the height of the bounding box.

        :param value: the new height of the bounding box
        """
        self.width *= value / self.height
