# Spécifications Techniques : Calcul des Poids de Terrain et Coûts de Routage

Le **poids de terrain** est un coefficient multiplicateur appliqué à la distance physique d'un segment. Il modélise le coût global (temps, effort biologique, contraintes environnementales) d'une progression piétonne. Plus ce poids est élevé, plus l'algorithme $A^*$ privilégiera des itinéraires alternatifs.



---

## 1. La Formule Fondamentale

La vitesse de référence sur un sentier plat et dégagé ($V_{\text{base}}$) est fixée à 5 km/h. Pour tout autre terrain ralentissant le marcheur, le facteur de poids est calculé par l'inversion de la vitesse effective :

$$\text{Facteur de Poids} = \frac{V_{\text{base}}}{V_{\text{terrain}}}$$

---

## 2. Origines Scientifiques des Modèles

### A. Cinématique : Équation de Pandolf (1977)
Pour le hors-piste, nous utilisons l'équation de l'USARIEM pour estimer la puissance métabolique ($M$) :

$$M = 1.5W + 2.0(W+L)\left(\frac{L}{W}\right)^2 + \eta(W+L)(1.5V^2 + 0.35VG)$$

Le coefficient de friction $\eta$ est dérivé des travaux de **Soule et Goldman (1972)**, qui quantifient la résistance au mouvement selon la nature du sol.

### B. Énergétique : Échelle METs
Le coût temporel est ajusté par la dépense énergétique relative :

$$W_{A^*} = \left( \frac{\text{MET}_{\text{terrain}}}{3.5} \right) \times \Phi(\eta)$$

*Où $3.5$ METs est la valeur de référence de la marche modérée sur sol ferme (Ainsworth et al., 2011).*

---

## 3. Tableau de Synthèse (`DEFAULT_WEIGHTS`)

| Terrain | ID | METs | $\eta$ | Multiplicateur ($A^*$) |
| :--- | :--- | :---: | :---: | :---: |
| Sentier | `trail` | 3.5 | 1.0 | **1.00** |
| Route | `road` | 3.0 | 1.1 | **0.85** |
| Pont | `bridge` | - | - | **1.05** |
| Végétation | `vegetation` | 6.5 | 1.5 | **1.85** |
| Roche nue | `bare_rock` | - | 1.6 | **2.00** |
| Éboulis | `scree` | 7.0 | 2.1 | **2.22** |
| Marécage | `wetland` | 8.0 | 1.8 | **2.28** |
| Glacier | `glacier` | 8.0 | 2.1 | **2.28** |
| Arête | `arete` | 8.5 | 2.2 | **2.42** |
| Gué | `water_small` | 8.5 | 2.2 | **2.42** |
| Traversée | `water_crossing`| 9.0 | 2.5 | **2.57** |

---

## 4. Références Bibliographiques
* **Équation de Pandolf (1977) :** [Predicting energy expenditure with loads while standing or walking](https://journals.physiology.org/doi/abs/10.1152/jappl.1977.43.4.577)
* **Coefficient de friction (Soule & Goldman, 1972) :** [Terrain coefficients for energy cost predictions](https://journals.physiology.org/doi/abs/10.1152/jappl.1972.32.5.706)
* **Échelle METs (Ainsworth et al., 2011) :** [Compendium of Physical Activities](https://journals.lww.com/acsm-msse/fulltext/2011/08000/2011_compendium_of_physical_activities.15.aspx)
* **Profils de vitesse OSRM :** [OSRM Foot Profile (`foot.lua`)](https://github.com/Project-OSRM/osrm-backend/blob/master/profiles/foot.lua)
* **Tobler’s Hiking Function (1993) :** [Three Presentations on Geographical Analysis](https://www.geog.ucsb.edu/~tobler/publications/pdf/Three_Presentations.pdf)f human movement on soft substrates*. Journal of Field Robotics.
* **coeficient pour les terrains :**[Velocity-Based Terrain Coefficients for Time-Based Models of Human Movement
Michelle de Gruchy, Edward Caswell and James Edwards](https://intarch.ac.uk/journal/issue45/4/1.html)