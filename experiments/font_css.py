"""Link local fonts as css in an svg file.

:author: Shay Hill
:created: 2025-06-04
"""

# pyright: reportUnknownMemberType = false
# pyright: reportAttributeAccessIssue = false
# pyright: reportUnknownArgumentType = false
# pyright: reportUnknownVariableType = false
# pyright: reportUnknownParameterType = false
# pyright: reportMissingTypeStubs = false

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import cssutils

from svg_ultralight.constructors import new_element
from svg_ultralight.string_conversion import encode_to_css_class_name

if TYPE_CHECKING:
    import os

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )


def _get_class_names_from_stylesheet(
    stylesheet: cssutils.css.CSSStyleSheet,
) -> list[str]:
    """Extract all class names from a given CSS stylesheet.

    :param stylesheet: A cssutils.css.CSSStyleSheet object.
    :return: A list of class names (without the leading dot).
    """
    class_names: list[str] = []
    for rule in stylesheet.cssRules:
        if rule.type == rule.STYLE_RULE:
            selectors = (s.strip() for s in rule.selectorText.split(","))
            class_names.extend(s[1:] for s in selectors if s.startswith("."))
    return class_names


def add_svg_font_class(root: EtreeElement, font: str | os.PathLike[str]) -> str:
    """Add a css class for the font to the root element.

    :param root: The root element of the SVG document.
    :param font: Path to the font file.
    :return: The class name for the font, e.g., "bahnschrift_2e_ttf"
    """
    assert Path(font).exists()
    family_name = encode_to_css_class_name(Path(font).stem)
    class_name = encode_to_css_class_name(Path(font).name)
    style = root.find("style")
    if style is None:
        style = new_element("style", type="text/css")
        root.insert(0, style)
    css = style.text or ""

    stylesheet = cssutils.parseString(css)
    existing_class_names = _get_class_names_from_stylesheet(stylesheet)
    if class_name in existing_class_names:
        return class_name

    font_face_rule = cssutils.css.CSSFontFaceRule()
    font_face_rule.style = cssutils.css.CSSStyleDeclaration()
    font_face_rule.style["font-family"] = f'"{family_name}"'
    font_face_rule.style["src"] = rf"url('{Path(font).as_posix()}')"
    stylesheet.add(font_face_rule)

    style_rule = cssutils.css.CSSStyleRule(selectorText=f".{class_name}")
    style_rule.style = cssutils.css.CSSStyleDeclaration()
    style_rule.style["font-family"] = f'"{family_name}"'
    stylesheet.add(style_rule)

    style.text = stylesheet.cssText.decode("utf-8")

    return class_name
