# Projet : agent de pilotage commercial temps réel pour marques de mode en ligne

> Nom de travail à définir. Hackathon Aiven. Statut : **cadrage validé, début d'implémentation**.
> Justification des choix : voir `question.md`. Comparatif des secteurs : voir `secteurs.md`.

---

## 1. En une phrase

> En mode, chaque produit est nouveau : il n'a pas d'historique. Les marques découvrent trop tard ce qui part (rupture, vague manquée) et ce qui ne part pas (invendus impossibles à détruire, pub gaspillée). **Notre agent capte les signaux en direct (tendances visuelles sur les réseaux, ventes, retours, stock, pub), teste, mesure et ajuste en continu la pub, la vitrine du site, les emails, le réassort et les démarques.**

---

## 2. Client et douleur

### Client cible
Marques de mode en ligne moyennes (2 à 50 M€ de chiffre d'affaires), vendant principalement sur leur site (Shopify) avec de fortes dépenses Meta Ads et Google Ads.
**Utilisateur** : responsable e-commerce / growth. **Acheteur** : fondateur ou directeur e-commerce.

### Douleurs
| Douleur | Conséquence |
|---|---|
| Pas d'historique par produit : chaque collection est un pari | Vagues manquées, ruptures sur les modèles qui marchent |
| Signaux de tendance détectés trop tard (rapports de saison, intuition) | Pub et mise en avant sur les mauvais produits |
| Invendus | Démarques lourdes en fin de saison ; destruction interdite (loi AGEC) |
| Retours élevés en ligne, motifs vus trop tard | Lots défectueux toujours expédiés, fiches produit fausses (taille, couleur) |
| Décisions en silos (pub, stock, site, CRM) | Pub sur un produit bientôt épuisé dans les tailles principales |

### Pourquoi c'est mal adressé
- Heuritech, WGSN, Trendalytics : prévoient les tendances **pour la saison suivante**, à destination de la création et des achats.
- Outils pub (Meta, Google) : optimisent leurs propres conversions, sans connaître ni la marge, ni le stock par taille, ni les retours.
- Shein et Zara font ce pilotage en interne : c'est leur cœur de métier. **Les marques moyennes n'ont rien.**
- **Le chaînon manquant est l'activation en direct** : relier le signal au stock, à la pub et au site.

---

## 3. Pourquoi le temps réel (et pas l'historique)

> **Valeur du temps réel = écart imprévisible × part encore actionnable × coût unitaire de l'erreur**

- **L'historique par produit n'existe pas** : en mode, le temps réel est la seule source d'information sur un modèle qui vient de sortir.
- **Les moments viraux se jouent en heures** : un post influent épuise un style en 24 h.
- **Les leviers sont numériques, bon marché et réversibles** (pub, mise en avant, email) : on peut agir même sur un signal imparfait.
- **Un lot défectueux coûte à chaque heure** où il continue d'être expédié.
- **Comparaison de référence** de la démo : « les meilleures règles appliquées sur les données de la veille ». L'écart avec l'agent mesure la valeur du temps réel.

---

## 4. Pourquoi un agent (et pas des règles)

Une règle (« si la similarité dépasse 0,85, augmenter la pub ») est naïve. L'agent :
1. **Vérifie que le signal est réel** : nombre de comptes distincts, accélération, robots.
2. **Vérifie qu'on peut servir la demande** : stock par taille, délai de réassort.
3. **Vérifie que c'est rentable** : marge, coût de la pub (qui monte quand tout le monde chasse la même tendance).
4. **Consulte sa mémoire** : ce type de signal a-t-il déjà prédit des ventes pour cette marque ?
5. **Dimensionne un pari** avec un groupe témoin, **mesure**, puis **amplifie ou abandonne**.
6. **Relie des données hétérogènes** : une photo de retour, un lot, un fournisseur, d'autres commandes en cours.

---

## 5. Les trois capteurs du produit

| Capteur | Signal | Décisions déclenchées |
|---|---|---|
| **Veille visuelle des tendances** | Images des réseaux sociaux → embeddings → modèle du catalogue le plus proche → accélération des correspondances | Pub, mise en avant, email ciblé, réassort, gel des démarques |
| **Pilotage ventes / stock / pub** | Ventes à la minute, stock par taille, dépenses et conversions pub | Réallocation du budget pub, protection des tailles bientôt épuisées, démarque précoce des modèles qui ne partent pas |
| **Qualité des retours (VLM)** | Motifs de retour (texte) + photos → regroupement par lot fournisseur | Blocage du lot, correction de la fiche produit (guide des tailles, photos), alerte fournisseur |

---

## 6. Catalogue d'événements (fermé)

| Événement | Détection (ClickHouse) | Exemples de réactions |
|---|---|---|
| `trend_spike` | Accélération des publications similaires à un modèle, nombre de comptes distincts | Pari pub + mise en avant + groupe témoin |
| `trend_decline` | Ralentissement des correspondances d'un style | Démarque précoce, arrêt du réassort |
| `sellout_risk` | Couverture de stock < X h par taille au rythme actuel | Ralentir la pub, réassort, mettre en avant un substitut |
| `burn_without_stock` | Dépense pub sur un modèle épuisé dans les tailles principales | Pause immédiate (Sentinel) |
| `slow_mover` | Taux d'écoulement après lancement sous la courbe attendue | Démarque précoce, changement de visuel, pub ciblée |
| `return_defect_cluster` | Pic de retours au même motif sur un lot | Blocage du lot, analyse VLM, correction de la fiche |
| `size_imbalance` | Une taille s'épuise, les autres restent | Réassort ciblé, ajustement du guide des tailles |
| `ad_fatigue` / `roas_collapse` | Taux de clic ou rentabilité de la pub en baisse | Changement de visuel, réallocation |
| `experiment_result` | Fin d'un test avec groupe témoin | Amplifier ou abandonner |

---

## 7. Architecture

```
Simulateur (boucle fermée)  +  flux social (images)
      │
      ▼
Aiven for Apache Kafka
  events.social.posts · events.web.sessions · events.orders · events.ads.metrics
  events.inventory · events.returns · events.human.inputs
      │                                   │
      ▼                                   ▼
Service d'embeddings (type CLIP)    Aiven for ClickHouse
      │  modèle le plus proche         fenêtres temporelles, vitesse, accélération,
      ▼                                détection d'anomalies
Aiven for PostgreSQL + pgvector            │
  catalogue, images, marges, stock         ▼
  par taille, segments, lots,        topic alerts.anomalies
  expériences, mémoire                     │
                         ┌─────────────────┼─────────────────┐
                    Sentinel          Strategist          Auditor
                    (règles, <5 s)    (LLM, enquête)      (LLM, mesure les
                         │                 │               tests, apprend)
                         ▼                 ▼                   │
               Moteur de politique d'autonomie (auto / approbation / suggestion)
                         │
                         ▼
          Plateformes simulées : Ads, site (mise en avant), CRM, fournisseurs
                         │
                         ▼
          Dashboard (SSE) : timeline pensée / action / observation,
          tendances, tests en cours, gains contre la comparaison de référence
```

### Agents
| Agent | Rôle | LLM |
|---|---|---|
| **Sentinel** | Réflexes déterministes (ex. `burn_without_stock` → pause) | Non |
| **Strategist** | Enquête multi-étapes, compare des options chiffrées, lance des paris avec groupe témoin | Oui |
| **Auditor** | Mesure les tests et les décisions passées, amplifie ou arrête, écrit en mémoire | Oui |

### Outils (≤ 12 pour le Strategist)
**Lecture et modèles**
- `get_sku_snapshot(sku)` : stock par taille, ventes récentes, marge, pub en cours, retours
- `get_trend_signal(sku | cluster)` : vitesse, accélération, comptes distincts, exemples d'images
- `find_similar_skus(sku | image)` : similarité visuelle (pgvector)
- `forecast_sellout(sku, size)` : heures avant rupture au rythme actuel
- `get_segment_affinity(sku)` : segments clients qui achètent ce style
- `inspect_return_cluster(lot)` : regroupement des retours + analyse VLM des photos
- `simulate_action(actions[])` : profit attendu de chaque option
- `query_clickhouse(sql)` / `query_postgres(sql)` : lecture seule, en dernier recours

**Actions** (passent par le moteur de politique d'autonomie)
- `set_ad_budget(sku, budget)`, `set_merch_rank(sku, slot)`, `send_campaign(segment, sku)`
- `create_reorder(sku, size, qty)`, `set_markdown(sku, pct)`, `block_lot(lot)`, `update_product_page(sku, patch)`
- `start_experiment(sku, action, holdout_pct)`, `schedule_reevaluation(decision_id, when)`, `log_decision_memory(data)`

### Principes
- **Aucun LLM ni VLM sur le flux brut** : embeddings bon marché pour tout le flux, VLM uniquement sur les cas signalés.
- **Chaque décision est tracée** (pensée, action, observation) et affichée.
- **Garde-fous** : variation maximale par heure, budget pub total constant, cooldown par produit, niveau d'autonomie configurable.
- **Images dans un stockage objet**, références uniquement dans Kafka. Aiven n'en propose pas, à choisir.

---

## 8. Données

| Besoin | Source |
|---|---|
| Catalogue, images, ventes de base | **Dataset H&M (Kaggle)** : environ 105 000 articles avec images réelles, environ 31 M de transactions (à vérifier : licence, volume) |
| Flux social | Simulé à partir d'images réelles (H&M ou autre dataset mode), injectées comme publications ; option : flux public Bluesky |
| Pub, stock par taille, retours, lots fournisseurs | **Simulateur en boucle fermée** : les actions de l'agent modifient réellement les ventes et les clics |
| Vérité terrain | Le simulateur connaît les vrais modèles « tendance », les lots défectueux et les élasticités : on peut mesurer la précision de l'agent |
| Photos de retours | Simulées (images catalogue altérées) ou dataset de défauts textiles (à trouver) |

---

## 9. Preuve que ça marche

Le même scénario, avec la même seed, tourne sous trois stratégies :
1. **Rien**
2. **Règles sur les données de la veille** (comparaison de référence : « ce que fait une bonne équipe aujourd'hui »)
3. **Agent temps réel**

Métriques :
- Profit (marge − pub − coût des retours − coût des invendus)
- Chiffre d'affaires capté pendant les vagues virales
- Dépense pub gaspillée (produits épuisés, lots défectueux)
- Délai de détection (tendance, lot défectueux)
- Gain mesuré par les tests contre groupe témoin
- Précision face à la vérité terrain (tendances et lots défectueux correctement identifiés)

---

## 10. Démo cible (≈ 3 min)

1. Dashboard live : flux de publications, ventes, stock, pub ; compteurs des 3 stratégies.
2. **Injection d'un post viral** (veste en lin) : correspondance avec le modèle n°0712 (similarité 0,91), l'accélération est détectée.
3. Le Strategist enquête (stock M/L faible, marge 62 %, réassort à 10 jours) et lance un pari : +25 % de pub, mise en page d'accueil, email au segment « lin », réassort ; groupe témoin de 20 %.
4. **Rupture d'une taille** : Sentinel coupe la pub en moins de 5 s et le Strategist réalloue.
5. **Pic de retours** « couture défaillante » sur un lot : le VLM confirme sur les photos, le lot est bloqué et la fiche corrigée.
6. L'Auditor mesure le test (+38 % de conversion contre le groupe témoin) et amplifie.
7. Écran final : écart de profit entre l'agent, les règles sur les données de la veille et l'inaction.

---

## 11. Structure du repo (proposition)

```
/infra          scripts de provisioning Aiven, schémas SQL (ClickHouse, Postgres), topics Kafka
/simulator      replayer H&M + simulateur boucle fermée + plateformes simulées (Ads, site, CRM)
/embeddings     service d'embeddings d'images, chargement du catalogue dans pgvector
/agents         Sentinel, Strategist, Auditor, outils, moteur de politique d'autonomie
/api            FastAPI : SSE vers le dashboard, déclencheurs de scénarios
/dashboard      React + TypeScript
/docs           project.md, question.md, secteurs.md
```

**Stack** : Python (simulateur, agents, API FastAPI, `confluent-kafka`, `clickhouse-connect`, `psycopg`, `pgvector`), modèle d'embeddings d'images de type CLIP, LLM/VLM pour les agents, TypeScript/React pour le dashboard.

---

## 12. Plan d'implémentation

| # | Étape | Priorité |
|---|---|---|
| 0 | Provisionner Aiven (Kafka, ClickHouse, PostgreSQL + pgvector), scaffolder le repo, configuration | P0 |
| 1 | Charger un sous-ensemble H&M (catalogue, images, transactions) ; schéma Postgres ; embeddings du catalogue dans pgvector | P0 |
| 2 | Simulateur en boucle fermée : sessions, commandes, pub, stock par taille, retours ; plateformes simulées | P0 |
| 3 | Flux social simulé + service d'embeddings + correspondance avec le catalogue | P0 |
| 4 | ClickHouse : ingestion Kafka, vues fenêtrées, règles d'anomalie → `alerts.anomalies` | P0 |
| 5 | Sentinel + moteur de politique d'autonomie | P0 |
| 6 | Strategist : boucle ReAct, outils, traces | P0 |
| 7 | Dashboard : timeline, tendances, boutons de scénarios, compteurs | P0 |
| 8 | Comparaison des 3 stratégies | P0 |
| 9 | Tests avec groupe témoin + Auditor + mémoire | P1 |
| 10 | Retours : regroupement par lot + VLM | P1 |
| 11 | Flux Bluesky réel, segments CRM avancés | P2 |

**Hors périmètre (extension pour le pitch)** : module salle de crise supply chain (navires, actualités, fournisseurs).

---

## 12 bis. Périmètre de la session de code (1 heure)

**Objectif** : une démo qui tourne de bout en bout et montre une valeur claire : l'agent temps réel bat les règles appliquées sur les données de la veille, avec des chiffres.

| Inclus | Remplacé par un bouchon / reporté |
|---|---|
| Simulateur en boucle fermée, 2 mondes en parallèle (règles sur données de la veille / agent), même seed | Dataset H&M complet (catalogue synthétique d'environ 30 modèles pour l'heure) |
| Kafka (Aiven) : commandes, pub, stock, publications sociales | Embeddings CLIP réels : **score de similarité fourni par le simulateur**, interface prête pour le vrai modèle |
| Consommateur Kafka → ClickHouse (Aiven), fenêtres et détection d'anomalies en SQL | Ingestion native Kafka engine de ClickHouse |
| PostgreSQL (Aiven) : catalogue, marges, stock par taille, journal des décisions | pgvector |
| Sentinel (règle) + Strategist (Claude, ~6 outils), traces pensée / action / observation | Auditor, tests avec groupe témoin, VLM sur les retours |
| Dashboard minimal (FastAPI + une page HTML en SSE) : timeline de l'agent, profit agent contre règles | React, moteur d'autonomie complet |
| 2 scénarios injectables : post viral, rupture d'une taille | Autres scénarios |

**Contraintes techniques constatées** : Python 3.14 (privilégier des bibliothèques pur Python : `kafka-python`, `clickhouse-connect`, `pg8000`), Node 24, Docker disponible, CLI Aiven (`avn`) non installée, aucune clé API dans l'environnement.

## 13. Contraintes et questions ouvertes

- [ ] Nom du produit
- [ ] Durée du hackathon, date limite, taille et compétences de l'équipe
- [ ] Livrables exigés (démo live, vidéo, repo, slides)
- [ ] Aiven : comptes, crédits, services déjà provisionnés
- [ ] Aiven Runtime : ce qu'il héberge (conteneurs, process long-running, GPU ?)
- [ ] Choix du LLM/VLM et budget d'appels
- [ ] Où tournent les embeddings (CPU suffisant pour un petit modèle ?)
- [ ] Stockage objet pour les images
- [ ] Licence et taille du dataset H&M (sous-ensemble à charger)
- [ ] Mode d'autonomie par défaut pour la démo
