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

if TYPE_CHECKING:
    from lxml.etree import _Element as EtreeElement  # type: ignore

    from svg_ultralight.query import BoundingBox


class BoundElement:

    """An element with a bounding box.

    Updates the element when x, y, x2, y2, width, or height are set.

    Can access these BoundingBox attributes (plus scale) as attributes of this object.
    """

    _bbox_setters = {"x", "cx", "x2", "y", "cy", "y2", "width", "height"}

    def __init__(self, element: EtreeElement, bounding_box: BoundingBox) -> None:
        """Initialize a BoundElement instance.

        :param element: the element to be bound
        :param bounding_box: the bounding box around the element
        """
        self.elem = element
        self.bbox = bounding_box

    def _update_elem(self):
        self.elem.attrib["transform"] = self.bbox.transform_string

    def __getattr__(self, name: str) -> float:
        """Allow direct access to a subset of BoundingBox attributes.

        :param name: x, y, x2, y2, width, height, scale
        :return: the value of self.bbox.name
        :raises AttributeError: if name is not in the subset of allowed BoundingBox
            attributes
        """
        if name in self._bbox_setters | {"scale"}:
            return getattr(self.bbox, name)
        msg = f"{self.__class__.__name__} has no attribute {name}"
        raise AttributeError(msg)

    def __setattr__(self, name: str, value: float) -> None:
        """Set settable BoundingBox attributes and update the element.

        :param name: x, y, x2, y2, width, height, scale
        :param value: the new value of self.bbox.name
        """
        if name in self._bbox_setters:
            setattr(self.bbox, name, value)
            self._update_elem()
        else:
            super().__setattr__(name, value)
