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
from typing import TYPE_CHECKING

from lxml import etree

from svg_ultralight import main

if TYPE_CHECKING:
    from lxml.etree import _Element as EtreeElement  # type: ignore


def export_text_to_path(
    inkscape: str | Path, input_file: str | Path, export_file: str | Path
) -> str:
    """Export copy of svg file with text converted to paths.

    :param inkscape: Path to inkscape executable.
    :param input_file: Path to svg file.
    :param export_file: Path to result.
    :return: Path to result.
    :effect: Writes to export_file.

    Find any text objects in an svg file and convert them to paths.
    """
    command = [
        str(inkscape),
        "--export-text-to-path",
        "--export-plain-svg",
        str(input_file),
        f"--export-filename={export_file}",
    ]
    _ = subprocess.call(command)
    return str(export_file)


def convert_text_to_path(inkscape: str | Path, root: EtreeElement) -> EtreeElement:
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
