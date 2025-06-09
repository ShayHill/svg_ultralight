"""One script to animate a list of pngs.

Requires: pillow, which is an optional project dependency.

:author: Shay Hill
:created: 7/26/2020
"""

from __future__ import annotations

try:
    from PIL import Image
except ModuleNotFoundError as exc:
    MSG = "`pip install pillow` to use svg_ultralight.animate module"
    raise ModuleNotFoundError(MSG) from exc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable


def write_gif(
    gif: str | os.PathLike[str],
    pngs: Iterable[str] | Iterable[os.PathLike[str]] | Iterable[str | os.PathLike[str]],
    duration: float = 100,
    loop: int = 0,
) -> None:
    """Create a gif from a sequence of pngs.

    :param gif: output filename (include .gif extension)
    :param pngs: png filenames
    :param duration: milliseconds per frame
    :param loop: how many times to loop gif. 0 -> forever
    :effects: write file to gif
    """
    images = [Image.open(x) for x in pngs]
    images[0].save(
        gif, save_all=True, append_images=images[1:], duration=duration, loop=loop
    )
