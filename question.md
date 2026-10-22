# Questions & justifications des choix

> Journal des questions soulevées pendant le cadrage, avec la réponse retenue.
> Sert à défendre nos choix devant le jury. Statut : ✅ décidé · 🟡 recommandé (à confirmer) · ❓ ouvert.

---

## 1. Problème & positionnement

**Q : Quel problème voulait-on résoudre au départ ?**
R : Le budget pub brûlé sur des produits en rupture, à cause d'une désynchronisation entre le stock réel et les campagnes (AdSentry). ✅ point de départ

**Q : Google et Meta ne mettent-ils pas déjà en pause les produits en rupture ?**
R : Si, via le flux produit, mais avec une latence de synchronisation (souvent quotidienne) et sans couvrir les campagnes hors catalogue. La vraie douleur est ailleurs. ✅

**Q : Où est alors la vraie douleur ?**
R : Les plateformes optimisent le ROAS sans connaître ni la marge ni le stock futur. Il faut piloter au profit (POAS) et de façon prédictive (runway de stock). ✅

**Q : Pourquoi ne pas simplement utiliser un repricer existant ?**
R : Les repricers (Prisync, Omnia, repricers Amazon) n'ont qu'un levier (le prix catalogue) et ne voient qu'un silo. Ils s'alignent même sur un concurrent qui déstocke. ✅

**Q : Quelle est la douleur racine qu'on attaque ?**
R : Des décisions liées (prix, pub, stock, finance) prises en silos par des outils qui ne se parlent pas. Le coût vient du manque de coordination. ✅

**Q : Notre approche « partir de la compétition prix entre entreprises » était-elle la bonne ?**
R : En partie : bon générateur d'événements, mais risque de choisir un domaine parce que la donnée existe plutôt que parce qu'un client souffre. On a corrigé avec une grille de notation explicite. ✅

**Q : Comment choisit-on un domaine de façon rigoureuse ?**
R : Grille notée : douleur, valeur de la fraîcheur, pourquoi un agent, données, preuve chiffrable, démo, différenciation, faisabilité, avantage de l'équipe. ✅

---

## 2. Pourquoi un agent (et pas des règles)

**Q : Pourquoi un LLM pour mettre une pub en pause quand le stock est à 0 ?**
R : Il n'en faut pas : un fast path déterministe (Sentinel) agit en < 5 s. Le LLM n'intervient que là où il y a un vrai arbitrage. ✅

**Q : Dans quels cas un agent apporte-t-il une vraie plus-value ?**
R : Quand l'événement est ambigu, qu'il y a plusieurs leviers, que les données sont dans plusieurs silos, qu'il y a une dimension temporelle et que la décision doit être justifiée. ✅

**Q : Un exemple concret où l'agent bat le repricer ?**
R : Un concurrent baisse de 15 %. Le repricer s'aligne. L'agent détecte un déstockage et notre rupture imminente, cible un coupon sur les seuls chasseurs de prix et réalloue la pub vers un substitut en surstock. ✅

**Q : Le LLM calcule-t-il lui-même les chiffres (élasticité, prévision) ?**
R : Non, jamais. Les chiffres viennent de modèles exposés comme outils. Le LLM orchestre, compare et décide. ✅

**Q : Le LLM traite-t-il le flux brut ?**
R : Non. ClickHouse filtre et détecte les anomalies. L'agent ne reçoit que des alertes et interroge des outils. ✅

---

## 3. Agents & outils

**Q : Mono-agent ou multi-agent ?**
R : Multi-agent par temporalité : Sentinel (règles, < 5 s), Strategist (LLM, enquête et décide), Auditor (LLM, réévalue après coup). ✅ 🟡

**Q : Les modèles de segmentation, de prévision, etc. sont-ils des agents ?**
R : Non, ce sont des outils déterministes. Les appeler « agents » serait inexact. ✅

**Q : Pourquoi ne pas faire un agent par silo (Pricing, Ads, Supply) ?**
R : C'est plus lent, plus coûteux et plus fragile en hackathon. On le garde en P2 pour illustrer le pitch des silos. 🟡

**Q : Quels modèles comme outils ?**
R : P0 : prévision de demande, élasticité prix, substituts, `simulate_action`. P1 : segmentation et offre ciblée. P2 : CLV, churn. 🟡

**Q : Quel est l'outil le plus important ?**
R : `simulate_action`. L'agent compare des options chiffrées en profit net au lieu de « penser que ». ✅

**Q : Donner du SQL libre à l'agent ?**
R : Des outils typés en priorité ; du SQL en lecture seule seulement comme échappatoire (utilisateur DB sans écriture, timeouts). ✅

**Q : Combien d'outils maximum ?**
R : Environ 10 à 12. Au-delà, l'agent choisit moins bien et la démo devient illisible. ✅

**Q : Comment éviter qu'un agent fasse des dégâts ?**
R : Garde-fous sur les actions (variation maximale par heure, budget total constant, cooldown par SKU) et niveau d'autonomie configurable (auto, approbation, suggestion). ✅

**Q : Comment montrer l'autonomie « long-running » ?**
R : L'Auditor revient sur chaque décision 15 min ou 1 h après, mesure l'effet réel, corrige et écrit la leçon en mémoire. ✅

**Q : Comment rendre les décisions explicables ?**
R : Chaque étape (pensée, action, observation) est persistée et affichée en timeline sur le dashboard. ✅

---

## 4. Données

**Q : H&M ou Instacart suffisent-ils ?**
R : Non : pas de dépenses pub, pas de stock (et pour Instacart, ni prix ni vrais timestamps). Ils ne peuvent servir que de catalogue. ✅

**Q : Données réelles ou simulées ?**
R : De vraies données dès que possible (le classement des secteurs en tient compte), et une simulation calibrée et assumée pour ce qui n'existe pas en public. ✅

**Q : Comment éviter que les gains affichés soient fictifs ?**
R : Un simulateur en boucle fermée : les actions de l'agent modifient réellement les clics et les ventes générés. ✅

**Q : Des modèles entraînés sur des données simulées ont-ils un sens ?**
R : Oui, si on injecte une vérité terrain (segments, élasticités). On peut alors mesurer la précision des modèles, ce qui est une preuve de plus. ✅

**Q : Peut-on scraper les prix des concurrents ?**
R : Non (conditions d'utilisation). On utilise de l'open data, des API officielles ou une simulation assumée. ✅

**Q : Préférer des flux publics live ?**
R : Oui quand c'est possible (météo Open-Meteo, RTE, GBFS…) : une démo branchée sur du réel est bien plus convaincante sur le critère « Data at the core ». ✅

**Q : Catalogue d'événements ouvert ou fermé ?**
R : Fermé (environ 11 types) : détection déterministe, démo reproductible, résultats mesurables. ✅

---

## 5. Architecture Aiven

**Q : Pourquoi Kafka ?**
R : Ingestion de flux hétérogènes (ventes, stock, prix, pub, saisies humaines) et découplage producteurs/consommateurs ; le topic `alerts.anomalies` déclenche les agents. ✅

**Q : Pourquoi ClickHouse ?**
R : Fenêtres temporelles et détection d'anomalies sur des centaines de millions de lignes en temps réel ; certaines prévisions simples se font directement en SQL. ✅

**Q : Pourquoi PostgreSQL ?**
R : Le référentiel métier (marges, substituts, réassorts, segments), la mémoire des décisions, et pgvector pour les substituts. ✅

**Q : Pourquoi Valkey ?**
R : Optionnel : cache des features et scores en ligne (segment d'un client, dernier score) à faible latence. 🟡

**Q : Comment mesurer la preuve (« Evidence it works ») ?**
R : Contrefactuel avec la même seed sous 3 stratégies (rien, repricer à règles, agent), comparées sur marge nette, gaspillage, budget brûlé et temps de réaction. ✅

---

## 6. Choix du secteur

**Q : Quels autres domaines prennent des décisions sur des événements live ?**
R : Logistique, aérien, énergie, hôtellerie, fraude, supply chain, mobilité, retail, restauration, santé… ✅ exploré

**Q : Le carburant (open data live) est-il un bon choix ?**
R : Données parfaites, mais un seul levier (le prix) et peu de valeur à réagir à la minute. Un agent y est peu justifié. ✅ écarté

**Q : L'énergie est-elle un bon choix ?**
R : Données et douleur excellentes, mais un optimiseur mathématique bat un LLM sur la planification. Alignement moyen. ✅ écarté comme cible principale

**Q : La crypto ou le trading ?**
R : Jury lassé, et la latence d'un LLM est inadaptée. ✅ écarté

**Q : Quel secteur ressort en tête ?**
R : Grande distribution, produits frais (14/15) : même architecture que notre piste, mais avec de vraies données massives (Favorita, M5) et la météo live. 🟡

**Q : Et notre piste e-commerce multi-canal ?**
R : Pitch et alignement parfaits, mais données faibles (concurrents et pub simulés). Elle devient une option secondaire ou un format « solopreneur ». 🟡

**Q : Pourquoi ne pas viser l'hôtellerie, Airbnb ou l'aérien ?**
R : Ajuster le prix à la demande est le cœur de leur métier, déjà traité par des outils matures. Difficile de prouver que le problème est mal adressé. ✅ écarté

**Q : Qu'est-ce qu'un problème « mal adressé » ?**
R : Process manuel ou périodique alors que les signaux arrivent en continu, outils réservés aux grands comptes, décideur non spécialiste, coût réel mais sans responsable désigné. ✅

**Q : Pourquoi regarder la finance, mais pas le trading ?**
R : L'idée était de viser des sous-secteurs où l'information bouge plus que les prix (risque client, conformité). Mais ils sont quotidiens, donc éliminés par le critère temps réel (voir plus bas). ✅

**Q : Qu'est-ce qui justifie vraiment le temps réel et Kafka ?**
R : Des événements au moins plusieurs fois par jour (idéalement toutes les secondes à 10 min) et une valeur de décision qui se perd en minutes ou en heures. Quotidien ou moins = batch. ✅ critère éliminatoire

**Q : Le risque client B2B est-il du temps réel ?**
R : Non : le BODACC est quotidien et les paiements aussi. Problème réel et mal adressé, mais Kafka n'y est pas justifié. ✅ éliminé

**Q : Et les pénuries de médicaments ?**
R : Données quotidiennes ou hebdomadaires (ANSM, épidémiologie). Ce n'est pas du temps réel. ✅ éliminé

**Q : Quels sous-secteurs financiers sont vraiment temps réel hors trading ?**
R : Ceux liés aux transactions : opérations de paiement (taux d'acceptation, routage) et instruction des alertes de fraude ; et l'assurance pendant une crise climatique. 🟡

**Q : Les événements et les décisions doivent-ils avoir la même fréquence ?**
R : Non : les événements arrivent à la seconde (caisses), le streaming les agrège, et l'agent décide toutes les 1 à 2 h (fournée, démarque). ✅

**Q : Si l'historique permet déjà de prévoir, que rapporte le temps réel ?**
R : Uniquement la correction de l'écart entre prévision et réalité (chocs imprévisibles), tant qu'il reste des leviers pour agir. Valeur = écart × part encore actionnable × coût unitaire de l'erreur. ✅

**Q : Comment prouver au jury que le temps réel apporte plus que l'historique ?**
R : La comparaison de référence est « la meilleure décision prise avec les données d'hier », pas « rien ». L'écart mesuré est la valeur du temps réel. ✅

**Q : Frais en magasin : l'historique ne suffit-il pas ?**
R : Pour les commandes fournisseurs, si. Le temps réel ne vaut que pour les décisions intra-journée (fournées, démarques) : les ventes du matin corrigent la prévision quand il reste des leviers. 🟡

**Q : E-commerce : l'historique ne suffit-il pas ?**
R : Pour la stratégie, si. Le temps réel vaut sur les anomalies imprévisibles (rupture pendant un pic, tunnel de paiement cassé, mouvement concurrent) où la pub brûle de l'argent à la minute. 🟡

**Q : Crise climatique : l'historique ne suffit-il pas ?**
R : Les modèles catastrophes historiques estiment les pertes moyennes, mais pas l'empreinte réelle de l'orage en cours. Le temps réel permet prévention, tri des sinistres et détection de fraude, mais c'est épisodique. 🟡

**Q : La fusion d'informations militaires (champ de bataille) est-elle un bon sujet ?**
R : Le besoin est réel, mais le secteur est déjà investi (Palantir, Anduril, Helsing), les données sont classifiées et le sujet est éthiquement sensible. On en garde la version civile : la salle de crise. ✅ écarté

**Q : Le trading sur actualités, discours et climat est-il un bon sujet ?**
R : C'est très adressé (fonds quantitatifs et fournisseurs d'analyse d'actualités depuis plus de 10 ans) et un LLM est trop lent face au trading haute fréquence. On garde l'idée pour les acteurs exposés aux prix sans desk de trading. ✅ écarté

**Q : Qu'apportent ces exemples comme nouvel axe ?**
R : La fusion temps réel d'informations non structurées (texte, transcriptions, actualités) venant de plusieurs canaux. C'est là qu'un LLM est indispensable, contrairement aux données numériques. ✅

**Q : Quelle version de cet axe est mal adressée ?**
R : Les ETI et organisations publiques sans cellule de veille ni desk : salle de crise supply chain, achats de matières premières, sécurité civile, crise de réputation. 🟡

**Q : L'e-commerce et la fast fashion sont-ils écartés ?**
R : Non. L'e-commerce généraliste est à 19/25 ; la mode en ligne pour les marques moyennes monte à 20/25 grâce aux signaux non structurés (tendances sociales, motifs de retour). Derrière la salle de crise supply chain (23). 🟡

**Q : La fast fashion n'est-elle pas déjà maîtrisée (Shein, Zara) ?**
R : Pour les géants, oui : c'est leur cœur de métier. Pour les marques de mode moyennes, non : elles décident encore sur des tableaux de bord de la veille. 🟡

**Q : Un agent pour la fast fashion n'est-il pas mal vu ?**
R : Risque d'image réel. On le présente comme un outil contre la surproduction et les invendus, que la loi AGEC interdit de détruire. 🟡

**Q : Des outils de vision (VLM) renforcent-ils le temps réel en e-commerce et en mode ?**
R : Oui sur des cas précis : photos de retours (défaut d'un lot détecté en heures), images sociales reliées au catalogue, usure des visuels pub. Sinon, c'est un gadget. 🟡

**Q : Passer chaque image dans un VLM n'est-il pas trop coûteux ?**
R : On filtre en amont : embeddings d'image bon marché pour tout le flux, VLM seulement sur les cas signalés. Même principe que « pas de LLM sur le flux brut ». ✅

**Q : Une veille mode en temps réel par similarité d'images a-t-elle un intérêt ?**
R : Oui, comme indicateur avancé de la demande sur des produits sans historique, avec des leviers numériques réversibles (pub, mise en avant, email). La valeur est forte pendant un moment viral, plus faible sur les tendances de fond. 🟡

**Q : Le buzz social prédit-il vraiment les ventes de notre marque ?**
R : Pas forcément. L'agent fait de petits paris, mesure l'effet par rapport à un groupe témoin, puis amplifie ou abandonne. Il apprend quels signaux prédisent pour cette marque. ✅

**Q : Ce n'est pas déjà fait par Heuritech ou WGSN ?**
R : Ils prévoient les tendances pour la création et les achats de la saison suivante. Le chaînon manquant est l'activation en direct sur le stock, la pub et la vitrine du site. 🟡

**Q : Peut-on accéder aux images d'Instagram ou TikTok ?**
R : Non (API restreintes, scraping interdit). Pour la démo : flux public de Bluesky, ou flux simulé construit à partir d'images réelles. ❓ risque principal

**Q : La démarque anti-gaspillage en rayon frais est-elle mal adressée ?**
R : En partie seulement (Smartway, Wasteless, Relex existent). Le vrai trou est la production intra-journée en magasin et la restauration collective. 🟡

**Q : Quel risque juridique anticiper ?**
R : Pricing algorithmique et collusion tacite. Notre agent optimise le profit et ne s'aligne pas systématiquement ; toutes ses décisions sont tracées. ✅

---

## 7. Client & format de produit

**Q : Plateforme multi-utilisateurs qui valide en temps réel, ou agent autonome pour un solopreneur ?**
R : Ça dépend de la nature des leviers : leviers numériques (prix en ligne, pub, coupon) = autopilote possible ; actions physiques (étiquettes, rayons) = humains dans la boucle. 🟡

**Q : Comment servir les deux sans deux produits ?**
R : Un noyau commun, avec un niveau d'autonomie configurable par type d'action (auto, approbation, suggestion) selon le montant et le risque. 🟡

**Q : Les humains sont-ils seulement des valideurs ?**
R : Non : ils sont aussi des capteurs. Leurs saisies (« frigo en panne », « événement local ») deviennent des événements Kafka que l'agent exploite. 🟡

---

## 8. Décision finale

**Q : Quels projets ont le plus de chances de devenir un produit concret, avec un client et une douleur concrets ?**
R : 1) Agent de pilotage commercial pour marques de mode en ligne moyennes. 2) Salle de crise supply chain pour ETI. 🟡

**Q : Pourquoi la mode en n°1 ?**
R : L'acheteur est clair (responsable e-commerce), achète vite (applis Shopify), les leviers sont numériques et le gain se prouve en heures avec un groupe témoin. ✅

**Q : Pourquoi la supply chain en n°2 et pas en n°1 ?**
R : Meilleures données réelles et meilleur argument « pourquoi un agent », mais cycle de vente long, intégration ERP lourde et preuve chiffrée plus lente à obtenir. ✅

**Q : Pourquoi pas l'information voyageurs ou la fraude au virement ?**
R : Information voyageurs : client public, cycle d'achat très long. Fraude au virement : données entièrement simulées et douleur ponctuelle. ✅

---

## 9. Protocole de test

**Q : Contre quoi compare-t-on l'agent ?**
R : Règles quotidiennes sur les données de la veille (pratique actuelle) et règles fixes déclenchées par les mêmes alertes temps réel. Le premier écart mesure le temps réel, le second le raisonnement. ✅

**Q : Un seul run suffit-il ?**
R : Non : 10 seeds pour le tableau A (moyenne ± écart-type, nombre de runs gagnés), 2 seeds avec le LLM pour le tableau B (coût et lenteur des appels). ✅

**Q : Figer le temps simulé pendant que le LLM réfléchit, est-ce tricher ?**
R : Non : un pas représente 10 min simulées, un appel LLM quelques secondes réelles. L'hypothèse correspond à la réalité. ✅

**Q : Pourquoi la pub a-t-elle des rendements décroissants dans le simulateur ?**
R : Sans cela, la pub serait toujours rentable et augmenter n'importe quel budget gagnerait. Le coût par clic monte au-delà du budget initial, comme sur les vraies plateformes. ✅

**Q : Pourquoi un scénario de fausse tendance ?**
R : Pour tester le raisonnement et pas seulement la vitesse : un pic de posts de 3 comptes robots ne doit pas déclencher de pub. Une règle naïve tombe dans le piège. ✅

**Q : Une règle plus fine (nombre d'auteurs) ne ferait-elle pas pareil ?**
R : Sur ce cas précis, si. La valeur de l'agent est de traiter des cas variés sans écrire une règle par piège, et d'expliquer sa décision. ✅

**Q : Pourquoi un surcoût sur les réassorts ?**
R : Sans coût, réassortir à l'aveugle serait toujours gagnant. Le réassort express coûte 15 % du coût unitaire par pièce, vendue ou non. ✅

---

## 10. Ouvert ❓

- Nom du produit (AdSentry est trop centré Ads).
- Secteur et client final retenus pour la démo.
- Durée du hackathon et taille de l'équipe (périmètre P1).
- Contraintes d'Aiven Runtime (langages, process long-running) et crédits disponibles.
- Licences des datasets (règles Kaggle pour Favorita et M5, Inside Airbnb en CC BY 4.0) à vérifier.
- Modèle LLM et budget d'appels.
- Accès à un vrai utilisateur pour valider la douleur.
