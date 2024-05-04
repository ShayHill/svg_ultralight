"""Test the inkscape module.

:author: Shay Hill
:created: 2023-02-14
"""

import random
import uuid
from pathlib import Path

import pytest
from lxml import etree
from lxml.etree import _Element as EtreeElement  # type: ignore

from svg_ultralight.constructors import new_sub_element
from svg_ultralight.inkscape import convert_text_to_path
from svg_ultralight.main import new_svg_root
from svg_ultralight.nsmap import NSMAP

INKSCAPE = Path(r"C:\Program Files\Inkscape\bin\inkscape")

if not INKSCAPE.with_suffix(".exe").exists():
    msg = "Inkscape not found. Please install Inkscape or update the INKSCAPE path var."
    raise FileNotFoundError(msg)


PATH_TAG = str(etree.QName(NSMAP["svg"], "path"))
TEXT_TAG = str(etree.QName(NSMAP["svg"], "text"))
G_TAG = str(etree.QName(NSMAP["svg"], "g"))


@pytest.fixture(scope="function")
def text_conversion() -> tuple[EtreeElement, EtreeElement]:
    """Return a root without text."""
    has_text = new_svg_root(0, 0, 1, 1)
    for _ in range(random.randint(1, 10)):
        random_string = str(uuid.uuid4())
        _ = new_sub_element(has_text, "text", text=random_string)
    no_text = convert_text_to_path(INKSCAPE, has_text)
    return has_text, no_text

    has_text = new_svg_root(0, 0, 1, 1)
    return has_text, no_text


# @pytest.mark.skipif(not INKSCAPE.exists(), reason="Inkscape not installed")
class TestTextToPath:
    """Test the convert_text_to_path function."""

    def test_one_path_per_text_elem(self, text_conversion):
        """Test the convert_text_to_path function."""
        has_text, no_text = text_conversion
        num_text = len(has_text.findall("text"))
        num_paths = len(no_text.findall(PATH_TAG))
        assert num_text == num_paths
