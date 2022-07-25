import re
import xml.etree.ElementTree as ET
from io import BytesIO

import pygame
from cairosvg import svg2png
from PIL import Image

def get_namespace(element):
    m = re.match("\{.*\}", element.tag)
    return m.group(0) if m else ""


def svg2img(svg_path, colour, size):
    tree = ET.parse(svg_path)

    if colour:
        if isinstance(colour, list):
            if len(colour) != 3: # assume RGB
                raise ValueError("colour must be a list of 3 values")
            colour = "rgb({}, {}, {})".format(*colour)
        root = tree.getroot()
        namespace = get_namespace(root)
        for path in root.findall(f".//{namespace}path"):
            path.set("fill", colour)

    with BytesIO() as xml_buff, BytesIO() as png_buff:
        tree.write(xml_buff)
        xml_buff.seek(0)
        svg2png(
            xml_buff.read(),
            write_to=png_buff,
            output_width=size[0],
            output_height=size[1],
        )
        png_buff.seek(0)
        image = pygame.image.load(png_buff, "image.png").convert_alpha()
    return image


def svg2PIL(svg_path, colour, size):
    tree = ET.parse(svg_path)

    if colour:
        if isinstance(colour, list):
            if len(colour) != 3: # assume RGB
                raise ValueError("colour must be a list of 3 values")
            colour = "rgb({}, {}, {})".format(*colour)
        root = tree.getroot()
        namespace = get_namespace(root)
        for path in root.findall(f".//{namespace}path"):
            path.set("fill", colour)

    with BytesIO() as xml_buff, BytesIO() as png_buff:
        tree.write(xml_buff)
        xml_buff.seek(0)
        svg2png(
            xml_buff.read(),
            write_to=png_buff,
            output_width=size[0],
            output_height=size[1],
        )
        png_buff.seek(0)
        image = Image.open(png_buff)
        image.load()
    return image
