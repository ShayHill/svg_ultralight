"""Test parsing an svg file into a BoundElement.

:author: Shay Hill
:created: 2025-12-28
"""

from conftest import TEST_RESOURCES

from svg_ultralight.bounding_boxes.bound_helpers import parse_bound_element

input_svg = TEST_RESOURCES / "fs_logo.svg"


def test_decopy_paths():
    """Replace any use elements with the elements they use."""
    blem = parse_bound_element(input_svg)
    assert len(blem.elem) == 7
    assert all(e.tag == "g" for e in blem.elem)
