from __future__ import annotations
import copy
import hashlib
import random
from dataclasses import dataclass
from app.models import Fragment, FragmentLayout, FragmentType

CANVAS_W = 1600
CANVAS_H = 2200

GRID_COLS = 8
GRID_ROWS = 11

SIZE_BUCKETS = {
    "small": (90, 240),
    "medium": (200, 480),
    "large": (380, 1100),
}

ROTATION_POOL = [-18, -12, -8, -4, -2, 0, 2, 4, 8, 12, 18]
ROTATION_WEIGHTS = [1, 2, 3, 5, 7, 4, 7, 5, 3, 2, 1]

IMAGE_FILTERS = [
    "", "", "",
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
TEXT_COLORS = ["#ffffff", "#ffffff", "#ffffff", "#f5e6d3", "#f5e6d3", "#ffd700", "#ffffff", "#1a1208"]

_TEXT_TYPES = {FragmentType.headline, FragmentType.snippet, FragmentType.metadata}
_IMAGE_TYPES = {FragmentType.image, FragmentType.archive_screenshot}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@dataclass
class _VibeParams:
    overlap_threshold: float
    image_margin: int
    placement_attempts: int
    max_image_width: int
    large_prob: float
    small_prob: float
    max_rotation: int
    spread_bias: float  # exponent on distance-from-centroid weighting; higher = more spread


def _make_vibe_params(vibe: float) -> _VibeParams:
    return _VibeParams(
        overlap_threshold=_lerp(0.04, 0.25, vibe),
        image_margin=int(_lerp(60, 8, vibe)),
        placement_attempts=int(_lerp(25, 12, vibe)),
        max_image_width=int(_lerp(420, 1100, vibe)),
        large_prob=_lerp(0.08, 0.40, vibe),
        small_prob=_lerp(0.35, 0.10, vibe),
        max_rotation=int(_lerp(8, 18, vibe)),
        spread_bias=_lerp(3.0, 0.5, vibe),
    )


def _seed_from_topic(topic: str) -> int:
    return int(hashlib.md5(topic.encode()).hexdigest(), 16) % (2 ** 32)


def _pick_size(rng: random.Random, ftype: FragmentType, params: _VibeParams) -> int:
    if ftype == FragmentType.metadata:
        return rng.randint(80, 160)
    if ftype in (FragmentType.headline, FragmentType.snippet):
        return rng.randint(200, 400)

    roll = rng.random()
    if roll < params.small_prob:
        lo, hi = SIZE_BUCKETS["small"]
    elif roll < 1.0 - params.large_prob:
        lo, hi = SIZE_BUCKETS["medium"]
    else:
        lo, hi = SIZE_BUCKETS["large"]
    hi = min(hi, params.max_image_width)
    lo = min(lo, hi)
    return rng.randint(lo, hi)


def _pick_rotation(rng: random.Random, ftype: FragmentType, max_rot: int) -> float:
    if ftype == FragmentType.metadata:
        opts = [r for r in [-18, -12, -8, 8, 12, 18] if abs(r) <= max_rot]
        return rng.choice(opts) if opts else 0
    pw = [(r, w) for r, w in zip(ROTATION_POOL, ROTATION_WEIGHTS) if abs(r) <= max_rot]
    if not pw:
        return 0
    pool, weights = zip(*pw)
    return rng.choices(pool, weights=weights, k=1)[0]


def _pick_z(rng: random.Random, ftype: FragmentType) -> int:
    if ftype in _IMAGE_TYPES:
        return rng.randint(1, 20)
    if ftype in (FragmentType.headline, FragmentType.snippet):
        return rng.randint(15, 35)
    return rng.randint(30, 50)


def _pick_text_color(rng: random.Random, ftype: FragmentType) -> str:
    if ftype not in _TEXT_TYPES:
        return ""
    return rng.choice(TEXT_COLORS)


def _pick_effects(rng: random.Random, ftype: FragmentType) -> tuple[str, str]:
    if ftype == FragmentType.image:
        return rng.choice(IMAGE_FILTERS), rng.choice(IMAGE_BLENDS)
    if ftype == FragmentType.archive_screenshot:
        return rng.choice(ARCHIVE_FILTERS), rng.choice(ARCHIVE_BLENDS)
    if ftype in _TEXT_TYPES:
        return rng.choice(TEXT_FILTERS), rng.choice(TEXT_BLENDS)
    return "", "normal"


def _sparse_position(
    rng: random.Random,
    placed_boxes: list[dict],
    width: int,
    height: int,
    spread_bias: float = 1.0,
) -> tuple[float, float]:
    cell_w = CANVAS_W / GRID_COLS
    cell_h = CANVAS_H / GRID_ROWS

    coverage = [[0] * GRID_ROWS for _ in range(GRID_COLS)]
    for box in placed_boxes:
        c1 = max(0, int(box["x"] / cell_w))
        r1 = max(0, int(box["y"] / cell_h))
        c2 = min(GRID_COLS - 1, int((box["x"] + box["w"]) / cell_w))
        r2 = min(GRID_ROWS - 1, int((box["y"] + box["h"]) / cell_h))
        for ci in range(c1, c2 + 1):
            for ri in range(r1, r2 + 1):
                coverage[ci][ri] += 1

    min_cov = min(coverage[c][r] for c in range(GRID_COLS) for r in range(GRID_ROWS))
    sparse = [(c, r) for c in range(GRID_COLS) for r in range(GRID_ROWS)
              if coverage[c][r] == min_cov]

    if placed_boxes and len(sparse) > 1:
        cxc = sum(b["x"] + b["w"] / 2 for b in placed_boxes) / len(placed_boxes)
        cyc = sum(b["y"] + b["h"] / 2 for b in placed_boxes) / len(placed_boxes)
        weights = [
            max(((sc + 0.5) * cell_w - cxc) ** 2 + ((sr + 0.5) * cell_h - cyc) ** 2, 1.0) ** (spread_bias / 2)
            for sc, sr in sparse
        ]
        c, r = rng.choices(sparse, weights=weights, k=1)[0]
    else:
        c, r = rng.choice(sparse)

    x = c * cell_w + rng.uniform(0.0, max(0.0, cell_w - width * 0.5))
    y = r * cell_h + rng.uniform(0.0, max(0.0, cell_h - height * 0.5))
    x = max(0.0, min(x, CANVAS_W - width))
    y = max(0.0, min(y, CANVAS_H - height))
    return x, y


def _image_overlap_score(x: float, y: float, w: int, h: int, placed_boxes: list[dict], margin: int) -> float:
    m = margin
    ax1, ay1, ax2, ay2 = x - m, y - m, x + w + m, y + h + m
    worst = 0.0
    for box in placed_boxes:
        if not box.get("is_image"):
            continue
        bx1, by1 = box["x"] - m, box["y"] - m
        bx2, by2 = box["x"] + box["w"] + m, box["y"] + box["h"] + m
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            continue
        intersection = (ix2 - ix1) * (iy2 - iy1)
        smaller = min((w + 2 * m) * (h + 2 * m), (box["w"] + 2 * m) * (box["h"] + 2 * m))
        if smaller > 0:
            worst = max(worst, intersection / smaller)
    return worst


def _place_fragment(
    rng: random.Random,
    placed_boxes: list[dict],
    width: int,
    height: int,
    is_image: bool,
    params: _VibeParams,
) -> tuple[float, float]:
    if not is_image:
        return _sparse_position(rng, placed_boxes, width, height, params.spread_bias)

    best_pos = None
    best_score = 1.1
    for _ in range(params.placement_attempts):
        cx, cy = _sparse_position(rng, placed_boxes, width, height, params.spread_bias)
        score = _image_overlap_score(cx, cy, width, height, placed_boxes, params.image_margin)
        if score < best_score:
            best_score = score
            best_pos = (cx, cy)
        if best_score < params.overlap_threshold:
            break
    return best_pos  # type: ignore[return-value]


def _layout_fragment(
    rng: random.Random,
    frag: Fragment,
    placed_boxes: list[dict],
    params: _VibeParams,
    is_repeat: bool = False,
) -> None:
    width = _pick_size(rng, frag.type, params)
    if frag.type in _IMAGE_TYPES:
        width = rng.randint(120, 240) if is_repeat else min(width, params.max_image_width)
    height = int(width * rng.uniform(0.55, 1.2)) if frag.type in _IMAGE_TYPES \
        else int(width * rng.uniform(0.25, 0.7))

    rotation = _pick_rotation(rng, frag.type, params.max_rotation)
    z = _pick_z(rng, frag.type)
    css_filter, blend_mode = _pick_effects(rng, frag.type)
    text_color = _pick_text_color(rng, frag.type)

    is_image = frag.type in _IMAGE_TYPES and not is_repeat
    x_px, y_px = _place_fragment(rng, placed_boxes, width, height, is_image, params)
    placed_boxes.append({"x": x_px, "y": y_px, "w": width, "h": height, "is_image": is_image})

    frag.layout = FragmentLayout(
        x=round(x_px, 2),
        y=round(y_px, 2),
        width=width,
        height=height,
        rotation=rotation,
        z_index=z,
        css_filter=css_filter,
        blend_mode=blend_mode,
        text_color=text_color,
    )


def compose(topic: str, fragments: list[Fragment], vibe: float = 0.5, density: str | None = None, layout_seed: int | None = None) -> list[Fragment]:
    seed = _seed_from_topic(topic) ^ (layout_seed if layout_seed is not None else 0)
    rng = random.Random(seed)
    params = _make_vibe_params(vibe)

    placed_boxes: list[dict] = []

    priority = [f for f in fragments if f.type in _IMAGE_TYPES]
    rest = [f for f in fragments if f.type not in _IMAGE_TYPES]
    rng.shuffle(priority)
    rng.shuffle(rest)

    repeats = []
    if len(priority) >= 2:
        max_repeats = 10 if density == "dense" else 2
        n_repeats = rng.randint(1, min(max_repeats, len(priority) - 1))
        for i in range(n_repeats):
            r = copy.deepcopy(priority[i % len(priority)])
            r.og = {**r.og, "_repeat": True}
            repeats.append(r)

    ordered = priority + rest + repeats
    for frag in ordered:
        _layout_fragment(rng, frag, placed_boxes, params, is_repeat=frag.og.get("_repeat", False))

    return ordered


def compose_incremental(
    topic: str,
    new_fragments: list[Fragment],
    existing_fragments: list[Fragment],
    vibe: float = 0.5,
    density: str | None = None,
    layout_seed: int | None = None,
) -> list[Fragment]:
    seed = _seed_from_topic(topic + "_enrich") ^ (layout_seed if layout_seed is not None else 0)
    rng = random.Random(seed)
    params = _make_vibe_params(vibe)

    placed_boxes: list[dict] = []
    for f in existing_fragments:
        if f.layout:
            is_img = f.type in _IMAGE_TYPES
            placed_boxes.append({
                "x": f.layout.x,
                "y": f.layout.y,
                "w": f.layout.width,
                "h": f.layout.height,
                "is_image": is_img,
            })

    priority = [f for f in new_fragments if f.type in _IMAGE_TYPES]
    rest = [f for f in new_fragments if f.type not in _IMAGE_TYPES]
    rng.shuffle(priority)
    rng.shuffle(rest)

    for frag in priority + rest:
        _layout_fragment(rng, frag, placed_boxes, params)

    return priority + rest
