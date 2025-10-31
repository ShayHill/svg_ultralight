"""A class to hold a list of bound elements and transform them together.

:author: Shay Hill
:created: 2024-05-05
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from lxml.etree import _Element as EtreeElement  # pyright: ignore[reportPrivateUsage]

from svg_ultralight.bounding_boxes.bound_helpers import new_bbox_union
from svg_ultralight.bounding_boxes.type_bounding_box import HasBoundingBox
from svg_ultralight.transformations import new_transformation_matrix, transform_element

if TYPE_CHECKING:
    from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
    from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox

_Matrix = tuple[float, float, float, float, float, float]


@dataclasses.dataclass
class BoundCollection(HasBoundingBox):
    """A class to hold a list of bound elements and transform them together.

    This will transform the individual elements in place.
    """

    blems: list[SupportsBounds | EtreeElement] = dataclasses.field(init=False)
    bbox: BoundingBox = dataclasses.field(init=False)

    def __init__(self, *blems: SupportsBounds | EtreeElement) -> None:
        """Initialize the bound collection.

        :param blems: bound elements to be transformed together
        """
        self.blems = list(blems)
        self.bbox = new_bbox_union(*self.blems)

    def transform(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: tuple[float, float] | float | None = None,
        dx: float | None = None,
        dy: float | None = None,
        reverse: bool = False,
    ) -> None:
        """Transform each bound element in self.blems.

        :param transformation: 2D transformation matrix
        :param scale: optional scale factor
        :param dx: optional x translation
        :param dy: optional y translation
        :param reverse: Transform the element as if it were in a <g> element
            transformed by tmat.

        Keep track of all compounding transformations in order to have a value for
        self.scale (required for members and to provide access to cumulative
        transforms should this be useful for any reason. This means all
        transformations must be applied to two bounding boxes: a persistant bbox to
        keep track of the scale property and a temporary bbox to isolate each
        transformation.
        """
        tmat = new_transformation_matrix(transformation, scale=scale, dx=dx, dy=dy)
        self.bbox.transform(tmat)
        for blem in self.blems:
            if isinstance(blem, EtreeElement):
                _ = transform_element(blem, tmat, reverse=reverse)
            else:
                blem.transform(tmat, reverse=reverse)
