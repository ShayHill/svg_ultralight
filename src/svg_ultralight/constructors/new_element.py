"""SVG Element constructors. Create an svg element from a dictionary.

:author: Shay Hill
:created: 1/31/2020

This is principally to allow passing values, rather than strings, as svg element
parameters.

Will translate ``stroke_width=10`` to ``stroke-width="10"``
"""

from __future__ import annotations

import copy
import warnings
from typing import TYPE_CHECKING

from lxml import etree

from svg_ultralight.string_conversion import set_attributes

if TYPE_CHECKING:
    from lxml.etree import _Element as EtreeElement  # type: ignore


def new_element(tag: str, **attributes: str | float) -> EtreeElement:
    """Create an etree.Element, make every kwarg value a string.

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
    parent: EtreeElement, tag: str, **attributes: str | float
) -> EtreeElement:
    """Create an etree.SubElement, make every kwarg value a string.

    :param parent: parent element
    :param tag: element tag
    :param attributes: element attribute names and values
    :returns: new ``tag`` element

        >>> parent = etree.Element('g')
        >>> _ = new_sub_element(parent, 'rect')
        >>> etree.tostring(parent)
        b'<g><rect/></g>'
    """
    elem = etree.SubElement(parent, tag)
    set_attributes(elem, **attributes)
    return elem


def update_element(elem: EtreeElement, **attributes: str | float) -> EtreeElement:
    """Update an existing etree.Element with additional params.

    :param elem: at etree element
    :param attributes: element attribute names and values
    :returns: the element with updated attributes

    This is to take advantage of the argument conversion in ``new_element``.
    """
    set_attributes(elem, **attributes)
    return elem


def deepcopy_element(elem: EtreeElement, **attributes: str | float) -> EtreeElement:
    """Create a deepcopy of an element. Optionally pass additional params.

    :param elem: at etree element or list of elements
    :param attributes: element attribute names and values
    :returns: a deepcopy of the element with updated attributes
    :raises DeprecationWarning:
    """
    warnings.warn(
        "deepcopy_element is deprecated. "
        + "Use copy.deepcopy from the standard library instead.",
        category=DeprecationWarning,
    )
    elem = copy.deepcopy(elem)
    _ = update_element(elem, **attributes)
    return elem
