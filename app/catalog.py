"""Catalogue de démo : environ 20 modèles d'une marque de mode moyenne.

Les attributs (prix, coût, demande de base) sont plausibles mais synthétiques ;
le catalogue réel (dataset H&M + images) se branche ici plus tard.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SIZES = ["S", "M", "L", "XL"]
SIZE_MIX = {"S": 0.2, "M": 0.35, "L": 0.3, "XL": 0.15}


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str
    color: str
    price: float
    unit_cost: float
    base_daily_demand: float     # ventes organiques/jour sans tendance
    base_daily_budget: float     # budget pub quotidien initial (€)
    initial_stock: dict[str, int] = field(default_factory=dict)

    @property
    def margin_pct(self) -> float:
        return round(100 * (self.price - self.unit_cost) / self.price, 1)


def _stock(total: int) -> dict[str, int]:
    return {s: max(1, round(total * SIZE_MIX[s])) for s in SIZES}


CATALOG: list[Product] = [
    Product("SKU-0712", "Veste en lin écru", "veste", "écru", 129, 41, 6, 80, _stock(70)),
    Product("SKU-0713", "Veste en lin sable", "veste", "sable", 129, 43, 5, 60, _stock(160)),
    Product("SKU-0720", "Blazer oversize noir", "veste", "noir", 149, 52, 8, 120, _stock(140)),
    Product("SKU-0731", "Trench court beige", "veste", "beige", 179, 66, 4, 70, _stock(90)),
    Product("SKU-1104", "Robe midi fleurie", "robe", "fleuri", 89, 26, 10, 110, _stock(150)),
    Product("SKU-1105", "Robe midi satinée verte", "robe", "vert", 99, 30, 7, 90, _stock(120)),
    Product("SKU-1120", "Robe chemise rayée", "robe", "rayé", 79, 24, 6, 60, _stock(110)),
    Product("SKU-2201", "Chemise en lin blanche", "chemise", "blanc", 69, 19, 12, 90, _stock(200)),
    Product("SKU-2202", "Chemise en lin bleu ciel", "chemise", "bleu", 69, 19, 9, 70, _stock(170)),
    Product("SKU-2230", "Chemise oversize rayée", "chemise", "rayé", 75, 22, 7, 50, _stock(130)),
    Product("SKU-3301", "Pantalon large plissé", "pantalon", "noir", 95, 28, 11, 100, _stock(180)),
    Product("SKU-3302", "Pantalon large crème", "pantalon", "crème", 95, 29, 6, 60, _stock(140)),
    Product("SKU-3320", "Jean droit brut", "pantalon", "indigo", 89, 27, 14, 130, _stock(220)),
    Product("SKU-4401", "Pull col rond cachemire", "pull", "gris", 159, 58, 5, 90, _stock(100)),
    Product("SKU-4402", "Gilet maille côtelée", "pull", "crème", 85, 25, 7, 70, _stock(130)),
    Product("SKU-4420", "Pull marin rayé", "pull", "rayé", 79, 23, 6, 50, _stock(120)),
    Product("SKU-5501", "Top dos nu satin", "top", "noir", 49, 13, 9, 60, _stock(150)),
    Product("SKU-5502", "Débardeur côtelé", "top", "blanc", 29, 7, 16, 50, _stock(260)),
    Product("SKU-6601", "Jupe midi plissée", "jupe", "vert", 79, 23, 6, 60, _stock(110)),
    Product("SKU-6602", "Mini-jupe en jean", "jupe", "indigo", 59, 17, 8, 50, _stock(140)),
]

BY_SKU: dict[str, Product] = {p.sku: p for p in CATALOG}
