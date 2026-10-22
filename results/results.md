# Résultats comparatifs

Scénario : vague virale (h+1), rupture M/L (h+3), fausse tendance robots (h+5) ; 2 jours simulés par run.

### Tableau A : valeur du temps réel (règles temps réel vs règles J-1)

10 seed(s) · moyenne ± écart-type · Règles temps réel > règles J-1 sur le profit dans 10/10 runs

| Métrique | Règles J-1 | Règles temps réel | Écart vs règles J-1 |
|---|---|---|---|
| Profit (marge − pub − surcoût réassort) | 23 003 ± 1 099 € | 27 181 ± 1 353 € | +4 178 € (+18 %) |
| Chiffre d'affaires | 38 692 ± 1 641 € | 44 694 ± 2 055 € | +6 002 € (+16 %) |
| Dépense pub | 2 658 ± 27 € | 2 657 ± 33 € | -1 € (-0 %) |
| Pub gaspillée sur tailles épuisées | 121 ± 8 € | 1 ± 0 € | -120 € (-100 %) |
| Marge perdue (ruptures) | 1 026 ± 390 € | 605 ± 110 € | -422 € (-41 %) |
| Ventes du modèle viral (SKU-0712) | 79 ± 5 u | 125 ± 10 u | +46 u (+58 %) |
| Pub supplémentaire sur la fausse tendance (SKU-2230) | 0 ± 0 € | 77 ± 18 € | +77 € |
| Surcoût réassorts express | 984 ± 98 € | 886 ± 197 € | -98 € (-10 %) |

### Tableau B : valeur du raisonnement (agent LLM vs règles)

3 seed(s) · moyenne ± écart-type · Agent LLM > règles J-1 sur le profit dans 3/3 runs

| Métrique | Règles J-1 | Règles temps réel | Agent LLM | Écart vs règles J-1 | Écart agent vs règles temps réel |
|---|---|---|---|---|---|
| Profit (marge − pub − surcoût réassort) | 21 350 ± 1 258 € | 26 819 ± 1 387 € | 24 908 ± 1 068 € | +3 558 € (+17 %) | -1 911 € |
| Chiffre d'affaires | 36 221 ± 2 015 € | 44 132 ± 2 157 € | 41 259 ± 1 619 € | +5 039 € (+14 %) | -2 873 € |
| Dépense pub | 2 703 ± 16 € | 2 667 ± 13 € | 2 496 ± 12 € | -207 € (-8 %) | -171 € |
| Pub gaspillée sur tailles épuisées | 117 ± 9 € | 5 ± 4 € | 13 ± 8 € | -104 € (-89 %) | +9 € |
| Marge perdue (ruptures) | 924 ± 292 € | 684 ± 344 € | 449 ± 330 € | -475 € (-51 %) | -235 € |
| Ventes du modèle viral (SKU-0712) | 75 ± 9 u | 123 ± 6 u | 110 ± 7 u | +34 u (+46 %) | -13 u |
| Pub supplémentaire sur la fausse tendance (SKU-2230) | 0 ± 0 € | 94 ± 6 € | -17 ± 39 € | -17 € | -112 € |
| Surcoût réassorts express | 894 ± 111 € | 820 ± 232 € | 1 002 ± 342 € | +108 € (+12 %) | +182 € |
