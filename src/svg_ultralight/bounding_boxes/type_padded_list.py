"""A list of padded text elements that transform as one.

This class simplifies working with multiple PaddedText elements as a group.

In addition to the usual PaddedText getters and setters (x, cx, x2, y, cy, y2, width,
height), it also provides tight versions of those (tx, tcx, tx2, ty, tcy, ty2,
twidth, theight) that operate on the unpadded bounding box. Get and set these
dimension attributes with the get_dim and set_dim methods.

Will additionally stack and align the elements. Stack (any method with a `name`
argument) will expect a one of x, cx, x2, y, cy, or y2 (or their tight equivalents
tx, tcx, tx2, ty, tcy, ty2).

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
from typing import cast, overload

from svg_ultralight.bounding_boxes.bound_helpers import new_bound_union
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.transformations import new_transformation_matrix

_Matrix = tuple[float, float, float, float, float, float]


class PaddedList:
    """A list of padded text elements that transform as one."""

    def __init__(self, *plems: PaddedText) -> None:
        """Initialize with a list of padded text elements."""
        self.plems = list(plems)

    @overload
    def __getitem__(self, idx: slice) -> "PaddedList": ...

    @overload
    def __getitem__(self, idx: int) -> PaddedText: ...

    def __getitem__(self, idx: slice | int) -> "PaddedList | PaddedText":
        """Get one or more padded text elements."""
        if isinstance(idx, int):
            return self.plems[idx]
        return PaddedList(*self.plems[idx])

    @property
    def bbox(self) -> BoundingBox:
        """The bounding box of the padded text elements."""
        return BoundingBox.merge(*(x.bbox for x in self.plems))

    @property
    def tbox(self) -> BoundingBox:
        """The unpadded bounding box of the padded text elements.

        t for true or tight.
        """
        return BoundingBox.merge(*(x.tbox for x in self.plems))

    def transform(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: tuple[float, float] | float | None = None,
        dx: float | None = None,
        dy: float | None = None,
    ) -> None:
        """Apply a transformation to all the padded text elements."""
        for p in self.plems:
            p.transform(transformation, scale=scale, dx=dx, dy=dy)

    @property
    def union(self) -> BoundElement:
        """A single bound element containing all the padded text elements."""
        return new_bound_union(*self.plems)

    @property
    def tunion(self) -> BoundElement:
        """A single bound element containing all the unpadded text elements."""
        union = self.union
        union.bbox = self.tbox
        return union

    def get_dim(self, name: str) -> float:
        """Get a dimension from bbox or tbox."""
        box = self.tbox if name.startswith("t") else self.bbox
        name = name.removeprefix("t")
        if name not in ("x", "cx", "x2", "y", "cy", "y2", "width", "height"):
            msg = f"Cannot get dimension '{name}'"
            raise AttributeError(msg)
        return cast("float", getattr(box, name))

    def new_tmat(self, name: str, value: float) -> _Matrix:
        """Create a transformation matrix to set a dimension to a value.

        This is a separate method so it can be, when necessary, be identified and
        applied to subsets of the PaddedList.
        """
        current_value = self.get_dim(name)
        name = name.removeprefix("t")
        if name in ("x", "cx", "x2"):
            return new_transformation_matrix(dx=value - current_value)
        if name in ("y", "cy", "y2"):
            return new_transformation_matrix(dy=value - current_value)
        if name in ("width", "height"):
            return new_transformation_matrix(scale=value / current_value)
        msg = f"Cannot set dimension '{name}'"
        raise AttributeError(msg)

    def set_dim(self, **kwargs: float) -> None:
        """Set a dimension on bbox or tbox."""
        for name, value in kwargs.items():
            tmat = self.new_tmat(name, value)
            self.transform(transformation=tmat)

    def align(self, dimension: str, value: float | None = None) -> None:
        """Align the specified edges or centers of the padded text elements.

        :param dimension: One of 'x', 'cx', 'x2', 'y', 'cy', or 'y2' or any of the
            same prefixed with 't'.
        :param value: If provided, align to this value. Otherwise, align to the
            corresponding edge or center of the bounding box of all the padded
            text elements.
        """
        if value is None:
            value = self.get_dim(dimension)
        for i, plem in enumerate(self.plems):
            tmat = self[i : i + 1].new_tmat(dimension, value)
            plem.transform(transformation=tmat)

    def stack(self, scale: float = 1, gap: float | None = None) -> None:
        """Stack the gapded text elements vertically with a gap.

        :param scale: If provided, scale the native line height (ascent + descent)
            of the text elements by this factor.
        :param gap: If provided, add this much space between the text elements. This
            is an alternate strategy for when you are using fonts of different sizes.
            If the gap parameter is passed, the scale parameter is ignored.
        """
        if gap is not None:
            for above, below in it.pairwise(self.plems):
                below.y = above.y2 + gap
            return
        for above, below in it.pairwise(self.plems):
            below.y = above.y + above.height * scale
