"""An element tied to a BoundingBox instance.

Take an element, associate it to a BoundingBox instance, transform the BoundingBox
instance. The element will be transformed accordingly.

It is critical to remember that self.elem is a reference. It is not necessary to
access self.elem through the BoundElement instance. Earlier and later references will
all be updated as the BoundElement instance is updated.

:author: Shay Hill
:created: 2022-12-09
"""

from typing import Any, TypeAlias

from lxml import etree

from svg_ultralight.query import BoundingBox

EtreeElement: TypeAlias = etree._Element  # type: ignore


class BoundElement:
    """An element with a bounding box.

    Updates the element when x, y, x2, y2, width, or height are set.

    Can access these BoundingBox attributes (plus scale) as attributes of this object.
    """

    _bbox_setters = {"x", "cx", "x2", "y", "cy", "y2", "width", "height"}

    def __init__(self, element: EtreeElement, bounding_box: BoundingBox):
        self.elem = element
        self.bbox = bounding_box

    def _update_elem(self):
        self.elem.attrib["transform"] = self.bbox.transform_string

    def __getattr__(self, name: str) -> str:
        """Allow direct access to a subset of BoundingBox attributes.

        :param name: x, y, x2, y2, width, height, scale
        :return: the value of self.bbox.name
        :raises AttributeError: if name is not in the subset of allowed BoundingBox
            attributes
        """
        if name in self._bbox_setters | {"scale"}:
            return getattr(self.bbox, name)
        raise AttributeError(f"{self.__class__.__name__} has no attribute {name}")

    def __setattr__(self, name: str, value: Any):
        """Set settable BounsingBox attributes and update the element."""
        if name in self._bbox_setters:
            setattr(self.bbox, name, value)
            self._update_elem()
        else:
            super().__setattr__(name, value)
