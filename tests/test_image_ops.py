"""Test functions in the image_ops.py module.

:author: Shay Hill
:created: 2026-07-16
"""

from typing import Any

import pytest
from conftest import TEST_RESOURCES

from svg_ultralight.font_tools.sanitize_text import sanitize_text
from svg_ultralight.nsmap import new_qname


@pytest.fixture(scope="module")
def pil_dependency() -> None:
    try:
        from PIL import Image  # noqa: PLC0415  # pyright: ignore[reportUnusedImport]
    except ImportError:
        pytest.skip("Pillow is not installed.")


class TestPassImageInstance:
    def test_pass_image_instance(self, pil_dependency: Any) -> None:
        from PIL import Image  # noqa: PLC0415

        from svg_ultralight.image_ops import new_image_blem  # noqa: PLC0415

        del pil_dependency

        blank_image = Image.new("RGB", (100, 100), color="white")
        _ = new_image_blem(blank_image)


class TestImageFile:
    def test_image_file(self, pil_dependency: Any) -> None:
        from PIL import Image  # noqa: PLC0415

        from svg_ultralight.image_ops import new_image_blem  # noqa: PLC0415

        del pil_dependency

        image_path = TEST_RESOURCES / "favicon.png"

        image = Image.open(image_path)
        blem = new_image_blem(image)
        blem.cx = 500
        assert list(blem.elem.attrib.keys())[-1] == "transform"
        sanitize_text(blem.elem)
        assert list(blem.elem.attrib.keys())[-1] == new_qname("xlink", "href")
