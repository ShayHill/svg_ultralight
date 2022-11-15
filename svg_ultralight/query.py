#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
""" Query an SVG file for bounding boxes

:author: Shay Hill
:created: 7/25/2020

Bounding boxes are generated with a command-line call to Inkscape, so an Inkscape
installation is required for this to work. The bounding boxes are returned as
BoundingBox instances, which are a big help with aligning objects (e.g., text on a
business card). Getting bounding boxes from Inkscape is not exceptionally fast.
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from subprocess import PIPE, Popen
from tempfile import NamedTemporaryFile
from typing import TypeAlias

from lxml import etree

from svg_ultralight.constructors import deepcopy_element
from svg_ultralight.main import new_svg_root, write_svg
from svg_ultralight.strings import format_number

_Element: TypeAlias = etree._Element  # type: ignore


def recursively_fill_ids(elem: _Element) -> _Element:
    """Set the id attribute of an element and all its children. Keep existing ids.

    :param elem: an etree element
    :returns: the element with an existing id or new random uique id

    This is just a convenience function in case you make deepcopies and want to
    replace the ids.
    """
    for child in elem:
        _ = recursively_fill_ids(child)
    if elem.get("id") is None:
        elem.set("id", str(uuid.uuid4()))
    return elem


def recursively_reset_ids(elem: _Element) -> _Element:
    """Replace the id attribute of an element and all its children.

    :param elem: an etree element
    :returns: the element with id attributes replaced
    """
    for child in elem:
        _ = recursively_reset_ids(child)
    elem.set("id", str(uuid.uuid4()))
    return elem


@dataclass
class BoundingBox:
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

    Transform the BoundingBox by setting these variables. Each time you set x, x2, y,
    y2, width, or height, private transformation values (_scale, _transform_x,
    and _transform_y) will be updated.

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

        self.scale is publicly visible, because it's convenient to fit a (usually
        text) element somewhere then scale other elements to the same size--even
        though element width and height may be different. This is a read-only
        attribute, because writing it would cause too many errors of intuition (would
        the scaled element stay anchored to x and y?).

        To match the scale of two elements:
            ``elem_b.width = elem_b.width * elem_a.scale / elem_b.scale``

        This is consistent with setting width any other way: the element will still
        be anchored at self.x and self.y.
        """
        return self._scale

    @property
    def x(self) -> float:
        """x left value of bounding box"""
        return (self._translation_x + self._x) * self._scale

    @x.setter
    def x(self, x: float) -> None:
        """Update transform values (do not alter self._x)"""
        self._add_transform(1, x - self.x, 0)

    @property
    def y(self) -> float:
        """y top value of bounding box"""
        return (self._translation_y + self._y) * self._scale

    @y.setter
    def y(self, y: float) -> None:
        """Update transform values (do not alter self._y)"""
        self._add_transform(1, 0, y - self.y)

    @property
    def x2(self) -> float:
        """x right value of bounding box"""
        return self.x + self.width

    @x2.setter
    def x2(self, x2: float) -> None:
        """Update transform values (do not alter self._x)"""
        self.x = x2 - self.width

    @property
    def y2(self) -> float:
        """y bottom value of bounding box"""
        return self.y + self.height

    @y2.setter
    def y2(self, y2: float) -> None:
        """Update transform values (do not alter self._y)"""
        self.y = y2 - self.height

    @property
    def width(self) -> float:
        """Width of transformed bounding box"""
        return self._width * self._scale

    @width.setter
    def width(self, width: float) -> None:
        """Update transform values, Do not alter self._width.

        Here transformed x and y value will be preserved. That is, the bounding box
        is scaled, but still anchored at (transformed) self.x and self.y
        """
        current_x = self.x
        current_y = self.y
        self._scale *= width / self.width
        self.x = current_x
        self.y = current_y

    @property
    def height(self) -> float:
        """Height of transformed bounding box"""
        return self._height * self._scale

    @height.setter
    def height(self, height: float) -> None:
        """Update transform values, Do not alter self._height.

        Here transformed x and y value will be preserved. That is, the bounding box
        is scaled, but still anchored at (transformed) self.x and self.y
        """
        self.width = height * self.width / self.height

    def _add_transform(self, scale: float, translation_x: float, translation_y: float):
        """Transform the bounding box by updating the transformation attributes

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
        transformation_values = (
            format_number(x)
            for x in (self._scale, self._translation_x, self._translation_y)
        )
        return "scale({}) translate({} {})".format(*transformation_values)

    def merge(self, *others: BoundingBox) -> BoundingBox:
        """Create a bounding box around all other bounding boxes.

        :param others: one or more bounding boxes to merge with self
        :return: a bounding box around self and other bounding boxes
        """
        raise DeprecationWarning(
            "Method a.merge(b, c) is deprecated. "
            + "Use classmethod BoundingBox.merged(a, b, c) instead."
        )
        return BoundingBox.merged(self, *others)

    @classmethod
    def merged(cls, *bboxes: BoundingBox) -> BoundingBox:
        """Create a bounding box around all other bounding boxes.

        This can be used to repace a bounding box after the element it bounds has
        been transformed with instance.transform_string.

        :param others: one or more bounding boxes
        :return: a bounding box encompasing all bboxes args
        """
        if not bboxes:
            raise ValueError("At least one bounding box is required")
        min_x = min(x.x for x in bboxes)
        max_x = max(x.x + x.width for x in bboxes)
        min_y = min(x.y for x in bboxes)
        max_y = max(x.y + x.height for x in bboxes)
        return BoundingBox(min_x, min_y, max_x - min_x, max_y - min_y)


def _normalize_views(elem: _Element) -> _Element:
    """Create a square viewbox for any element with an svg tag.

    :param elem: an etree element
    :returns: the element with a square viewbox

    This prevents the bounding boxes from being skewed. Only do this to copies,
    because there's no way to undo it.
    """
    for child in elem:
        _ = _normalize_views(child)
    if str(elem.tag).endswith("svg"):
        elem.set("viewBox", "0 0 1 1")
        elem.set("width", "1")
        elem.set("height", "1")
    return elem


def map_ids_to_bounding_boxes(
    inkscape: str | Path, *elem_args: _Element
) -> dict[str, BoundingBox]:
    # noinspection SpellCheckingInspection
    """Query an svg file for bounding-box dimensions

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param elem_args: xml element (written to a temporary file then queried)
    :return: svg element ids (and a bounding box for the entire svg file as ``svg``)
        mapped to (x, y, width, height)

    Bounding boxes are relative to svg viewbox. If viewbox x == -10,
    all bounding-box x values will be offset -10. So, everything is wrapped in a root
    element with a "normalized" viewbox, (viewbox=(0, 0, 1, 1)) then any child root
    elements ("child root elements" sounds wrong, but it works) viewboxes are
    normalized as well. This works even with a root element around a root element, so
    input elem_args can be root elements or "normal" elements like "rect", "circle",
    or "text" or a mixture of both.

    The ``inkscape --query-all svg`` call will return a tuple:

    (b'svg1,x,y,width,height\\r\\elem1,x,y,width,height\\r\\n', None)
    where x, y, width, and height are strings of numbers.

    This calls the command and formats the output into a dictionary.

    dpu_ arguments to new_svg_root transform the bounding boxes in non-useful ways.
    This copies all elements except the root element in to a (0, 0, 1, 1) root. This
    will put the boxes where you'd expect them to be, no matter what root you use.
    """
    xml_prime = new_svg_root(0, 0, 1, 1, id_=f"svg_root_{uuid.uuid4()}")
    xml_prime.extend(deepcopy_element(e) for e in elem_args)
    _ = recursively_fill_ids(xml_prime)
    _ = _normalize_views(xml_prime)

    with NamedTemporaryFile(mode="wb", delete=False, suffix=".svg") as svg_file:
        svg = write_svg(svg_file, xml_prime)

    bb_process = Popen(f'"{inkscape}" --query-all {svg}', stdout=PIPE)
    bb_data = str(bb_process.communicate()[0])[2:-1]
    bb_strings = re.split(r"[\\r]*\\n", bb_data)[:-1]
    os.unlink(svg_file.name)

    id2bbox: dict[str, BoundingBox] = {}
    for id_, *bounds in (x.split(",") for x in bb_strings):
        id2bbox[id_] = BoundingBox(*(float(x) for x in bounds))
    return id2bbox


def get_bounding_box(inkscape: str | Path, elem: _Element) -> BoundingBox:
    """Get bounding box around a single element.

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param elem_args: xml elements
    :return: a BoundingBox instance around elem.

    This will work most of the time, but if you're missing an nsmap, you'll need to
    create an entire xml file with a custom nsmap (using
    `svg_ultralight.new_svg_root`) then call `map_ids_to_bounding_boxes` directly.
    """
    id2bbox = map_ids_to_bounding_boxes(inkscape, elem)
    return id2bbox[elem.attrib["id"]]
