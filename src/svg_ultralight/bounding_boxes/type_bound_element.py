"""An element tied to a BoundingBox instance.

Take an element, associate it to a BoundingBox instance, transform the BoundingBox
instance. The element will be transformed accordingly.

It is critical to remember that self.elem is a reference. It is not necessary to
access self.elem through the BoundElement instance. Earlier and later references will
all be updated as the BoundElement instance is updated.

:author: Shay Hill
:created: 2022-12-09
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from svg_ultralight.bounding_boxes.type_bounding_box import HasBoundingBox
from svg_ultralight.transformations import new_transformation_matrix, transform_element

if TYPE_CHECKING:
    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

    from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox

_Matrix = tuple[float, float, float, float, float, float]


class BoundElement(HasBoundingBox):
    """An element with a bounding box.

    Updates the element when x, y, x2, y2, width, or height are set.

    Can access these BoundingBox attributes (plus scale) as attributes of this object.
    """

    def __init__(self, element: EtreeElement, bounding_box: BoundingBox) -> None:
        """Initialize a BoundElement instance.

        :param element: the element to be bound
        :param bounding_box: the bounding box around the element
        """
        self.elem = element
        self.bbox = bounding_box

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
        self.bbox.transform(tmat, reverse=reverse)
        _ = transform_element(self.elem, tmat, reverse=reverse)
