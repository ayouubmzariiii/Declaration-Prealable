"""
Modèles de données pour la Déclaration Préalable de Travaux.
Basé sur le formulaire CERFA n°13703*09.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date


@dataclass
class Demandeur:
    """Identité du demandeur (Section 1 du CERFA)."""
    civilite: str = "M."
    nom: str = "Dupont"
    prenom: str = "Jean"
    date_naissance: str = "15/03/1985"
    lieu_naissance: str = "Paris"
    adresse: str = "12 Rue de la République"
    code_postal: str = "75001"
    ville: str = "Paris"
    telephone: str = "06 12 34 56 78"
    email: str = "jean.dupont@email.fr"
    qualite: str = "Propriétaire"


@dataclass
class Terrain:
    """Localisation et caractéristiques du terrain (Section 2 du CERFA)."""
    adresse: str = "25 Chemin des Vignes"
    lieu_dit: str = ""
    code_postal: str = "19100"
    commune: str = "Brive-la-Gaillarde"
    section_cadastrale: str = "AB"
    numero_parcelle: str = "0123"
    superficie_terrain: float = 850.0
    zone_plu: str = "UB"
    est_lotissement: bool = False
    est_zone_protegee: bool = False
    est_monument_historique: bool = False


@dataclass
class TravauxDetail:
    """Détail des travaux envisagés (Section 3 du CERFA)."""
    type_travaux: str = "Modification de l'aspect extérieur"
    description_courte: str = "Ravalement de façade avec remplacement des menuiseries"
    surface_plancher_existante: float = 95.0
    surface_plancher_creee: float = 0.0
    emprise_au_sol_existante: float = 110.0
    emprise_au_sol_creee: float = 0.0
    hauteur_existante: float = 5.5
    hauteur_projetee: float = 5.5
    date_debut_prevue: str = "01/04/2026"
    duree_travaux_mois: int = 3


@dataclass
class AspectExterieur:
    """Aspect extérieur des constructions (Section 4 du CERFA). Rempli par l'IA."""
    facade_materiaux_existants: str = ""
    facade_materiaux_projetes: str = ""
    menuiseries_existantes: str = ""
    menuiseries_projetees: str = ""
    toiture_materiaux_existants: str = ""
    toiture_materiaux_projetes: str = ""
    cloture_existante: str = ""
    cloture_projetee: str = ""
    couleur_facade: str = ""
    couleur_menuiseries: str = ""
    couleur_volets: str = ""
    couleur_toiture: str = ""
    
    # Nouvelles clés d'analyse technique
    nombre_ouvertures_existantes: str = ""
    nombre_ouvertures_projetees: str = ""


@dataclass
class PhotoSet:
    """
    Paire de photos avant/après pour un même emplacement.
    Exemple: la façade principale — avant et après travaux.
    """
    label: str = ""              # Ex: "Façade principale", "Pignon latéral"
    chemin_avant: str = ""       # Chemin vers la photo avant
    chemin_apres: str = ""       # Chemin vers la photo après
    description_avant: str = ""  # Description auto ou manuelle
    description_apres: str = ""


@dataclass
class NoticeDescriptive:
    """Notice descriptive du projet (pièce obligatoire). Rempli par l'IA."""
    etat_initial: str = ""
    etat_projete: str = ""
    justification: str = ""
    insertion_paysagere: str = ""
    impact_environnemental: str = ""
    
    # Nouvelles clés d'analyse technique
    modifications_detaillees: str = ""
    modification_volume: str = ""
    modification_emprise_au_sol: str = ""
    modification_surface_plancher: str = ""
    hauteur_estimee_existante: str = ""
    hauteur_estimee_projete: str = ""
    coherence_architecturale: str = ""
    risques_reglementaires_potentiels: str = ""
    niveau_confiance_global: str = ""


@dataclass
class DeclarationPrealable:
    """Modèle complet d'une Déclaration Préalable de Travaux."""
    reference: str = ""
    date_creation: str = ""

    demandeur: Demandeur = field(default_factory=Demandeur)
    terrain: Terrain = field(default_factory=Terrain)
    travaux: TravauxDetail = field(default_factory=TravauxDetail)
    aspect_exterieur: AspectExterieur = field(default_factory=AspectExterieur)
    notice: NoticeDescriptive = field(default_factory=NoticeDescriptive)

    # Photos — paired sets (before/after of same location)
    photo_sets: list = field(default_factory=list)

    # Pièces jointes requises
    pieces_jointes: dict = field(default_factory=lambda: {
        "DP1": {"nom": "Plan de situation", "fourni": False},
        "DP2": {"nom": "Plan de masse", "fourni": False},
        "DP3": {"nom": "Plan en coupe", "fourni": False},
        "DP4": {"nom": "Plan des façades et des toitures", "fourni": False},
        "DP5": {"nom": "Représentation de l'aspect extérieur", "fourni": False},
        "DP6": {"nom": "Document graphique d'insertion", "fourni": False},
        "DP7": {"nom": "Photographie environnement proche (état existant)", "fourni": False},
        "DP8": {"nom": "Photographie environnement lointain (état projeté)", "fourni": False},
        "DP11": {"nom": "Notice descriptive", "fourni": True},
    })

    def __post_init__(self):
        if not self.reference:
            self.reference = f"DP-{date.today().strftime('%Y%m%d')}-001"
        if not self.date_creation:
            self.date_creation = date.today().strftime("%d/%m/%Y")


def get_dummy_declaration() -> DeclarationPrealable:
    """Retourne une déclaration pré-remplie avec des données fictives."""
    dp = DeclarationPrealable()
    # No photo sets by default — user uploads their own
    return dp
