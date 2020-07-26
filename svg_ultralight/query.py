#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
""" Query an SVG file for bounding boxes

:author: Shay Hill
:created: 7/25/2020

None of this is exceptionally fast.
"""
import os
import tempfile
from subprocess import PIPE, Popen
from typing import Dict, NamedTuple, Optional

from lxml import etree  # type: ignore

from svg_ultralight import write_svg


class BoundingBox(NamedTuple):
    """ Bounding box dimensions for an svg object """

    x: float
    y: float
    width: float
    height: float


def map_ids_to_bounding_boxes(
    inkscape: str, svg: Optional[str] = None, xml: Optional[etree.Element] = None,
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
    """
    if svg is None:
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, suffix=".svg"
        ) as svg_file:
            svg = write_svg(svg_file, xml)
        result = map_ids_to_bounding_boxes(inkscape, svg)
        os.unlink(svg)
        return result

    bb_process = Popen(f'"{inkscape}" --query-all {svg}', stdout=PIPE)
    bb_data = str(bb_process.communicate()[0])[2:-1]
    bb_strings = bb_data.split("\\r\\n")[:-1]
    id2bbox = {}
    for id_, *bounds in (x.split(",") for x in bb_strings):
        id2bbox[id_] = BoundingBox(*(float(x) for x in bounds))
    return id2bbox
