"""A list of padded text elements that transform as one.

This class simplifies working with multiple PaddedText elements as a group.

A PaddedList instance contains no information except pointers to the PaddedText
elements, so you could, for instance, create a jagged arrangements of text elements
with

```python
padded_list.align('x')
padded_list.stack()
padded_list[::2].transform(dx=10)
```

:author: Shay Hill
:created: 2025-11-17
"""

import itertools as it
from typing import overload

from svg_ultralight.attrib_hints import ElemAttrib
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import (
    FontMetrics,
    PaddedText,
    new_empty_padded_union,
    new_padded_union,
)

_Matrix = tuple[float, float, float, float, float, float]


class PaddedList(PaddedText):
    """A list of padded text elements that transform as one."""

    def __init__(self, *plems: PaddedText) -> None:
        """Initialize with a list of padded text elements."""
        self.plems = list(plems)
        self.__mock_union: PaddedText | None = None

    @overload
    def __getitem__(self, idx: slice) -> "PaddedList": ...

    @overload
    def __getitem__(self, idx: int) -> PaddedText: ...

    def __getitem__(self, idx: slice | int) -> "PaddedList | PaddedText":
        """Get one or more padded text elements."""
        if isinstance(idx, int):
            return self.plems[idx]
        return PaddedList(*self.plems[idx])

    def append(self, ptext: PaddedText) -> None:
        """Append a padded text element to the list."""
        self.plems.append(ptext)

    @property
    def _mock_union(self) -> PaddedText:
        """Return a mock union of plems for attribute calculations.

        This is distinct from union to avoid stealing the elements each time it is
        called.
        """
        if self.__mock_union is None:
            self.__mock_union = new_empty_padded_union(*self.plems)
        return self.__mock_union

    def union(self, **attribs: ElemAttrib) -> PaddedText:
        """Return a single bound element containing all the padded text elements."""
        return new_padded_union(*self.plems, **attribs)

    @property
    def metrics(self) -> FontMetrics:
        """The combined metrics of the padded text elements."""
        return self._mock_union.metrics

    @property
    def bbox(self) -> BoundingBox:
        """The bounding box of the padded text elements."""
        return self._mock_union.bbox

    @bbox.setter
    def bbox(self, value: BoundingBox) -> None:
        """Forbid setting the bbox directly."""
        del value
        msg = "Cannot set bbox."
        raise AttributeError(msg)

    @property
    def tbox(self) -> BoundingBox:
        """The unpadded bounding box of the padded text elements."""
        return self._mock_union.tbox

    @property
    def caps_bbox(self) -> BoundingBox:
        """The caps bounding box of the padded text elements."""
        return self._mock_union.caps_bbox

    def transform(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: tuple[float, float] | float | None = None,
        dx: float | None = None,
        dy: float | None = None,
        reverse: bool = False,
    ) -> None:
        """Apply a transformation to all the padded text elements."""
        self.ptmat = (transformation, scale, dx, dy, reverse)
        for p in self.plems:
            p.transform(transformation, scale=scale, dx=dx, dy=dy, reverse=reverse)
        self.__mock_union = None

    def transform_preserve_sidebearings(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: tuple[float, float] | float | None = None,
        dx: float | None = None,
        dy: float | None = None,
        reverse: bool = False,
    ) -> None:
        """Apply a transformation to all the padded text elements."""
        for p in self.plems:
            p.transform_preserve_sidebearings(
                transformation, scale=scale, dx=dx, dy=dy, reverse=reverse
            )
        self.__mock_union = None

    def align(self, attr: str, value: float | None = None) -> None:
        """Align the specified handles of the padded text elements.

        :param attr: Any attribute to all be set to the same value.
        :param value: If provided, align to this value. Otherwise, align to the
            corresponding edge or center of the bounding box of all the padded
            text elements.
        """
        if value is None:
            value = getattr(self._mock_union, attr)
        for plem in self.plems:
            setattr(plem, attr, value)
        self.__mock_union = None

    def stack(
        self, offset: float | None = None, bottom_handle: str = "baseline"
    ) -> None:
        """Stack the padded text elements vertically.

        :param offset: The distance between baselines. Default is the leading
            attribute with some adjustment for potentially differing font sizes.
        :param bottom_handle: The handle on the lower text element to align to the
            offset above the upper text element's baseline. Default is 'baseline'.

        If bottom_handle is set to 'capline', then the offset will be the fixed
        distance between the baseline of one element and the capline of the element
        below. This will usually be a better choice than a fixed baseline-to-baseline
        distance when stacking text elements of different font sizes.
        """
        for above, below in it.pairwise(self.plems):
            if offset is None:
                offset = above.leading + above.y + below.ascent
            dy = getattr(below, bottom_handle) - (above.baseline + offset)
            below.transform(dy=-dy)
