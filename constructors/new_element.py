#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
"""SVG Element constructors. Create an svg element from a dictionary.

:author: Shay Hill
:created: 1/31/2020

This is principally to allow passing values, rather than strings, as svg element
parameters.

Will translate ``stroke_width=10`` to ``stroke-width="10"``
"""

import copy
from typing import Union

from lxml import etree  # type: ignore


def _set_params(elem: etree.Element, **params: Union[str, float]) -> None:
    """
    Set name: value items as element attributes. Make every value a string.

    :param elem: element to receive element.set(keyword, str(value)) calls
    :param params: element attribute names and values. Knows what to do with 'text'
        keyword.V :effects: updates ``elem``

    This is just to save a lot of typing. etree.Elements will only accept string
    values. Takes each in params.values(), and passes it to etree.Element as a
    string. Will also replace `_` with `-` to translate valid Python variable names
    for xml parameter names.

    That's almost it. The function will also handle the 'text' keyword, placing the
    value between element tags.
    """
    if "text" in params:
        elem.text = params.pop("text")
    for k, v in params.items():
        elem.set(k.rstrip("_").replace("_", "-"), str(v))


def new_element(tag: str, **params: Union[str, float]) -> etree.Element:
    """
    Create an etree.Element, make every kwarg value a string.

    :param tag: element tag
    :param params: element attribute names and values
    :returns: new ``tag`` element

        >>> elem = new_element('line', x1=0, y1=0, x2=5, y2=5)
        >>> etree.tostring(elem)
        b'<line x1="0" y1="0" x2="5" y2="5"/>'

    Strips trailing underscores

        >>> elem = new_element('line', in_="SourceAlpha")
        >>> etree.tostring(elem)
        b'<line in="SourceAlpha"/>'

    Translates other underscores to hyphens

        >>> elem = new_element('line', stroke_width=1)
        >>> etree.tostring(elem)
        b'<line stroke-width="1"/>'

    Special handling for a 'text' argument. Places value between element tags.

        >>> elem = new_element('text', text='please star my project')
        >>> etree.tostring(elem)
        b'<text>please star my project</text>'

    """
    elem = etree.Element(tag)
    _set_params(elem, **params)
    return elem


def new_sub_element(
    parent: etree.Element, tag: str, **params: Union[str, float]
) -> etree.Element:
    """
    Create an etree.SubElement, make every kwarg value a string.

    :param parent: parent element
    :param tag: element tag
    :param params: element attribute names and values
    :returns: new ``tag`` element

        >>> parent = etree.Element('g')
        >>> _ = new_sub_element('rect')
        >>> etree.tostring(parent)
        b'<g><rect/></g>'
    """
    elem = etree.SubElement(parent, tag)
    _set_params(elem, **params)
    return elem


def update_element(elem: etree.Element, **params: Union[str, float]) -> etree.Element:
    """
    Update an existing etree.Element with additional params.

    :param elem: at etree element
    :param params: element attribute names and values
    """
    _set_params(elem, **params)
    return elem


def deepcopy_element(elem: etree.Element, **params: Union[str, float]) -> etree.Element:
    """
    Create a deepcopy of an element. Optionally pass additional params.

    :param elem: at etree element
    :param params: element attribute names and values
    """
    if isinstance(elem, list):
        return [deepcopy_element(x, **params) for x in elem]
    elem = copy.deepcopy(elem)
    update_element(elem, **params)
    return elem


if __name__ == "__main__":
    import doctest

    doctest.testmod()
