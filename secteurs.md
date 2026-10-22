# Analyse des secteurs

> Pour chaque secteur : **(1)** les événements temps réel, **(2)** pourquoi la solution exige de croiser de nombreuses données live, **(3)** l'impact monétaire de la décision prise par l'agent à l'instant *t*.
>
> ⚠️ **Les chiffres sont des ordres de grandeur et des hypothèses de calcul** pour un client type, à valider et sourcer avant le pitch. Seuls les montants réglementaires (ex. EU261) sont des faits établis.

---

## Synthèse

| # | Secteur | Alignement | Douleur | Données | Total /15 | Levier principal | Format naturel |
|---|---|---|---|---|---|---|---|
| 1 | Grande distribution, produits frais | 5 | 5 | 4 | **14** | Démarque, commande, offre ciblée | Copilote collaboratif + tâches terrain |
| 2 | Hôtellerie / location courte durée | 5 | 4 | 4 | **13** | Prix par nuit, canaux, durée de séjour | Autopilote |
| 3 | Énergie, flexibilité | 3 | 5 | 5 | **13** | Charge/décharge, décalage | Autopilote avec garde-fous |
| 4 | E-commerce multi-canal | 5 | 4 | 2 | **11** | Prix, pub, coupon | Autopilote (solo) / copilote (marque) |
| 5 | Aérien, perturbations | 4 | 5 | 2 | **11** | Rebooking, appareils, équipages | Copilote avec validation |
| 6 | Mobilité partagée | 3 | 3 | 5 | **11** | Rééquilibrage, incitations | Copilote + tâches terrain |
| 7 | Quick commerce / dark stores | 5 | 4 | 1 | **10** | Assortiment, temps promis, prix | Copilote + tâches terrain |
| 8 | Logistique / transport routier | 4 | 4 | 2 | **10** | Tournées, affectation, tarifs | Copilote + tâches terrain |
| 9 | Fraude / paiements | 2 | 5 | 3 | **10** | Bloquer, laisser passer, escalader | Copilote analyste |
| 10 | Stations-service | 2 | 3 | 5 | **10** | Prix | Autopilote |
| 11 | Santé / hôpital | 4 | 5 | 1 | **10** | Lits, personnel, flux patients | Copilote avec validation |

---

## 1. Grande distribution, produits frais

**Client** : enseigne (siège, magasins, chefs de rayon), franchisés, épiciers indépendants.

### Événements temps réel
- `sales_velocity_drop` / `sales_spike` sur une référence fraîche
- `expiry_approaching` : lot à J-1 ou J-2 avec stock important
- `weather_shift` : canicule, pluie, chute de température (prévision mise à jour)
- `delivery_shortfall` / `delivery_surplus` : livraison fournisseur incomplète ou en excès
- `equipment_failure` : panne de frigo ou de vitrine (saisie humaine)
- `competitor_promo` : promo concurrente dans la zone de chalandise
- `local_event` : match, marché, jour férié, vacances scolaires
- `markdown_ineffective` : démarque appliquée sans effet sur les ventes
- `stock_discrepancy` : écart entre le stock théorique et le comptage du rayon

### Pourquoi croiser de nombreuses données live
Une décision sur un yaourt à J-1 dépend simultanément de :
- **Stock et dates de péremption** par lot (pas seulement le stock total)
- **Vélocité de vente actuelle** contre la prévision (heure, jour, magasin)
- **Météo** des prochaines heures (une canicule fait exploser la demande de salades et de boissons et chuter celle de soupes)
- **Élasticité de la démarque** par catégorie et par magasin (−30 % suffit-il, ou faut-il −50 % ?)
- **Segments clients** de l'application fidélité (qui achète du frais démarqué ? qui est à proximité ?)
- **Commandes fournisseurs en cours** (faut-il réduire la commande de demain ?)
- **Autres magasins** (un transfert est-il possible et rentable ?)
- **Débouchés de dernier recours** (don, plateformes anti-gaspi) et leur valeur fiscale

Une règle fixe (« −30 % à J-1 ») ignore la météo, l'heure, le magasin, le profil client et la commande suivante : elle démarque trop tôt, trop fort ou trop tard.

### Décision à l'instant *t*
> Mardi 17 h, magasin de Lyon. 120 barquettes de fraises à J-1, vélocité à 40 % de la prévision (temps froid inattendu). Prévision : pluie demain.
> L'agent compare : démarque −30 % maintenant (écoule 70, reste 50 jetées) ; offre push −40 % aux 800 clients « frais / fruits » du segment fidélité présents dans un rayon de 3 km (écoule environ 100) ; don des 20 restantes ; **et réduit de 40 % la commande de fraises de jeudi.**
> → Offre ciblée + don + réduction de commande. Tâche poussée au chef de rayon ; le siège est notifié de l'ajustement de commande.

### Impact monétaire
- **Mécanismes** : moins de casse/gaspillage, démarques moins profondes (cibler plutôt que démarquer pour tous), commandes ajustées, ventes sauvées en cas de pic (ruptures évitées), réduction fiscale sur les dons.
- **Ordre de grandeur (hypothèses)** : un hypermarché réalisant 20 M€/an de ventes de frais avec 3 % de démarque et de casse perd environ 600 k€/an. Réduire ces pertes de 20 à 30 % = **120 à 180 k€/an par magasin**, avant tout gain sur les ruptures. Multiplié par un réseau de 100 magasins, cela représente 12 à 18 M€/an.
- **Valeur de la réactivité** : une décision prise à 17 h plutôt qu'à la fermeture laisse 4 heures de vente. Le frais périssable perd sa valeur en heures, pas en jours.

### Données accessibles
Favorita (environ 125 M de lignes de ventes réelles, avec promos et jours fériés), M5/Walmart (environ 30 000 produits, environ 5 ans, avec prix et événements), Open-Meteo (météo live gratuite). Péremption, segments clients et concurrence sont à simuler.

---

## 2. Hôtellerie / location courte durée

**Client** : hôtel indépendant, conciergerie (20 à 200 logements), revenue manager de chaîne.

### Événements temps réel
- `booking_pace_deviation` : rythme de réservation (pickup) au-dessus ou en dessous de la prévision pour une date
- `competitor_rate_change` : le comp set change ses prix
- `competitor_sold_out` : un concurrent est complet sur une date
- `cancellation` / `group_release` : libération de chambres
- `local_event_detected` : concert, salon, match annoncé
- `weather_forecast_change` (loisirs, destinations de plage ou de ski)
- `review_score_drop` : chute de la note après de mauvais avis
- `room_out_of_order` : chambre indisponible (saisie humaine)
- `channel_parity_breach` : un canal affiche un prix inférieur au site direct

### Pourquoi croiser de nombreuses données live
Le prix optimal d'une nuit dépend de :
- **Rythme de réservation** contre l'historique pour le même délai d'anticipation
- **Prix et disponibilité du comp set**, en temps réel
- **Événements locaux et météo**
- **Mix de segments** (affaires, loisirs, groupes) et leur sensibilité au prix
- **Coût par canal** (commission de 15 à 25 % sur les plateformes de réservation, contre 0 % en direct)
- **Contraintes opérationnelles** (chambres hors service, capacité de ménage, durée de séjour)
- **Note et avis**, qui modifient la capacité à tenir un prix

Un outil de pricing classique fixe le prix ; il n'arbitre pas entre canaux, ne lit pas la capacité de ménage et n'explique pas pourquoi le rythme décroche.

### Décision à l'instant *t*
> Mercredi 10 h. Un salon est annoncé dans 3 semaines ; deux concurrents du comp set viennent de passer complets ; le rythme de réservation est 2× au-dessus de la normale pour ces dates.
> L'agent : +35 % sur les nuits concernées, séjour minimum de 2 nuits, **fermeture des tarifs les moins chers sur les plateformes de réservation** et lancement d'une campagne de réservation directe ciblant les visiteurs du salon (segment affaires).

### Impact monétaire
- **Mécanismes** : hausse du revenu par chambre disponible (RevPAR), basculement de réservations vers le canal direct (économie de commission), moins de chambres vendues trop tôt ou trop peu cher.
- **Ordre de grandeur (hypothèses)** : un hôtel indépendant de 50 chambres, à 70 % d'occupation et 120 € de prix moyen, réalise environ 1,5 M€/an. +5 à 10 % de RevPAR = **75 à 150 k€/an** ; chaque point de réservations basculé vers le direct économise environ 15 à 25 % de commission sur ces ventes.
- **Valeur de la réactivité** : quand un concurrent passe complet, les heures qui suivent sont celles où l'on peut vendre plus cher ; réagir le lendemain, c'est avoir déjà vendu au mauvais prix.

### Données accessibles
Inside Airbnb (vraies annonces et calendriers de prix, instantanés périodiques, licence CC BY 4.0 à vérifier), Hotel Booking Demand (environ 119 000 réservations réelles), APIs d'événements (OpenAgenda, Ticketmaster), Open-Meteo.

---

## 3. Énergie, flexibilité (batteries, flottes de véhicules électriques, sites industriels)

**Client** : gestionnaire de flotte électrique, site industriel avec stockage, agrégateur de flexibilité.

### Événements temps réel
- `spot_price_spike` / `negative_price` : pic ou prix négatif sur le marché
- `grid_tension_signal` (signal d'effacement, alerte de tension du réseau)
- `solar_forecast_change` : variation de la production solaire prévue
- `vehicle_low_soc` : batterie d'un véhicule basse avant une mission
- `mission_schedule_change` : planning de tournée modifié
- `carbon_intensity_change` : variation du contenu carbone du mix
- `charger_fault` : borne en panne

### Pourquoi croiser de nombreuses données live
Il faut croiser prix spot, prévision météo et solaire, contraintes métier (missions, horaires), état des batteries, tarifs d'acheminement réseau et contraintes contractuelles d'effacement. **Mais** un optimiseur mathématique (programmation linéaire) résout la planification mieux qu'un LLM : la valeur de l'agent se limite aux **exceptions** (mission urgente, panne, conflit entre contraintes) et à l'explication.

### Décision à l'instant *t*
> 18 h : pic de prix spot, signal de tension du réseau. 12 véhicules en charge, dont 3 partent à 6 h pour des missions longues.
> L'agent : suspend la charge de 9 véhicules jusqu'à 23 h (prix bas), maintient les 3 véhicules prioritaires, et propose un effacement rémunéré à l'agrégateur.

### Impact monétaire
- **Mécanismes** : facture d'énergie réduite, revenus d'effacement, pénalités évitées, CO₂ évité.
- **Ordre de grandeur (hypothèses)** : une flotte de 100 véhicules utilitaires consommant environ 1 GWh/an. Décaler la charge vers les heures creuses peut faire gagner de 10 à 25 % sur le coût d'énergie, soit des dizaines de k€/an, plus les revenus d'effacement.
- **Limite** : l'essentiel de ce gain est capté par un optimiseur, pas par le raisonnement d'un LLM.

### Données accessibles
RTE éCO2mix, ENTSO-E Transparency (prix, production, consommation), Open-Meteo : **réelles et live**. Flotte et missions à simuler.

---

## 4. E-commerce multi-canal / vendeurs marketplace

**Client** : solopreneur Shopify, marque de 5 à 50 M€, agence e-commerce.

### Événements temps réel
- `competitor_price_drop` / `competitor_price_raise`, `competitor_stockout`, `competitor_promo_launch`, `new_competitor_offer`
- `stockout` / `burn_without_stock`, `low_stock_runway`, `overstock_aging`
- `ad_cost_spike` / `roas_collapse`
- `buybox_lost` / `rank_drop`
- `demand_spike`

### Pourquoi croiser de nombreuses données live
La réponse à un même événement (le concurrent baisse son prix) dépend de son stock à lui, du mien, de la date de réassort, des segments qui achètent, de l'élasticité, des dépenses pub en cours, des substituts en surstock et de la marge réelle. Ces données sont réparties entre 4 outils (repricer, Ads, ERP, finance) qui ne se parlent pas.

### Décision à l'instant *t*
> Un concurrent baisse de 15 %. Diagnostic : déstockage. Notre stock couvre 6 jours, le réassort arrive dans 12.
> L'agent : prix inchangé, coupon ciblé sur les seuls chasseurs de prix, budget pub réalloué vers un substitut en surstock, réévaluation programmée au moment de la rupture du concurrent.

### Impact monétaire
- **Mécanismes** : marge préservée (pas d'alignement inutile), budget pub non gaspillé, surstock écoulé, ruptures évitées.
- **Ordre de grandeur (hypothèses)** : une marque de 10 M€ de CA avec 1,5 M€/an de pub. Récupérer 5 à 10 % du budget gaspillé (75 à 150 k€) plus 1 point de marge brute (100 k€) = **175 à 250 k€/an**.
- **Valeur de la réactivité** : chaque heure de pub sur un produit épuisé ou mal positionné est perdue ; lors d'un pic (influenceur, soldes), on parle de quelques heures.

### Données accessibles
Olist, H&M, Retailrocket (clickstream) pour le catalogue et les ventes. **Concurrents et pub à simuler**, c'est le point faible.

---

## 5. Aérien, gestion des perturbations

**Client** : centre de contrôle des opérations d'une compagnie.

### Événements temps réel
- `flight_delay`, `aircraft_aog` (avion immobilisé au sol), `crew_timeout` (dépassement du temps de service légal)
- `weather_closure`, `atc_restriction` (restriction du contrôle aérien)
- `missed_connections_predicted`, `overbooking`, `gate_conflict`

### Pourquoi croiser de nombreuses données live
Il faut croiser positions des avions, état des équipages (temps de service), correspondances des passagers, statut et valeur de chaque passager, disponibilité des appareils de réserve, créneaux aéroportuaires et règles d'indemnisation. Une décision locale (retarder un vol) a des effets en cascade sur toute la journée.

### Décision à l'instant *t*
> Le vol A arrive avec 50 min de retard ; 38 passagers ont une correspondance sur le vol B.
> L'agent : faire attendre B 20 min (impact acceptable sur les vols suivants) plutôt que rebooker 38 passagers, ce qui évite des indemnités et l'hébergement.

### Impact monétaire
- **Mécanismes** : indemnités évitées, hébergement et rebooking évités, rotations préservées.
- **Fait réglementaire** : l'EU261 impose 250, 400 ou 600 € par passager selon la distance (au-delà de 3 h de retard ou en cas d'annulation, hors circonstances extraordinaires).
- **Ordre de grandeur** : un seul vol de 180 passagers annulé peut coûter des dizaines de milliers d'euros (jusqu'à environ 100 k€ avec l'hébergement et le rebooking).
- **Limite** : les données internes (équipages, passagers) sont inaccessibles.

### Données accessibles
OpenSky (positions ADS-B live), historique de ponctualité BTS (États-Unis). Équipages, passagers et prix sont fermés.

---

## 6. Mobilité partagée (vélos, trottinettes)

**Client** : opérateur de vélos ou trottinettes en libre-service, collectivité.

### Événements temps réel
- `station_empty_predicted` / `station_full_predicted`
- `demand_surge` (sortie de bureaux, fin de concert)
- `weather_change` (pluie : la demande s'effondre)
- `truck_available`, `vehicle_fault`, `transit_disruption` (grève, panne de métro)

### Pourquoi croiser de nombreuses données live
Il faut croiser l'état des stations, la prévision de demande par station, la météo, les événements, les perturbations des transports en commun, la position et la capacité des camions de rééquilibrage. Mais un algorithme d'optimisation de tournées couvre une grande partie du besoin.

### Décision à l'instant *t*
> Panne de métro à 18 h, ligne 1. L'agent anticipe que les stations autour seront vidées, redirige 2 camions et active un bonus pour les usagers qui déposent un vélo dans ces stations.

### Impact monétaire
- **Mécanismes** : pénalités contractuelles évitées (stations vides ou pleines), revenus de trajets non perdus, km de camion économisés.
- **Ordre de grandeur (hypothèses)** : un réseau de 1 000 stations ; quelques % de trajets perdus en moins et des pénalités évitées = **centaines de k€/an**. Valeur moindre que les secteurs du haut du classement.

### Données accessibles
GBFS (Vélib', Citi Bike…) : **réel et live**, mis à jour chaque minute. GTFS-Realtime (transports en commun), Open-Meteo.

---

## 7. Quick commerce / dark stores

**Client** : opérateur de dark stores, restaurant présent sur plusieurs plateformes.

### Événements temps réel
- `item_stockout`, `order_surge`, `picker_shortage`, `courier_shortage`
- `promised_eta_breach` : délai de livraison promis dépassé
- `competitor_fee_change` : frais de livraison concurrents
- `weather_change` (la pluie fait monter la demande)

### Pourquoi croiser de nombreuses données live
Il faut croiser stock par entrepôt, préparateurs et livreurs disponibles, demande prévue, météo, temps de livraison promis, prix et frais concurrents. Les décisions (fermer une zone, rallonger le délai promis, retirer des produits) ont un effet immédiat sur la conversion et sur la note.

### Décision à l'instant *t*
> Pluie à 19 h, demande en hausse de 60 %, 3 livreurs manquants.
> L'agent : rallonge le délai promis de 10 min, réduit le périmètre de livraison et retire les produits encombrants, ce qui préserve la note et évite les annulations.

### Impact monétaire
- **Mécanismes** : commandes non annulées, remboursements évités, note préservée, moins de casse.
- **Ordre de grandeur (hypothèses)** : un dark store réalise quelques M€/an ; chaque soir de pic mal géré peut coûter plusieurs k€ en annulations et remboursements.

### Données accessibles
Très faibles : Instacart (commandes sans prix ni vrais timestamps). Presque tout est à simuler.

---

## 8. Logistique / transport routier

**Client** : transporteur, commissionnaire, logistique du dernier kilomètre.

### Événements temps réel
- `vehicle_breakdown`, `driver_delay`, `traffic_incident`
- `customer_absent`, `urgent_order_inserted`, `parcel_damaged`
- `fuel_price_change`, `spot_freight_offer` (offre de fret à prix spot)

### Pourquoi croiser de nombreuses données live
Il faut croiser positions GPS, trafic, fenêtres de livraison des clients, SLA et pénalités, capacité des véhicules, temps de conduite légal, prix du gazole et offres de fret du marché spot.

### Décision à l'instant *t*
> Le camion 7 tombe en panne avec 60 colis, dont 12 sous SLA premium.
> L'agent : répartit les 12 colis premium sur 2 tournées voisines, reporte les autres au lendemain avec notification des clients, et commande un dépannage.

### Impact monétaire
- **Mécanismes** : pénalités de SLA évitées, deuxièmes passages évités, km et heures de conduite économisés.
- **Ordre de grandeur (hypothèses)** : pour un transporteur de 100 véhicules, quelques % de km et de pénalités évités = **centaines de k€/an**.

### Données accessibles
Prix des carburants (open data français, live), trafic (APIs commerciales), AIS pour le maritime. Les données internes de tournées sont à simuler.

---

## 9. Fraude / paiements

**Client** : prestataire de paiement, néobanque, e-commerçant à fort volume.

### Événements temps réel
- `transaction_scored_high_risk`, `velocity_anomaly` (rafale de transactions)
- `new_device`, `geo_mismatch`, `chargeback_received`
- `account_network_link` : lien avec un compte déjà frauduleux

### Pourquoi croiser de nombreuses données live
Il faut croiser historique du client, appareil, géolocalisation, réseau de comptes liés et comportement de navigation. **Mais** il s'agit d'une classification (bloquer ou non) plutôt que d'un arbitrage entre plusieurs leviers ; l'agent sert surtout à **instruire les alertes** pour les analystes.

### Décision à l'instant *t*
> Alerte sur un paiement de 2 400 €. L'agent enquête (appareil connu, géolocalisation cohérente, client fidèle depuis 4 ans) : c'est un faux positif probable. Il laisse passer avec une authentification forte plutôt que de bloquer.

### Impact monétaire
- **Mécanismes** : moins de fraude passée, **moins de faux positifs** (ventes légitimes refusées), temps des analystes économisé.
- **Ordre de grandeur (hypothèses)** : les faux positifs coûtent souvent plus en ventes perdues que la fraude elle-même ; quelques points de faux positifs en moins valent des M€ pour un gros acteur.

### Données accessibles
PaySim (synthétique), IEEE-CIS Fraud (Kaggle, réel anonymisé). Pas de flux live.

---

## 10. Stations-service

**Client** : station indépendante, réseau régional, stations de supermarchés.

### Événements temps réel
- `competitor_price_change` dans un rayon de X km
- `wholesale_price_change` : variation du prix de gros
- `tank_level_low` : cuve basse
- `traffic_pattern_change` (vacances, départs en week-end)

### Pourquoi croiser de nombreuses données live
Il faut croiser les prix des concurrents proches, le prix de gros, le niveau de cuve et la fréquentation. Mais **un seul levier** (le prix) et des changements de prix peu fréquents (environ une fois par jour) : une règle ou un modèle d'élasticité suffit souvent.

### Décision à l'instant *t*
> Une station de supermarché à 2 km baisse le gazole de 4 centimes. L'agent : baisse de 2 centimes seulement (au-delà de 3 centimes d'écart, le volume chute de 30 % d'après l'historique), réévaluation dans 2 h.

### Impact monétaire
- **Mécanismes** : marge par litre préservée, volume maintenu.
- **Ordre de grandeur (hypothèses)** : une station vendant 3 M L/an ; +0,5 c/L de marge moyenne = **15 k€/an**. Impact modeste par station.

### Données accessibles
prix-carburants.gouv.fr (environ 10 000 stations, rafraîchi toutes les ~10 min) : **réel, live, gratuit, légal**. Historique annuel disponible pour un backtest.

---

## 11. Santé / gestion hospitalière

**Client** : direction des opérations d'un hôpital, gestionnaire de lits.

### Événements temps réel
- `ed_surge` : afflux aux urgences
- `bed_shortage_predicted` : manque de lits prévu
- `discharge_delayed` : sortie de patient retardée
- `staff_absence`, `patient_deterioration` (signes vitaux)
- `epidemic_signal` (grippe, bronchiolite)

### Pourquoi croiser de nombreuses données live
Il faut croiser l'occupation des lits par service, les sorties prévues, le flux des urgences, le personnel disponible, les signaux épidémiques et l'état clinique des patients.

### Décision à l'instant *t*
> Lundi 9 h, afflux aux urgences prévu (épidémie de grippe) et 6 lits manquants en médecine. L'agent identifie 8 sorties possibles avant midi si les examens sont accélérés, alerte les équipes et propose de mobiliser une unité tampon.

### Impact monétaire
- **Mécanismes** : moins de patients sur brancard, moins de transferts, durée de séjour réduite, personnel mieux affecté.
- **Ordre de grandeur (hypothèses)** : une journée d'hospitalisation coûte de l'ordre de plusieurs centaines à plus de mille euros ; réduire la durée moyenne de séjour de quelques % représente des M€/an pour un grand hôpital.
- **Limites** : données inaccessibles (MIMIC sous accréditation), forte réglementation, validation clinique obligatoire.

### Données accessibles
MIMIC (accès sous accréditation), données agrégées de Santé publique France (épidémiologie). Inadapté à un hackathon.

---

## Conclusion

- **Grande distribution, produits frais** : le meilleur équilibre entre impact monétaire (centaines de k€ par magasin et par an), nécessité de croiser de nombreuses données live (stock par lot, péremption, météo, segments, commandes) et données réelles massives disponibles.
- **Hôtellerie** : impact solide et leviers 100 % numériques (autopilote), mais des concurrents établis à adresser dans le pitch.
- **E-commerce multi-canal** : le pitch le plus clair sur le thème des silos, mais des données faibles.
- Énergie et stations-service : excellentes données mais un agent peu justifié face à un optimiseur ou à une règle.
- Aérien et santé : impact fort mais données inaccessibles.

---

# Révision : critères « mal adressé » et « vrai temps réel »

## Critère « mal adressé »
Un problème est mal adressé si au moins 2 de ces conditions sont vraies :
1. **Process manuel ou périodique** (Excel, revue mensuelle, intuition) alors que les signaux arrivent en continu.
2. **Outils réservés aux grands comptes**, PME et ETI oubliées.
3. **Décideur non spécialiste** : c'est une tâche annexe de son poste.
4. **Coût réel mais sans responsable désigné**, dilué entre plusieurs services.

Conséquence : hôtellerie, Airbnb et aérien sont **écartés**, car ajuster le prix à la demande est leur cœur de métier, déjà outillé.

## Critère « vrai temps réel » (éliminatoire)
Kafka et le streaming ne se justifient que si **les événements sont fréquents** et que **la valeur de la décision se dégrade vite**.

| Niveau | Fréquence des événements utiles | Exemple | Verdict |
|---|---|---|---|
| **T1** | Toutes les secondes à 30 s | Passages en caisse, clics pub, positions GPS, transactions | ✅ Streaming indispensable |
| **T2** | Toutes les 5 à 10 min | Radar météo, état des stations de vélos, prix de l'énergie au quart d'heure | ✅ Streaming justifié |
| **T3** | Plusieurs fois par jour (toutes les 1 à 2 h) | Fournées, fenêtres de démarque, ajustements de budget pub | ✅ Minimum acceptable |
| **T4** | Quotidien ou moins | Publications BODACC, ruptures ANSM, factures | ❌ **Batch : Kafka non justifié** |

Deux nuances :
- **Le volume agrégé compte.** Un magasin seul génère peu d'événements par minute ; un réseau de 500 magasins en génère des milliers par seconde.
- **Il faut distinguer la fréquence des événements de celle des décisions.** Les événements peuvent arriver toutes les secondes (caisses) et les décisions toutes les 1 à 2 h (fournée suivante). C'est un bon schéma : le streaming agrège, l'agent décide au bon rythme.

## Fréquences réelles par secteur

| Secteur | Événements | Décisions | La valeur se perd en… | Niveau | Verdict |
|---|---|---|---|---|---|
| Risque client B2B | BODACC quotidien, paiements quotidiens, actualités 15 min (rarement pertinentes) | Quotidiennes | Jours | **T4** | ❌ Éliminé |
| Pénuries de médicaments | ANSM et épidémiologie : quotidien à hebdomadaire | Quotidiennes | Jours | **T4** | ❌ Éliminé |
| Restauration collective | Inscriptions J-1, service d'1 h | Quotidiennes | Heures (pendant le service seulement) | T4 / T2 | ❌ Faible |
| **Frais et production en magasin (multi-sites)** | Caisses : secondes ; météo : horaire | Toutes les 1 à 2 h (fournées, démarques) | Heures | **T1 → T3** | ✅ |
| **E-commerce multi-canal** | Clics et dépenses pub : secondes ; commandes : minutes ; prix concurrents : plusieurs fois par jour | Horaires | Minutes à heures | **T1 → T2** | ✅ |
| **Assurance, crise climatique** | Radar 5 min, afflux de déclarations à la minute **pendant l'épisode** | Toutes les minutes à toutes les heures | Heures | **T1-T2 en épisode** | ✅ (épisodique) |
| Logistique dernier kilomètre | GPS 10 à 30 s, scans de colis, trafic | Minutes | Minutes | **T1** | ✅ |
| Quick commerce | Commandes à la minute, GPS des livreurs | Minutes | Minutes | **T1** | ✅ |
| Mobilité partagée | GBFS environ 60 s | 15 à 30 min | Dizaines de minutes | **T1-T2** | ✅ |
| Énergie, flexibilité | Prix et production au quart d'heure | Au quart d'heure | Quart d'heure | **T2** | ✅ |
| Opérations de paiement (taux d'acceptation, routage PSP) | Transactions à la seconde | Minutes | Minutes | **T1** | ✅ |
| Fraude (instruction des alertes) | Transactions à la seconde | Minutes | Minutes | **T1** | ✅ (mais LLM trop lent pour l'autorisation elle-même) |
| Agriculture, gel | Stations météo 5 à 10 min, **quelques nuits par an** | Horaires | Heures | T2 saisonnier | 🟡 |

## Finance : quels sous-secteurs sont vraiment temps réel ?
Les sous-secteurs « où l'information bouge » (risque client, conformité, pénuries) sont **quotidiens**, donc pas temps réel. En finance hors trading, ce qui est vraiment temps réel est lié aux **transactions** :
- **Opérations de paiement** pour les marchands moyens : chute soudaine du taux d'acceptation (panne d'un PSP, vague de refus d'une banque émettrice, échecs 3-D Secure). L'agent diagnostique et agit : routage vers un PSP de secours, ajustement des exemptions 3-D Secure, alerte. Partiellement adressé (orchestrateurs Primer, Spreedly) ; données simulées.
- **Instruction des alertes de fraude** en minutes (pas l'autorisation à la milliseconde). Partiellement adressé (Stripe Radar, Sift).
- **Assurance pendant une crise climatique** : vraiment temps réel pendant l'épisode, avec des données publiques réelles (radar, vigilances, crues).

## Classement consolidé (/25, temps réel éliminatoire en dessous de T3)

| # | Secteur | Alignement | Douleur | Mal adressé | Données | Temps réel | **Total** |
|---|---|---|---|---|---|---|---|
| 1 | **Frais et production intra-journée en magasin (multi-sites)** | 4 | 4 | 5 | 3 | 4 | **20** |
| 2 | **Assurance, gestion de crise climatique** | 5 | 4 | 4 | 3 | 3 | **19** |
| 3 | **E-commerce multi-canal (coordination prix, pub, stock)** | 5 | 4 | 3 | 2 | 5 | **19** |
| 4 | Mobilité partagée | 3 | 3 | 3 | 5 | 5 | 19 |
| 5 | Énergie, flexibilité | 3 | 5 | 2 | 5 | 4 | 19 |
| 6 | Logistique dernier kilomètre (PME transporteurs) | 4 | 4 | 3 | 2 | 5 | 18 |
| 7 | Quick commerce | 5 | 4 | 3 | 1 | 5 | 18 |
| 8 | Opérations de paiement | 4 | 4 | 3 | 1 | 5 | 17 |
| 9 | Fraude (instruction des alertes) | 2 | 5 | 2 | 3 | 5 | 17 |
| — | Risque client B2B | 5 | 5 | 4 | 4 | 1 | ❌ éliminé (T4) |
| — | Pénuries de médicaments | 4 | 5 | 5 | 3 | 1 | ❌ éliminé (T4) |
| — | Restauration collective | 4 | 4 | 5 | 2 | 2 | ❌ éliminé |

À égalité, l'ordre est départagé par « mal adressé » puis par l'alignement. Les notes sont des estimations à challenger.
