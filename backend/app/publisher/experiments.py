"""The experiment scheduler — picks what to generate and how it gets tagged.

One collage per post, always. Series and wandering happen through TAGS, not photosets.
Topics are drawn from meta-topic buckets so the meta-topic tag is known, not guessed.
Biased toward dense collages.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field

import httpx


@dataclass
class Shot:
    topic: str
    density: str | None = "dense"          # default dense; ladders/neutral use None (auto)
    layout_seed: int | None = None
    meta_topics: tuple[str, ...] = ()


@dataclass
class Experiment:
    name: str
    tag: str
    shots: list[Shot]


# ── meta-topic buckets: bucket -> seed words (every specimen carries its bucket) ──
# Each word lives in exactly one bucket so the meta-topic tag is unambiguous.
META_TOPICS: dict[str, list[str]] = {
    "history": ["almanac", "ledger", "census", "chronicle", "gazette", "archive"],
    "nature": ["fog", "glacier", "tide", "orchard", "moth", "marsh", "moss", "frost", "estuary"],
    "science": ["observatory", "telescope", "greenhouse", "specimen", "barometer", "microscope", "herbarium"],
    "art": ["fresco", "engraving", "mosaic", "portrait", "still life", "etching", "tapestry"],
    "culture": ["carnival", "festival", "arcade", "fairground", "vaudeville", "phonograph"],
    "architecture": ["lighthouse", "aqueduct", "rotunda", "pavilion", "stairwell", "bandstand", "facade"],
    "transport": ["tram", "canal", "railway", "harbor", "ferry", "locomotive", "dirigible"],
    "communication": ["telegraph", "switchboard", "telephone", "radio", "typewriter", "transmitter"],
    "ritual": ["procession", "masquerade", "shrine", "pilgrimage", "maypole", "vigil"],
    "industry": ["loom", "kiln", "foundry", "mill", "cannery", "colliery", "printing press"],
}

QUALIFIERS = [
    "at night", "in winter", "operators", "interior", "abandoned", "under snow",
    "by lamplight", "from above", "in fog", "diagram",
]
YEARS = [str(y) for y in range(1890, 1979)]
# Single words that fan out across unrelated domains (no single meta-topic).
AMBIGUOUS = [
    "mercury", "delta", "apollo", "saturn", "phoenix", "amazon", "java", "titan",
    "iris", "atlas", "nova", "echo", "vega", "orion", "sable",
]

# ── drift: evocative / polysemous / half-surreal seeds that push the system's edges ──
POLYSEMOUS = [
    "mercury", "echo", "current", "charge", "vessel", "mantle", "fault", "relay",
    "signal", "drift", "atlas", "iris", "nova", "ember", "relic", "specter",
    "mirror", "needle", "crown", "vault", "tongue", "compass", "prism", "static",
]
EVOCATIVE = [
    "vertigo", "mirage", "reverie", "oblivion", "trance", "rupture", "decay",
    "hush", "fever", "halo", "eclipse", "threshold", "undertow", "delirium",
]
MATTER = [
    "rust", "salt", "ash", "glass", "copper", "neon", "velvet", "smoke", "amber",
    "tar", "chrome", "bone", "wax", "ivory", "obsidian",
]
VESSELS = [
    "cathedral", "ruin", "engine", "machine", "garden", "opera", "circus", "asylum",
    "observatory", "reliquary", "mausoleum", "carnival", "altar", "menagerie",
]


def _seed(rng: random.Random) -> int:
    return rng.randint(0, 2**31 - 1)


def _pick_meta(rng: random.Random) -> tuple[str, str]:
    """Return (meta_topic, seed_word)."""
    mt = rng.choice(list(META_TOPICS))
    return mt, rng.choice(META_TOPICS[mt])


def build_specimen(rng: random.Random) -> Experiment:
    """A plain dense pull — a specimen of ordinary system behavior."""
    mt, word = _pick_meta(rng)
    topic = f"{word} {rng.choice(YEARS)}" if rng.random() < 0.5 else word
    return Experiment("specimen", "specimen",
                      [Shot(topic=topic, density="dense", meta_topics=(mt,))])


def build_domain_drift(rng: random.Random) -> Experiment:
    """One ambiguous word the collage catches mid-confusion (spans meta-topics)."""
    word = rng.choice(AMBIGUOUS)
    return Experiment("domain drift", "domain-drift",
                      [Shot(topic=word, density="dense", meta_topics=())])


def build_seed_series(rng: random.Random) -> Experiment:
    """One prompt, N layout seeds — same fragments, different dice. Grouped by the topic tag."""
    mt, word = _pick_meta(rng)
    topic = f"{word} {rng.choice(QUALIFIERS)}"
    shots = [Shot(topic=topic, density="dense", layout_seed=_seed(rng), meta_topics=(mt,))
             for _ in range(3)]
    return Experiment("seed series", "seed-series", shots)


def build_density_ladder(rng: random.Random) -> Experiment:
    """word -> word qual -> word qual year. Auto density so vibe climbs across the posts."""
    mt, word = _pick_meta(rng)
    qual, year = rng.choice(QUALIFIERS), rng.choice(YEARS)
    rungs = [word, f"{word} {qual}", f"{word} {qual} {year}"]
    return Experiment("density ladder", "density-ladder",
                      [Shot(topic=t, density=None, meta_topics=(mt,)) for t in rungs])


def build_neutral_zone(rng: random.Random) -> Experiment:
    """Two words from one bucket whose vibe is decided by an md5, not meaning."""
    mt = rng.choice(list(META_TOPICS))
    pair = rng.sample(META_TOPICS[mt], 2)
    return Experiment("neutral zone", "neutral-zone",
                      [Shot(topic=t, density=None, meta_topics=(mt,)) for t in pair])


def _drift_topic(rng: random.Random) -> str:
    r = rng.random()
    if r < 0.45:                                   # single polysemous/evocative word -> domain drift
        return rng.choice(POLYSEMOUS + EVOCATIVE)
    if r < 0.80:                                   # concrete matter + charged vessel
        return f"{rng.choice(MATTER)} {rng.choice(VESSELS)}"   # "salt cathedral", "neon circus"
    return f"{rng.choice(MATTER)} {rng.choice(EVOCATIVE)}"      # "rust vertigo", "amber undertow"


def build_drift(rng: random.Random) -> Experiment:
    """The walk: evocative, polysemous, half-surreal seeds that make the system drift."""
    return Experiment("drift", "drift", [Shot(topic=_drift_topic(rng), density="dense", meta_topics=())])


# ── the infinite engine: random Wikipedia subjects ──────────────────────────
_WIKI_API = "https://en.wikipedia.org/w/api.php"
_WIKI_UA = "euphemera/1.0 (ephemera tumblr bot; +https://github.com/nazanindev/ephemera)"


def _good_seed(title: str) -> bool:
    """Skip titles that make poor collage prompts (disambiguation, lists, dates)."""
    if not title or len(title) > 38:
        return False
    low = title.lower()
    if "(" in title:
        return False
    if low.startswith(("list of", "index of", "outline of", "timeline of", "glossary of")):
        return False
    if sum(c.isdigit() for c in title) >= 3:  # "2007 in film", catalog numbers, dates
        return False
    return True


def random_wikipedia_topic(rng: random.Random | None = None) -> str | None:
    """A clean random Wikipedia article title — an unbounded, serendipitous seed."""
    try:
        resp = httpx.get(
            _WIKI_API,
            params={"action": "query", "list": "random", "rnnamespace": 0,
                    "rnlimit": 12, "format": "json"},
            timeout=10,
            headers={"User-Agent": _WIKI_UA},
        )
        titles = [x["title"] for x in resp.json().get("query", {}).get("random", [])]
    except Exception:
        return None
    good = [t for t in titles if _good_seed(t)]
    if good:
        return (rng or random).choice(good)
    return titles[0] if titles else None


def build_wander(rng: random.Random) -> Experiment:
    """Wander: a random Wikipedia subject — the never-repeating feed.

    Falls back to a curated dense specimen if Wikipedia is unreachable.
    """
    title = random_wikipedia_topic(rng)
    if not title:
        mt, word = _pick_meta(rng)
        return Experiment("wander", "wander", [Shot(topic=word, density="dense", meta_topics=(mt,))])
    return Experiment("wander", "wander", [Shot(topic=title, density="dense", meta_topics=())])


BUILDERS = {
    "drift": build_drift,
    "wander": build_wander,
    "specimen": build_specimen,
    "domain-drift": build_domain_drift,
    "seed-series": build_seed_series,
    "density-ladder": build_density_ladder,
    "neutral-zone": build_neutral_zone,
}

# drift carries the walk (pushes the system's edges); the historical/curated work is
# an occasional interesting drip. wander (Wikipedia) stays available via --experiment
# but is out of the random feed — too square to govern the walk.
WEIGHTS = {
    "drift": 10,
    "specimen": 2,
    "density-ladder": 1,
    "seed-series": 1,
}


def build(name: str, rng: random.Random | None = None) -> Experiment:
    rng = rng or random.Random()
    if name not in BUILDERS:
        raise KeyError(f"unknown experiment {name!r}; choices: {', '.join(BUILDERS)}")
    return BUILDERS[name](rng)


def pick_experiment(rng: random.Random | None = None) -> Experiment:
    rng = rng or random.Random()
    names = list(WEIGHTS)
    name = rng.choices(names, weights=[WEIGHTS[n] for n in names], k=1)[0]
    return BUILDERS[name](rng)
