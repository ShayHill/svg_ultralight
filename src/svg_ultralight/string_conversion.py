"""Quasi-private functions for high-level string conversion.

:author: Shay Hill
:created: 7/26/2020

Rounding some numbers to ensure quality svg rendering:
* Rounding floats to six digits after the decimal
"""

from __future__ import annotations

import binascii
import itertools as it
import re
from enum import Enum
from typing import TYPE_CHECKING, Literal, cast

import svg_path_data
from lxml import etree

from svg_ultralight.nsmap import NSMAP

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

    from svg_ultralight.attrib_hints import ElemAttrib


# match a hex color string with 8 digits: #RRGGBBAA
_HEX_COLOR_8DIGIT = re.compile(r"^#([0-9a-fA-F]{8})$")


def format_number(num: float | str, resolution: int | None = 6) -> str:
    """Format a number into an svg-readable float string with resolution = 6.

    :param num: number to format (string or float)
    :param resolution: number of digits after the decimal point, defaults to 6. None
        to match behavior of `str(num)`.
    :return: string representation of the number with six digits after the decimal
        (if in fixed-point notation). Will return exponential notation when shorter.
    """
    return svg_path_data.format_number(num, resolution=resolution)


def format_numbers(
    nums: Iterable[float] | Iterable[str] | Iterable[float | str],
) -> list[str]:
    """Format multiple strings to limited precision.

    :param nums: iterable of floats
    :return: list of formatted strings
    """
    return [format_number(num) for num in nums]


def _split_opacity(
    prefix: Literal["fill", "stroke"], hex_color: str
) -> Iterator[tuple[str, str]]:
    """Get a fill and fill-opacity or stroke and stroke-opacity for an svg element.

    :param prefix: either "fill" or "stroke"
    :param color: an 8-digit hex color with leading # ("#RRGGBBAA")
    :yield: tuples of (attribute name, attribute value)
    """
    rgb, opacity = hex_color[:7], hex_color[7:]
    if opacity == "00":
        yield (prefix, "none")
    else:
        yield (prefix, rgb)
        yield f"{prefix}-opacity", format_number(int(opacity, 16) / 255)


def _fix_key_and_format_val(key: str, val: ElemAttrib) -> Iterator[tuple[str, str]]:
    """Format one key, value pair for an svg element.

    :param key: element attribute name
    :param val: element attribute value
    :return: tuple of key, value
    :raises ValueError: if key is 'd' and val is not a string

    etree.Elements will only accept string
    values. This saves having to convert input to strings.

    * convert float values to formatted strings
    * replace '_' with '-' in keywords
    * remove trailing '_' from keywords
    * will convert `namespace:tag` to a qualified name
    * will convert 8-digit hex colors to color + opacity. SVG supports 8-digit hex
      colors, but Inkscape (and likely other Linux-based SVG rasterizers) do not.

    SVG attribute names like `font-size` and `stroke-width` are not valid python
    keywords, but can be passed as `font_size` and `stroke_width`.

    Reserved Python keywords that are also valid and useful SVG attribute names (a
    popular one will be 'class') can be passed with a trailing underscore (e.g.,
    class_='body_text') to keep your code highlighter from getting confused.
    """
    if "http:" in key or "https:" in key:
        key_ = key
    elif ":" in key:
        namespace, tag = key.split(":")
        key_ = str(etree.QName(NSMAP[namespace], tag))
    else:
        key_ = key.rstrip("_").replace("_", "-")

    if val is None:
        val_ = "none"
    elif isinstance(val, (int, float)):
        val_ = format_number(val)
    elif _HEX_COLOR_8DIGIT.match(val):
        if key_ == "fill":
            yield from _split_opacity("fill", val)
            return
        if key_ == "stroke":
            yield from _split_opacity("stroke", val)
            return
        val_ = val
    else:
        val_ = val

    yield key_, val_


def format_attr_dict(**attributes: ElemAttrib) -> dict[str, str]:
    """Use svg_ultralight key / value fixer to create a dict of attributes.

    :param attributes: element attribute names and values.
    :return: dict of attributes, each key a valid svg attribute name, each value a str
    """
    items = attributes.items()
    return dict(it.chain(*(_fix_key_and_format_val(k, v) for k, v in items)))


def set_attributes(elem: EtreeElement, **attributes: ElemAttrib) -> None:
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


def get_view_box_str(
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


# ===================================================================================
#   Encode and decode arbitrary strings to / from valid CSS class names.
# ===================================================================================


# insert his before any class name that would otherwise start with a digit
_NAME_PREFIX = "__"

_DELIMITED_HEX = re.compile(r"_[0-9a-fA-F]{2,8}_")


def _encode_class_name_invalid_char_to_hex(char: str) -> str:
    """Encode any invalid single char to a hex representation prefixed with '_x'.

    :param char: The character to encode.
    :return: A string in the format '_x' followed by the hex value of the character.

    Return valid css-class-name characters unchanged. Encode others. Exception: This
    function encodes `_`, which *are* valid CSS class characters, in order to reserve
    underscores for `_` hex delimiters and `__` -name prefixes.
    """
    if re.match(r"[a-zA-Z0-9-]", char):
        return char
    hex_ = binascii.hexlify(char.encode("utf-8")).decode("ascii")
    return f"_{hex_}_"


def encode_to_css_class_name(text: str) -> str:
    """Convert text to a valid CSS class name in a reversible way.

    :param text: The text to convert.
    :return: A valid CSS class name derived from the text. The intended use is to pass
        a font filename, so the filename can be decoded from the contents of an SVG
        file and each css class created from a font file will, if the style is not
        altered, have a unique class name.

    Non-ascii characters like `é` will be encoded as hex, even if they are, by
    documentation, valid CSS class characters. The class name will be ascii only.
    """
    css_class = "".join(_encode_class_name_invalid_char_to_hex(c) for c in text)
    # add a prefix if the name starts with a digit or is empty
    if not css_class or not re.match(r"^[a-zA-Z_]", css_class):
        css_class = _NAME_PREFIX + css_class
    return css_class


def decode_from_css_class_name(css_class: str) -> str:
    """Reverse the conversion from `filename_to_css_class`.

    :param css_class: The CSS class name to convert back to text. This will not
        be meaningful if the class name was not created by encode_css_class_name. If
        you use another string, there is a potential for a hex decoding error.
    :return: The original filename passed to `filename_to_css_class`.
    """
    css_class = css_class.removeprefix(_NAME_PREFIX)

    result = ""
    while css_class:
        if match := _DELIMITED_HEX.match(css_class):
            hex_str = match.group(0)[1:-1]
            result += binascii.unhexlify(hex_str).decode("utf-8")
            css_class = css_class[len(match.group(0)) :]
        else:
            result += css_class[0]
            css_class = css_class[1:]
    return result
