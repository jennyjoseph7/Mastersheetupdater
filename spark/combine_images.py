import argparse
import io
import os, sys
from PIL import Image
import cairosvg
from wand.image import Image as WandImage, Color
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from gryd_worker import gryd, gryd_helpers as hp
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
mlogger = hp.get_logger(__name__)
CAIROSVG_FONT_PATH = joinpath(BASE_DIR, "fonts")
if CAIROSVG_FONT_PATH not in os.environ.get("CAIROSVG_FONT_PATH", ""):
    os.environ["CAIROSVG_FONT_PATH"] = os.pathsep.join([CAIROSVG_FONT_PATH, os.environ.get("CAIROSVG_FONT_PATH", "")])
    mlogger.info(f"CAIROSVG_FONT_PATH set to: {os.environ['CAIROSVG_FONT_PATH']}")

DEFAULT_SCALE = 1.0
DEFAULT_X = 0
DEFAULT_Y = 0

DEFAULT_OUTPUT_PATH = joinpath(BASE_DIR, "output")


def parse_layer_args(args):
    """
    Parses variable-length layer arguments:
    PATH [SCALE] [X] [Y]
    """
    path = args[0]
    scale = float(args[1]) if len(args) > 1 else DEFAULT_SCALE
    x = int(args[2]) if len(args) > 2 else DEFAULT_X
    y = int(args[3]) if len(args) > 3 else DEFAULT_Y
    return path, scale, x, y


def load_png_layer(path, scale):
    img = Image.open(path).convert("RGBA")

    if scale != 1.0:
        w, h = img.size
        img = img.resize(
            (int(w * scale), int(h * scale)),
            Image.LANCZOS
        )

    return img


def load_svg_layer(path, scale, base_size):
    base_w, base_h = base_size
    
    svg_png_bytes = cairosvg.svg2png(
        url=path,
        output_width=int(base_w * scale),
        output_height=int(base_h * scale)
    )

    return Image.open(io.BytesIO(svg_png_bytes)).convert("RGBA")

def load_wand_layer(path, scale, base_size):
    base_w, base_h = base_size
    with open(path, "rb") as f:
        svg_data = f.read()
        with Color("transparent") as background:
            with WandImage(blob=svg_data, format="svg", background=background) as image:
                image.resize(int(base_w * scale), int(base_h * scale))
                png_image = image.make_blob("png")
                image = Image.open(io.BytesIO(png_image)).convert("RGBA")
                return image

def load_svg_lib_layer(path, scale, base_size):
    drawing = svg2rlg(path)
    base_w, base_h = base_size
    with io.BytesIO() as output:
        renderPM.drawToFile(drawing, output, fmt="PNG")
        #png_image = output.getvalue()
        ret_image = Image.open(output).convert("RGBA")
        ret_image = ret_image.resize((int(base_w * scale), int(base_h * scale)))
        return ret_image

def merge_layers(base_png: str, png_layers: list[tuple[str, float, int, int]] = None, svg_layers: list[tuple[str, float, int, int]] = None, output_path: str = None, logger: hp.logging.Logger = None):
    """
    Merge a base PNG image with multiple PNG and SVG overlay layers and
    save the result as a new PNG.

    Args:
        base_png: File path to the base PNG image. This image acts as the canvas
        onto which all other layers are composited.
        png_layers: A list of PNG overlay layer definitions. Each tuple must be in the form: (path, scale, x, y), (default: None)
        svg_layers: A list of SVG overlay layer definitions. Each tuple must be in the form: (path, scale, x, y), (default: None)
        output_path: File path where the merged PNG image will be written.
        logger: Logger to use for logging.
    Returns:
        None
        The merged image is written to `output_path`.

    """
    logger = logger or mlogger
    logger.info(f"Merging base image: {base_png} with PNG layers: {png_layers} and SVG layers: {svg_layers} into {output_path}")
    base_img = Image.open(base_png).convert("RGBA")
    base_size = base_img.size
    png_layers = png_layers or []
    svg_layers = svg_layers or []
    output_path = output_path or joinpath(DEFAULT_OUTPUT_PATH, f"{os.path.basename(base_png).split('.')[0]}_merged.png")

    def manage_layer(layer):
        if not isinstance(layer, tuple):
            layer = (layer, DEFAULT_SCALE, DEFAULT_X, DEFAULT_Y)
        if len(layer) >= 4:
            path, scale, x, y = layer[:4]
        elif len(layer) >= 2:
            path, scale = layer[:2]
            x, y = DEFAULT_X, DEFAULT_Y
        elif len(layer) == 1:
            path = layer[0]
            scale, x, y = DEFAULT_SCALE, DEFAULT_X, DEFAULT_Y
        else:
            raise ValueError(f"Invalid layer definition: {layer}")
        return path, scale, x, y

    for png_layer in png_layers:
        path, scale, x, y = manage_layer(png_layer)
        logger.info(f"Loading PNG layer: {path} with scale: {scale} and x: {x} and y: {y}")
        img = load_png_layer(path, scale)
        base_img.paste(img, (x, y), img)

    for svg_layer in svg_layers:
        path, scale, x, y = manage_layer(svg_layer)
        logger.info(f"Loading SVG layer: {path} with scale: {scale} and x: {x} and y: {y}")
        img = load_svg_layer(path, scale, base_size)
        base_img.paste(img, (x, y), img)

    base_img.save(output_path, format="PNG")
    logger.info(f"✅ Output written to {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="""
        Merge base PNG with multiple PNG and SVG overlays and save the result as a new PNG. e.g.
        python combine_images.py base.png --add-png layer1.png 1.0 0 0 --add-svg layer2.svg 1.0 0 0 -o output.png
        """
    )

    parser.add_argument("base", help="Base PNG image")

    parser.add_argument(
        "--add-png",
        action="append",
        nargs=4,
        metavar=("PATH", "SCALE", "X", "Y"),
        help="Add PNG overlay: path [scale] [x] [y]"
    )

    parser.add_argument(
        "--add-svg",
        action="append",
        nargs=4,
        metavar=("PATH", "SCALE", "X", "Y"),
        help="Add SVG overlay: path [scale] [x] [y]"
    )

    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output PNG file"
    )

    args = parser.parse_args()

    if not os.path.exists(args.base):
        raise FileNotFoundError(f"Base PNG not found: {args.base}")

    png_layers = []
    svg_layers = []

    if args.add_png:
        for layer_args in args.add_png:
            path, scale, x, y = parse_layer_args(layer_args)
            if not os.path.exists(path):
                raise FileNotFoundError(f"PNG layer not found: {path}")
            png_layers.append((path, scale, x, y))

    if args.add_svg:
        for layer_args in args.add_svg:
            path, scale, x, y = parse_layer_args(layer_args)
            if not os.path.exists(path):
                raise FileNotFoundError(f"SVG layer not found: {path}")
            svg_layers.append((path, scale, x, y))

    merge_layers(
        base_png=args.base,
        png_layers=png_layers,
        svg_layers=svg_layers,
        output_path=args.output
    )


if __name__ == "__main__":
    main()

