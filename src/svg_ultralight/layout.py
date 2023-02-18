"""Manage inferences for pad_ and dpu_ arguments.

:author: Shay Hill
:created: 2023-02-12
"""
from collections.abc import Sequence

from svg_ultralight.unit_conversion import Measurement, MeasurementArg

PadArg = float | str | Measurement | Sequence[float | str | Measurement]


def expand_pad_arg(pad: PadArg) -> tuple[float, float, float, float]:
    """Transform a single value or tuple of values to a 4-tuple of user units.

    :param pad: padding value(s)
    :return: 4-tuple of padding values in (scaled) user units

    >>> expand_pad_arg(1)
    (1.0, 1.0, 1.0, 1.0)

    >>> expand_pad_arg((1, 2))
    (1.0, 2.0, 1.0, 2.0)

    >>> expand_pad_arg("1in")
    (96.0, 96.0, 96.0, 96.0)

    >>> expand_pad_arg(("1in", "2in"))
    (96.0, 192.0, 96.0, 192.0)

    >>> expand_pad_arg(Measurement("1in"))
    (96.0, 96.0, 96.0, 96.0)

    >>> expand_pad_arg((Measurement("1in"), Measurement("2in")))
    (96.0, 192.0, 96.0, 192.0)
    """
    if isinstance(pad, (int, float, str, Measurement)):
        return expand_pad_arg([pad])
    as_ms = [m if isinstance(m, Measurement) else Measurement(m) for m in pad]
    as_units = [m.value for m in as_ms]
    as_units = [as_units[i % len(as_units)] for i in range(4)]
    return as_units[0], as_units[1], as_units[2], as_units[3]


def pad_viewbox(
    viewbox: tuple[float, float, float, float], pads: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    """Expand viewbox by padding.

    :param viewbox: viewbox to pad (x, y, width height)
    :param pads: padding (top, right, bottom, left)
    :return: padded viewbox
    """
    x, y, width, height = viewbox
    top, right, bottom, left = pads
    return x - left, y - top, width + left + right, height + top + bottom


def _scale_pads(
    pads: tuple[float, float, float, float], scale: float
) -> tuple[float, float, float, float]:
    """Scale padding by a factor.

    :param pads: padding to scale (top, right, bottom, left)
    :param scale: factor to scale by
    :return: scaled padding
    """
    top, right, bottom, left = pads
    return top * scale, right * scale, bottom * scale, left * scale


def _infer_scale(
    print_h: Measurement, print_w: Measurement, viewbox_h: float, viewbox_w: float
) -> float:
    """Determine size of viewbox units.

    :param print_h: height of print area
    :param print_w: width of print area
    :param viewbox_h: height of viewbox
    :param viewbox_w: width of viewbox
    :return: scale factor to apply to viewbox to match print area
    :raises ValueError: if no valid scale can be determined

    If one of width or height cannot be used, will defer to the other.

    Will ignore ONE, but not both of these conditions:
    * print_w > 0 / viewbox_w == 0
    * print_h > 0 / viewbox_h == 0

    Any potential scale would be infinite, so this raises a ValueError

    Will ignore ONE, but not both of these conditions:
    * print_w == 0 / viewbox_w > 0
    * print_h == 0 / viewbox_h > 0

    The print area is invalid, but there is special handling for this. Interpret
    viewbox units as print_w.native_unit and determe print area from viewbox area 1
    to 1.

        >>> _infer_scale(Measurement("in"), Measurement("in"), 1, 2)
        96

    Will additionally raise a ValueError for any negative measurement.

    Scaling is safe for zero values. If both are zero, the scaling will be 1.
    Padding might add a non-zero value to width or height later, producing a valid
    viewbox, but that isn't guaranteed here.
    """
    if any(x < 0 for x in (print_h.value, print_w.value, viewbox_h, viewbox_w)):
        msg = "Negative values are not allowed"
        raise ValueError(msg)

    candidate_scales: set[float] = set()
    if print_w.value and viewbox_w:
        candidate_scales.add(print_w.value / viewbox_w)
    if print_h.value and viewbox_h:
        candidate_scales.add(print_h.value / viewbox_h)
    if candidate_scales:
        # size of picture is determined by print area
        return min(candidate_scales)
    if any([print_w.value, print_h.value]):
        msg = "All potential scales would be infinite."
        raise ValueError(msg)
    # a print unit was given, but not a print size. Size of picture is determined
    # by interpreting viewbox dimensions as print_width or print_height units
    return print_w.native_unit.value[1]


def pad_and_scale(
    viewbox: tuple[float, float, float, float],
    pad: PadArg,
    print_width: MeasurementArg | None = None,
    print_height: MeasurementArg | None = None,
) -> tuple[tuple[float, float, float, float], dict[str, float | str]]:
    """Expand and scale the pad argument. If necessary, scale image.

    :param viewbox: viewbox to pad (x, y, width height)
    :param pad: padding to add around image, in user units or inches.
        if a sequence, it should be (top, right, bottom, left).
        if a single float or string, it will be applied to all sides.
        if two floats, top and bottom then left and right.
        if three floats, top, left and right, then bottom.
        if four floats, top, right, bottom, left.
    :param print_width: width of print area, in user units (float), a string with a
        unit specifier (e.g., "452mm"), or just a unit specifier (e.g., "pt")
    :param print_height: height of print area, in user units (float), a string with a
        unit specifier (e.g., "452mm"), or just a unit specifier (e.g., "pt")
    :return: padded viewbox 4-tuple and scaling attributes

    SVGs are built in "user units". An optional width and height (not the viewbox
    with and height, these are separate arguments) define the size of those user
    units.

    * If the width and height are not specified, the user units are 1 pixel (1/96th
    of an inch).

    * If the width and height are specified, the user units become whatever they need
    to be to fit that requirement. For instance, if the viewbox width is 96 and the
    width argument is "1in", then the user units are *still* pixels, because there
    are 96 pixels in an inch. If the viewbox with is 2 and the width argument is
    "1in", then the user units are 1/2 of an inch (i.e., 48 pixels) each, because
    there are 2 user units in an inch. If the viewbox width is 3 and the width
    argument is "1yd", the each user unit is 1 foot.

    To pad around the viewbox, we need to first figure out what the user units are
    then scale the padding to it will print (or display) correctly.

    Ideally, we know the size of the print or display area from the beginning and
    build the geometry out at whatever size we want, so no scaling is necessarily
    required. Even that won't always work, because some software doesn't like "user
    units" and insists on 'pt' or 'in'. If everything is already in 'pt' or 'in' and
    you want to keep it that way, just call the function with print_width="pt" or
    print_height="in". The function will add the unit designators without changing
    the scale.

    Print aspect ratio is ignored. Viewbox aspect ratio is preserved. For instance,
    If you take a 100x100 unit image then pass pad="0.25in" and print_width="12in",
    the output image will be 12.25 inches across. Whatever geometry was visible in
    the original viewbox will be much larger, but the padding will still be 0.25
    inches. If you want to use padding and need a specific output image size,
    remember to subtract the padding width from your print_width or print_height.

    Scaling attributes are returns as a dictonary that can be "exploded" into the
    element constructor, e.g., {"width": "12.25in", "height": "12.25in"}.

    * If neighther a print_width nor print_height is specified, no scaling attributes
    will be returned.

    * If either is specified, both a width and height will be returned (even if one
    argument is None). These will always match the viewbox aspect ratio, so there is
    no additional information supplied by giving both, but I've had unexpected
    behavior from pandoc when one was missing.

    * If only a unit is given, (e.g., "pt"), the user units (viewbox width and
    height) will be interpreted as that unit. This is important for InDesign, which
    may not display in image at all if the width and height are not explicitly "pt".

    * Print ratios are discarded. The viwebox ratio is preserved. For instance, if
    the viewbox is (0, 0, 16, 9), giving a 16:9 aspect ratio and the print_width and
    print_height are both 100, giving a 1:1 aspect ratio, the output scaling
    attributes will be {"width": "100", "height", "56.25"}, preserving viewbox aspect
    ratio with a "best fit" scaling (i.e, the image is as large as it can be without
    exceeding the specified print area).

    You can pass something impossible like a viewbox width of 1 and a print box of 0.
    The function will give up, set scaling to 1, and pad the viewbox. This does not
    try to guard against bad values sent to lxml.
    """
    pads = expand_pad_arg(pad)

    # no print information given, pad and return viewbox
    if print_width is None and print_height is None:
        return pad_viewbox(viewbox, pads), {}

    _, _, viewbox_w, viewbox_h = viewbox
    print_w = Measurement(print_width or 0)
    print_h = Measurement(print_height or 0)

    # match unspecified (None) width or height units.
    if print_width is None:
        print_w.native_unit = print_h.native_unit
    elif print_height is None:
        print_h.native_unit = print_w.native_unit

    scale = _infer_scale(print_h, print_w, viewbox_h, viewbox_w)

    print_w.value = viewbox_w * scale
    print_h.value = viewbox_h * scale

    # add padding and increase print area
    print_w.value += pads[1] + pads[3]
    print_h.value += pads[0] + pads[2]

    # scale pads to viewbox to match input size when later scaled to print area
    padded_viewbox = pad_viewbox(viewbox, _scale_pads(pads, 1 / scale))
    return padded_viewbox, {
        "width": print_w.get_svg(print_w.native_unit),
        "height": print_h.get_svg(print_h.native_unit),
    }
