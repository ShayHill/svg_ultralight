"""Crop an image before converting to binary and including in the svg file.

This optional module requires the Pillow library. Create an svg image element with a
rasterized image positioned inside a bounding box.

:author: Shay Hill
:created: 2024-11-20
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from paragraphs import par

try:
    from PIL import Image

    if TYPE_CHECKING:
        from PIL.Image import Image as ImageType
except ImportError as err:
    msg = par(
        """PIL is not installed. Install it using 'pip install Pillow' to use
        svg_ultralight.image_ops module."""
    )
    raise ImportError(msg) from err

import base64
import io

from lxml import etree

from svg_ultralight import NSMAP
from svg_ultralight.bounding_boxes.bound_helpers import bbox_dict
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.constructors import new_element

if TYPE_CHECKING:
    import os

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore [reportPrivateUsage]
    )


def _symmetric_crop(
    image: ImageType, center: tuple[float, float] | None = None
) -> ImageType:
    """Crop an image symmetrically around a center point.

    :param image: PIL.Image instance
    :param center: optional center point for cropping. Proportions of image with and
        image height, so the default value, (0.5, 0.5), is the true center of the
        image.  (0.4, 0.5) would crop 20% off the right side of the image.
    :return: PIL.Image instance
    """
    if center is None:
        return image

    if not all(0 < x < 1 for x in center):
        msg = "Center must be between (0, 0) and (1, 1)"
        raise ValueError(msg)

    xd, yd = (min(x, 1 - x) for x in center)
    left, right = sorted(x * image.width for x in (center[0] - xd, center[0] + xd))
    top, bottom = sorted(x * image.height for x in (center[1] - yd, center[1] + yd))

    return image.crop((left, top, right, bottom))


def _crop_image_to_bbox_ratio(
    image: ImageType, bbox: BoundingBox, center: tuple[float, float] | None
) -> ImageType:
    """Crop an image to the ratio of a bounding box.

    :param image: PIL.Image instance
    :param bbox: BoundingBox instance
    :param center: optional center point for cropping. Proportions of image with and
        image height, so the default value, (0.5, 0.5), is the true center of the
        image. (0.4, 0.5) would crop 20% off the right side of the image.
    :return: PIL.Image instance

    This crops the image to the specified ratio. It's not a resize, so it will cut
    off the top and bottom or the sides of the image to fit the ratio.
    """
    image = _symmetric_crop(image, center)
    width, height = image.size

    ratio = bbox.width / bbox.height
    if width / height > ratio:
        new_width = height * ratio
        left = (width - new_width) / 2
        right = width - left
        return image.crop((left, 0, right, height))
    new_height = width / ratio
    top = (height - new_height) / 2
    bottom = height - top
    return image.crop((0, top, width, bottom))


def _get_svg_embedded_image_str(image: ImageType) -> str:
    """Return the string you'll need to embed an image in an svg.

    :param image: PIL.Image instance
    :return: argument for xlink:href
    """
    in_mem_file = io.BytesIO()
    image.save(in_mem_file, format="PNG")
    _ = in_mem_file.seek(0)
    img_bytes = in_mem_file.read()
    base64_encoded_result_bytes = base64.b64encode(img_bytes)
    base64_encoded_result_str = base64_encoded_result_bytes.decode("ascii")
    return "data:image/png;base64," + base64_encoded_result_str


def new_image_blem(
    filename: str | os.PathLike[str],
    bbox: BoundingBox | None = None,
    center: tuple[float, float] | None = None,
) -> BoundElement:
    """Create a new svg image element inside a bounding box.

    :param filename: filename of source image
    :param bbox: bounding box for the image
    :param center: center point for cropping. Proportions of image width and image
        height, so the default value, (0.5, 0.5), is the true center of the image.
        (0.4, 0.5) would crop 20% off the right side of the image.
    :return: a BoundElement element with the cropped image embedded
    """
    image = Image.open(filename)
    if bbox is None:
        bbox = BoundingBox(0, 0, image.width, image.height)
    image = _crop_image_to_bbox_ratio(Image.open(filename), bbox, center)
    svg_image = new_element("image", **bbox_dict(bbox))
    svg_image.set(
        etree.QName(NSMAP["xlink"], "href"), _get_svg_embedded_image_str(image)
    )
    return BoundElement(svg_image, bbox)


def new_image_elem_in_bbox(
    filename: str | os.PathLike[str],
    bbox: BoundingBox | None = None,
    center: tuple[float, float] | None = None,
) -> EtreeElement:
    """Create a new svg image element inside a bounding box.

    :param filename: filename of source image
    :param bbox: bounding box for the image
    :param center: center point for cropping. Proportions of image width and image
        height, so the default value, (0.5, 0.5), is the true center of the image.
        (0.4, 0.5) would crop 20% off the right side of the image.
    :return: an etree image element with the cropped image embedded
    """
    return new_image_blem(filename, bbox, center).elem
