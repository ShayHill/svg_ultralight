"""A class to hold a list of bound elements and transform them together.

:author: Shay Hill
:created: 2024-05-05
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from lxml.etree import _Element as EtreeElement  # type: ignore

from svg_ultralight.bounding_boxes.bound_helpers import new_bbox_union
from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
from svg_ultralight.transformations import transform_element

if TYPE_CHECKING:
    from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox

_Matrix = tuple[float, float, float, float, float, float]


@dataclasses.dataclass
class BoundConfederation(SupportsBounds):
    """A class to hold a list of bound elements and transform them together.

    This will transform the individual elements in place.
    """

    blems: list[SupportsBounds | EtreeElement] = dataclasses.field(init=False)
    bbox: BoundingBox = dataclasses.field(init=False)

    def __init__(self, *blems: SupportsBounds | EtreeElement) -> None:
        """Initialize the bound confederation.

        :param blems: bound elements to be transformed together
        """
        self.blems = list(blems)
        self.bbox = new_bbox_union(*self.blems)

    @property
    def transformation(self) -> _Matrix:
        """Get the transformation matrix of the bounding box."""
        return self.bbox.transformation

    def transform(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: float | None = None,
        dx: float | None = None,
        dy: float | None = None,
    ):
        """Transform each bound element in self.blems.

        :param transformation: 2D transformation matrix
        :param scale: optional scale factor
        :param dx: optional x translation
        :param dy: optional y translation

        Keep track of all compounding transformations in order to have a value for
        self.scale (required for membersh and to provide access to cumulative
        transforms should this be useful for any reason. This means all
        transformations must be applied to two bounding boxes: a persistant bbox to
        keep track of the scale property and a temporary bbox to isolate each
        transformation.
        """
        temp_bbox = self.bbox.merge()
        temp_bbox.transform(transformation, scale=scale, dx=dx, dy=dy)

        self.bbox.transform(transformation, scale=scale, dx=dx, dy=dy)
        for blem in self.blems:
            if isinstance(blem, EtreeElement):
                _ = transform_element(blem, temp_bbox.transformation)
            else:
                blem.transform(temp_bbox.transformation)

    @property
    def scale(self) -> float:
        """Get scale of the bounding box."""
        return self.transformation[0]

    @scale.setter
    def scale(self, value: float) -> None:
        """Scale by a uniform factor."""
        self.transform(scale=value / self.scale)

    @property
    def x(self) -> float:
        """Return x left value of bounding box."""
        return self.bbox.x

    @x.setter
    def x(self, value: float) -> None:
        """Update transformation values."""
        self.transform(dx=value - self.x)

    @property
    def cx(self) -> float:
        """Center x value."""
        return self.bbox.cx

    @cx.setter
    def cx(self, value: float):
        """Center x value."""
        self.x += value - self.cx

    @property
    def x2(self) -> float:
        """Return x right value of bounding box."""
        return self.bbox.x2

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
        return self.bbox.y

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
        return self.bbox.cy

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
        return self.bbox.y2

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
        return self.bbox.width

    @width.setter
    def width(self, value: float) -> None:
        """Update transformation values, Do not alter self._width.

        :param value: new width value after transformation

        Here transformed x and y value will be preserved. That is, the bounding box
        is scaled, but still anchored at (transformed) self.x and self.y
        """
        current_x = self.x
        current_y = self.y
        self.scale *= value / self.width
        self.x = current_x
        self.y = current_y

    @property
    def height(self) -> float:
        """Height of transformed bounding box.

        :return: internal _height value transformed by scale
        """
        return self.bbox.height

    @height.setter
    def height(self, value: float) -> None:
        """Update transformation values, Do not alter self._height.

        :param value: new height value after transformation

        Here transformed x and y value will be preserved. That is, the bounding box
        is scaled, but still anchored at (transformed) self.x and self.y
        """
        self.width = value * self.width / self.height
