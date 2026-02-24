# Déclaration Préalable SaaS

Une application web SaaS (Software as a Service) conçue pour simplifier et automatiser la création des dossiers de Déclaration Préalable de Travaux (DP) en France, en utilisant l'Intelligence Artificielle générative multimodale (vision + texte).

## 🚀 Le Flux (Workflow) de l'Application

L'application guide l'utilisateur à travers un processus en 5 étapes simples :

### Étape 1 : Le Projet
L'utilisateur renseigne les informations administratives de base :
- **Identité du demandeur** (Nom, Prénom, Email, Téléphone)
- **Informations sur le terrain** (Adresse complète, Zone PLU, Référence cadastrale)

### Étape 2 : Les Travaux
L'utilisateur décrit brièvement la nature de son projet :
- **Type de travaux** (Ex: Ravalement de façade, Création d'ouverture, Pose de Vélux...)
- **Description courte**
- **Surfaces et Hauteurs** (Surface de plancher existante/créée, Hauteur du projet)

### Étape 3 : Les Photos (Avants / Après)
L'utilisateur télécharge les pièces graphiques nécessaires au dossier :
- Les photos sont organisées par **"Paires"** (ex: "Façade Sud").
- Pour chaque paire, l'utilisateur fournit une photo de l'**État Existant (Avant)** et un photomontage ou croquis de l'**État Projeté (Après)**.

### Étape 4 : L'Analyse IA
C'est le cœur de l'application. L'IA vision analyse les photos et les croise avec les informations des étapes 1 et 2 pour générer automatiquement :
1. **La Notice Descriptive** (Art. R.431-8 du Code de l'Urbanisme)
   - L'état initial du terrain et de la construction
   - La description du projet (état projeté)
   - La justification architecturale et réglementaire
   - L'insertion paysagère
   - L'impact environnemental
2. **L'Aspect Extérieur (Matériaux et Couleurs)**
   - Détection des matériaux de façade, toiture, et menuiseries (existant vs projeté)
   - Détection des couleurs (avec correspondances RAL quand c'est possible)

*L'utilisateur peut choisir le modèle d'IA à utiliser et modifier librement les textes générés.*

### Étape 5 : Le Récapitulatif et Génération PDF
L'utilisateur accède au récapitulatif complet de son dossier.
D'un simple clic, il peut télécharger un **PDF professionnel et formaté** prêt à être déposé en mairie, contenant :
- Les fiches d'identité et de description
- La notice architecturale complète
- Les tableaux comparatifs d'aspect extérieur
- Les planches de photos Avant/Après mises en page côte à côte

---

## 🧠 Les Modèles de Données et Structure

L'application requiert et manipule les données suivantes (définies dans `models.py`) :

*   **`Demandeur`** : Identité du requérant.
*   **`Terrain`** : Localisation et règles d'urbanisme applicables.
*   **`TravauxDetail`** : Nature, description et dimensions du projet.
*   **`PhotoSet`** : Groupe logique associant une photo "Avant", une photo "Après" et un libellé.
*   **`NoticeDescriptive`** : Les paragraphes textuels réglementaires générés par l'IA.
*   **`AspectExterieur`** : Les caractéristiques physiques (matériaux, couleurs) extraites par l'IA.
*   **`DeclarationPrealable`** : L'objet maître agrégeant toutes ces données pour une session utilisateur.

---

## 🤖 Intégration de l'Intelligence Artificielle (NVIDIA API)

L'application utilise l'API NVIDIA Integrate pour accéder aux puissants modèles multimodaux (Vision Language Models).

Deux modèles sont implémentés et sélectionnables par l'utilisateur :

1.  **Nemotron Nano 12B V2 VL** (`nvidia/nemotron-nano-12b-v2-vl`)
    *   **Le modèle par défaut.**
    *   Rapide, léger, et excelle dans l'extraction de données structurées.
    *   Utilise une directive système spécifique (`/no_think`) pour forcer une réponse JSON stricte sans prose générative.
2.  **Qwen 3.5 397B** (`qwen/qwen3.5-397b-a17b`)
    *   Modèle de très grande taille, extrêmement performant pour la rédaction de textes complexes (comme les justifications architecturales).
    *   Utilise le paramètre `chat_template_kwargs: {"enable_thinking": True}` dans d'autres contextes, mais désactivé ici (`use_thinking=False`) pour garantir une sortie JSON parsable.

### Le défi du parsing JSON et la solution
Les LLMs modernes, en particulier ceux dotés de tokens de raisonnement (thinking models), ont tendance à répondre avec du texte libre (prose) même lorsqu'on leur demande du JSON.
Pour garantir la stabilité de l'application, nous avons implémenté un système de **Fallback robuste** dans `ai_service.py` :
1.  **Extraction stricte** : Une fonction parse la réponse pour trouver des blocs ````json ... ```` ou extraire le contenu entre accolades `{ ... }`.
2.  **Aplatissement (Flattening)** : Si l'IA groupe les données sous des en-têtes (ex: `{"NOTICE": {"etat_initial": "..."}}`), le script "aplatit" le JSON pour correspondre aux variables du code.
3.  **Fallback Text-to-JSON** : Si le modèle (malgré les instructions strictes) répond par de la prose narrative pur, le script fait un *second appel à l'API* avec un prompt système de "traduction" pour forcer la conversion de ce texte brut en un objet JSON valide comprenant exactement les 15 champs requis.

## 💻 Stack Technique
- **Backend** : Python 3, Flask
- **Frontend** : HTML5, CSS3 (variables, grid, flexbox), Vanilla JavaScript
- **Génération PDF** : ReportLab
- **IA** : API NVIDIA (Nemotron & Qwen)
- **Persistance** : Flask Session (les données temporaires sont stockées côté serveur pendant la navigation)
