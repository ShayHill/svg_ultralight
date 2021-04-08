#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
""" Query an SVG file for bounding boxes

:author: Shay Hill
:created: 7/25/2020

None of this is exceptionally fast.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from subprocess import PIPE, Popen
from tempfile import NamedTemporaryFile
from typing import Dict

from lxml import etree  # type: ignore

from svg_ultralight import write_svg
from .constructors import deepcopy_element
from .strings import format_number
from .svg_ultralight import new_svg_root


@dataclass
class BoundingBox:
    """
    Mutable bounding box object for svg_ultralight.

    Bounding box can be transformed (uniform scale and translate only).
    Transformations will be combined and scored to be passes to new_element as a
    transform value.
    """

    origin_x: float
    origin_y: float
    origin_width: float
    origin_height: float
    scale: float = 1
    translation_x: float = 0
    translation_y: float = 0

    @property
    def x(self) -> float:
        return (self.translation_x + self.origin_x) * self.scale

    @x.setter
    def x(self, x) -> None:
        self.add_transform(1, x - self.x, 0)

    @property
    def y(self) -> float:
        return (self.translation_y + self.origin_y) * self.scale

    @y.setter
    def y(self, y) -> None:
        self.add_transform(1, 0, y - self.y)

    @property
    def x2(self) -> float:
        """ Higher x value """
        return self.x + self.width

    @x2.setter
    def x2(self, x2) -> None:
        self.x = x2 - self.width

    @property
    def y2(self) -> float:
        """ Higher y value """
        return self.y + self.height

    @y2.setter
    def y2(self, y2) -> None:
        self.y = y2 - self.height

    @property
    def width(self) -> float:
        return self.origin_width * self.scale

    @width.setter
    def width(self, width: float) -> None:
        self.translation_x *= self.width / width
        self.translation_y *= self.width / width
        self.scale *= width / self.width

    @property
    def height(self) -> float:
        return self.origin_height * self.scale

    @height.setter
    def height(self, height: float) -> None:
        self.width = height * self.width / self.height

    def _asdict(self):
        return {x: getattr(self, x) for x in ("x", "y", "width", "height")}

    def add_transform(self, scale: float, translation_x: float, translation_y: float):
        self.translation_x += translation_x / self.scale
        self.translation_y += translation_y / self.scale
        self.scale *= scale

    @property
    def transform_string(self):
        """
        Transformation property string value for svg element.

        :return: string value for an svg transform attribute.
        """
        scale, tx, ty = (
            format_number(getattr(self, x))
            for x in ("scale", "translation_x", "translation_y")
        )
        return f"scale({scale}) translate({tx} {ty})"

    def merge(self, *others) -> BoundingBox:
        """
        Create a bounding box around all other bounding boxes.

        :param others: one or more bounding boxes to merge with self
        :return: a bounding box around self and other bounding boxes
        """
        bboxes = (self,) + others
        min_x = min(x.x for x in bboxes)
        max_x = max(x.x + x.width for x in bboxes)
        min_y = min(x.y for x in bboxes)
        max_y = max(x.y + x.height for x in bboxes)
        return BoundingBox(min_x, min_y, max_x - min_x, max_y - min_y)


def map_ids_to_bounding_boxes(
    inkscape: str,
    xml: etree.Element,
) -> Dict[str, BoundingBox]:
    """
    Query an svg file for bounding-box dimensions

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``

    PROVIDE ONE OF:
    :param svg: path to an svg file (temporary files will work).
    :param xml: xml element (written to a temporary file then queried)

    :return: svg element ids (and a bounding box for the entire svg file as ``svg\\d``)
        mapped to (x, y, width, height)

    Bounding boxes are relative to svg viewbox. If viewbox x == -10,
    all bounding-box x values will be offset -10.

    The ``inkscape --query-all svg`` call will return a tuple:

    (b'svg1,x,y,width,height\\r\\elem1,x,y,width,height\\r\\n', None)
    where x, y, width, and height are strings of numbers.

    This calls the command and formats the output into a dictionary.

    dpu_ arguments to new_svg_root transform the bounding boxes in non-useful ways.
    This copies all elements except the root element in to a (0, 0, 1, 1) root. This
    will put the boxes where you'd expect them to be, no matter what root you use.
    """
    xml_prime = new_svg_root(0, 0, 1, 1)
    xml_prime.extend((deepcopy_element(x) for x in xml))
    with NamedTemporaryFile(mode="wb", delete=False, suffix=".svg") as svg_file:
        svg = write_svg(svg_file, xml_prime)

    bb_process = Popen(f'"{inkscape}" --query-all {svg}', stdout=PIPE)
    bb_data = str(bb_process.communicate()[0])[2:-1]
    bb_strings = re.split(r"[\\r]*\\n", bb_data)[:-1]
    os.unlink(svg_file.name)

    id2bbox = {}
    for id_, *bounds in (x.split(",") for x in bb_strings):
        id2bbox[id_] = BoundingBox(*(float(x) for x in bounds))
    return id2bbox


def get_bounding_box(inkscape: str, elem: etree.Element) -> BoundingBox:
    """
    Get bounding box around a single element.

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param elem: xml element
    :return: a BoundingBox instance around elem.

    This will work most of the time, but if you're missing an nsmap, you'll need to
    create an entire xml file with a custom nsmap (using
    `svg_ultralight.new_svg_root`) then call `map_ids_to_bounding_boxes` directly.
    """
    temp_screen = new_svg_root(0, 0, 1, 1)
    temp_screen.append(deepcopy_element(elem))
    return list(map_ids_to_bounding_boxes(inkscape, xml=temp_screen).values())[1]
