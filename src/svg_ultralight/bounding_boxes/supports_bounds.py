"""A protocol for objects that support bounds.

Existing and future types like BoundingBox, BoundElement, and PaddedText can be
arranged, aligned, and uniformly scaled by reading and setting their bounds.

    bbox_1.x == bbox_2.y

This is the interface needed to support such alignment.

:author: Shay Hill
:created: 2023-02-15
"""
# ignore missing docstrings for protocol methods
# ruff: noqa D102
# pylint: disable=missing-docstring

from typing import Protocol


class SupportsBounds(Protocol):

    """Bounds can be get and set."""

    @property
    def x(self) -> float:
        ...

    @x.setter
    def x(self, x: float):
        ...

    @property
    def x2(self) -> float:
        ...

    @x2.setter
    def x2(self, x2: float):
        ...

    @property
    def cx(self) -> float:
        ...

    @cx.setter
    def cx(self, cx: float):
        ...

    @property
    def y(self) -> float:
        ...

    @y.setter
    def y(self, y: float):
        ...

    @property
    def y2(self) -> float:
        ...

    @y2.setter
    def y2(self, y2: float):
        ...

    @property
    def cy(self) -> float:
        ...

    @cy.setter
    def cy(self, cy: float):
        ...

    @property
    def width(self) -> float:
        ...

    @width.setter
    def width(self, width: float):
        ...

    @property
    def height(self) -> float:
        ...

    @height.setter
    def height(self, height: float):
        ...

    @property
    def scale(self) -> float:
        ...
