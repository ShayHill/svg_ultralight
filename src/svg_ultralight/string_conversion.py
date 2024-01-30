"""Quasi-private functions for high-level string conversion.

:author: Shay Hill
:created: 7/26/2020

Rounding some numbers to ensure quality svg rendering:
* Rounding floats to six digits after the decimal
* Rounding viewBox dimensions to ints
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, cast

from lxml import etree

from svg_ultralight.nsmap import NSMAP

if TYPE_CHECKING:
    from collections.abc import Iterable

    from lxml.etree import _Element as EtreeElement  # type: ignore


def format_number(num: float) -> str:
    """Format strings at limited precision.

    :param num: anything that can print as a float.
    :return: str

    I've read articles that recommend no more than four digits before and two digits
    after the decimal point to ensure good svg rendering. I'm being generous and
    giving six. Mostly to eliminate exponential notation, but I'm "rstripping" the
    strings to reduce filesize and increase readability
    """
    as_str = f"{num:0.6f}".rstrip("0").rstrip(".")
    if as_str == "-0":
        as_str = "0"
    return as_str


def format_numbers(nums: Iterable[float]) -> list[str]:
    """Format multiple strings to limited precision.

    :param nums: iterable of floats
    :return: list of formatted strings
    """
    return [format_number(num) for num in nums]


def _fix_key(key: str, val: str | float) -> tuple[str, str]:
    """Format one key, value pair for an svg element.

    :param key: element attribute name
    :param val: element attribute value
    :return: tuple of key, value

    This is just to save a lot of typing. etree.Elements will only accept string
    values. Takes each in params.values(), and passes it to etree.Element as a
    string. Will also replace `_` with `-` to translate valid Python variable names
    for xml parameter names.

    Invalid names (a popular one will be 'class') can be passed with a trailing
    underscore (e.g., class_='body_text').

    That's almost all. The function will also handle the 'text' keyword, placing the
    value between element tags.

    Format floats through f'{value:f} to avoid exponential representation
    (e.g., 10e-06) which svg parsers won't understand.
    """
    if ":" in key:
        namespace, tag = key.split(":")
        key_ = str(etree.QName(NSMAP[namespace], tag))
    else:
        key_ = key.rstrip("_").replace("_", "-")
    try:
        val_ = format_number(float(val))
    except ValueError:
        val_ = str(val)
    return key_, val_


def format_attr_dict(**attributes: str | float) -> dict[str, str]:
    """Use svg_ultralight key / value fixer to create a dict of attributes.

    :param attributes: element attribute names and values. Knows what to do with 'text'
    :return: dict of attributes, each key a valid svg attribute name, each value a str
    """
    return dict(_fix_key(key, val) for key, val in attributes.items())


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
    return cast(bytes, as_bytes)


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
