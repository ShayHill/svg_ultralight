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
        assert plem.elem.attrib["data-text"] == "b"

    def test_getitem_slice(self):
        sublist = test_instance[0::2]
        assert isinstance(sublist, PaddedList)
        assert len(sublist.plems) == 2
        assert sublist.plems[0].elem.attrib["data-text"] == "a"
        assert sublist.plems[1].elem.attrib["data-text"] == "c"

    def test_transform(self):
        plist = copy.deepcopy(test_instance)
        old_bbox = plist.bbox
        plist.transform(dx=10)
        new_bbox = plist.bbox
        assert new_bbox.x == old_bbox.x + 10

    def test_union_bbox(self):
        union = test_instance.union(fill="red")
        assert union.bbox.values() == test_instance.bbox.values()
        assert union.elem.attrib["fill"] == "red"

    def test_union_tbox(self):
        union = test_instance.tunion(stroke="blue")
        assert union.bbox.values() == test_instance.tbox.values()
        assert union.elem.attrib["stroke"] == "blue"

    def test_get_dim_bbox(self):
        for dim in ("x", "cx", "x2", "y", "cy", "y2", "width", "height"):
            assert test_instance.get_dim(dim) == getattr(test_instance.bbox, dim)

    def test_get_dim_tbox(self):
        for dim in ("tx", "tcx", "tx2", "ty", "tcy", "ty2", "twidth", "theight"):
            assert test_instance.get_dim(dim) == getattr(test_instance.tbox, dim[1:])

    def test_set_dim_bbox(self):
        for dim in ("x", "cx", "x2", "y", "cy", "y2", "width", "height"):
            plist = copy.deepcopy(test_instance)
            plist.set_dim(**{dim: 50})
            try:
                assert getattr(plist.bbox, dim) == 50
            except:
                breakpoint()

    def test_set_dim_tbox(self):
        for dim in ("tx", "tcx", "tx2", "ty", "tcy", "ty2", "twidth", "theight"):
            plist = copy.deepcopy(test_instance)
            plist.set_dim(**{dim: 50})
            assert math.isclose(getattr(plist.tbox, dim[1:]), 50)

    def test_set(self):
        """Test setting attributes."""
        plist = copy.deepcopy(test_instance)
        plist.set(fill="green", stroke="black")
        for p in plist.plems:
            assert p.elem.attrib["fill"] == "green"
            assert p.elem.attrib["stroke"] == "black"

    def test_align(self):
        for dim in ("x", "cx", "x2", "y", "cy", "y2", "width", "height"):
            plist = copy.deepcopy(test_instance)
            plist.align(dim, 100)
            for p in plist.plems:
                assert math.isclose(getattr(p, dim), 100)

    def test_stack_scale(self):
        plist = copy.deepcopy(test_instance)
        plist.stack(scale=2)
        for above, below in it.pairwise(plist.plems):
            height = above.height
            assert math.isclose(above.y + height * 2, below.y)

    def test_stack_gap(self):
        plist = copy.deepcopy(test_instance)
        gap = 5
        plist.stack(gap=gap)
        for above, below in it.pairwise(plist.plems):
            assert math.isclose(above.y2 + gap, below.y)

    def test_padded_union(self):
        union = test_instance.padded_union(pad=2, fill="yellow")
        assert union.tbox.values() == test_instance.tbox.values()
        assert union.bbox.values() == test_instance.bbox.values()
