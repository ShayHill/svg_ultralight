"""Build root elements in various ways.

:author: Shay Hill
:created: 2023-09-23
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.main import new_svg_root

if TYPE_CHECKING:
    from lxml.etree import _Element as EtreeElement  # type: ignore

    from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
    from svg_ultralight.layout import PadArg


def _viewbox_args_from_bboxes(*bboxes: BoundingBox) -> dict[str, float]:
    """Create x_, y_, width_, height_ new_svg_root arguments from bounding boxes.

    :param bbox: bounding boxes to merge
    :return: dict of new_svg_root arguments
    """
    merged = BoundingBox.merged(*bboxes)
    return {
        "x_": merged.x,
        "y_": merged.y,
        "width_": merged.width,
        "height_": merged.height,
    }


def new_svg_root_around_bounds(
    *bounded: SupportsBounds | EtreeElement,
    pad_: PadArg = 0,
    print_width_: float | str | None = None,
    print_height_: float | str | None = None,
    dpu_: float = 1,
    nsmap: dict[str | None, str] | None = None,
    **attributes: float | str,
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
    :param attributes: element attribute names and values
    :return: root svg element
    :raise ValueError: if no bounding boxes are found in bounded
    """
    bboxes = [x for x in bounded if isinstance(x, BoundingBox)]
    bboxes += [x.bbox for x in bounded if isinstance(x, BoundElement)]
    bboxes += [x.padded_bbox for x in bounded if isinstance(x, PaddedText)]

    if not bboxes:
        msg = "no bounding boxes found"
        raise ValueError(msg)

    viewbox = _viewbox_args_from_bboxes(*bboxes)
    return new_svg_root(
        x_=viewbox["x_"],
        y_=viewbox["y_"],
        width_=viewbox["width_"],
        height_=viewbox["height_"],
        pad_=pad_,
        print_width_=print_width_,
        print_height_=print_height_,
        dpu_=dpu_,
        nsmap=nsmap,
        **attributes,
    )
