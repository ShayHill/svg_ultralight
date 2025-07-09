"""Type hints for pass-through arguments to lxml constructors.

:author: Shay Hill
:created: 2025-07-09
"""

from collections.abc import Mapping
from typing import Union

# Types svg_ultralight can format to pass through to lxml constructors.
ElemAttrib = Union[str, float, None]

# Type for an optional dictionary of element attributes.
ElemAttribArg = Union[Mapping[str, ElemAttrib], None]
