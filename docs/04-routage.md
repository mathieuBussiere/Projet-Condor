# Routage

## Introduction

Le module de routage (routage/) est responsable de la recherche de chemin et de l'évaluation des trajets générés. À l'aide d'une grille d'élévation (DEM), d'une grille de multiplicateurs de terrain OSM, il calcule un itinéraire optimal entre deux points en minimisant un coût physique basé sur le relief et la difficulté du terrain.

## Organisation du code dans routage/

- routage/
  - a_star.py
  - simplify.py

---

## simplify.py

### Fonction simplifier_rdp

- Implémentation de l'algorithme de simplification Ramer-Douglas-Peucker (RDP).
- Réduit le nombre de points d'un chemin tout en préservant sa forme générale.
- Fonctionne sur des coordonnées géographiques (lat, lon).
- La tolérance est exprimée en mètres via le paramètre epsilon_m.
- Les deux extrémités du chemin sont toujours conservées.
- Utilisée à la fin du pipeline de routage pour réduire la taille des trajets retournés.
- Note : epsilon_m contrôle le niveau de simplification. Un epsilon de 5 m signifie que tout point supprimé reste à moins de 5 m d’un segment conservé. Plus epsilon est grand, plus le chemin final contient peu de points.

### Fonction projectlocal_xy

- Convertit des coordonnées géographiques en coordonnées locales (x, y) exprimées en mètres.
- Utilisée pour permettre les calculs géométriques du RDP.
- Comme les points sont en lat/lon, ils sont d’abord projetés localement en mètres.
- Cette projection simple est acceptable pour une petite zone de randonnée.

### Fonction perpendiculardistance

- Calcule la distance perpendiculaire d'un point à la droite formée par line_start et line_end. Si les deux extrémités sont identiques, elle retourne simplement la distance euclidienne au point.
- Sert à déterminer quels points doivent être conservés par l'algorithme RDP.

---

## a_star.py

### Introduction

Ce fichier contient l'implémentation principale du système de routage.
Il regroupe : l'algorithme A*, le calcul des coûts de déplacement, des fonctions de comparaison de chemins, des utilitaires de conversion de coordonnées. Les calculs physiques reposent sur les fonctions définies dans :

```python
cost_model.physique
```

afin que le coût utilisé par le routage soit exactement le même que celui affiché dans les cartes de coût.

### Fonction voisins

- Retourne les 8 cellules voisines d'une cellule donnée.
- Autorise les déplacements dans les huit directions de la grille, déplacements horizontaux, verticaux et diagonaux parce qu'un randonneur peut se déplacer dans ces 8 directions.
- Dans les boucles de A*, chaque voisin est ensuite filtré : hors limites, déjà fermé, obstacle infranchissable ou coût impossible.

### Fonction heuristique

- L’heuristique évalue le coût minimal approximatif entre une cellule a et l’objectif b.
- Elle utilise une distance adaptée à une grille à 8 directions : on prend autant de diagonales que possible, puis on complète avec des mouvements droits.
– Le facteur 0.9 rend l’heuristique volontairement optimiste. Une heuristique admissible ne doit jamais surestimer le vrai coût optimal restant. Ici, elle suppose un terrain parfait, sans obstacle et à vitesse maximale.

### Fonction cout_arrete

- Calcule le coût physique d'un déplacement entre la cellule courante et la cellule voisine.
- Prend en compte : la distance parcourue, la pente, la vitesse de Tobler, la difficulté du terrain OSM, l'altitude.
- Le coût n'est pas symétrique : monter et descendre n'ont pas le même coût.
- Exemple d'un calcul de coût de déplacement entre current -> v :
    1. Vérifier obstacle OSM
    2. Calculer dz signé
    3. Choisir distance : orthogonale ou diagonale
    4. Calculer pente = dz / distance
    5. Vitesse = Tobler(pente)
    6. Pénalité altitude sur la destination
    7. coût = temps  difficulté terrain  difficulté altitude

### Fonction a_star

- Cherche le chemin de coût minimal entre une cellule de départ et une cellule d'arrivée.
- Implémentation principale de l'algorithme A*. Elle utilise une file de priorité open_list, un dictionnaire g pour les coûts connus, un dictionnaire parent pour reconstruire le chemin et un closed_set pour éviter de retraiter les nœuds déjà finalisés.
- Voici la structure interne de A* : 
    - open_list : prochains nœuds à explorer, triés par f
    - closed_set : nœuds déjà finalisés
    - g[n] : meilleur coût connu du départ jusqu’à n
    - parent[n] : prédécesseur de n pour reconstruire le chemin
- La relaxation est le mécanisme central : si on trouve un chemin moins coûteux vers v, on met à jour g[v], on mémorise current comme parent, puis on replace v dans la file de priorité.
- Lorsque goal est rencontré, le code reconstruit le chemin à partir du dictionnaire parent. On part de goal, puis on remonte jusqu’à start.
- Retourne une liste de cellules (row, col) représentant le chemin trouvé.

### Fonction relaxer_voisins

- Factorise la logique de traitement des voisins. Elle reprend la logique de la boucle for v in voisins(current), mais la rend paramétrable pour fonctionner en forward ou en backward. Elle met aussi à jour un meilleur chemin dès qu’un nœud est connu par l’autre sens.
- Exemple d'une recherche bidirectionnelle :

```
start ---> ---> ---> M <--- <--- <--- goal
                     ^
                     |
                 rencontre
Coût candidat = g_forward[M] + g_backward[M]
```

- g_heap sert à connaître rapidement le plus petit coût g encore ouvert. Cela permet d’appliquer une condition d’arrêt efficace sans scanner toute la file open_list.
- Conçue pour être réutilisée par un futur A* bidirectionnel.

### Fonction simplifier_chemin

- Cette fonction retire les points intermédiaires qui ne changent pas la direction du chemin. Elle ne garde que les virages.
- Contrairement à RDP, elle exige un alignement parfait.
- Une limite importante : cette fonction retourne seulement les points intermédiaires conservés, sans départ ni arrivée. Pour produire un chemin complet, il faut réajouter les extrémités si nécessaire.

### Fonction calculer_cout_tobler

- Cette fonction estime après coup le temps Tobler d’un chemin exprimé en latitude/longitude.
- Retourne le temps de parcours estimé en heures.
- Elle sert surtout à l’évaluation, à la comparaison avec un GPX humain et au calcul du ratio d’effort.
- Voici un résumé de l'évaluation d'un segment géographique:
    - Distance horizontale : Haversine
    - Pente : dz/distance
    - Vitesse : Tobler (pente)
    - Temps : distance / vitesse

### Fonction calculer_distance_frechet

- Calcule la distance de Fréchet discrète entre deux trajectoires.
- Retourne une mesure de similarité géométrique en mètres.
- Elle mesure une sorte de distance maximale entre deux trajectoires, comme une laisse entre une personne et son chien.
- Le résultat peut être interprété comme ceci : Un ratio inférieur à 1 signifie que le chemin trouvé est moins coûteux que la référence. Un ratio supérieur à 1 signifie que le chemin A* est plus difficile ou plus long en effort estimé.

### Fonction comparer_chemins

- Calcule différentes mesures de similarité entre deux trajets.
- Compare deux chemins. Un donné en référence et l'autre calculé à l'aide de A*.

### Fonction score_qualite_chemin

- C'est la méthode principale de la comparaison de chemins. Elle produit un résumé des métriques de qualité d'un chemin.
- Combine les mesures géométriques et l'effort physique.
- Voici quelques indicateurs :
    - Score 0-100 : plus haut = meilleur
    - Fréchet < 500 m = bon, > 2000 m = mauvais
    - Effort ratio < 1 = bonus, > 1.2 = pénalité

### Fonction ratio_effort

- Compare l'effort physique d'un trajet calculé avec A* à une trajectoire de référence avec la méthode calculer_cout_tobler.
- Voici des indicateurs :
    - < 1.0 → A* trouve un chemin moins difficile que la référence.
    - 1.0 → effort identique
    - > 1.0 → A* est plus dur que le sentier humain.

### Fonction traduire_colrow_vers_latlon

- Convertit un chemin exprimé en coordonnées (row, col) vers des coordonnées (lat, lon).
- Note : cette conversion est nécessaire pour l'affichage du chemin dans l'interface utilisateur.

### Fonction snap_to_traversable

- Si le point de départ ou d'arrivée tombe sur une cellule infranchissable, recherche automatiquement la cellule franchissable la plus proche.
– Le périmètre le plus grand est de 20 cases de grille.

### Fonction decimerpas_m

- Réduit la densité d'un chemin en supprimant les points trop rapprochés. Elle décime un chemin lat/lon pour que les points consécutifs soient espacés d'au moins pas_m mètres.
- Nécessaire avant calculer_cout_tobler : un GPX dense (points aux ~5 m) lu contre un DEM à 30 m attribue tout le dénivelé d'une cellule à un micro-segment au franchissement de chaque frontière de cellule, ce qui crée des pentes fictives de 50-100 % et gonfle le coût de ~2x.
- Utilisée avant certaines métriques de comparaison (ratio_effort).

### Fonction recherche_meilleur_chemin

- Méthode principale du module de routage.
- Reçoit : la grille des multiplicateurs OSM, le DEM, le transform affine, les positions de départ et d'arrivée.
- Effectue le pipeline suivant : exécution de A*, simplification du chemin, conversion de (col, row) vers (lat, lon), application du RDP.