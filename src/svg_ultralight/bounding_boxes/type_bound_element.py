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

from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds

if TYPE_CHECKING:
    from lxml.etree import _Element as EtreeElement  # type: ignore

    from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox


class BoundElement(SupportsBounds):

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

    def _update_elem(self):
        self.elem.attrib["transform"] = self.bbox.transform_string

    @property
    def x(self) -> float:
        """The x coordinate of the left edge of the bounding box.

        :return: the x coordinate of the left edge of the bounding box
        """
        return self.bbox.x

    @x.setter
    def x(self, x: float):
        """Set the x coordinate of the left edge of the bounding box.

        :param x: the new x coordinate of the left edge of the bounding box
        """
        self.bbox.x = x
        self._update_elem()

    @property
    def x2(self) -> float:
        """The x coordinate of the right edge of the bounding box.

        :return: the x coordinate of the right edge of the bounding box
        """
        return self.bbox.x2

    @x2.setter
    def x2(self, x2: float):
        """Set the x coordinate of the right edge of the bounding box.

        :param x2: the new x coordinate of the right edge of the bounding box
        """
        self.bbox.x2 = x2
        self._update_elem()

    @property
    def cx(self) -> float:
        """The x coordinate of the center of the bounding box.

        :return: the x coordinate of the center of the bounding box
        """
        return self.bbox.cx

    @cx.setter
    def cx(self, cx: float):
        """Set the x coordinate of the center of the bounding box.

        :param cx: the new x coordinate of the center of the bounding box
        """
        self.bbox.cx = cx
        self._update_elem()

    @property
    def y(self) -> float:
        """The y coordinate of the top edge of the bounding box.

        :return: the y coordinate of the top edge of the bounding box
        """
        return self.bbox.y

    @y.setter
    def y(self, y: float):
        """Set the y coordinate of the top edge of the bounding box.

        :param y: the new y coordinate of the top edge of the bounding box
        """
        self.bbox.y = y
        self._update_elem()

    @property
    def y2(self) -> float:
        """The y coordinate of the bottom edge of the bounding box.

        :return: the y coordinate of the bottom edge of the bounding box
        """
        return self.bbox.y2

    @y2.setter
    def y2(self, y2: float):
        """Set the y coordinate of the bottom edge of the bounding box.

        :param y2: the new y coordinate of the bottom edge of the bounding box
        """
        self.bbox.y2 = y2
        self._update_elem()

    @property
    def cy(self) -> float:
        """The y coordinate of the center of the bounding box.

        :return: the y coordinate of the center of the bounding box
        """
        return self.bbox.cy

    @cy.setter
    def cy(self, cy: float):
        """Set the y coordinate of the center of the bounding box.

        :param cy: the new y coordinate of the center of the bounding box
        """
        self.bbox.cy = cy
        self._update_elem()

    @property
    def width(self) -> float:
        """The width of the bounding box.

        :return: the width of the bounding box
        """
        return self.bbox.width

    @width.setter
    def width(self, width: float):
        """Set the width of the bounding box.

        :param width: the new width of the bounding box
        """
        self.bbox.width = width
        self._update_elem()

    @property
    def height(self) -> float:
        """The height of the bounding box.

        :return: the height of the bounding box
        """
        return self.bbox.height

    @height.setter
    def height(self, height: float):
        """Set the height of the bounding box.

        :param height: the new height of the bounding box
        """
        self.bbox.height = height
        self._update_elem()

    @property
    def scale(self) -> float:
        """The scale of the bounding box.

        :return: the scale of the bounding box
        """
        return self.bbox.scale
