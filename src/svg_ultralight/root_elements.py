"""Build root elements in various ways.

:author: Shay Hill
:created: 2023-09-23
"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from svg_ultralight.bounding_boxes import bound_helpers as bound
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.constructors.new_element import new_element_union
from svg_ultralight.main import new_svg_root

if TYPE_CHECKING:
    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

    from svg_ultralight.attrib_hints import ElemAttrib, OptionalElemAttribMapping
    from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
    from svg_ultralight.layout import PadArg
    from svg_ultralight.unit_conversion import MeasurementArg


def _viewbox_args_from_bboxes(*bboxes: BoundingBox) -> dict[str, float]:
    """Create x_, y_, width_, height_ new_svg_root arguments from bounding boxes.

    :param bbox: bounding boxes to merge
    :return: dict of new_svg_root arguments
    """
    merged = BoundingBox.union(*bboxes)
    return {
        "x_": merged.x,
        "y_": merged.y,
        "width_": merged.width,
        "height_": merged.height,
    }


def new_svg_root_around_bounds(
    *bounded: SupportsBounds | EtreeElement,
    pad_: PadArg = 0,
    print_width_: MeasurementArg | None = None,
    print_height_: MeasurementArg | None = None,
    dpu_: float | None = None,
    nsmap: dict[str | None, str] | None = None,
    attrib: OptionalElemAttribMapping = None,
    **attributes: ElemAttrib,
) -> EtreeElement:
    """Create svg root around BoundElements.

    :param bounded: BoundingBox istances, BoundElement instances, PaddedText
        instances, or any other EtreeElement instances. Anything that isn't a
        bounding box or SupportsBounds will be ignored.
    :param pad_: optionally increase viewBox by pad in all directions. Acceps a
        single value or a tuple of values applied to (cycled over) top, right,
        bottom, left. pad can be floats or dimension strings*
    :param print_width_: optionally explicitly set unpadded width in units
        (float) or a dimension string*
    :param print_height_: optionally explicitly set unpadded height in units
        (float) or a dimension string*
    :param dpu_: dots per unit. Scale the output by this factor. This is
        different from print_width_ and print_height_ in that dpu_ scales the
        *padded* output.
    :param nsmap: optionally pass a namespace map of your choosing
    :param attrib: optionally pass additional attributes as a mapping instead of as
        anonymous kwargs. This is useful for pleasing the linter when unpacking a
        dictionary into a function call.
    :param attributes: element attribute names and values
    :return: root svg element
    :raise ValueError: if no bounding boxes are found in bounded
    """
    attributes.update(attrib or {})
    bbox = bound.new_bbox_union(*bounded)
    elem: EtreeElement | None = None
    with suppress(ValueError):
        elem = new_element_union(*bounded)
    viewbox = _viewbox_args_from_bboxes(bbox)
    root = new_svg_root(
        x_=viewbox["x_"],
        y_=viewbox["y_"],
        width_=viewbox["width_"],
        height_=viewbox["height_"],
        pad_=pad_,
        print_width_=print_width_,
        print_height_=print_height_,
        dpu_=dpu_,
        nsmap=nsmap,
        attrib=attributes,
    )
    if elem is None:
        return root
    for subelem in elem:
        root.append(subelem)
    return root
