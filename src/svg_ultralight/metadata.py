"""Add metadata exactly as Inkscape formats it.

See https://paladini.github.io/dublin-core-basics/ for a description of the metadata
fields.

:author: Shay Hill
:created: 2024-01-29
"""

import warnings

from lxml.etree import _Element as EtreeElement  # pyright: ignore[reportPrivateUsage]

from svg_ultralight.constructors.new_element import new_element, new_sub_element
from svg_ultralight.nsmap import new_qname

_KNOWN_METADATA_FIELDS = {
    # tags in both Dublin Core and the Inkscape interface
    "title",
    "date",
    "creator",
    "rights",
    "publisher",
    "identifier",
    "source",
    "relation",
    "language",
    "coverage",
    "description",
    "contributor",
    # *almost* in both. This is "contributors" in the Inkscape interface. Output as
    # "contributor".
    "contributors",
    # tags in Dublin Core but not the Inkscape interface.
    "subject",
    "type",
    "format",
    # tags in the Inkscape interface but not Dublin Core
    "keywords",  # Inkscape alias for "subject". Will be subject in the output.
}


def _wrap_agent(title: str) -> EtreeElement:
    """Create nested elements for creator, rights, publisher, and contributors.

    :param title: The text to put in the nested element.
    :return: an agent element to be places in a dc:creator, dc:rights, dc:publisher,
        or dc:contributors element.

    This is the way Inkscape formats these fields.
    """
    agent = new_element(new_qname("cc", "Agent"))
    _ = new_sub_element(agent, new_qname("dc", "title"), text=title)
    return agent


def _wrap_bag(title: str) -> EtreeElement:
    """Create nested elements for keywords.

    :param title: The text to put in the nested element.
    :return: an agent element to be places in a dc:subject element.

    This is the way Inkscape formats these fields. Keywords are put in a subject
    element.
    """
    items = title.split(",")
    agent = new_element(new_qname("rdf", "Bag"))
    for title_item in items:
        _ = new_sub_element(agent, new_qname("rdf", "li"), text=title_item)
    return agent


def new_metadata(**kwargs: str) -> EtreeElement:
    """Return a new metadata string.

    :param kwargs: The metadata fields to include.

    This is the way Inkscape formats metadata. If you create a metadata element,
    svg_ultralight will create an empty `dc:title` element even if no title keyword
    is passed.

    The following keywords can be used without a warning:
    title, date, creator, rights, publisher, identifier, source, relation, language,
    coverage, description, contributor, contributors, subject, type, format, keywords.

    Only the keywords `keywords` and `subject` accept treat comma-delimited strings
    as multiple values. Every other value will be treated as a single string. You can
    pass other fields. They will be included as
    `<dc:other_field>value</dc:other_field>`.

    Will hardcode the id to "metadata1" because that's what Inkscape does. If that
    doesn't satisfy, replace id after description.
    """
    for tag in kwargs:
        if tag not in _KNOWN_METADATA_FIELDS:
            msg = f"Unknown metadata field: {tag}"
            warnings.warn(msg, stacklevel=2)

    metadata = new_element("metadata", id_="metadata1")
    rdf = new_sub_element(metadata, new_qname("rdf", "RDF"))
    work = new_sub_element(rdf, new_qname("cc", "Work"), **{"rdf:about": ""})

    _ = new_sub_element(work, new_qname("dc", "title"), text=kwargs.pop("title", ""))
    for k, v in kwargs.items():
        tag = k
        # aliases
        if tag == "contributors":
            tag = "contributor"
        elif tag == "subject":
            tag = "keywords"

        if tag in {"creator", "rights", "publisher", "contributor"}:
            elem = new_sub_element(work, new_qname("dc", tag))
            elem.append(_wrap_agent(v))
            continue
        if tag == "keywords":
            elem = new_sub_element(work, new_qname("dc", "subject"))
            elem.append(_wrap_bag(v))
            continue
        _ = new_sub_element(work, new_qname("dc", tag), text=v)

    return metadata
