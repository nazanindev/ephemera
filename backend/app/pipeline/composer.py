from __future__ import annotations
import hashlib
import random
from app.models import Fragment, FragmentLayout, FragmentType

CANVAS_W = 1800
CANVAS_H = 1200

# 3×2 zone grid — interleaved top/bottom so images scatter across full canvas
ZONES = [
    (0.0,  0.0,  0.33, 0.5),   # top-left
    (0.0,  0.5,  0.33, 1.0),   # bottom-left
    (0.33, 0.0,  0.66, 0.5),   # top-center
    (0.33, 0.5,  0.66, 1.0),   # bottom-center
    (0.66, 0.0,  1.0,  0.5),   # top-right
    (0.66, 0.5,  1.0,  1.0),   # bottom-right
]

MAX_IMAGE_WIDTH = 700  # px — prevents one image from dominating

SIZE_BUCKETS = {
    "small": (120, 220),
    "medium": (250, 450),
    "large": (480, 750),
}

ROTATION_POOL = [-18, -12, -8, -4, -2, 0, 2, 4, 8, 12, 18]
ROTATION_WEIGHTS = [1, 2, 3, 5, 7, 4, 7, 5, 3, 2, 1]

IMAGE_FILTERS = [
    "",
    "",
    "",
    "sepia(0.25)",
    "contrast(1.3) saturate(1.15)",
    "contrast(1.2) saturate(0.85)",
    "contrast(1.4) brightness(0.92)",
]
IMAGE_BLENDS = ["normal", "normal", "normal", "multiply", "multiply"]

ARCHIVE_FILTERS = [
    "sepia(0.5) contrast(1.15)",
    "sepia(0.3) contrast(1.1)",
    "contrast(1.2) brightness(0.9)",
]
ARCHIVE_BLENDS = ["multiply", "multiply", "normal"]

TEXT_FILTERS = ["", "", "opacity(0.88)"]
TEXT_BLENDS = ["normal", "normal", "multiply"]


def _seed_from_topic(topic: str) -> int:
    return int(hashlib.md5(topic.encode()).hexdigest(), 16) % (2 ** 32)


def _pick_size(rng: random.Random, ftype: FragmentType) -> int:
    if ftype == FragmentType.metadata:
        return rng.randint(80, 160)
    if ftype in (FragmentType.headline, FragmentType.snippet):
        return rng.randint(200, 400)

    # image / archive: bias toward medium/large, hard cap applied in compose()
    roll = rng.random()
    if roll < 0.15:
        lo, hi = SIZE_BUCKETS["small"]
    elif roll < 0.65:
        lo, hi = SIZE_BUCKETS["medium"]
    else:
        lo, hi = SIZE_BUCKETS["large"]
    return rng.randint(lo, hi)


def _pick_rotation(rng: random.Random, ftype: FragmentType) -> float:
    if ftype == FragmentType.metadata:
        # metadata gets extreme rotations
        return rng.choice([-18, -12, 12, 18, -8, 8])
    return rng.choices(ROTATION_POOL, weights=ROTATION_WEIGHTS, k=1)[0]


def _pick_z(rng: random.Random, ftype: FragmentType) -> int:
    if ftype in (FragmentType.image, FragmentType.archive_screenshot):
        return rng.randint(1, 20)
    if ftype in (FragmentType.headline, FragmentType.snippet):
        return rng.randint(15, 35)
    return rng.randint(30, 50)  # metadata always on top


def _pick_effects(rng: random.Random, ftype: FragmentType) -> tuple[str, str]:
    if ftype == FragmentType.image:
        return rng.choice(IMAGE_FILTERS), rng.choice(IMAGE_BLENDS)
    if ftype == FragmentType.archive_screenshot:
        return rng.choice(ARCHIVE_FILTERS), rng.choice(ARCHIVE_BLENDS)
    if ftype in (FragmentType.headline, FragmentType.snippet, FragmentType.metadata):
        return rng.choice(TEXT_FILTERS), rng.choice(TEXT_BLENDS)
    return "", "normal"


def _overlap_fraction(a: dict, b: dict) -> float:
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = ax1 + a["w"], ay1 + a["h"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = bx1 + b["w"], by1 + b["h"]

    ix = max(0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0, min(ay2, by2) - max(ay1, by1))
    intersection = ix * iy
    area_a = (ax2 - ax1) * (ay2 - ay1)
    if area_a == 0:
        return 0.0
    return intersection / area_a


def compose(topic: str, fragments: list[Fragment]) -> list[Fragment]:
    seed = _seed_from_topic(topic)
    rng = random.Random(seed)

    placed_boxes: list[dict] = []
    zone_filled = [False] * len(ZONES)

    # Shuffle fragments but keep images/archive first for visual anchoring
    priority = [f for f in fragments if f.type in (FragmentType.image, FragmentType.archive_screenshot)]
    rest = [f for f in fragments if f.type not in (FragmentType.image, FragmentType.archive_screenshot)]
    rng.shuffle(priority)
    rng.shuffle(rest)

    # Repeat 1–2 anchor images as smaller echoes (photocopied motif)
    import copy
    repeats = []
    if len(priority) >= 2:
        n_repeats = rng.randint(1, min(2, len(priority) - 1))
        for i in range(n_repeats):
            r = copy.deepcopy(priority[i])
            r.og = {**r.og, "_repeat": True}
            repeats.append(r)

    ordered = priority + rest + repeats

    for i, frag in enumerate(ordered):
        is_repeat = frag.og.get("_repeat", False)
        width = _pick_size(rng, frag.type)
        if frag.type in (FragmentType.image, FragmentType.archive_screenshot):
            if is_repeat:
                width = rng.randint(120, 240)  # echo: deliberately small
            else:
                width = min(width, MAX_IMAGE_WIDTH)
        height = int(width * rng.uniform(0.55, 1.2)) if frag.type in (
            FragmentType.image, FragmentType.archive_screenshot
        ) else int(width * rng.uniform(0.25, 0.7))

        rotation = _pick_rotation(rng, frag.type)
        z = _pick_z(rng, frag.type)
        css_filter, blend_mode = _pick_effects(rng, frag.type)

        # Try to fill an empty zone first
        x_frac, y_frac = None, None
        for zi, zone in enumerate(ZONES):
            if not zone_filled[zi]:
                zx1, zy1, zx2, zy2 = zone
                x_frac = rng.uniform(zx1, max(zx1, zx2 - width / CANVAS_W))
                y_frac = rng.uniform(zy1, max(zy1, zy2 - height / CANVAS_H))
                zone_filled[zi] = True
                break

        if x_frac is None:
            # Free placement — try up to 5 positions, nudge if too crowded
            for attempt in range(5):
                x_frac = rng.uniform(0.0, max(0.01, 1.0 - width / CANVAS_W))
                y_frac = rng.uniform(0.0, max(0.01, 1.0 - height / CANVAS_H))
                box = {"x": x_frac * CANVAS_W, "y": y_frac * CANVAS_H, "w": width, "h": height}
                heavy_overlaps = sum(
                    1 for pb in placed_boxes if _overlap_fraction(box, pb) > 0.4
                )
                if heavy_overlaps < 3:
                    break
                # Nudge 10% toward canvas center
                x_frac = x_frac * 0.9 + 0.05
                y_frac = y_frac * 0.9 + 0.05

        x_px = x_frac * CANVAS_W
        y_px = y_frac * CANVAS_H

        placed_boxes.append({"x": x_px, "y": y_px, "w": width, "h": height})

        frag.layout = FragmentLayout(
            x=round(x_px, 2),
            y=round(y_px, 2),
            width=width,
            height=height,
            rotation=rotation,
            z_index=z,
            css_filter=css_filter,
            blend_mode=blend_mode,
        )

    return ordered
