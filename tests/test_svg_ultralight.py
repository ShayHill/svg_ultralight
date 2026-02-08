"""Test functions in ``svg_ultralight``.

:author: Shay Hill
:created: 10/25/2019

Explicitly tests string output, so any change in format will cause the tests to fail.
No tests for png writing.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from lxml import etree

from svg_ultralight import NSMAP
from svg_ultralight.constructors import new_element

from svg_ultralight.main import _reuse_paths, new_svg_root, write_svg
from svg_ultralight.string_conversion import svg_tostring

if TYPE_CHECKING:
    from lxml.etree import _Element as EtreeElement


def _local_tag(elem: EtreeElement) -> str:
    """Return the local part of the element tag (no namespace)."""
    tag_str = str(elem.tag) if elem.tag else ""
    return tag_str.split("}")[-1] if "}" in tag_str else tag_str


@pytest.fixture
def css_source():
    """Temporary css file object with meaningless contents."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as css_source:
        _ = css_source.write("/** css for my project **/")
    yield css_source.name
    os.unlink(css_source.name)


@pytest.fixture
def temp_filename(mode: str = "w"):
    """Temporary file object to capture test output."""
    with tempfile.NamedTemporaryFile(mode=mode, delete=False) as svg_output:
        yield svg_output.name
    os.unlink(svg_output.name)


class TestWriteSvg:
    def test_linked(
        self, css_source: str | os.PathLike[str], temp_filename: str | os.PathLike[str]
    ) -> None:
        """Insert stylesheet reference."""
        blank = etree.Element("blank")
        _ = write_svg(
            Path(temp_filename),
            blank,
            css_source,
            do_link_css=True,
            xml_declaration=True,
        )
        with Path(temp_filename).open("rb") as svg_binary:
            svg_lines = [x.decode() for x in svg_binary]

        relative_css_path = Path(css_source).relative_to(Path(temp_filename).parent)
        assert svg_lines == [
            "<?xml version='1.0' encoding='UTF-8'?>\n",
            '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n',
            '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n',
            f'<?xml-stylesheet href="{relative_css_path}" type="text/css"?>\n',
            "<blank/>\n",
        ]

    def test_not_linked(
        self, css_source: str | os.PathLike[str], temp_filename: str | os.PathLike[str]
    ) -> None:
        """Copy css_source contents into svg file."""
        blank = etree.Element("blank")
        _ = write_svg(Path(temp_filename), blank, css_source)
        with Path(temp_filename).open("rb") as svg_binary:
            svg_lines = [x.decode() for x in svg_binary]

        assert svg_lines == [
            "<blank>\n",
            '  <style type="text/css"><![CDATA[\n',
            "/** css for my project **/\n",
            "]]></style>\n",
            "</blank>\n",
        ]

    def test_css_none(self, temp_filename: str | os.PathLike[str]) -> None:
        """Do not link or copy in css if no css_source is passed."""
        blank = etree.Element("blank")
        _ = write_svg(Path(temp_filename), blank, do_link_css=True)
        with Path(temp_filename).open("rb") as svg_binary:
            svg_lines = [x.decode() for x in svg_binary]

        assert svg_lines == ["<blank/>\n"]

        # test with do_link_css = False
        _ = write_svg(Path(temp_filename), blank)
        with Path(temp_filename).open("rb") as svg_binary:
            svg_lines_false = [x.decode() for x in svg_binary]
        assert svg_lines_false == svg_lines


def svg_root(**kwargs: str | float) -> EtreeElement:
    """Create an svg root from attribute kwargs.

    :param kwargs: exact svg attribute names
    :return: a valid root to test against

    The process is this:
    * create a root here with explicit attributes
    * create a root with a function that infers explicit attributes
    * compare results
    """
    namespace = tuple(NSMAP.items())
    xmlns = [f'xmlns="{namespace[0][1]}"']
    xmlns += [f'xmlns:{k}="{v}"' for k, v in namespace[1:]]
    attributes = " ".join([f'{k}="{v}"' for k, v in kwargs.items()])
    return etree.fromstring(f"<svg {' '.join(xmlns)} {attributes}/>".encode())


class TestNewSvgRoot:
    def test_nsmap(self) -> None:
        """NSMAP passed by default and parseable by lxml."""
        result = new_svg_root()
        assert result.nsmap == NSMAP

    def test_args_pass(self) -> None:
        """Arguments and xmlns appear in element.

        Build the svg element namespace from NSMAP and compare to output
        """
        expect = svg_root(viewBox="0 1 2 3")
        result = new_svg_root(0, 1, 2, 3)
        assert result.attrib == expect.attrib

    def test_additional_params(self) -> None:
        """Pass additional params."""
        expect = svg_root(attr="value", viewBox="0 1 2 3")
        result = new_svg_root(0, 1, 2, 3, attr="value")
        assert result.attrib == expect.attrib

    def test_conflicting_params(self) -> None:
        """Explicit params overwrite trailing-underscore-inferred params."""
        expect = svg_root(viewBox="0 1 2 3", height="30")
        result = new_svg_root(0, 1, 2, 3, height=30)
        assert result.attrib == expect.attrib

    def test_new_svg_root_no_viewbox(self) -> None:
        """No viewBox when no trailing-underscore params."""
        expect = svg_root(width="14in", height="7in")
        result = new_svg_root(print_width_="14in", print_height_="7in")
        assert result.attrib == expect.attrib


class TestTostringKwargs:
    """Pass write_svg **kwargs to lxml.etree.tostring."""

    def test_no_args(self) -> None:
        """Svg content only when no tostring kwargs."""
        blank = etree.Element("blank")
        assert svg_tostring(blank) == b"<blank/>\n"

    def test_default(self) -> None:
        """Default params when xml_declaration is True."""
        blank = etree.Element("blank")
        assert svg_tostring(blank, xml_declaration=True).split(b"\n") == [
            b"<?xml version='1.0' encoding='UTF-8'?>",
            b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"',
            b'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">',
            b"<blank/>",
            b"",
        ]

    def test_override_doctype(self) -> None:
        """Override default params."""
        blank = etree.Element("blank")
        result = svg_tostring(blank, xml_declaration=True, doctype=None)
        assert result.split(b"\n") == [
            b"<?xml version='1.0' encoding='UTF-8'?>",
            b"<blank/>",
            b"",
        ]

    def test_override_encoding(self) -> None:
        """Default params when xml_declaration is True."""
        blank = etree.Element("blank")
        result = svg_tostring(blank, xml_declaration=True, encoding="ascii")
        assert result.split(b"\n") == [
            b"<?xml version='1.0' encoding='ascii'?>",
            b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"',
            b'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">',
            b"<blank/>",
            b"",
        ]


class TestReusePaths:
    """Test _reuse_paths moves path definitions to defs and replaces with use."""

    def test_creates_defs_and_replaces_paths_with_use(self) -> None:
        """Paths are moved to defs and replaced by use elements."""
        root = new_svg_root(0, 0, 100, 100)
        g = new_element("g")
        path_d = "M0 0 L10 10"
        p1 = new_element("path", d=path_d)
        p2 = new_element("path", d=path_d)
        g.append(p1)
        g.append(p2)
        root.append(g)
        _reuse_paths(root)
        defs = next((c for c in root if _local_tag(c) == "defs"), None)
        assert defs is not None
        path_defs = [c for c in defs if _local_tag(c) == "path"]
        assert len(path_defs) == 1
        assert path_defs[0].attrib.get("d") == path_d
        assert "id" in path_defs[0].attrib
        ref_id = path_defs[0].attrib["id"]
        use_elems = [c for c in g if _local_tag(c) == "use"]
        assert len(use_elems) == 2
        for use_elem in use_elems:
            assert use_elem.attrib.get("href") == f"#{ref_id}"

    def test_duplicate_path_reuses_same_id(self) -> None:
        """Two paths with same d get one def and two use elements with same href."""
        root = new_svg_root(0, 0, 100, 100)
        g = new_element("g")
        same_d = "M0 0 L5 5"
        g.append(new_element("path", d=same_d))
        g.append(new_element("path", d=same_d))
        root.append(g)
        _reuse_paths(root)
        defs = next((c for c in root if _local_tag(c) == "defs"), None)
        assert defs is not None
        path_defs = [c for c in defs if _local_tag(c) == "path"]
        assert len(path_defs) == 1
        ref_id = path_defs[0].attrib["id"]
        uses = [c for c in g if _local_tag(c) == "use"]
        assert len(uses) == 2
        assert all(u.attrib.get("href") == f"#{ref_id}" for u in uses)

    def test_empty_path_skipped(self) -> None:
        """Path with empty d is skipped and defs remains empty or removed."""
        root = new_svg_root(0, 0, 100, 100)
        g = new_element("g")
        g.append(new_element("path", d=""))
        root.append(g)
        _reuse_paths(root)
        defs_list = [c for c in root if _local_tag(c) == "defs"]
        if defs_list:
            assert len(list(defs_list[0])) == 0
