# Résultats comparatifs

Scénario : vague virale (h+1), rupture M/L (h+3), fausse tendance robots (h+5) ; 2 jours simulés par run.

### Tableau A : valeur du temps réel (règles temps réel vs règles J-1)

10 seed(s) · moyenne ± écart-type · realtime_rules > règles J-1 sur le profit dans 10/10 runs

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

2 seed(s) · moyenne ± écart-type · agent > règles J-1 sur le profit dans 2/2 runs

| Métrique | Règles J-1 | Règles temps réel | Agent LLM | Écart vs règles J-1 |
|---|---|---|---|---|
| Profit (marge − pub − surcoût réassort) | 21 963 ± 1 116 € | 27 531 ± 1 167 € | 25 689 ± 1 418 € | +3 726 € (+17 %) |
| Chiffre d'affaires | 37 234 ± 1 735 € | 45 033 ± 2 132 € | 41 744 ± 2 046 € | +4 510 € (+12 %) |
| Dépense pub | 2 707 ± 18 € | 2 673 ± 12 € | 2 582 ± 3 € | -125 € (-5 %) |
| Pub gaspillée sur tailles épuisées | 123 ± 5 € | 7 ± 3 € | 14 ± 14 € | -108 € (-88 %) |
| Marge perdue (ruptures) | 1 071 ± 252 € | 806 ± 365 € | 1 196 ± 75 € | +125 € (+12 %) |
| Ventes du modèle viral (SKU-0712) | 80 ± 6 u | 126 ± 6 u | 104 ± 12 u | +23 u (+29 %) |
| Pub supplémentaire sur la fausse tendance (SKU-2230) | 0 ± 0 € | 91 ± 6 € | 23 ± 10 € | +23 € |
| Surcoût réassorts express | 972 ± 12 € | 738 ± 246 € | 449 ± 18 € | -523 € (-54 %) |
