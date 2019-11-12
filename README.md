# svg_ultralight 

The most straightforward way to create SVG files with Python.

## Four functions only:

    from svg_ultralight import new_svg_root, write_svg, write_png_from_svg, write_png
    
## One convenience:

    from svg_ultralight import NSMAP

### new_svg_root
    x: float,
    y: float,
    width: float,
    height: float,
    pad: float = 0
    -> etree.Element

Create an svg root element from viewBox style arguments and provide the necessary svg-specific attributes and namespaces. This is your window onto the scene. The arguments are the same you'd use to create a `rect` element (plus `pad`):

See `namespaces` below.

* `x`: x value in upper-left corner
* `y`: y value in upper-left corner
* `width`: width of viewBox
* `height`: height of viewBox
* `pad`: The one small convenience I've provided. Optionally increase viewBox by `pad` in all directions.

### namespaces (svg_ultralight.NSMAP)

`new_svg_root` will create a root with several available namespaces.

* "dc": "http://purl.org/dc/elements/1.1/",
* "cc": "http://creativecommons.org/ns#",
* "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
* "svg": "http://www.w3.org/2000/svg",
* "xlink": "http://www.w3.org/1999/xlink",
* "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
* "inkscape": "http://www.inkscape.org/namespaces/inkscape",

I have made these available to you as `svg_ultralight.NSMAP`

### write_svg
    svg: str,
    xml: etree.Element,
    stylesheet: Optional[str] = None,
    do_link_css: bool = False,
    -> str:

Write an xml element as an svg file. This will link or inline your css code and insert the necessary declaration, doctype, and processing instructions.

* `svg`: path to output file (include extension .svg)
* `param xml`: root node of your svg geometry (created by `new_svg_root`)
* `stylesheet`: optional path to a css stylesheet
* `do_link_css`: link to stylesheet, else (default) write contents of stylesheet into svg (ignored if `stylesheet` is None)
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
* `effects`: creates png file at `png` (or infers png filename from `svg`)

### write_png

    inkscape_exe: str,
    png: str,
    xml: etree.Element,
    stylesheet: Optional[str] = None,
    
Create a png without writing an initial svg to your filesystem. This is not faster (it may be slightly slower), but it may be important when writing many images (animation frames) to your filesystem.
    
* `inkscape_exe`: path to inkscape.exe
* `png`: path to output file (include extension .png)
* `param xml`: root node of your svg geometry (created by `new_svg_root`)
* `stylesheet`: optional path to a css stylesheet
* `returns`: for convenience, returns png filename (`png`)
* `effects`: creates png file at `png`

[Full Documentation and Tutorial](https://shayallenhill.com/svg-with-css-in-python/)