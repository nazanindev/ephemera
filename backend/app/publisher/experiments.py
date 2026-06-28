"""The 'topic generator' reframed as an experiment scheduler.

Each experiment exercises a documented Ephemera quirk and knows:
  - the shots (topic / density / layout_seed) to generate
  - whether to post them as one photoset or as separate posts
  - the series tag + a one-line blurb for the caption
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field


@dataclass
class Shot:
    topic: str
    density: str | None = None
    layout_seed: int | None = None


@dataclass
class Experiment:
    name: str
    tag: str
    shots: list[Shot]
    blurb: str = ""
    photoset: bool = False


# ── word banks (lean archival / amateur / pre-stock-photo) ──────────────────
NOUNS = [
    "fog", "radio", "harbor", "telephone", "orchard", "tram", "ledger", "almanac",
    "switchboard", "glacier", "lighthouse", "typewriter", "greenhouse", "canal",
    "observatory", "tide", "moth", "kiln", "aqueduct", "loom",
]
QUALIFIERS = [
    "at night", "in winter", "operators", "interior", "abandoned", "under snow",
    "by lamplight", "from above", "in fog", "diagram",
]
YEARS = [str(y) for y in range(1890, 1979)]
# Single words that fan out across unrelated domains.
AMBIGUOUS = [
    "mercury", "delta", "apollo", "saturn", "phoenix", "amazon", "java", "titan",
    "iris", "atlas", "nova", "echo", "vega", "orion", "sable",
]


def _seed(rng: random.Random) -> int:
    return rng.randint(0, 2**31 - 1)


def build_density_ladder(rng: random.Random) -> Experiment:
    """fog -> fog harbor -> fog harbor 1932. Watch vibe climb and the canvas thicken."""
    noun = rng.choice(NOUNS)
    qual = rng.choice(QUALIFIERS)
    year = rng.choice(YEARS)
    rungs = [noun, f"{noun} {qual}", f"{noun} {qual} {year}"]
    return Experiment(
        name="density ladder",
        tag="density-ladder",
        shots=[Shot(topic=t) for t in rungs],
        blurb="same root, escalating specificity — vibe.py marches it sparse → dense.",
        photoset=True,
    )


def build_seed_series(rng: random.Random) -> Experiment:
    """One prompt, N layout seeds. Same fragments, different dice — what's deterministic vs. chance."""
    noun = rng.choice(NOUNS)
    qual = rng.choice(QUALIFIERS)
    topic = f"{noun} {qual}"
    shots = [Shot(topic=topic, layout_seed=_seed(rng)) for _ in range(3)]
    return Experiment(
        name="seed series",
        tag="seed-series",
        shots=shots,
        blurb="one query, three layout seeds — placement, rotation and repeats are the dice.",
        photoset=True,
    )


def build_neutral_zone(rng: random.Random) -> Experiment:
    """Two near-synonyms whose vibe is decided by an md5 hash, not meaning."""
    pair = rng.sample(NOUNS, 2)
    return Experiment(
        name="neutral zone",
        tag="neutral-zone",
        shots=[Shot(topic=t) for t in pair],
        blurb="vibe scores landed mid-range, so an md5 of the word broke the tie.",
        photoset=True,
    )


def build_domain_drift(rng: random.Random) -> Experiment:
    """A single ambiguous word the system catches mid-confusion."""
    word = rng.choice(AMBIGUOUS)
    return Experiment(
        name="domain drift",
        tag="domain-drift",
        shots=[Shot(topic=word)],
        blurb="one ambiguous word — the collage wanders across the senses it could mean.",
    )


def build_specimen(rng: random.Random) -> Experiment:
    """A plain single pull — a specimen of ordinary system behavior."""
    topic = rng.choice(NOUNS)
    if rng.random() < 0.5:
        topic = f"{topic} {rng.choice(YEARS)}"
    return Experiment(
        name="specimen",
        tag="specimen",
        shots=[Shot(topic=topic)],
    )


BUILDERS = {
    "density-ladder": build_density_ladder,
    "seed-series": build_seed_series,
    "neutral-zone": build_neutral_zone,
    "domain-drift": build_domain_drift,
    "specimen": build_specimen,
}

# Relative frequency on the blog.
WEIGHTS = {
    "density-ladder": 3,
    "seed-series": 2,
    "neutral-zone": 2,
    "domain-drift": 3,
    "specimen": 2,
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
