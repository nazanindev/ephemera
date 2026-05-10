from __future__ import annotations
import hashlib
import random
from app.models import Fragment, FragmentLayout, FragmentType

CANVAS_W = 1600
CANVAS_H = 2200

# Sparse-grid dimensions for even coverage
GRID_COLS = 8
GRID_ROWS = 11  # ~200px cells

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


def _sparse_position(rng: random.Random, placed_boxes: list[dict], width: int, height: int) -> tuple[float, float]:
    """Pick a canvas position biased toward areas with the fewest placed fragments."""
    cell_w = CANVAS_W / GRID_COLS
    cell_h = CANVAS_H / GRID_ROWS

    # Count fragment centers per cell
    coverage = [[0] * GRID_ROWS for _ in range(GRID_COLS)]
    for box in placed_boxes:
        ci = min(int((box["x"] + box["w"] / 2) / cell_w), GRID_COLS - 1)
        ri = min(int((box["y"] + box["h"] / 2) / cell_h), GRID_ROWS - 1)
        coverage[ci][ri] += 1

    min_cov = min(coverage[c][r] for c in range(GRID_COLS) for r in range(GRID_ROWS))
    sparse = [(c, r) for c in range(GRID_COLS) for r in range(GRID_ROWS)
              if coverage[c][r] == min_cov]

    c, r = rng.choice(sparse)
    x = c * cell_w + rng.uniform(0.0, max(0.0, cell_w - width * 0.5))
    y = r * cell_h + rng.uniform(0.0, max(0.0, cell_h - height * 0.5))
    x = max(0.0, min(x, CANVAS_W - width))
    y = max(0.0, min(y, CANVAS_H - height))
    return x, y


def compose_incremental(
    topic: str,
    new_fragments: list[Fragment],
    existing_fragments: list[Fragment],
) -> list[Fragment]:
    """Place new_fragments into gaps left by existing_fragments."""
    seed = _seed_from_topic(topic + "_enrich")
    rng = random.Random(seed)

    # Pre-populate placed_boxes from existing layouts
    placed_boxes: list[dict] = []
    for f in existing_fragments:
        if f.layout:
            placed_boxes.append({
                "x": f.layout.x,
                "y": f.layout.y,
                "w": f.layout.width,
                "h": f.layout.height,
            })

    priority = [f for f in new_fragments if f.type in (FragmentType.image, FragmentType.archive_screenshot)]
    rest = [f for f in new_fragments if f.type not in (FragmentType.image, FragmentType.archive_screenshot)]
    rng.shuffle(priority)
    rng.shuffle(rest)

    for frag in priority + rest:
        width = _pick_size(rng, frag.type)
        if frag.type in (FragmentType.image, FragmentType.archive_screenshot):
            width = min(width, MAX_IMAGE_WIDTH)
        height = int(width * rng.uniform(0.55, 1.2)) if frag.type in (
            FragmentType.image, FragmentType.archive_screenshot
        ) else int(width * rng.uniform(0.25, 0.7))

        rotation = _pick_rotation(rng, frag.type)
        z = _pick_z(rng, frag.type)
        css_filter, blend_mode = _pick_effects(rng, frag.type)

        x_px, y_px = _sparse_position(rng, placed_boxes, width, height)
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

    return priority + rest


def compose(topic: str, fragments: list[Fragment]) -> list[Fragment]:
    seed = _seed_from_topic(topic)
    rng = random.Random(seed)

    placed_boxes: list[dict] = []

    # Images/archive first for visual anchoring, then text
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

    for frag in ordered:
        is_repeat = frag.og.get("_repeat", False)
        width = _pick_size(rng, frag.type)
        if frag.type in (FragmentType.image, FragmentType.archive_screenshot):
            width = rng.randint(120, 240) if is_repeat else min(width, MAX_IMAGE_WIDTH)
        height = int(width * rng.uniform(0.55, 1.2)) if frag.type in (
            FragmentType.image, FragmentType.archive_screenshot
        ) else int(width * rng.uniform(0.25, 0.7))

        rotation = _pick_rotation(rng, frag.type)
        z = _pick_z(rng, frag.type)
        css_filter, blend_mode = _pick_effects(rng, frag.type)

        x_px, y_px = _sparse_position(rng, placed_boxes, width, height)
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
