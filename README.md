# svg_writer 

The most straightforward way to create SVG files with Python.

## Three functions only:

    from svg_writer import new_svg_root, write_svg, write_png_from_svg

### new_svg_root
    x: float,
    y: float,
    width: float,
    height: float,
    pad: float = 0
    -> etree.Element

Create an svg root element from viewBox style arguments and provide the necessary svg-specific attributes. This is your window onto the scene. The arguments are the same you'd use to create a `rect` element (plus `pad`):
* `x`: x value in upper-left corner
* `y`: y value in upper-left corner
* `width`: width of viewBox
* `height`: height of viewBox
* `pad`: The one small convenience I've provided. Optionally increase viewBox by `pad` in all directions.


### write_svg
    filename: str,
    xml: etree.Element,
    stylesheet: Optional[str] = None,
    do_link_css: bool = True,
    -> None:

Write an xml element as an svg file. This will link or inline your css code and insert the necessary declaration, doctype, and processing instructions.

* `filename`: path to output file (include extension .svg)
* `param xml`: root node of your svg geometry (created by `new_svg_root`)
* `stylesheet`: optional path to a css stylesheet
* `do_link_css`: link to stylesheet, else write contents of stylesheet into svg (ignored if `stylesheet` is None)

### write_png_from_svg

    inkscape_exe: PathType,
    svg: str
    -> Path
    
Convert an svg file to a png. Python does not have a library for this. That has an upside, as any library would be one more set of svg implementation idiosyncrasies we'd have to deal with. Inkscape will convert the file. This function provides the necessary command-line arguments.

* `inkscape_exe`: path to inkscape.exe
* `svg`: path to svg file
* `return`: png filename

[Full Documentation and Tutorial](https://shayallenhill.com/svg-with-css-in-python/)