"""Test methods of the PaddedList class.

:author: Shay Hill
:created: 2025-11-18
"""

import copy
import itertools as it
import math
from pathlib import Path

from svg_ultralight.bounding_boxes.padded_text_initializers import pad_text
from svg_ultralight.bounding_boxes.type_padded_list import PaddedList

font = Path("C:/Windows/Fonts/bahnschrift.ttf")

test_instance = PaddedList(
    pad_text(font, "a"), pad_text(font, "b"), pad_text(font, "c")
)


class TestPaddedList:
    def test_init(self):
        assert len(test_instance.plems) == 3

    def test_getitem_int(self):
        plem = test_instance[1]
        assert plem.elem[0].attrib["data-text"] == "b"

    def test_getitem_slice(self):
        sublist = test_instance[0::2]
        assert isinstance(sublist, PaddedList)
        assert len(sublist.plems) == 2
        assert sublist.plems[0].elem[0].attrib["data-text"] == "a"
        assert sublist.plems[1].elem[0].attrib["data-text"] == "c"

    def test_transform(self):
        plist = copy.deepcopy(test_instance)
        old_bbox = plist.bbox
        plist.transform(dx=10)
        new_bbox = plist.bbox
        assert new_bbox.x == old_bbox.x + 10

    def test_union(self):
        union = test_instance.union(fill="red")
        assert union.bbox.values() == test_instance.bbox.values()
        assert union.elem.attrib["fill"] == "red"

    def test_align(self):
        for dim in ("x", "cx", "x2", "y", "cy", "y2", "width", "height"):
            plist = copy.deepcopy(test_instance)
            plist.align(dim, 100)
            for p in plist.plems:
                assert math.isclose(getattr(p, dim), 100)

    def test_stack_defaults(self):
        plist = copy.deepcopy(test_instance)
        plist.stack()
        for above, below in it.pairwise(plist.plems):
            offset = below.leading
            assert below.baseline == above.baseline + offset

    def test_stack_gap(self):
        plist = copy.deepcopy(test_instance)
        gap = 5
        plist.stack(gap, "capline")
        for above, below in it.pairwise(plist.plems):
            below.capline = above.baseline + gap

    def test_float_setters(self) -> None:
        """All getters match setter(value)."""
        plist = copy.deepcopy(test_instance)
        # fmt: off
        attrs = [
            "caps_cy", "tx", "tcx", "tx2", "ty", "tcy", "ty2", "twidth",
            "theight", "baseline", "capline", "xline", "font_size",
            "cap_height", "caps_cy", "x_height", "tpad", "rpad", "bpad", "lpad",
            "width", "height", "x", "cx", "x2", "y", "cy", "y2",
        ]
        # fmt: on
        for attr in attrs:
            setattr(plist, attr, 50)
            assert math.isclose(getattr(plist, attr), 50)
