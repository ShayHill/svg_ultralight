"""xml namespace entries for svg files.

:author: Shay Hill
:created: 1/14/2021

I started by copying out entries from Inkscape output. Added more as I found them
necessary. This is a pretty robust list. Can be pared down as documented at
https://shayallenhill.com/svg-with-css-in-python/
"""

_SVG_NAMESPACE = "http://www.w3.org/2000/svg"
NSMAP = {
    None: _SVG_NAMESPACE,
    "dc": "http://purl.org/dc/elements/1.1/",
    "cc": "http://creativecommons.org/ns#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "svg": _SVG_NAMESPACE,
    "xlink": "http://www.w3.org/1999/xlink",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
    "inkscape": "http://www.inkscape.org/namespaces/inkscape",
}
