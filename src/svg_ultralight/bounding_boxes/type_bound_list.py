"""A class to hold a list of bound elements and transform them together.

:author: Shay Hill
:created: 2024-05-05
"""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from lxml.etree import _Element as EtreeElement

from svg_ultralight.bounding_boxes.bound_helpers import new_bbox_union, new_bound_union
from svg_ultralight.bounding_boxes.type_bounding_box import HasBoundingBox
from svg_ultralight.transformations import new_transformation_matrix, transform_element

if TYPE_CHECKING:
    from svg_ultralight.attrib_hints import ElemAttrib
    from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
    from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
    from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox

_Matrix = tuple[float, float, float, float, float, float]


class BoundList(HasBoundingBox):
    """A class to hold a list of bound elements and transform them together.

    This will transform the individual elements in place.
    """

    def __init__(self, *blems: SupportsBounds | EtreeElement) -> None:
        """Initialize the bound list.

        :param blems: bound elements to be transformed together
        """
        self.blems = list(blems)

    @overload
    def __getitem__(self, idx: slice) -> BoundList: ...

    @overload
    def __getitem__(self, idx: int) -> SupportsBounds | EtreeElement: ...

    def __getitem__(
        self, idx: slice | int
    ) -> BoundList | SupportsBounds | EtreeElement:
        """Get one or more padded text elements."""
        if isinstance(idx, int):
            return self.blems[idx]
        return BoundList(*self.blems[idx])

    def append(self, blem: SupportsBounds | EtreeElement) -> None:
        """Append a padded text element to the list."""
        self.blems.append(blem)

    def union(self, **attribs: ElemAttrib) -> BoundElement:
        """Return a single bound element containing all the bound elements."""
        return new_bound_union(*self.blems, **attribs)

    @property
    def bbox(self) -> BoundingBox:
        """The bounding box of the bound list."""
        return new_bbox_union(*self.blems)

    @bbox.setter
    def bbox(self, value: BoundingBox) -> None:
        """Forbid setting the bbox directly.

        Required because, per inheritance, bbox is a writeable attribute.
        """
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
        for blem in self.blems:
            if isinstance(blem, EtreeElement):
                _ = transform_element(blem, tmat, reverse=reverse)
            else:
                blem.transform(tmat, reverse=reverse)
