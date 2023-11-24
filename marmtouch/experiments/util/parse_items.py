import math


def transform_location(loc, transform, invert=False):
    if invert:
        in_label, out_label = "OUT_RECT", "IN_RECT"
    else:
        in_label, out_label = "IN_RECT", "OUT_RECT"
    x, y = loc
    theta = math.radians(transform["rotation"])
    rx = math.cos(theta) * x - math.sin(theta) * y
    ry = math.sin(theta) * x + math.cos(theta) * y
    normx = (rx - transform[in_label]["l"]) / transform[in_label]["w"]
    normy = (ry - transform[in_label]["b"]) / transform[in_label]["h"]
    screenx = (normx * transform[out_label]["w"]) + transform[out_label]["l"]
    screeny = (normy * transform[out_label]["h"]) + transform[out_label]["b"]
    return screenx, screeny


def parse_item(params, transform=None):
    if transform is None:
        return params

    if "loc" in params:
        params["loc"] = transform_location(params["loc"], transform)
    if "radius" in params:
        params["radius"] = (
            params["radius"] * transform["OUT_RECT"]["w"] / transform["IN_RECT"]["w"]
        )
    if "window" in params:
        params["window"] = (
            params["window"][0]
            * transform["OUT_RECT"]["w"]
            / transform["IN_RECT"]["w"],
            params["window"][1]
            * transform["OUT_RECT"]["h"]
            / transform["IN_RECT"]["h"],
        )
    return params


def parse_items(items, transform=None):
    """
    Parse the items from config.
    """
    if transform is None:
        return items
    parsed_items = {}
    for k, v in items.items():
        parsed_items[k] = parse_item(v, transform)
    return parsed_items
