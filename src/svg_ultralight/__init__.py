"""Import functions into the package namespace.

:author: ShayHill
:created: 2019-12-22
"""

from svg_ultralight.bounding_boxes.bound_helpers import (
    bbox_dict,
    cut_bbox,
    get_bounding_box_from_root,
    new_bbox_rect,
    new_bbox_union,
    new_bound_union,
    pad_bbox,
    parse_bound_element,
)
from svg_ultralight.bounding_boxes.padded_text_initializers import (
    align_tspans,
    join_tspans,
    pad_text,
    pad_text_inkscape,
    wrap_text,
)
from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
from svg_ultralight.bounding_boxes.type_bound_collection import BoundCollection
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_list import PaddedList
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText, new_padded_union
from svg_ultralight.constructors.new_element import (
    deepcopy_element,
    new_element,
    new_element_union,
    new_sub_element,
    update_element,
)
from svg_ultralight.font_tools.font_info import FTFontInfo
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
from svg_ultralight.query import (
    clear_svg_ultralight_cache,
    get_bounding_box,
    get_bounding_boxes,
)
from svg_ultralight.root_elements import new_svg_root_around_bounds
from svg_ultralight.string_conversion import (
    format_attr_dict,
    format_number,
    format_numbers,
)
from svg_ultralight.transformations import (
    mat_apply,
    mat_dot,
    mat_invert,
    transform_element,
)

__all__ = [
    "NSMAP",
    "BoundCollection",
    "BoundElement",
    "BoundingBox",
    "FTFontInfo",
    "PaddedList",
    "PaddedText",
    "SupportsBounds",
    "align_tspans",
    "bbox_dict",
    "clear_svg_ultralight_cache",
    "cut_bbox",
    "deepcopy_element",
    "format_attr_dict",
    "format_number",
    "format_numbers",
    "get_bounding_box",
    "get_bounding_box_from_root",
    "get_bounding_boxes",
    "join_tspans",
    "mat_apply",
    "mat_dot",
    "mat_invert",
    "new_bbox_rect",
    "new_bbox_union",
    "new_bound_union",
    "new_element",
    "new_element_union",
    "new_metadata",
    "new_padded_union",
    "new_qname",
    "new_sub_element",
    "new_svg_root",
    "new_svg_root_around_bounds",
    "pad_bbox",
    "pad_text",
    "pad_text_inkscape",
    "parse_bound_element",
    "transform_element",
    "update_element",
    "wrap_text",
    "write_pdf",
    "write_pdf_from_svg",
    "write_png",
    "write_png_from_svg",
    "write_root",
    "write_svg",
]
