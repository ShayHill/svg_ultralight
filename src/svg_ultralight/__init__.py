"""Bring many of the svg_ultralight functions into the svg_ultralight namespace.

:author: Shay Hill
:created: 12/22/2019.
"""

from svg_ultralight.bounding_boxes.bound_helpers import (
    new_bbox_union,
    new_bound_union,
    new_element_union,
)
from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
from svg_ultralight.bounding_boxes.type_bound_collection import BoundCollection
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.constructors.new_element import (
    deepcopy_element,
    new_element,
    new_sub_element,
    update_element,
)
from svg_ultralight.import_svg import import_svg
from svg_ultralight.inkscape import (
    write_pdf,
    write_pdf_from_svg,
    write_png,
    write_png_from_svg,
    write_root,
)
from svg_ultralight.main import new_svg_root, write_svg
from svg_ultralight.metadata import new_metadata
from svg_ultralight.nsmap import NSMAP, new_qname
from svg_ultralight.query import pad_text
from svg_ultralight.root_elements import new_svg_root_around_bounds
from svg_ultralight.string_conversion import (
    format_attr_dict,
    format_number,
    format_numbers,
    format_numbers_in_string,
)
from svg_ultralight.transformations import (
    mat_apply,
    mat_dot,
    mat_invert,
    transform_element,
)

__all__ = [
    "BoundCollection",
    "BoundElement",
    "BoundingBox",
    "NSMAP",
    "PaddedText",
    "SupportsBounds",
    "deepcopy_element",
    "format_attr_dict",
    "format_number",
    "format_numbers",
    "format_numbers_in_string",
    "import_svg",
    "mat_apply",
    "mat_dot",
    "mat_invert",
    "new_bbox_union",
    "new_bound_union",
    "new_element",
    "new_element_union",
    "new_metadata",
    "new_qname",
    "new_sub_element",
    "new_svg_root",
    "new_svg_root_around_bounds",
    "pad_text",
    "transform_element",
    "update_element",
    "write_pdf",
    "write_pdf_from_svg",
    "write_png",
    "write_png_from_svg",
    "write_root",
    "write_svg",
]
