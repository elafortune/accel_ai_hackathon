# Agent de pilotage commercial temps réel pour marques de mode en ligne

> En mode, chaque produit est nouveau : il n'a pas d'historique. Les marques découvrent trop tard ce qui part
> (rupture, vague manquée) et ce qui ne part pas (pub gaspillée, invendus). Ce projet capte en temps réel
> les tendances visuelles sur les réseaux, les ventes, le stock par taille et la pub. Des agents décident en
> continu de la pub, de la mise en avant sur le site et des réassorts, **au profit et non au chiffre d'affaires**.

Hackathon Aiven · Données : **Aiven for Apache Kafka · Aiven for ClickHouse · Aiven for PostgreSQL** · Agents : boucle ReAct (OpenAI)

| Document | Contenu |
|---|---|
| [`project.md`](project.md) | Cadrage produit : client, douleur, événements, architecture cible |
| [`question.md`](question.md) | Toutes les questions posées pendant le cadrage et la justification de chaque choix |
| [`secteurs.md`](secteurs.md) | Comparatif des secteurs étudiés et critères de sélection |
| [`results/results.md`](results/results.md) | Résultats du benchmark (généré par `run_simulation.py`) |

---

## Sommaire
1. [Le problème](#1-le-problème)
2. [La solution](#2-la-solution)
3. [Architecture](#3-architecture)
4. [Agents, outils et garde-fous](#4-agents-outils-et-garde-fous)
5. [Quickstart](#5-quickstart)
6. [Déploiement sur Aiven](#6-déploiement-sur-aiven)
7. [Résultats](#7-résultats)
8. [Protocole de test et hypothèses du simulateur](#8-protocole-de-test-et-hypothèses-du-simulateur)
9. [Limites et suite](#9-limites-et-suite)
10. [Structure du code](#10-structure-du-code)

---

## 1. Le problème

**Client** : marques de mode en ligne moyennes (2 à 50 M€ de chiffre d'affaires), sur Shopify, avec de fortes dépenses Meta Ads et Google Ads. **Utilisateur** : responsable e-commerce ou growth.

| Douleur | Conséquence |
|---|---|
| Aucun historique par produit : chaque collection est un pari | Vagues virales manquées, ruptures sur les modèles qui marchent |
| Tendances repérées trop tard (rapports de saison, intuition) | Pub et mise en avant sur les mauvais produits |
| Décisions en silos (pub, stock, site) prises sur les données de la veille | Pub payée sur des tailles épuisées, réassorts trop tardifs |
| Signaux trompeurs (pics de posts générés par des robots) | Budget dépensé sur une demande qui n'existe pas |

**Pourquoi c'est mal adressé.** Les outils de tendances (Heuritech, WGSN) prévoient la saison suivante pour les équipes création. Les plateformes pub optimisent leurs propres conversions sans connaître la marge ni le stock par taille. Shein et Zara font ce pilotage en interne ; les marques moyennes n'ont rien. **Le chaînon manquant est l'activation en direct** : relier le signal au stock, à la pub et au site.

**Pourquoi le temps réel.** Un modèle qui vient de sortir n'a pas d'historique : le temps réel est la seule information disponible. Une vague virale se joue en heures, et chaque heure de pub sur une taille épuisée est perdue. La règle de comparaison du projet est donc « la meilleure décision prise avec les données de la veille ».

## 2. La solution

1. **Ingestion** des flux (ventes, stock par taille, pub, publications sociales rapprochées du catalogue par similarité d'images) dans **Kafka**.
2. **Analyse en continu** dans **ClickHouse** : fenêtres temporelles et détection d'anomalies en SQL (`trend_spike`, `burn_without_stock`, `sellout_risk`).
3. **Décision** par deux agents :
   - **Sentinel**, réflexe déterministe : coupe la pub d'un modèle dont les tailles principales sont épuisées, en moins d'une seconde.
   - **Strategist**, agent ReAct (LLM) : enquête avec des outils (stock, tendance, prévision, substituts), arbitre au profit, agit (budget pub, mise en avant, réassort) et explique sa décision.
4. **Traçabilité** dans **PostgreSQL** : chaque pensée, action et observation est enregistrée et affichée en direct sur le dashboard.
5. **Boucle fermée** : les actions modifient réellement le monde simulé, et le gain est mesuré contre des stratégies de référence.

## 3. Architecture

```mermaid
flowchart LR
    subgraph SRC["Sources temps réel"]
        SIM["Simulateur boucle fermée<br/>ventes · stock par taille · pub"]
        SOC["Flux social<br/>similarité image → catalogue"]
    end

    subgraph AIVEN["Services managés Aiven"]
        K[("Aiven for Apache Kafka<br/>events.orders · events.inventory<br/>events.ads.metrics · events.social.posts<br/>alerts.anomalies · actions.commands")]
        CH[("Aiven for ClickHouse<br/>fenêtres temporelles<br/>détection d'anomalies en SQL")]
        PG[("Aiven for PostgreSQL<br/>catalogue · marges · réassorts<br/>traces des agents · décisions")]
    end

    subgraph AGENTS["Agents"]
        SEN["Sentinel<br/>réflexe déterministe &lt; 1 s"]
        STR["Strategist : boucle ReAct (LLM)<br/>pensée → outil → observation"]
    end

    EXE["Exécuteur d'actions<br/>Ads · site · fournisseurs"]
    UI["Dashboard SSE<br/>raisonnement + profit comparé"]

    SIM --> K
    SOC --> K
    K -->|ingestion| CH
    CH -->|détection| K
    K -->|alerts.anomalies| SEN
    K -->|alerts.anomalies| STR
    STR <-->|outils de lecture| CH
    STR <-->|outils de lecture| PG
    SEN -->|actions.commands| K
    STR -->|actions.commands| K
    K --> EXE --> SIM
    STR -->|traces| PG
    PG --> UI
```

### Rôle de chaque service Aiven

| Service | Rôle | Objets |
|---|---|---|
| **Aiven for Apache Kafka** | Bus d'événements, découplage producteurs / consommateurs | Topics `events.orders`, `events.inventory`, `events.ads.metrics`, `events.social.posts`, `events.lost_sales`, `alerts.anomalies`, `actions.commands`, `control.scenarios` |
| **Aiven for ClickHouse** | Analytique temps réel sur les flux, détection d'anomalies en SQL fenêtré, lecture par les outils de l'agent | Tables `orders`, `inventory`, `ads`, `social`, `lost_sales` (MergeTree) |
| **Aiven for PostgreSQL** | Référentiel métier et mémoire des décisions | Tables `catalog`, `reorders`, `agent_trace`, `decisions` |

### Principes
- **Le LLM ne voit jamais le flux brut.** ClickHouse agrège et détecte ; l'agent ne reçoit que des alertes et interroge les bases via des outils typés.
- **Le LLM ne devine jamais un chiffre.** Les quantités (heures avant rupture, demande à 24 h, réassort suggéré) viennent des outils.
- **Fast path déterministe, slow path agentique.** Sentinel agit en moins d'une seconde sans LLM ; le Strategist intervient quand il faut arbitrer.
- **Décisions explicables** : pensée, action et observation sont stockées dans PostgreSQL et affichées en direct.

## 4. Agents, outils et garde-fous

### Événements détectés (SQL ClickHouse, `app/detector.py`)
| Alerte | Condition |
|---|---|
| `trend_spike` | ≥ 8 posts très similaires (≥ 0,8) à un modèle sur 30 min et 3× la moyenne des 2 h précédentes. **Ne filtre pas sur le nombre d'auteurs** : juger si le pic est réel est le travail de la stratégie |
| `burn_without_stock` | Tailles M et L épuisées alors que le budget pub du modèle est positif |
| `sellout_risk` | Moins de 8 h de stock au rythme de vente des 2 dernières heures |

### Outils du Strategist (`app/tools.py`)
| Lecture | Action |
|---|---|
| `get_sku_snapshot` : stock par taille, ventes, marge, pub, réassorts en route | `set_ad_budget` : budget pub quotidien (0 = pause) |
| `get_trend_signal` : posts similaires par fenêtre de 30 min, auteurs distincts | `feature_product` : mise en avant en page d'accueil |
| `forecast_sellout` : heures avant rupture, demande à 24 h, quantité de réassort suggérée | `create_reorder` : réassort express (arrivée sous 3 h) |
| `find_substitutes` : modèles de la même catégorie avec stock et marge | |

### Garde-fous
- Budget pub d'un modèle plafonné à 3× sa valeur initiale ; budget total plafonné à 130 % du budget initial.
- Réassort borné (1 à 200 pièces par taille).
- Une action refusée est renvoyée à l'agent comme observation, et il doit s'adapter.
- Sans clé OpenAI, le Strategist bascule sur un repli à règles clairement étiqueté « sans LLM ».

## 5. Quickstart

Prérequis : **Docker** et **Python ≥ 3.11**.

```bash
git clone https://github.com/elafortune/accel_ai_hackathon.git
cd accel_ai_hackathon
python -m venv .venv
# macOS / Linux
.venv/bin/pip install -r requirements.txt
# Windows
.venv\Scripts\pip install -r requirements.txt

cp .env.example .env          # renseigner OPENAI_API_KEY (facultatif)
docker compose up -d          # Kafka (9092), ClickHouse (8124), PostgreSQL (5442) en local
```

### Reproduire le tableau de résultats (une commande)
```bash
python run_simulation.py                          # tableau A (10 seeds) + tableau B (2 seeds avec LLM)
python run_simulation.py --seeds 3 --llm-seeds 0  # version rapide (~3 min, sans LLM)
python run_simulation.py --seeds 0 --llm-seeds 3  # relance uniquement le tableau B (A est conservé)
```
Résultats écrits dans `results/results.md` et `results/results.json`. Un run de 2 jours simulés prend environ 1 min sans LLM et 3 à 5 min avec LLM.

### Lancer la démo live
```bash
python -m app.main --reset     # http://localhost:8000
```
Le dashboard affiche le profit des trois stratégies côte à côte, les tendances visuelles et le raisonnement des agents en direct. Trois boutons injectent les scénarios :
1. **Post viral** : vague réelle sur la veste en lin (SKU-0712).
2. **Rupture M/L** : tailles principales de la robe fleurie (SKU-1104) épuisées.
3. **Fausse tendance** : pic de posts venant de 3 comptes robots sur la chemise rayée (SKU-2230).

Avec `make` (macOS / Linux) : `make demo`, `make bench`, `make bench-quick`.

> Sous Windows, utiliser `127.0.0.1` plutôt que `localhost` (déjà le cas par défaut) : la résolution IPv6 de `localhost` rend chaque appel environ 7× plus lent.

## 6. Déploiement sur Aiven

### 6.1 Créer les services
Dans la console Aiven, dans le même projet et la même région :
1. **Aiven for PostgreSQL** (le plan gratuit suffit).
2. **Aiven for Apache Kafka** (au moins 8 topics ; activer `kafka.auto_create_topics_enable` en sécurité, le code crée les topics lui-même).
3. **Aiven for ClickHouse** (plus petit plan ; facturation à l'heure, le service peut être créé juste avant la démo puis supprimé : le schéma est recréé par `--reset`).

### 6.2 Configurer `.env.aiven`
Le code lit `.env` par défaut, ou le fichier indiqué par `ENV_FILE`. Ce fichier est exclu de git.

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini

# Kafka : host:port, SANS https://
KAFKA_BOOTSTRAP=fashion-kafka-xxx.aivencloud.com:PORT
KAFKA_SSL_DIR=certs                 # dossier contenant ca.pem (+ service.cert et service.key)

# ClickHouse : connexion "ClickHouse HTTPS" (pas "native"), AVEC https:// et le port
CLICKHOUSE_URL=https://fashion-clickhouse-xxx.aivencloud.com:PORT
CLICKHOUSE_USER=avnadmin
CLICKHOUSE_PASSWORD=...

# PostgreSQL : Service URI, préfixe postgresql://
PG_URL=postgresql://avnadmin:...@fashion-pg-xxx.aivencloud.com:PORT/defaultdb?sslmode=require
```

### 6.3 Authentification Kafka : certificat client ou SASL
Aiven expose Kafka sur **deux ports différents** selon la méthode d'authentification. Le port doit correspondre à la méthode configurée.

| Méthode | Port à utiliser | Fichiers / variables |
|---|---|---|
| **Client certificate** | port affiché dans l'onglet *Client certificate* | `certs/ca.pem`, `certs/service.cert`, `certs/service.key` |
| **SASL** | port affiché dans l'onglet *SASL* | `certs/ca.pem` + `KAFKA_SASL_USERNAME=avnadmin` et `KAFKA_SASL_PASSWORD=...` |

Symptôme d'un mauvais couple port / méthode : la connexion TLS réussit, puis le broker ferme la connexion dès la première requête de métadonnées (`KafkaTimeoutError: Unable to bootstrap`). Voir [§ 6.5](#65-dépannage).

### 6.4 Lancer sur Aiven
```bash
ENV_FILE=.env.aiven python -m app.main --reset            # démo live sur les services Aiven
ENV_FILE=.env.aiven python run_simulation.py --seeds 3    # benchmark sur Aiven
```
Sous PowerShell : `$env:ENV_FILE=".env.aiven"; python -m app.main --reset`.

Les topics sont créés au démarrage avec un facteur de réplication de 2, et les tables ClickHouse et PostgreSQL sont recréées par `--reset`.

### 6.5 Dépannage
| Symptôme | Cause | Solution |
|---|---|---|
| `Request URL is missing an 'http://' or 'https://' protocol` | `CLICKHOUSE_URL` sans schéma | Ajouter `https://` et le port HTTPS |
| `Unable to bootstrap` avec `https://` dans `KAFKA_BOOTSTRAP` | Kafka n'est pas un protocole HTTP | Écrire `host:port` seul |
| TLS OK puis `socket disconnected` à la requête de métadonnées | Port SASL utilisé avec un certificat client (ou l'inverse) | Prendre le port de l'onglet *Client certificate*, ou renseigner `KAFKA_SASL_USERNAME` / `KAFKA_SASL_PASSWORD` |
| `FileNotFoundError` sur `ca.pem` | CA du projet non téléchargé | Télécharger *CA certificate* dans `certs/ca.pem` |
| Erreur SSL au démarrage sous Windows | Variable `SSL_CERT_FILE` pointant vers un fichier absent | Ignorée automatiquement par `app/config.py` |

### 6.6 Conteneur
Un `Dockerfile` est fourni pour déployer l'application sur une plateforme de conteneurs :
```bash
docker build -t fashion-agent .
docker run -p 8000:8000 --env-file .env.aiven -v "$PWD/certs:/app/certs" fashion-agent
```

## 7. Résultats

Protocole complet en [section 8](#8-protocole-de-test-et-hypothèses-du-simulateur). Chiffres : moyenne ± écart-type sur 2 jours simulés.

### Tableau A : valeur du temps réel (10 seeds)

Règles temps réel > règles J-1 sur le profit dans **10/10 runs**.

| Métrique | Règles J-1 | Règles temps réel | Écart |
|---|---|---|---|
| **Profit** (marge − pub − surcoût réassort) | 23 003 ± 1 099 € | **27 181 ± 1 353 €** | **+4 178 € (+18 %)** |
| Chiffre d'affaires | 38 692 ± 1 641 € | 44 694 ± 2 055 € | +6 002 € (+16 %) |
| Dépense pub | 2 658 ± 27 € | 2 657 ± 33 € | −1 € (0 %) |
| Pub gaspillée sur tailles épuisées | 121 ± 8 € | 1 ± 0 € | **−120 € (−100 %)** |
| Marge perdue (ruptures) | 1 026 ± 390 € | 605 ± 110 € | −422 € (−41 %) |
| Ventes du modèle viral | 79 ± 5 u | 125 ± 10 u | **+46 u (+58 %)** |
| Pub supplémentaire sur la fausse tendance | 0 € | 77 ± 18 € | +77 € |
| Surcoût réassorts express | 984 ± 98 € | 886 ± 197 € | −98 € (−10 %) |

**Lecture :** à budget pub identique, réagir aux données temps réel fait gagner **+18 % de profit**, supprime la pub gaspillée sur les tailles épuisées et capte **+58 %** de ventes sur la vague virale. En revanche, des règles fixes tombent dans le piège de la fausse tendance.

### Tableau B : valeur du raisonnement (3 seeds, agent LLM)

L'agent bat les règles J-1 sur le profit dans **3/3 runs**, et les règles temps réel dans **1/3 runs**.

| Métrique | Règles J-1 | Règles temps réel | Agent LLM | Agent vs J-1 | Agent vs règles temps réel |
|---|---|---|---|---|---|
| **Profit** | 21 350 ± 1 258 € | **26 819 ± 1 387 €** | 24 908 ± 1 068 € | **+3 558 € (+17 %)** | −1 911 € |
| Chiffre d'affaires | 36 221 ± 2 015 € | 44 132 ± 2 157 € | 41 259 ± 1 619 € | +5 039 € (+14 %) | −2 873 € |
| Dépense pub | 2 703 ± 16 € | 2 667 ± 13 € | 2 496 ± 12 € | −207 € (−8 %) | −171 € |
| Pub gaspillée sur tailles épuisées | 117 ± 9 € | 5 ± 4 € | 13 ± 8 € | −104 € (−89 %) | +9 € |
| Marge perdue (ruptures) | 924 ± 292 € | 684 ± 344 € | **449 ± 330 €** | −475 € (−51 %) | **−235 €** |
| Ventes du modèle viral | 75 ± 9 u | 123 ± 6 u | 110 ± 7 u | +34 u (+46 %) | −13 u |
| Pub supplémentaire sur la fausse tendance | 0 € | 94 ± 6 € | **−17 ± 39 €** | −17 € | **−112 €** |
| Surcoût réassorts express | 894 ± 111 € | 820 ± 232 € | 1 002 ± 342 € | +108 € (+12 %) | +182 € |

**Lecture honnête :**
- **L'agent est meilleur là où il faut du jugement** : il ignore la fausse tendance (−112 € de pub inutile par rapport aux règles naïves) et limite le mieux les ruptures (−235 € de marge perdue).
- **Il est moins bon sur le profit total que des règles temps réel bien choisies** (−1 911 €) : il est plus prudent sur la vraie vague virale (−13 ventes) et réduit parfois le budget d'autres modèles rentables pour financer ses décisions.
- **Conclusion d'architecture** : la meilleure combinaison est un fast path déterministe (Sentinel, règles temps réel) pour les réflexes évidents, et l'agent pour les cas ambigus (signal douteux, arbitrage entre plusieurs leviers). C'est l'architecture du projet ; la répartition fine des rôles entre règles et agent est la prochaine itération.

### Historique des itérations de l'agent
| Version | Changement | Profit de l'agent vs règles temps réel | Marge perdue (ruptures) |
|---|---|---|---|
| v1 ([`results/results_v1.md`](results/results_v1.md), 2 seeds) | Prompt initial | −1 842 € | 1 196 € |
| v2 (3 seeds) | Prévision de demande à 24 h, réassorts en cours visibles, économie rupture / réassort dans le prompt | −1 911 € | 449 € |

La v2 a divisé par 2,7 la marge perdue en ruptures sans combler l'écart de profit : l'agent reste trop prudent sur la vague virale. Pistes identifiées : remplacer le modèle mis en avant le plus ancien plutôt qu'un modèle au hasard (biais du simulateur qui pénalise l'agent quand il met en avant plus de 3 produits), interdire la baisse de budget d'un modèle rentable sans justification, s'engager pleinement quand la tendance est confirmée.

## 8. Protocole de test et hypothèses du simulateur

**Stratégies comparées, dans des mondes simulés identiques (même seed) :**
- **Règles J-1** : une fois par jour, sur les données de la veille : pause des modèles épuisés, +20 % de budget sur les 3 meilleures ventes, réassort si le stock couvre moins de 2 jours. C'est la pratique actuelle d'une bonne équipe.
- **Règles temps réel** : les mêmes alertes que l'agent, réponses fixes : pause sur rupture, budget ×2 et mise en avant sur tendance, réassort de 20 pièces par taille sur risque de rupture.
- **Agent LLM** : Sentinel + Strategist.

**Scénario commun (2 jours simulés, pas de 10 minutes) :** vague virale réelle à h+1, rupture des tailles M/L d'un best-seller à h+3, fausse tendance générée par 3 comptes robots à h+5.

**Hypothèses économiques :**
| Paramètre | Valeur |
|---|---|
| Coût par clic | 0,70 €, avec rendements décroissants : CPC × (budget / budget initial)^0,5 au-delà du budget initial |
| Conversion d'un clic payant | 1,8 % × multiplicateur de tendance × effet de mise en avant (×1,4) |
| Vague virale | demande jusqu'à ×12, montée en 2 h, décroissance sur 24 h |
| Réassort express | arrivée en 3 h, surcoût de 15 % du coût unitaire par pièce |
| Catalogue | 20 modèles, marges de 64 à 76 % |

**Pourquoi ces hypothèses.** Sans rendements décroissants, augmenter n'importe quel budget serait rentable et le test de la fausse tendance n'aurait pas de sens. Sans surcoût, réassortir à l'aveugle serait toujours gagnant.

**Temps simulé et latence du LLM.** Pendant le benchmark, le temps simulé est figé quand l'agent réfléchit. Un pas représente 10 minutes, un appel LLM quelques secondes : l'hypothèse correspond à la réalité.

## 9. Limites et suite

**Limites assumées**
- **Similarité d'images simulée** : le score est fourni par le simulateur (`similarity_source = simulated`, visible dans chaque événement). `app/similarity.py` est prêt pour des embeddings CLIP.
- **Catalogue synthétique** de 20 modèles ; pub, stock et comportements clients simulés avec une vérité terrain connue.
- **Tableau B sur 3 seeds** seulement (coût et durée des appels LLM).

**Suite**
- Répartition fine règles / agent (l'agent n'intervient que sur les alertes ambiguës).
- Agent Auditor : tests avec groupe témoin, mesure de l'effet réel des décisions, mémoire.
- Embeddings CLIP sur les images du dataset H&M ; analyse VLM des photos de retours.
- Module d'extension : salle de crise supply chain (positions des navires, actualités).

## 10. Structure du code
```
app/config.py       configuration (.env ou ENV_FILE), noms des topics
app/bus.py          client Kafka (local, Aiven certificat client ou SASL)
app/stores.py       clients ClickHouse (HTTP) et PostgreSQL
app/schema.py       création des tables, chargement du catalogue
app/catalog.py      catalogue de démo (20 modèles)
app/similarity.py   similarité image → catalogue (simulée, prête pour CLIP)
app/simulator.py    simulateur boucle fermée (3 mondes, vérité terrain, scénarios)
app/ingest.py       Kafka → ClickHouse
app/detector.py     règles d'anomalies en SQL ClickHouse
app/agents.py       Sentinel, Strategist (ReAct), exécuteur d'actions
app/tools.py        outils de l'agent et garde-fous
app/policies.py     stratégie « règles temps réel » (comparaison)
app/main.py         démo live (API FastAPI + dashboard SSE)
app/static/         dashboard
run_simulation.py   benchmark reproductible → results/
docker-compose.yml  Kafka, ClickHouse, PostgreSQL en local
Dockerfile          image de l'application
```
