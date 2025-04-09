"""Quasi-private functions for high-level string conversion.

:author: Shay Hill
:created: 7/26/2020

Rounding some numbers to ensure quality svg rendering:
* Rounding floats to six digits after the decimal
* Rounding viewBox dimensions to ints
"""

from __future__ import annotations

import re
from contextlib import suppress
from enum import Enum
from typing import TYPE_CHECKING, cast

from lxml import etree

from svg_ultralight.nsmap import NSMAP

if TYPE_CHECKING:
    from collections.abc import Iterable

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )


def format_number(num: float | str) -> str:
    """Format strings at limited precision.

    :param num: anything that can print as a float.
    :return: str

    I've read articles that recommend no more than four digits before and two digits
    after the decimal point to ensure good svg rendering. I'm being generous and
    giving six. Mostly to eliminate exponential notation, but I'm "rstripping" the
    strings to reduce filesize and increase readability

    * reduce fp precision to 6 digits
    * remove trailing zeros
    * remove trailing decimal point
    * convert "-0" to "0"
    """
    as_str = f"{float(num):0.6f}".rstrip("0").rstrip(".")
    if as_str == "-0":
        as_str = "0"
    return as_str


def format_numbers(
    nums: Iterable[float] | Iterable[str] | Iterable[float | str],
) -> list[str]:
    """Format multiple strings to limited precision.

    :param nums: iterable of floats
    :return: list of formatted strings
    """
    return [format_number(num) for num in nums]


def _is_float_or_float_str(data: float | str) -> bool:
    """Check if a string is a float.

    :param data: string to check
    :return: bool
    """
    try:
        _ = float(data)
    except ValueError:
        return False
    else:
        return True


def format_numbers_in_string(data: float | str) -> str:
    """Find and format floats in a string.

    :param data: string with floats or a float value
    :return: string with floats formatted to limited precision

    Works as a more robust version of format_number. Will correctly handle input
    floats in exponential notation. This should work for any parameter value in an
    svg except 'text', 'id' and for any other value except hex color codes. The
    function will fail with input strings like 'ice3.14bucket', because 'e3.14' will
    be identified as a float. SVG param values will not have such strings, but the
    'text' attribute could. This function will not handle that case. Do not attempt
    to reformat 'text' attribute values.
    """
    with suppress(ValueError):
        # try as a regular number to strip spaces from simple float strings
        return format_number(data)
    if str(data).startswith("#"):
        return str(data)
    words = re.split(r"([^\d.eE-]+)", str(data))
    words = [format_number(w) if _is_float_or_float_str(w) else w for w in words]
    return "".join(words)


def _fix_key_and_format_val(key: str, val: str | float) -> tuple[str, str]:
    """Format one key, value pair for an svg element.

    :param key: element attribute name
    :param val: element attribute value
    :return: tuple of key, value
    :raises ValueError: if key is 'd' and val is not a string

    etree.Elements will only accept string
    values. This saves having to convert input to strings.

    * convert float values to formatted strings
    * format datastring values when keyword is 'd'
    * replace '_' with '-' in keywords
    * remove trailing '_' from keywords
    * will convert `namespace:tag` to a qualified name

    SVG attribute names like `font-size` and `stroke-width` are not valid python
    keywords, but can be passed as `font-size` and `stroke-width`.

    Reserved Python keywords that are also valid and useful SVG attribute names (a
    popular one will be 'class') can be passed with a trailing underscore (e.g.,
    class_='body_text').
    """
    if "http:" in key or "https:" in key:
        key_ = key
    elif ":" in key:
        namespace, tag = key.split(":")
        key_ = str(etree.QName(NSMAP[namespace], tag))
    else:
        key_ = key.rstrip("_").replace("_", "-")

    if key_ in {"id", "text"}:
        return key_, str(val)

    return key_, format_numbers_in_string(val)


def format_attr_dict(**attributes: str | float) -> dict[str, str]:
    """Use svg_ultralight key / value fixer to create a dict of attributes.

    :param attributes: element attribute names and values.
    :return: dict of attributes, each key a valid svg attribute name, each value a str
    """
    return dict(_fix_key_and_format_val(key, val) for key, val in attributes.items())


def set_attributes(elem: EtreeElement, **attributes: str | float) -> None:
    """Set name: value items as element attributes. Make every value a string.

    :param elem: element to receive element.set(keyword, str(value)) calls
    :param attributes: element attribute names and values. Knows what to do with 'text'
        keyword.V :effects: updates ``elem``
    """
    attr_dict = format_attr_dict(**attributes)

    dots = {"text"}
    for dot in dots & set(attr_dict):
        setattr(elem, dot, attr_dict.pop(dot))

    for key, val in attr_dict.items():
        elem.set(key, val)


class _TostringDefaults(Enum):
    """Default values for an svg xml_header."""

    DOCTYPE = (
        '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n'
        + '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
    )
    ENCODING = "UTF-8"


def svg_tostring(xml: EtreeElement, **tostring_kwargs: str | bool | None) -> bytes:
    """Contents of svg file with optional xml declaration.

    :param xml: root node of your svg geometry
    :param tostring_kwargs: keyword arguments to etree.tostring.
        pass xml_header=True for sensible defaults, see further documentation on xml
        header in write_svg docstring.
    :return: bytestring of svg file contents
    """
    tostring_kwargs["pretty_print"] = tostring_kwargs.get("pretty_print", True)
    if tostring_kwargs.get("xml_declaration"):
        for default in _TostringDefaults:
            arg_name = default.name.lower()
            value = tostring_kwargs.get(arg_name, default.value)
            tostring_kwargs[arg_name] = value
    as_bytes = etree.tostring(etree.ElementTree(xml), **tostring_kwargs)  # type: ignore
    return cast("bytes", as_bytes)


def get_viewBox_str(
    x: float,
    y: float,
    width: float,
    height: float,
    pad: float | tuple[float, float, float, float] = 0,
) -> str:
    """Create a space-delimited string.

    :param x: x value in upper-left corner
    :param y: y value in upper-left corner
    :param width: width of viewBox
    :param height: height of viewBox
    :param pad: optionally increase viewBox by pad in all directions
    :return: space-delimited string "x y width height"
    """
    if not isinstance(pad, tuple):
        pad = (pad, pad, pad, pad)
    pad_t, pad_r, pad_b, pad_l = pad
    pad_h = pad_l + pad_r
    pad_v = pad_t + pad_b
    dims = [
        format_number(x) for x in (x - pad_l, y - pad_t, width + pad_h, height + pad_v)
    ]
    return " ".join(dims)
