"""Read SVG file and extract text content.

Note about svg resolution: Despite the fact that vector graphics have effectively
infinite resolution, ePub apparently uses the actual geometry size to determine the
resolution of the image. For images ike a business card drawn in real-world inches
(3.5" width), an ePub will assume a size of 3.5 pixels. There may be some unit for
the width and height variables (for InDesign, it's pnt) that addresses this, but I
don't trust it to be consistent across ePub readers. I adjust the units to something
large, then use CSS to scale it down to the correct size.

:author: Shay Hill
:created: 2025-07-28
"""

import os
from pathlib import Path

from lxml import etree
from lxml.etree import _Element as EtreeElement  # pyright: ignore[reportPrivateUsage]

import svg_ultralight as su


def get_bounding_box_from_root(root: EtreeElement) -> su.BoundingBox:
    """Extract bounding box from SVG root element.

    :param root: the root element of the SVG file
    :raise ValueError: if the viewBox attribute is not present

    """
    viewbox = root.get("viewBox", "")
    try:
        x, y, width, height = map(float, viewbox.split())
    except ValueError as e:
        msg = f"Invalid or missing viewBox attribute: '{viewbox}'"
        raise ValueError(msg) from e
    return su.BoundingBox(x, y, width, height)


def parse(svg_file: str | os.PathLike[str]) -> su.BoundElement:
    """Import an SVG file and return an SVG object.

    :param svg_file: Path to the SVG file.
    :return: A BoundElement containing the SVG content and the svg viewBox as a
        BoundingBox.

    Near equivalent to `etree.parse(file).getroot()`, but returns a BoundElement
    instance. This will only work with SVG files that have a viewBox attribute.
    """
    with Path(svg_file).open("r", encoding="utf-8") as f:
        root = etree.parse(f).getroot()
    if len(root) == 1:
        elem = root[0]
    else:
        elem = su.new_element("g")
        elem.extend(list(root))
    bbox = get_bounding_box_from_root(root)
    return su.BoundElement(elem, bbox)
