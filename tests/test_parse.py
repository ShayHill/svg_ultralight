"""Test parsing an svg file into a BoundElement.

:author: Shay Hill
:created: 2025-12-28
"""

from pathlib import Path

from conftest import TEST_RESOURCES

from svg_ultralight.bounding_boxes.bound_helpers import parse_bound_element
from svg_ultralight.main import new_svg_root, write_svg

input_svg = TEST_RESOURCES / "fs_logo.svg"


def test_decopy_paths() -> None:
    """Replace any use elements with the elements they use."""
    blem = parse_bound_element(input_svg)
    assert len(blem.elem) == 7
    assert all(e.tag == "g" for e in blem.elem)


def test_parse_and_rewrite_preserves_unique_path_ids(tmp_path: Path) -> None:
    """Expand reused paths without carrying definition IDs into each instance."""
    source = tmp_path / "source.svg"
    output = tmp_path / "output.svg"
    _ = source.write_text(
        """<svg viewBox="0 0 10 10">
        <defs><path id="E" data-text="E" d="M0 0H1"/></defs>
        <g><use href="#E" transform="translate(1)"/>
        <use href="#E" transform="translate(2)"/></g>
        </svg>""",
        encoding="utf-8",
    )

    blem = parse_bound_element(source)
    root = new_svg_root(0, 0, 10, 10)
    root.append(blem.elem)
    _ = write_svg(output, root, do_reuse_paths=True)

    output_text = output.read_text(encoding="utf-8")
    ids = root.xpath(".//*[@id]/@id")
    assert len(ids) == len(set(ids))
    assert 'id="E"' in output_text
    assert 'href="#E"' in output_text
    assert 'id="E" href="#E"' not in output_text
