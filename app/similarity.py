"""Similarité visuelle entre une publication sociale et le catalogue.

Deux modes :
- "clip"      : embeddings CLIP réels (si open_clip + images disponibles) ;
- "simulated" : score fictif dérivé de la vérité terrain du simulateur.
Le mode est tracé dans chaque événement (`similarity_source`) : la démo ne cache pas le bouchon.
"""
from __future__ import annotations

import random

from app.catalog import CATALOG

try:  # CLIP optionnel : jamais requis pour faire tourner la démo
    import open_clip  # type: ignore  # noqa: F401
    CLIP_AVAILABLE = False  # passer à True une fois les images catalogue embarquées
except ImportError:
    CLIP_AVAILABLE = False

SOURCE = "clip" if CLIP_AVAILABLE else "simulated"


def match_post(true_sku: str | None, rng: random.Random) -> tuple[str, float]:
    """Retourne (modèle du catalogue le plus proche, score de similarité)."""
    if true_sku:
        return true_sku, round(min(0.98, max(0.8, rng.gauss(0.88, 0.04))), 3)
    return rng.choice(CATALOG).sku, round(rng.uniform(0.35, 0.74), 3)
