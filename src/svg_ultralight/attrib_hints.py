"""Type hints for pass-through arguments to lxml constructors.

:author: Shay Hill
:created: 2025-07-09
"""

from collections.abc import Mapping
from typing import TypeAlias

# Types svg_ultralight can format to pass through to lxml constructors.
ElemAttrib: TypeAlias = str | float | None

# Type for an optional dictionary of element attributes.
OptionalElemAttribMapping: TypeAlias = Mapping[str, ElemAttrib] | None
