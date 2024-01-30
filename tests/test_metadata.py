"""Test the metadata module.

:author: Shay Hill
:created: 2024-01-30
"""

from svg_ultralight.metadata import new_metadata
from svg_ultralight.main import new_svg_root
from lxml import etree

_inkscape_output = """
<metadata id="metadata1">
    <rdf:RDF>
        <cc:Work rdf:about="">
        <dc:title>TITLE</dc:title>
        <dc:date>DATE</dc:date>
        <dc:creator>
            <cc:Agent>
                <dc:title>CREATOR</dc:title>
            </cc:Agent>
        </dc:creator>
        <dc:rights>
            <cc:Agent>
                <dc:title>RIGHTS</dc:title>
            </cc:Agent>
        </dc:rights>
        <dc:publisher>
            <cc:Agent>
                <dc:title>PUBLISHER</dc:title>
            </cc:Agent>
        </dc:publisher>
        <dc:identifier>IDENTIFIER</dc:identifier>
        <dc:source>SOURCE</dc:source>
        <dc:relation>RELATION</dc:relation>
        <dc:language>LANGUAGE</dc:language>
        <dc:subject>
            <rdf:Bag>
                <rdf:li>KEY</rdf:li>
                <rdf:li>WORDS</rdf:li>
            </rdf:Bag>
        </dc:subject>
        <dc:coverage>COVERAGE</dc:coverage>
        <dc:description>DESCRIPTION</dc:description>
        <dc:contributor>
            <cc:Agent>
                <dc:title>CONTRIBUTORS</dc:title>
            </cc:Agent>
        </dc:contributor>
        </cc:Work>
    </rdf:RDF>
</metadata>
"""

_inkscape_output = "".join([x.strip() for x in _inkscape_output.splitlines()])

class TestMetedata:
    def test_inkscape_explicit(self):
        """Output matches Inkscape output.

        Wrap this is a root element or lxml will add namespace info to the metadata
        tag.
        """
        root = new_svg_root()
        metadata = new_metadata(
            title="TITLE",
            date="DATE",
            creator="CREATOR",
            rights="RIGHTS",
            publisher="PUBLISHER",
            identifier="IDENTIFIER",
            source="SOURCE",
            relation="RELATION",
            language="LANGUAGE",
            keywords="KEY,WORDS",
            coverage="COVERAGE",
            description="DESCRIPTION",
            contributors="CONTRIBUTORS",
        )
        root.append(metadata)
        assert _inkscape_output in etree.tostring(root).decode()

    def test_blank_title(self):
        """Title defaults to empty string."""
        root = new_svg_root()
        metadata = new_metadata()
        root.append(metadata)
        assert "<dc:title></dc:title>" in etree.tostring(root).decode()
