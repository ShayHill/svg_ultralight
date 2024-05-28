"""Test importing an SVG file.

:author: Shay Hill
:created: 2024-05-28
"""

from pathlib import Path
from svg_ultralight.import_svg import import_svg
from lxml import etree

_TEST_RESOURCES = Path(__file__).parent / "resources"
_TEST_FILE = _TEST_RESOURCES / "arrow.svg"



class TestImportSvg:
    def test_get_bbox(self):
        """Import an svg file as a BoundElement instance."""
        blem = import_svg(_TEST_FILE)
        assert blem.bbox.x == -3
        assert blem.bbox.y == -3
        assert blem.bbox.width == 128
        assert blem.bbox.height == 128

    def test_get_geometry(self):
        tree = etree.parse(_TEST_FILE)
        root = tree.getroot()
        blem = import_svg(_TEST_FILE)
        assert [x.tag for x in blem.elem] == [x.tag for x in root]



