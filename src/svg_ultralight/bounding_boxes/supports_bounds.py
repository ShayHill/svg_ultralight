"""A protocol for objects that support bounds.

This module defines a protocol for objects that can have bounds. Existing and
future types like BoundingBox, BoundElement, and PaddedText can be arranged,
aligned, and uniformly scaled by reading and setting their bounds. This is the
interface needed to support such alignment.

Attributes:
    x (float): The minimum x coordinate. x2 (float): The maximum x coordinate.
    cx (float): The center x coordinate. y (float): The minimum y coordinate. y2
    (float): The maximum y coordinate. cy (float): The center y coordinate.
    width (float): The width of the object. height (float): The height of the
    object. scale (float): The scale of the object.

:author: Shay Hill
:created: 2023-02-15
"""

from __future__ import annotations

from typing import Protocol

_Matrix = tuple[float, float, float, float, float, float]


class SupportsBounds(Protocol):
    """Protocol for objects that can have bounds.

    Attributes:
        transformation (_Matrix): An svg-style transformation matrix.
        transform (method): Apply a transformation to the object.
        x (float): The minimum x coordinate.
        x2 (float): The maximum x coordinate.
        cx (float): The center x coordinate.
        y (float): The minimum y coordinate.
        y2 (float): The maximum y coordinate.
        cy (float): The center y coordinate.
        width (float): The width of the object.
        height(float): The height of the object.
        scale ((float, float)): The x and yx and y scale of the object.

    There is no setter for scale. Scale is a function of width and height.
    Setting scale would be ambiguous. because the typical implementation of
    scale would modify the x and y coordinates. If you want to scale an object,
    set width and height.
    """

    def transform(
        self,
        transformation: _Matrix | None = None,
        *,
        scale: tuple[float, float] | float | None = None,
        dx: float | None = None,
        dy: float | None = None,
        reverse: bool = False,
    ) -> None:
        """Apply a transformation to the object."""
        ...

    @property
    def x(self) -> float:
        """Return minimum x coordinate."""
        ...

    @x.setter
    def x(self, value: float) -> None:
        """Set minimum x coordinate.

        :param value: The minimum x coordinate.
        """

    @property
    def x2(self) -> float:
        """Return maximum x coordinate."""
        ...

    @x2.setter
    def x2(self, value: float) -> None:
        """Set maximum x coordinate.

        :param value: The maximum x coordinate.
        """

    @property
    def cx(self) -> float:
        """Return center x coordinate."""
        ...

    @cx.setter
    def cx(self, value: float) -> None:
        """Set center x coordinate.

        :param value: The center x coordinate.
        """

    @property
    def y(self) -> float:
        """Return minimum y coordinate."""
        ...

    @y.setter
    def y(self, value: float) -> None:
        """Set minimum y coordinate.

        :param value: The minimum y coordinate.
        """

    @property
    def y2(self) -> float:
        """Return maximum y coordinate."""
        ...

    @y2.setter
    def y2(self, value: float) -> None:
        """Set maximum y coordinate.

        :param value: The maximum y coordinate.
        """

    @property
    def cy(self) -> float:
        """Return center y coordinate."""
        ...

    @cy.setter
    def cy(self, value: float) -> None:
        """Set center y coordinate.

        :param value: The center y coordinate.
        """

    @property
    def width(self) -> float:
        """Return width of the object."""
        ...

    @width.setter
    def width(self, value: float) -> None:
        """Set width of the object.

        :param value: The width of the object.
        """

    @property
    def height(self) -> float:
        """Return height of the object."""
        ...

    @height.setter
    def height(self, value: float) -> None:
        """Set height of the object.

        :param value: The height of the object.
        """

    @property
    def scale(self) -> tuple[float, float]:
        """Return scale of the object."""
        ...

    @scale.setter
    def scale(self, value: tuple[float, float]) -> None:
        """Return scale of the object.

        :param value: The scale of the object.
        """
        ...
