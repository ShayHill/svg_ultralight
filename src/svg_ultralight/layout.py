"""Manage inferences for pad_ and dpu_ arguments.

:author: Shay Hill
:created: 2023-02-12
"""


from svg_ultralight.pad_argument import PadArg, expand_pad_arg
from svg_ultralight.unit_conversion import Measurement


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


def _pad_viewbox(
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


def pad_and_scale(
    viewbox: tuple[float, float, float, float],
    pad: PadArg,
    print_width: float | str | None = None,
    print_height: float | str | None = None,
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
        return _pad_viewbox(viewbox, pads), {}

    _, _, viewbox_w, viewbox_h = viewbox
    print_w = Measurement(print_width or 0)
    print_h = Measurement(print_height or 0)

    # match unspecified (None) width or height units.
    if print_width is None:
        print_w.native_unit = print_h.native_unit
    elif print_height is None:
        print_h.native_unit = print_w.native_unit

    # If only a unit is given, take width and height as the value.
    print_w.value = print_w.value or viewbox_w
    print_h.value = print_h.value or viewbox_h

    # scaling is safe for 0 width and/or 0 height viewboxes. Padding may provide a
    # non-zero width and height later.
    has_dimensions = (viewbox_w > 0, viewbox_h > 0)
    if has_dimensions == (True, False):
        scale = print_w.value / viewbox_w
    elif has_dimensions == (False, True):
        scale = print_h.value / viewbox_h
    elif has_dimensions == (True, True):
        scale = min(print_w.value / viewbox_w, print_h.value / viewbox_h)
    else:
        scale = 1

    print_w.value = viewbox_w * scale
    print_h.value = viewbox_h * scale

    # add padding and increase print area
    print_w.value += pads[1] + pads[3]
    print_h.value += pads[0] + pads[2]

    # scale pads to viewbox to match input size when later scaled to print area
    padded_viewbox = _pad_viewbox(viewbox, _scale_pads(pads, scale))
    return padded_viewbox, {"width": print_w.native, "height": print_h.native}
