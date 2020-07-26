#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
""" One script to animate a list of pngs

:author: Shay Hill
:created: 7/26/2020
"""
from PIL import Image
from typing import Iterable


def write_gif(
    gif: str, pngs: Iterable[str], duration: float = 100, loop: int = 0
) -> None:
    """
    Create a gif from a sequence of pngs.

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
