"""Font metrics for text layout.

:author: Shay Hill
:created: 2025-01-15
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class FontMetrics:
    """Font metrics."""

    _font_size: float
    _ascent: float
    _descent: float
    _cap_height: float
    _x_height: float
    _line_gap: float
    _scalar: float = dataclasses.field(default=1.0, init=False)

    def scale(self, scalar: float) -> None:
        """Scale the font metrics by a scalar.

        :param scalar: The scaling factor.
        """
        self._scalar *= scalar

    @property
    def font_size(self) -> float:
        """The font size."""
        return self._font_size * self._scalar

    @property
    def ascent(self) -> float:
        """Return the ascent."""
        return self._ascent * self._scalar

    @property
    def descent(self) -> float:
        """Return the descent."""
        return self._descent * self._scalar

    @property
    def cap_height(self) -> float:
        """Return the cap height."""
        return self._cap_height * self._scalar

    @property
    def x_height(self) -> float:
        """Return the x height."""
        return self._x_height * self._scalar

    @property
    def line_gap(self) -> float:
        """Return the line gap."""
        return self._line_gap * self._scalar
