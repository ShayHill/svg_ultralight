#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
""" Quasi-private functions for high-level string conversion

:author: Shay Hill
:created: 7/26/2020

Rounding some numbers to ensure quality svg rendering:
* Rounding floats to six digits after the decimal
* Rounding viewBox dimensions to ints
"""
from enum import Enum
from typing import TypeAlias, Union

from lxml import etree

from svg_ultralight.nsmap import NSMAP

_Element: TypeAlias = etree._Element  # type: ignore


def format_number(num: float) -> str:
    """
    Format strings at limited precision

    :param num: anything that can print as a float.
    :return: str

    I've read articles that recommend no more than four digits before and two digits
    after the decimal point to ensure good svg rendering. I'm being generous and
    giving six. Mostly to eliminate exponential notation, but I'm "rstripping" the
    strings to reduce filesize and increase readability
    """
    return f"{num:0.6f}".rstrip("0").rstrip(".")


def set_attributes(elem: _Element, **attributes: Union[str, float]) -> None:
    """
    Set name: value items as element attributes. Make every value a string.

    :param elem: element to receive element.set(keyword, str(value)) calls
    :param attributes: element attribute names and values. Knows what to do with 'text'
        keyword.V :effects: updates ``elem``

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
    dots = {"text"}
    for dot in dots & set(attributes):
        setattr(elem, dot, attributes.pop(dot))

    for k, v in attributes.items():
        if ":" in k:
            namespace, tag = k.split(":")
            k = etree.QName(NSMAP[namespace], tag)
        else:
            k = k.rstrip("_").replace("_", "-")
        try:
            val = format_number(float(v))
        except ValueError:
            val = str(v)
        elem.set(k, val)


class _TostringDefaults(Enum):
    """Default values for an svg xml_header"""

    doctype = (
        '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n'
        + '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
    )
    encoding = "UTF-8"


def svg_tostring(xml: _Element, **tostring_kwargs: str | bool) -> bytes:
    """
    Contents of svg file with optional xml declaration.

    :param xml: root node of your svg geometry
    :param tostring_kwargs: keyword arguments to etree.tostring.
        pass xml_header=True for sensible defaults, see further documentation on xml
        header in write_svg docstring.
    """
    tostring_kwargs["pretty_print"] = tostring_kwargs.get("pretty_print", True)
    if tostring_kwargs.get("xml_declaration"):
        for default in _TostringDefaults:
            value = tostring_kwargs.get(default.name, default.value)
            tostring_kwargs[default.name] = value
    svg_contents = etree.tostring(etree.ElementTree(xml), **tostring_kwargs)
    return svg_contents


def get_viewBox_str(
    x: float, y: float, width: float, height: float, pad: float = 0
) -> str:
    """
    Create a space-delimited string.

    :param x: x value in upper-left corner
    :param y: y value in upper-left corner
    :param width: width of viewBox
    :param height: height of viewBox
    :param pad: optionally increase viewBox by pad in all directions
    :return: space-delimited string "x y width height"
    """
    dims = [
        format_number(a + b)
        for a, b in zip((x, y, width, height), (-pad, -pad, pad * 2, pad * 2))
    ]
    return " ".join(dims)
