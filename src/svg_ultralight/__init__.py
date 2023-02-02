"""Bring many of the svg_ultralight functions into the svg_ultralight namespace.

:author: Shay Hill
:created: 12/22/2019.
"""
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.constructors.new_element import (
    deepcopy_element,
    new_element,
    new_sub_element,
    update_element,
)
from svg_ultralight.main import (
    new_svg_root,
    write_pdf,
    write_pdf_from_svg,
    write_png,
    write_png_from_svg,
    write_svg,
)
from svg_ultralight.nsmap import NSMAP

__all__ = [
    "BoundElement",
    "BoundingBox",
    "PaddedText",
    "new_element",
    "new_sub_element",
    "update_element",
    "deepcopy_element",
    "new_svg_root",
    "write_svg",
    "write_png_from_svg",
    "write_png",
    "write_pdf_from_svg",
    "write_pdf",
    "NSMAP",
]
