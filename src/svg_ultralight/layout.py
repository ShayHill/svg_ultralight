"""Manage inferences for pad_ and dpu_ arguments.

:author: Shay Hill
:created: 2023-02-12
"""

import math

from svg_ultralight.pad_argument import PadArg, expand_pad_arg
from svg_ultralight.unit_conversion import Measurement


def _infer_scale(
    width: float, height: float, pw_units: float, ph_units: float
) -> float:
    """Infer scale factor from print width and height.

    :param width: width of viewbox in user units
    :param height: height of viewbox in user units
    :param print_width: width of output in units, inches, centimeters, or millimeters
    :param print_height: height of output in units, inches, centimeters, or millimeters
    :return: scale to fit within both print_width and  print_height, 1 if neighther
        print_width or print_height > 0
    """
    scale = None
    if pw_units:
        scale = pw_units / width
    if ph_units:
        vscale = ph_units / height
        scale = vscale if scale is None else min(scale, vscale)
    return scale or 1


def pad_and_scale(
    width: float,
    height: float,
    pad: PadArg,
    print_width: float | str | None,
    print_height: float | str | None,
) -> tuple[tuple[float, float, float, float], dict[str, float | str]]:
    """Expand and scale the pad argument. If necessary, scale image.

    :param pad: padding to add around image, in user units or inches.
        if a sequence, it should be (top, right, bottom, left).
        if a single float or string, it will be applied to all sides.
        if two floats, top and bottom then left and right.
        if three floats, top, left and right, then bottom.
        if four floats, top, right, bottom, left.
    :param width: width of viewbox, in user units
    :param height: height of viewbox, in user units or inches
    :param print_width: width of print area, in user units, inches, cm, or mm
    :param print_height: height of print area, in user units, inches, cm, or mm
    :return: pad and scaling attributes
    :raise ValueError: if scale is not proportional to any args (unexpected)

    Ideally, we know the size of the print or display area from the beginning and
    build the geometry out at 96 dpi. If that doesn't work out or things change, we
    can scale the image to fit the print or display area. If the image is scaled, the
    padding dpu changes, but the ultimate padding dimension will not.

    For instance, If you take a 100x100 unit image then pass pad="0.25in" and
    print_width="12in", the output image will be 12.25 inches across. Whatever
    geometry was visible in the original viewbox will be much larger, but the padding
    will still be 0.25 inches. If you want to use padding and need a specific output
    image size, remember to subtract the padding width from your print_width or
    print_height.
    """
    print_w = Measurement(print_width or 0)
    print_h = Measurement(print_height or 0)

    scale = _infer_scale(width, height, print_w.value, print_h.value)
    pad = expand_pad_arg(pad, scale)

    if scale == 1:
        return pad, {}

    if math.isclose(print_w.value / width, scale):
        padded_w = Measurement(print_w.native)
        padded_w.value += (pad[1] + pad[3]) / scale
        return pad, {"width": padded_w.native}

    if math.isclose(print_h.value / height, scale):
        padded_h = Measurement(print_h.native)
        padded_h.value += (pad[0] + pad[2]) / scale
        return pad, {"height": padded_h.native}

    msg = "Unable to infer print area from viewbox and padding"
    raise ValueError(msg)
