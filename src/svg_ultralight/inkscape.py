"""Operations on existing svg files.

This module contains Inkscape calls for manipulating svg files after they have been
created, but not necessarily written to disk. These are just wrappers around
selections from the Inkscape command line interface.

Inkscape cli calls generally take the form

   inkscape --some-option input_filename.svg --export-filename=export_filename.svg

This module allows you to optionally make these calls with svg root elements instead
of filenames. In such cases, the root elements will be written to a temporary file,
the Inkscape CLI called, and something returned.

:author: Shay Hill
:created: 2023-02-14
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from lxml import etree

from svg_ultralight import main

if TYPE_CHECKING:
    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )


def write_png_from_svg(
    inkscape: str | os.PathLike[str],
    svg: str | os.PathLike[str],
    png: str | os.PathLike[str] | None = None,
) -> str:
    """Convert an svg file to a png.

    :param inkscape: path to inkscape executable
    :param svg: path to svg file
    :param png: optional path to png output file
    :return: png filename
    :effects: creates a new png from svg filename
    :raises ValueError: if unable to write png. This could result from an error with
        Inkscape.

    If no output png path is given, the output path will be inferred from the ``svg``
    filename.
    """
    inkscape = Path(inkscape).with_suffix("")  # remove .exe if present
    png = str(Path(svg).with_suffix(".png")) if png is None else str(png)

    # inkscape versions >= 1.0
    options = [f'"{svg}"', "--export-type=png", f'--export-filename="{png}"']
    return_code = subprocess.call(f'"{inkscape}" ' + " ".join(options))
    if return_code == 0:
        return png

    # inkscape versions < 1.0
    return_code = subprocess.call(f'"{inkscape}" -f "{svg}" -e "{png}"')
    if return_code == 0:
        return png

    msg = f"failed to write {png} with inkscape {inkscape}"
    raise ValueError(msg)


def write_png(
    inkscape: str | os.PathLike[str],
    png: str | os.PathLike[str],
    root: EtreeElement,
    stylesheet: str | os.PathLike[str] | None = None,
) -> str:
    """Create a png file without writing an intermediate svg file.

    :param inkscape: path to inkscape executable
    :param png: path to output png file
    :param root: root node of your svg geometry
    :param stylesheet: optional path to css stylesheet
    :return: png filename (the same you input as ``png``)
    :effects: creates a new png file

    This just creates a tempfile, writes the svg to the tempfile, then calls
    ``write_png_from_svg`` with the tempfile. This isn't faster (it might be slightly
    slower), but it keeps the filesystem clean when you only want the png.
    """
    with NamedTemporaryFile(mode="wb", delete=False) as svg_file:
        svg = main.write_svg(svg_file, root, stylesheet)
    _ = write_png_from_svg(inkscape, svg, png)
    os.unlink(svg)
    return str(png)


def write_pdf_from_svg(
    inkscape: str | os.PathLike[str],
    svg: str | os.PathLike[str],
    pdf: str | os.PathLike[str] | None = None,
) -> str:
    """Convert an svg file to a pdf.

    :param inkscape: path to inkscape executable
    :param svg: path to svg file
    :param pdf: optional path to png output file
    :return: pdf filename
    :effects: creates a new pfd from svg filename
    :raises ValueError: if unable to write pdf. This could result from an error with
        Inkscape.

    If no output png path is given, the output path will be inferred from the ``svg``
    filename.
    """
    inkscape = Path(inkscape).with_suffix("")  # remove .exe if present
    pdf = str(Path(svg).with_suffix(".pdf")) if pdf is None else str(pdf)

    # inkscape versions >= 1.0
    options = [f'"{svg}"', "--export-type=pdf", f'--export-filename="{pdf}"']
    return_code = subprocess.call(f'"{inkscape}" ' + " ".join(options))
    if return_code == 0:
        return pdf

    # inkscape versions < 1.0
    return_code = subprocess.call(f'"{inkscape}" -f "{svg}" -e "{pdf}"')
    if return_code == 0:
        return pdf

    msg = f"failed to write {pdf} from {svg}"
    raise ValueError(msg)


def write_pdf(
    inkscape: str | os.PathLike[str],
    pdf: str | os.PathLike[str],
    root: EtreeElement,
    stylesheet: str | os.PathLike[str] | None = None,
) -> str:
    """Create a pdf file without writing an intermediate svg file.

    :param inkscape: path to inkscape executable
    :param pdf: path to output pdf file
    :param root: root node of your svg geometry
    :param stylesheet: optional path to css stylesheet
    :return: pdf filename (the same you input as ``pdf``)
    :effects: creates a new pdf file

    This just creates a tempfile, writes the svg to the tempfile, then calls
    ``write_pdf_from_svg`` with the tempfile. This isn't faster (it might be slightly
    slower), but it keeps the filesystem clean when you only want the pdf.
    """
    with NamedTemporaryFile(mode="wb", delete=False) as svg_file:
        svg = main.write_svg(svg_file, root, stylesheet)
    _ = write_pdf_from_svg(inkscape, svg, pdf)
    os.unlink(svg)
    return str(pdf)


def export_text_to_path(
    inkscape: str | os.PathLike[str],
    input_file: str | os.PathLike[str],
    export_file: str | os.PathLike[str],
) -> str:
    """Export copy of svg file with text converted to paths.

    :param inkscape: Path to inkscape executable.
    :param input_file: Path to svg file.
    :param export_file: Path to result.
    :return: Path to result.
    :effect: Writes to export_file.

    Find any text objects in an svg file and convert them to paths.
    """
    inkscape = Path(inkscape).with_suffix("")  # remove .exe if present
    command = [
        str(inkscape),
        "--export-text-to-path",
        "--export-plain-svg",
        str(input_file),
        f"--export-filename={export_file}",
    ]
    _ = subprocess.call(command)
    return str(export_file)


def convert_text_to_path(
    inkscape: str | os.PathLike[str], root: EtreeElement
) -> EtreeElement:
    """Convert text to path in a root svg element.

    :param inkscape: Path to inkscape executable.
    :param root: SVG root element.
    :return: SVG root element with text converted to path.
    """
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        _ = main.write_svg(f, root)
        temp_input = f.name
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_export = Path(temp_dir) / "export.svg"
        _ = export_text_to_path(inkscape, temp_input, temp_export)
        root = etree.parse(temp_export).getroot()
    os.unlink(temp_input)
    return root


def write_root(
    inkscape: str | os.PathLike[str],
    filename: str | os.PathLike[str],
    root: EtreeElement,
    *,
    do_text_to_path: bool = True,
    do_svg: bool = True,
    do_png: bool | str | os.PathLike[str] = False,
    do_pdf: bool | str | os.PathLike[str] = False,
) -> EtreeElement:
    """Save xml in multiple file formats, optionally updating text to paths.

    :param inkscape: Path to the Inkscape executable or command.
    :param filename: Path to the output svg file.
    :param root: The XML element to be saved.
    :param do_text_to_path: Whether to convert text to paths.
    :param do_svg: Whether to save the file in SVG format.
    :param do_png: Whether to save the file in PNG format. If True, the output
        filename will be generated from the filename argument. Optionally
        explicity specify an output path.
    :param do_pdf: Whether to save the file in PDF format. If True, the output
        filename will be generated from the filename argument. Optionally
        explicity specify an output path.
    :return: The XML element that was saved.

    This is an umbrella function over the other functions in this module. If you
    have Inkscape installed, this function will likeley be a better choice than
    `write_svg`, even if it will not accept IO objects as filename arguments.

    The largest errors between Inkscape and browsers have to do with text. If the
    browser doesn't know about your font (even if it *should*), your svg will
    not look the same in your browser (or book) as it does in Inkscape. It's
    good practice to save all svg images with text using this function.
    """
    output_svg = Path(filename).with_suffix(".svg")
    output_png = output_svg.with_suffix(".png") if isinstance(do_png, bool) else do_png
    output_pdf = output_svg.with_suffix(".pdf") if isinstance(do_pdf, bool) else do_pdf

    if do_text_to_path and next(root.itertext(), None) is not None:
        root = convert_text_to_path(inkscape, root)
    if do_svg:
        _ = main.write_svg(output_svg, root)
    if do_png:
        if do_svg:
            _ = write_png_from_svg(inkscape, output_svg, output_png)
        else:
            _ = write_png(inkscape, output_png, root)
    if do_pdf:
        if do_svg:
            _ = write_pdf_from_svg(inkscape, output_svg, output_pdf)
        else:
            _ = write_pdf(inkscape, output_pdf, root)
    return root
