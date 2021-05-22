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

from ..string_conversion import set_attributes


def new_element(tag: str, **attributes: Union[str, float]) -> etree.Element:
    # noinspection PyShadowingNames
    """
    Create an etree.Element, make every kwarg value a string.

    :param tag: element tag
    :param attributes: element attribute names and values
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
    set_attributes(elem, **attributes)
    return elem


def new_sub_element(
    parent: etree.Element, tag: str, **attributes: Union[str, float]
) -> etree.Element:
    # noinspection PyShadowingNames
    """
    Create an etree.SubElement, make every kwarg value a string.

    :param parent: parent element
    :param tag: element tag
    :param attributes: element attribute names and values
    :returns: new ``tag`` element

        >>> parent = etree.Element('g')
        >>> _ = new_sub_element('rect')
        >>> etree.tostring(parent)
        b'<g><rect/></g>'
    """
    elem = etree.SubElement(parent, tag)
    set_attributes(elem, **attributes)
    return elem


def update_element(
    elem: etree.Element, **attributes: Union[str, float]
) -> etree.Element:
    """
    Update an existing etree.Element with additional params.

    :param elem: at etree element
    :param attributes: element attribute names and values
    """
    set_attributes(elem, **attributes)
    return elem


def deepcopy_element(
    elem: etree.Element, **attributes: Union[str, float]
) -> etree.Element:
    """
    Create a deepcopy of an element. Optionally pass additional params.

    :param elem: at etree element
    :param attributes: element attribute names and values
    """
    if isinstance(elem, list):
        return [deepcopy_element(x, **attributes) for x in elem]
    elem = copy.deepcopy(elem)
    update_element(elem, **attributes)
    return elem


if __name__ == "__main__":
    import doctest

    doctest.testmod()
