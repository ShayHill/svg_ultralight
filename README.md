# svg_ultralight

The most straightforward way to create SVG files with Python.

## Four principal functions:

    from svg_ultralight import new_svg_root, write_svg, write_png_from_svg, write_png

## One convenience:

    from svg_ultralight import NSMAP

### new_svg_root
    x_: Optional[float],
    y_: Optional[float],
    width_: Optional[float],
    height_: Optional[float],
    pad_: float = 0
    dpu_: float = 1
    nsmap: Optional[Dict[str, str]] = None (svg_ultralight.NSMAP if None)
    **attributes: Union[float, str],
    -> etree.Element

Create an svg root element from viewBox style arguments and provide the necessary svg-specific attributes and namespaces. This is your window onto the scene.

Three ways to call:

1. The trailing-underscore arguments are the same you'd use to create a `rect` element (plus `pad_` and `dpu_`).  `new_svg_root` will infer `viewBox`, `width`, and `height` svg attributes from these values.
2. Use the svg attributes you already know: `viewBox`, `width`, `height`, etc. These will be written to the xml file.
3. Of course, you can combine 1. and 2. if you know what you're doing.

See `namespaces` below.

* `x_`: x value in upper-left corner
* `y_`: y value in upper-left corner
* `width_`: width of viewBox
* `height_`: height of viewBox
* `pad_`: the one small convenience I've provided. Optionally increase viewBox by `pad` in all directions.
* `dpu_`: pixels per viewBox unit for output png images.
* `nsmap`: namespaces. (defaults to svg_ultralight.NSMAP). Available as an argument should you wish to add additional namespaces. To do this, add items to NSMAP then call with `nsmap=NSMAP`.
* `**attributes`: the trailing-underscore arguments are an *optional* shortcut for creating a scene. The entire svg interface is available to you through kwargs. See `A few helpers` below for details on attribute-name translation between Python and xml (the short version: `this_name` becomes `this-name` and `this_` becomes `this`)

### namespaces (svg_ultralight.NSMAP)

`new_svg_root` will create a root with several available namespaces.

* `"dc": "http://purl.org/dc/elements/1.1/"`
* `"cc": "http://creativecommons.org/ns#"`
* `"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"`
* `"svg": "http://www.w3.org/2000/svg"`
* `"xlink": "http://www.w3.org/1999/xlink"`
* `"sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"`
* `"inkscape": "http://www.inkscape.org/namespaces/inkscape"`

I have made these available to you as `svg_ultralight.NSMAP`

### write_svg
    svg: str,
    xml: etree.Element,
    stylesheet: Optional[str] = None,
    do_link_css: bool = False,
    **tostring_kwargs,
    -> str:

Write an xml element as an svg file. This will link or inline your css code and insert the necessary declaration, doctype, and processing instructions.

* `svg`: path to output file (include extension .svg)
* `param xml`: root node of your svg geometry (created by `new_svg_root`)
* `stylesheet`: optional path to a css stylesheet
* `do_link_css`: link to stylesheet, else (default) write contents of stylesheet into svg (ignored if `stylesheet` is None). If you have a stylesheet somewhere, the default action is to dump the entire contents into your svg file. Linking to the stylesheet is more elegant, but inlining *always* works.
* `**tostring_kwargs`: optional kwarg arguments for `lxml.etree.tostring`. Passing `xml_declaration=True` by itself will create an xml declaration with encoding set to UTF-8 and an svg DOCTYPE. These defaults can be overridden with keyword arguments `encoding` and `doctype`. If you don't know what this is, you can probably get away without it.
* `returns`: for convenience, returns svg filename (`svg`)
* `effects`: creates svg file at `svg`

### write_png_from_svg

    inkscape_exe: str,
    svg: str
    png: Optional[str]
    -> str

Convert an svg file to a png. Python does not have a library for this. That has an upside, as any library would be one more set of svg implementation idiosyncrasies we'd have to deal with. Inkscape will convert the file. This function provides the necessary command-line arguments.

* `inkscape_exe`: path to inkscape.exe
* `svg`: path to svg file
* `png`: optional path to png output (if not given, png name will be inferred from `svg`: `'name.svg'` becomes `'name.png'`)
* `return`: png filename
* `effects`: creates png file at `png` (or infers png path and filename from `svg`)

### write_png

    inkscape_exe: str,
    png: str,
    xml: etree.Element,
    stylesheet: Optional[str] = None
    -> str

Create a png without writing an initial svg to your filesystem. This is not faster (it may be slightly slower), but it may be important when writing many images (animation frames) to your filesystem.

* `inkscape_exe`: path to inkscape.exe
* `png`: path to output file (include extension .png)
* `param xml`: root node of your svg geometry (created by `new_svg_root`)
* `stylesheet`: optional path to a css stylesheet
* `returns`: for convenience, returns png filename (`png`)
* `effects`: creates png file at `png`

## A few helpers:

    from svg_ultralight.constructors import new_element, new_sub_element

I do want to keep this ultralight and avoid creating some pseudo scripting language between Python and lxml, but here are two very simple, very optional functions to save your having to `str()` every argument to `etree.Element`.

### constructors.new_element

    tag: str
    **params: Union[str, float]
    -> etree.Element

Python allows underscores in variable names; xml uses dashes.

Python understands numbers; xml wants strings.

This is a convenience function to swap `"_"` for `"-"` and `10.2` for `"10.2"` before creating an xml element.

Translates numbers to strings

    >>> elem = new_element('line', x1=0, y1=0, x2=5, y2=5)
    >>> etree.tostring(elem)
    b'<line x1="0" y1="0" x2="5" y2="5"/>'

Translates underscores to hyphens

    >>> elem = new_element('line', stroke_width=1)
    >>> etree.tostring(elem)
    b'<line stroke-width="1"/>'

Removes trailing underscores. You'll almost certainly want to use reserved names like ``class`` as svg parameters. This
can be done by passing the name with a trailing underscore.

    >>> elem = new_element('line', class_='thick_line')
    >>> etree.tostring(elem)
    b'<line class="thick_line"/>'

Special handling for a 'text' argument. Places value between element tags.

    >>> elem = new_element('text', text='please star my project')
    >>> etree.tostring(elem)
    b'<text>please star my project</text>'

### constructors.new_sub_element

    parent: etree.Element
    tag: str
    **params: Union[str, float]
    -> etree.Element

As above, but creates a subelement.

    >>> parent = etree.Element('g')
    >>> _ = new_sub_element('rect')
    >>> etree.tostring(parent)
    b'<g><rect/></g>'

### update_element

Another way to add params through the new_element name / float translator. Again unnecessary, but potentially helpful. Easily understood from the code or docstrings.

## Extras:

### query.map_elems_to_bounding_boxes

Python cannot parse an svg file. Python can *create* an svg file, and Inkscape can parse (and inspect) it. Inkscape has a command-line interface capable of reading an svg file and returning some limited information. This is the only way I know for a Python program to:

1. create an svg file (optionally without writing to filesystem)
2. query the svg file for bounding-box information
3. create an adjusted svg file.

This would be necessary for, e.g., algorithmically fitting text in a box.

    from svg_ultralight.queries import map_elems_to_bounding_boxes

You can get a tiny bit more sophisticated with Inkscape bounding-box queries, but not much. This will give you pretty much all you can get out of it.

### animate.write_gif

Create an animated gif from a sequence of png filenames. This is a Pillow one-liner, but it's convenient for me to have it, so it might be convenient for you. Requires pillow, which is not a project dependency.

    from svg_ultralight.animate import write_gif

[Full Documentation and Tutorial](https://shayallenhill.com/svg-with-css-in-python/)
