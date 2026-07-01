import argparse
import base64
import glob
import io
import os, sys
from PIL import Image
import bs4

try:
    import cairosvg
except (ImportError, OSError) as e:
    cairosvg = None
from gryd_worker import gryd, gryd_helpers as hp
from os.path import dirname, abspath, join as joinpath

BASE_DIR = dirname(abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
mlogger = hp.get_logger(__name__)

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
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    return img


_FONT_DIRS = [
    "/usr/local/share/fonts",
    "/usr/share/fonts",
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    "/System/Library/Fonts",
]

# PostScript weight suffix → (font-weight value, fallback style if file not found)
_PS_WEIGHT = {
    "Black": ("900", None),
    "ExtraBold": ("800", None),
    "Bold": ("700", None),
    "SemiBold": ("600", None),
    "Medium": ("400", "Regular"),
    "Regular": ("400", None),
    "Light": ("300", None),
    "ExtraLight": ("200", None),
    "Thin": ("100", None),
}


def _find_font_file(family: str, style: str) -> str | None:
    for d in _FONT_DIRS:
        for stem in (f"{family} {style}", f"{family}-{style}"):
            for ext in (".ttf", ".otf"):
                hits = glob.glob(os.path.join(d, "**", f"{stem}{ext}"), recursive=True)
                if hits:
                    return hits[0]
    return None


def _embed_fonts_in_svg(svg_content: str) -> str:
    """Normalize PostScript font names and embed font files as @font-face."""
    soup = bs4.BeautifulSoup(svg_content, "xml")
    elements = soup.find_all(attrs={"font-family": True})
    mlogger.info(
        f"[font-embed] found {len(elements)} elements with font-family attribute"
    )

    face_rules = []
    seen = set()

    for el in elements:
        ff = (
            el["font-family"].strip("'\"").split(",")[0].strip()
        )  # take first in fallback list
        mlogger.info(f'[font-embed] element font-family="{ff}"')
        if "-" not in ff:
            continue
        family, suffix = ff.rsplit("-", 1)
        if suffix not in _PS_WEIGHT:
            mlogger.warning(
                f'[font-embed] unknown suffix "{suffix}" in "{ff}", skipping'
            )
            continue
        weight, fallback_style = _PS_WEIGHT[suffix]

        # Normalize element so fontconfig can resolve by family + weight
        el["font-family"] = family
        el["font-weight"] = weight
        mlogger.info(
            f'[font-embed] normalized "{ff}" → family="{family}" weight={weight}'
        )

        if ff in seen:
            continue
        seen.add(ff)

        font_file = _find_font_file(family, suffix) or (
            _find_font_file(family, fallback_style) if fallback_style else None
        )
        mlogger.info(f'[font-embed] font file for "{ff}": {font_file}')
        if not font_file:
            mlogger.warning(
                f'[font-embed] font file not found for "{ff}", skipping embed'
            )
            continue
        ext = os.path.splitext(font_file)[1].lower()
        mime, fmt = (
            ("font/ttf", "truetype") if ext == ".ttf" else ("font/otf", "opentype")
        )
        b64 = base64.b64encode(open(font_file, "rb").read()).decode("ascii")
        face_rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url('data:{mime};base64,{b64}')format('{fmt}');}}"
        )
        mlogger.info(f'[font-embed] embedded {font_file} as "{family}" weight={weight}')

    mlogger.info(f"[font-embed] total @font-face rules added: {len(face_rules)}")
    if face_rules:
        style_tag = soup.new_tag("style")
        style_tag.string = "\n".join(face_rules)
        soup.find("svg").insert(0, style_tag)

    return str(soup)


def load_svg_layer(path, scale, base_size, logger=None):
    if not cairosvg:
        raise ValueError("CairoSVG not loaded, cannot perform merge on this system")
    base_w, base_h = base_size

    with open(path, "r", encoding="utf-8") as f:
        svg_content = f.read()
    svg_content = _embed_fonts_in_svg(svg_content)

    svg_png_bytes = cairosvg.svg2png(bytestring=svg_content.encode("utf-8"))
    im = Image.open(io.BytesIO(svg_png_bytes)).convert("RGBA")
    imsize = im.size
    scale = scale * (base_w / imsize[0])
    (logger or mlogger).info(
        f"SVG layer {path}: base_size={base_size},raw_imsize={imsize}, "
    )
    svg_png_bytes = cairosvg.svg2png(
        bytestring=svg_content.encode("utf-8"),
        output_width=int(imsize[0] * scale),
        output_height=int(imsize[1] * scale),
    )
    svg_image = Image.open(io.BytesIO(svg_png_bytes)).convert("RGBA")
    (logger or mlogger).info(f"__svg_layer_path:{path}svg_image_size={svg_image.size}")
    return svg_image


def merge_layers(
    base_png: str,
    png_layers: list[tuple[str, float, int, int]] = None,
    svg_layers: list[tuple[str, float, int, int]] = None,
    output_path: str = None,
    logger: hp.logging.Logger = None,
):
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
    logger.info(
        f"Merging base image: {base_png} with PNG layers: {png_layers} and SVG layers: {svg_layers} into {output_path}"
    )
    base_img = Image.open(base_png).convert("RGBA")
    base_size = base_img.size
    print(f"__base_image_size{base_size}")
    png_layers = png_layers or []
    svg_layers = svg_layers or []
    output_path = output_path or joinpath(
        DEFAULT_OUTPUT_PATH, f"{os.path.basename(base_png).split('.')[0]}_merged.png"
    )

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
        return path, scale, int(x), int(y)

    for png_layer in png_layers:
        path, scale, x, y = manage_layer(png_layer)
        logger.info(
            f"Loading PNG layer: {path} with scale: {scale} and x: {x} and y: {y}"
        )
        img = load_png_layer(path, scale)
        base_img.paste(img, (x, y), img)

    for svg_layer in svg_layers:
        path, scale, x, y = manage_layer(svg_layer)
        logger.info(
            f"Loading SVG layer: {path} with scale: {scale} and x: {x} and y: {y}"
        )
        img = load_svg_layer(path, scale, base_size, logger=logger)
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
        help="Add PNG overlay: path [scale] [x] [y]",
    )

    parser.add_argument(
        "--add-svg",
        action="append",
        nargs=4,
        metavar=("PATH", "SCALE", "X", "Y"),
        help="Add SVG overlay: path [scale] [x] [y]",
    )

    parser.add_argument("-o", "--output", default=None, help="Output PNG file")

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
        output_path=args.output,
    )


# Below are the default PNG elements that are used to merge the PNG layers into the base PNG image.
DEFAULT_PNG_ELEMENTS = ["brand_logo", "dealership_logo", "qr_code"]
# Below are the default SVG elements that are used to merge the SVG layers into the base PNG image.
# URL, refers to the attribute in the template model that contains the URL of the SVG file.
# IDs, refers to the attribute in the template model that contains the IDs of the elements to be replaced in the SVG file.
# The values of the IDs are the attributes in the rooftop model that are used to replace the IDs in the SVG file.
DEFAULT_SVG_ELEMENTS = {
    "dealership_details": {
        "url": "dealership_details_url",
        "ids": {
            "dealership_address_id": "address",
            "dealership_phone_number_id": "contact_number",
            "dealership_email_id": "email",
        },
    },
    "offer_details": {
        "url": "offer_details_url",
        "ids": {
            "offer_currency_id": "offer_currency",
            "offer_amount_id": "offer_amount",
            "offer_units_id": "offer_units",
            "offer_terms_id": "offer_terms",
        },
    },
    "slogan": {
        "url": "slogan_url",
        "ids": {
            "slogan_1_id": "hook",
            "slogan_2_id": "slogan",
            "slogan_3_id": "message",
            "slogan_4_id": "hashtags",
            "slogan_5_id": "caption",
        },
    },
}
DEFAULT_OFFER = {
    "offer_currency": "₹            ",
    "offer_amount": "10.55",
    "offer_units": "           Lakh",
    "offer_terms": "*Valid for limited time only",
}
DEFAULT_CAMPAIGN_DETAILS = {
    "slogan": "Limited Time Offer",
    "hook": "Save Big on Your Next Purchase",
    "message": "Don't miss out on this limited time offer. Act now to get the best price on your next purchase.",
    "hashtags": "#LimitedTimeOffer #SaveBig #ActNow",
    "caption": "Limited Time Offer: Save Big on Your Next Purchase",
}
DEFAULT_TEMPLATE_ID = "default"


def replace_svg_text_by_id(
    svg_path: str, text_to_ids: dict, logger: hp.logging.Logger = None
):
    logger = logger or mlogger
    with open(svg_path, "r") as f:
        soup = bs4.BeautifulSoup(f, "xml")
    for id_, text_to_replace in text_to_ids.items():
        logger.debug(
            f"Replacing text {text_to_replace} with id {id_} in SVG file {svg_path}"
        )
        try:
            text_to_replace = str(text_to_replace)
        except Exception as e:
            logger.error(
                f"Error converting text to string: {e} for input: {text_to_replace} in id: {id_} in SVG file {svg_path}"
            )
            text_to_replace = ""
        if isinstance(text_to_replace, str):
            text_to_replace = text_to_replace.strip()
        else:
            text_to_replace = ""
        el = soup.find(id=id_)
        if not el:
            el = soup.find(attrs={"data-name": id_})
        if el:
            while len(list(el.children)) > 0:
                cel = list(el.children)[0]
                if cel.name:
                    el = cel
                    continue
                break
            el.string = text_to_replace
        else:
            logger.warning(f"Element with id {id_} not found in SVG file {svg_path}")
    with open(svg_path, "w") as f:
        f.write(soup.prettify())
    return svg_path


if __name__ == "__main__":
    main()
