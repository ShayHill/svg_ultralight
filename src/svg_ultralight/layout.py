"""Manage inferences for pad_ and dpu_ arguments.

:author: Shay Hill
:created: 2023-02-12
"""

from __future__ import annotations

from typing import TypeAlias, cast

from svg_ultralight.string_conversion import format_number
from svg_ultralight.unit_conversion import (
    Measurement,
    MeasurementArg,
    is_measurement_arg,
)

_MeasurementArgs: TypeAlias = (
    tuple[MeasurementArg]
    | tuple[MeasurementArg, MeasurementArg]
    | tuple[MeasurementArg, MeasurementArg, MeasurementArg]
    | tuple[MeasurementArg, MeasurementArg, MeasurementArg, MeasurementArg]
)

PadArg: TypeAlias = MeasurementArg | _MeasurementArgs


def _expand_pad_args(pad: _MeasurementArgs) -> tuple[float, float, float, float]:
    """Transform a tuple of MeasurementArgs to a 4-tuple of user units."""
    as_ms = (m if isinstance(m, Measurement) else Measurement(m) for m in pad)
    as_units = [m.value for m in as_ms]
    if len(as_units) == 1:
        as_units = as_units * 4
    elif len(as_units) == 2:
        as_units = as_units * 2
    elif len(as_units) == 3:
        as_units = [*as_units, as_units[1]]
    return as_units[0], as_units[1], as_units[2], as_units[3]


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
    if is_measurement_arg(pad):
        pads = cast("_MeasurementArgs", (pad,))
        return _expand_pad_args(pads)
    pads = cast("_MeasurementArgs", pad)
    return _expand_pad_args(pads)


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
    pad: PadArg = 0,
    print_width: MeasurementArg | None = None,
    print_height: MeasurementArg | None = None,
    dpu: float = 1,
) -> tuple[tuple[float, float, float, float], dict[str, float | str]]:
    """Expand and scale the pad argument. If necessary, scale image.

    :param viewbox: viewbox to pad (x, y, width height)
    :param pad: padding to add around image, in user units or inches. If a
        sequence, it should be (top, right, bottom, left). if a single float or
        string, it will be applied to all sides. If two floats, top and bottom
        then left and right. If three floats, top, left and right, then bottom.
        If four floats, top, right, bottom, left.
    :param print_width: width of print area, in user units (float), a string
        with a unit specifier (e.g., "452mm"), or just a unit specifier (e.g.,
        "pt")
    :param print_height: height of print area, in user units (float), a string
        with a unit specifier (e.g., "452mm"), or just a unit specifier (e.g.,
        "pt")
    :param dpu: scale the print units. This is useful when you want to print the
        same image at different sizes.
    :return: padded viewbox 4-tuple and scaling attributes

    SVGs are built in "user units". An optional width and height (not the
    viewbox with and height, these are separate arguments) define the size of
    those user units.

    * If the width and height are not specified, the user units are 1 pixel
      (1/96th of an inch).

    If the width and height *are* specified, the user units become whatever they
    need to be to fit that requirement. For instance, if the viewbox width is 96
    and the width argument is "1in", then the user units are *still* pixels,
    because there are 96 pixels in an inch. If the viewbox width is 2 and the
    width argument is "1in", then the user units are 1/2 of an inch (i.e., 48
    pixels) each, because there are 2 user units in an inch. If the viewbox
    width is 3 and the width argument is "1yd", the each user unit is 1 foot.

    To pad around the viewbox, we need to first figure out what the user units
    are then scale the padding so it will print (or display) correctly. For
    instance, if

    * the viewbox width is 3;
    * the width argument is "1yd"; and
    * the pad argument is "1in"

    the printed result will be 38" wide. That's 1yd for the width plus 1 inch of
    padding on each side. The viewbox will have 1/12 of a unit (3 user units
    over 1 yard = 1 foot per user unit) added on each side.

    Ideally, we know the size of the print or display area from the beginning
    and build the geometry out at whatever size we want, so no scaling is
    necessarily required. Even that won't always work, because some software
    doesn't like "user units" and insists on 'pt' or 'in'. If everything is
    already in 'pt' or 'in' and you want to keep it that way, just call the
    function with print_width="pt" or print_height="in". The function will add
    the unit designators without changing the scale.

    Print aspect ratio is ignored. Viewbox aspect ratio is preserved. For
    instance, if you created two images

    * x_=0, y_=0, width_=1, height_=2, pad_="0.25in", print_width_="6in"

    * x_=0, y_=0, width_=1, height_=2, pad_="0.25in", print_width_="12in"

    ... (note that the images only vary in print_width_), the first image would be
    rendered at 6.5x12.5 inches and the second at 12.5x24.5 inches. The visible
    content in the viewbox would be exactly twice as wide in the larger image, but
    the padding would remain 0.25 in both images. Despite setting `print_width_` to
    exactly 6 or 12 inches, you would not get an image exactly 6 or 12 inches wide.
    Despite a viewbox aspect ratio of 1:2, you would not get an output image of
    exactly 1:2. If you want to use padding and need a specific output image size or
    aspect ratio, remember to subtract the padding width from your print_width or
    print_height.

    Scaling attributes are returned as a dictonary that can be "exploded" into
    the element constructor, e.g., {"width": "12.5in", "height": "12.5in"}.

    * If neither a print_width nor print_height is specified, no scaling
      attributes will be returned.

    * If either is specified, both a width and height will be returned (even if
      one argument is None). These will always match the viewbox aspect ratio,
      so there is no additional information supplied by giving both, but I've
      had unexpected behavior from pandoc when one was missing.

    * If only a unit is given, (e.g., Unit.PT), the user units (viewbox width and
      height) will be interpreted as that unit. This is important for InDesign, which
      may not display an image at all if the width and height are not explicitly
      "pt".

    * Print ratios are discarded. The viwebox ratio is preserved. For instance,
      if the viewbox is (0, 0, 16, 9), giving a 16:9 aspect ratio and the
      print_width and print_height are both 100, giving a 1:1 aspect ratio, the
      output scaling attributes will be {"width": "100", "height", "56.25"},
      preserving viewbox aspect ratio with a "best fit" scaling (i.e, the image
      is as large as it can be without exceeding the specified print area).

    You can pass something impossible like a viewbox width of 1 and a print box
    of 0. The function will give up, set scaling to 1, and pad the viewbox. This
    does not try to guard against bad values sent to lxml.

    All of the above is important when you want your padding in real-world units
    (e.g., when you need to guarantee a certain amount of padding above and
    below an image in a book layout). However, it does add some complexity,
    because aspect ratio is not maintained when print_width increases. Worse, if
    there is some geomtry like a background pattern in your padding, then more
    or less of that pattern will be visible depending on the print_width.

    That's not hard to work around, just change the padding every time you
    change the width. Or, to make it even simpler, use the dpu argument. The dpu
    argument will scale the width and the padding together. So, you can produce
    a 16" x 9" image with viwebox(0, 0, 14, 7), pad_="1in", print_width_="14in"
    ... then scale the printout with dpu_=2 to get a 32" x 18" image with the
    same viewbox. This means the padding will be 2" on all sides, but the image
    will be identical (just twice as wide and twice as high) as the 16" x 9" image.
    """
    pads = expand_pad_arg(pad)

    # no print information given, pad and return viewbox
    if print_width is None and print_height is None:
        padded = pad_viewbox(viewbox, pads)
        dims: dict[str, float | str] = {}
        if dpu != 1:
            dims["width"] = format_number(padded[2] * dpu)
            dims["height"] = format_number(padded[3] * dpu)
        return padded, dims

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
        "width": (print_w * dpu).get_svg(print_w.native_unit),
        "height": (print_h * dpu).get_svg(print_h.native_unit),
    }
