"""Bounding box classes for SVG elements.

:author: Shay Hill
:created: 2022-12-09
"""

from __future__ import annotations

import dataclasses
import math

from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
from svg_ultralight.strings import svg_matrix
from svg_ultralight.transformations import mat_apply, mat_dot, new_transformation_matrix
from svg_ultralight.unit_conversion import MeasurementArg, to_user_units

_Matrix = tuple[float, float, float, float, float, float]


class HasBoundingBox(SupportsBounds):
    """A parent class for BoundElement and others that have a bbox attribute."""

    def __init__(self, bbox: BoundingBox) -> None:
        """Initialize the HasBoundingBox instance."""
        self.bbox = bbox

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
        x = self.bbox.base_x
        y = self.bbox.base_y
        x2 = x + self.bbox.base_width
        y2 = y + self.bbox.base_height
        return (x, y), (x, y2), (x2, y2), (x2, y)

    def values(self) -> tuple[float, float, float, float]:
        """Get the values of the bounding box.

        :return: x, y, width, height of the bounding box
        """
        return (
            self.bbox.x,
            self.bbox.y,
            self.bbox.width,
            self.bbox.height,
        )

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
            self.transformation

        These quadrilateral defined by these corners may not be axis aligned. This is
        purely for determining the bounds of the transformed box.
        """
        c0, c1, c2, c3 = (
            mat_apply(self.bbox.transformation, c) for c in self._get_input_corners()
        )
        return c0, c1, c2, c3

    @property
    def corners(
        self,
    ) -> tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ]:
        """Get the corners of the bbox in the current state. CW from top left."""
        x, y, x2, y2 = self.x, self.y, self.x2, self.y2
        return ((x, y), (x, y2), (x2, y2), (x2, y))

    def transform(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: tuple[float, float] | float | None = None,
        dx: float | None = None,
        dy: float | None = None,
        reverse: bool = False,
    ) -> None:
        """Transform the bounding box by updating the transformation attribute.

        :param transformation: 2D transformation matrix
        :param scale: scale factor
        :param dx: x translation
        :param dy: y translation
        :param reverse: Transform the element as if it were in a <g> element
            transformed by tmat.

        All parameters are optional. Scale, dx, and dy are optional and applied after
        the transformation matrix if both are given. This shouldn't be necessary in
        most cases, the four parameters are there to allow transformation arguments
        to be passed in a variety of ways. Scale, dx, and dy are the sensible values
        to pass "by hand". The transformation matrix is the sensible argument to pass
        when applying a transformation from another bounding box instance.
        """
        tmat = new_transformation_matrix(transformation, scale=scale, dx=dx, dy=dy)
        if reverse:
            self.bbox.transformation = mat_dot(self.bbox.transformation, tmat)
        else:
            self.bbox.transformation = mat_dot(tmat, self.bbox.transformation)

    @property
    def scale(self) -> tuple[float, float]:
        """Get scale of the bounding box.

        :return: x and y scale of the bounding box

        Use caution, the scale attribute can cause errors in intuition. Changing
        width or height will change the scale attribute, but not the x or y values.
        The scale setter, on the other hand, will work in the tradational manner.
        I.e., x => x*scale, y => y*scale, x2 => x*scale, y2 => y*scale, width =>
        width*scale, height => height*scale, scale => scale*scale. This matches how
        scale works in almost every other context.
        """
        xx, xy, yx, yy, *_ = self.bbox.transformation
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
        """Set the x coordinate of the left edge of the bounding box.

        :param value: the new x coordinate of the left edge of the bounding box
        """
        self.transform(dx=value - self.x)

    @property
    def cx(self) -> float:
        """Center x value.

        :return: midpoint of transformed x and x2
        """
        return self.x + self.width / 2

    @cx.setter
    def cx(self, value: float) -> None:
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
    def cy(self, value: float) -> None:
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
        self.transform(scale=value / self.width)
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
        return svg_matrix(self.bbox.transformation)


@dataclasses.dataclass
class BoundingBox(HasBoundingBox):
    """Mutable bounding box object for svg_ultralight.

    :param x: left x value
    :param y: top y value
    :param width: width of the bounding box
    :param height: height of the bounding box

    The below optional parameter, in addition to the required parameters, captures
    the entire state of a BoundingBox instance. It could be used to make a copy or
    to initialize a transformed box with the same transform_string as another box.
    Under most circumstances, it will not be used.

    :param transformation: transformation matrix

    Functions that return a bounding box will return a BoundingBox instance. This
    instance can be transformed. Transformations will be combined and stored to be
    passed to new_element as a transform value.

    Define the bbox with x=, y=, width=, height=

    Transform the BoundingBox by setting these variables. Each time you set x, cx,
    x2, y, cy, y2, width, or height, private transformation value `transformation`
    will be updated.

    The ultimate transformation can be accessed through ``.transform_string``.
    So the workflow will look like :

        1. Get the bounding box of an svg element
        2. Update the bounding box x, y, width, and height
        3. Transform the original svg element with
            svg_ultralight.transform_element(elem, bbox.transformation)
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

    base_x: float = dataclasses.field(init=False)
    base_y: float = dataclasses.field(init=False)
    base_width: float = dataclasses.field(init=False)
    base_height: float = dataclasses.field(init=False)
    transformation: _Matrix = dataclasses.field(init=False)

    def __init__(
        self,
        x: MeasurementArg,
        y: MeasurementArg,
        width: MeasurementArg,
        height: MeasurementArg,
        transformation: _Matrix = (1, 0, 0, 1, 0, 0),
    ) -> None:
        """Initialize a BoundingBox instance.

        :param x: left x value
        :param y: top y value
        :param width: width of the bounding box
        :param height: height of the bounding box
        """
        self.base_x = to_user_units(x)
        self.base_y = to_user_units(y)
        self.base_width = to_user_units(width)
        self.base_height = to_user_units(height)
        self.transformation = transformation
        self.bbox = self

    def join(self, *others: BoundingBox) -> BoundingBox:
        """Create a bounding box around all other bounding boxes.

        :param others: one or more bounding boxes to merge with self
        :return: a bounding box around self and other bounding boxes
        :raises DeprecationWarning:
        """
        return BoundingBox.union(self, *others)

    def intersect(self, *bboxes: SupportsBounds) -> BoundingBox | None:
        """Create a bounding box around the intersection of all other bounding boxes.

        :param bboxes: one or more bounding boxes to intersect with self
        :return: a bounding box around the intersection of self and other bounding
             boxes, or None if there is no intersection
        """
        return BoundingBox.intersection(self, *bboxes)

    @classmethod
    def union(cls, *bboxes: SupportsBounds) -> BoundingBox:
        """Create a bounding box around all other bounding boxes.

        :param bboxes: one or more bounding boxes
        :return: a bounding box encompasing all bboxes args
        :raises ValueError: if no bboxes are given
        """
        if not bboxes:
            msg = "At least one bounding box is required"
            raise ValueError(msg)
        xs = [*(x.x for x in bboxes), *(x.x2 for x in bboxes)]
        ys = [*(x.y for x in bboxes), *(x.y2 for x in bboxes)]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return BoundingBox(min_x, min_y, max_x - min_x, max_y - min_y)

    @classmethod
    def intersection(cls, *bboxes: SupportsBounds) -> BoundingBox | None:
        """Create a bounding box around the intersection of all other bounding boxes.

        :param bboxes: one or more bounding boxes
        :return: a bounding box around the intersection of all bboxes, or None if
            there is no intersection
        :raises ValueError: if no bboxes are given
        """
        if not bboxes:
            return None
        valid_bboxes: list[BoundingBox] = []
        for bbox in bboxes:
            x, x2 = sorted([bbox.x, bbox.x2])
            y, y2 = sorted([bbox.y, bbox.y2])
            valid_bboxes.append(BoundingBox(x, y, x2 - x, y2 - y))
        x = max(x.x for x in valid_bboxes)
        x2 = min(x.x2 for x in valid_bboxes)
        y = max(x.y for x in valid_bboxes)
        y2 = min(x.y2 for x in valid_bboxes)
        if x > x2 or y > y2:
            return None
        return BoundingBox(x, y, x2 - x, y2 - y)
