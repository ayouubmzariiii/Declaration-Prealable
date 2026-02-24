"""
Application Flask — Déclaration Préalable de Travaux SaaS
Flux : Identité/Lieu → Type de travaux → Photos (paires avant/après) → Analyse IA → Revue → PDF
"""

import os
import io
import json
import uuid
import tempfile
from datetime import date
from flask import (
    Flask, render_template, request, session, redirect,
    url_for, send_file, flash, jsonify, Response, make_response
)
from dotenv import load_dotenv

load_dotenv()

from models import (
    DeclarationPrealable, Demandeur, Terrain, TravauxDetail,
    AspectExterieur, NoticeDescriptive, PhotoSet, get_dummy_declaration
)
from ai_service import analyser_photos, generer_notice_descriptive, generer_description_photo, get_available_models, get_default_model
from pdf_generator import generer_pdf

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── Helper: session ↔ model conversion ───────────────────────────
def _session_to_dp() -> DeclarationPrealable:
    """Reconstruit un objet DeclarationPrealable depuis la session."""
    data = session.get("dp_data", {})
    dp = DeclarationPrealable()

    if "demandeur" in data:
        for k, v in data["demandeur"].items():
            if hasattr(dp.demandeur, k):
                setattr(dp.demandeur, k, v)

    if "terrain" in data:
        for k, v in data["terrain"].items():
            if hasattr(dp.terrain, k):
                setattr(dp.terrain, k, v)

    if "travaux" in data:
        for k, v in data["travaux"].items():
            if hasattr(dp.travaux, k):
                setattr(dp.travaux, k, v)

    if "aspect_exterieur" in data:
        for k, v in data["aspect_exterieur"].items():
            if hasattr(dp.aspect_exterieur, k):
                setattr(dp.aspect_exterieur, k, v)

    if "notice" in data:
        for k, v in data["notice"].items():
            if hasattr(dp.notice, k):
                setattr(dp.notice, k, v)

    if "photo_sets" in data:
        dp.photo_sets = [PhotoSet(**ps) for ps in data["photo_sets"]]

    if "reference" in data:
        dp.reference = data["reference"]
    if "date_creation" in data:
        dp.date_creation = data["date_creation"]

    return dp


def _dp_to_session(dp: DeclarationPrealable):
    """Sérialise un objet DeclarationPrealable vers la session."""
    data = {
        "demandeur": dp.demandeur.__dict__,
        "terrain": dp.terrain.__dict__,
        "travaux": dp.travaux.__dict__,
        "aspect_exterieur": dp.aspect_exterieur.__dict__,
        "notice": dp.notice.__dict__,
        "photo_sets": [ps.__dict__ for ps in dp.photo_sets],
        "reference": dp.reference,
        "date_creation": dp.date_creation,
    }
    session["dp_data"] = data


# ═══════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/nouvelle-declaration")
def nouvelle_declaration():
    """Initialise une nouvelle DP et redirige vers étape 1."""
    dp = get_dummy_declaration()
    _dp_to_session(dp)
    return redirect(url_for("etape", num=1))


# ─── ÉTAPE 1 : Identité + Lieu ────────────────────────────────────
@app.route("/etape/1", methods=["GET", "POST"])
def etape_1():
    if "dp_data" not in session:
        return redirect(url_for("nouvelle_declaration"))
    dp = _session_to_dp()

    if request.method == "POST":
        dp.demandeur.civilite = request.form.get("civilite", dp.demandeur.civilite)
        dp.demandeur.nom = request.form.get("nom", dp.demandeur.nom)
        dp.demandeur.prenom = request.form.get("prenom", dp.demandeur.prenom)
        dp.demandeur.date_naissance = request.form.get("date_naissance", dp.demandeur.date_naissance)
        dp.demandeur.lieu_naissance = request.form.get("lieu_naissance", dp.demandeur.lieu_naissance)
        dp.demandeur.adresse = request.form.get("adresse_demandeur", dp.demandeur.adresse)
        dp.demandeur.code_postal = request.form.get("cp_demandeur", dp.demandeur.code_postal)
        dp.demandeur.ville = request.form.get("ville_demandeur", dp.demandeur.ville)
        dp.demandeur.telephone = request.form.get("telephone", dp.demandeur.telephone)
        dp.demandeur.email = request.form.get("email", dp.demandeur.email)
        dp.demandeur.qualite = request.form.get("qualite", dp.demandeur.qualite)

        dp.terrain.adresse = request.form.get("adresse_terrain", dp.terrain.adresse)
        dp.terrain.lieu_dit = request.form.get("lieu_dit", dp.terrain.lieu_dit)
        dp.terrain.code_postal = request.form.get("cp_terrain", dp.terrain.code_postal)
        dp.terrain.commune = request.form.get("commune", dp.terrain.commune)
        dp.terrain.section_cadastrale = request.form.get("section_cadastrale", dp.terrain.section_cadastrale)
        dp.terrain.numero_parcelle = request.form.get("numero_parcelle", dp.terrain.numero_parcelle)
        dp.terrain.superficie_terrain = float(request.form.get("superficie_terrain", dp.terrain.superficie_terrain) or 0)
        dp.terrain.zone_plu = request.form.get("zone_plu", dp.terrain.zone_plu)
        dp.terrain.est_lotissement = "est_lotissement" in request.form
        dp.terrain.est_zone_protegee = "est_zone_protegee" in request.form
        dp.terrain.est_monument_historique = "est_monument_historique" in request.form

        _dp_to_session(dp)
        return redirect(url_for("etape", num=2))

    return render_template("step1_identity_place.html", dp=dp, step=1, total_steps=5)


# ─── ÉTAPE 2 : Type de travaux ────────────────────────────────────
@app.route("/etape/2", methods=["GET", "POST"])
def etape_2():
    if "dp_data" not in session:
        return redirect(url_for("nouvelle_declaration"))
    dp = _session_to_dp()

    if request.method == "POST":
        dp.travaux.type_travaux = request.form.get("type_travaux", dp.travaux.type_travaux)
        dp.travaux.description_courte = request.form.get("description_courte", dp.travaux.description_courte)
        dp.travaux.surface_plancher_existante = float(request.form.get("surface_plancher_existante", dp.travaux.surface_plancher_existante) or 0)
        dp.travaux.surface_plancher_creee = float(request.form.get("surface_plancher_creee", dp.travaux.surface_plancher_creee) or 0)
        dp.travaux.emprise_au_sol_existante = float(request.form.get("emprise_au_sol_existante", dp.travaux.emprise_au_sol_existante) or 0)
        dp.travaux.emprise_au_sol_creee = float(request.form.get("emprise_au_sol_creee", dp.travaux.emprise_au_sol_creee) or 0)
        dp.travaux.hauteur_existante = float(request.form.get("hauteur_existante", dp.travaux.hauteur_existante) or 0)
        dp.travaux.hauteur_projetee = float(request.form.get("hauteur_projetee", dp.travaux.hauteur_projetee) or 0)
        dp.travaux.date_debut_prevue = request.form.get("date_debut_prevue", dp.travaux.date_debut_prevue)
        dp.travaux.duree_travaux_mois = int(request.form.get("duree_travaux_mois", dp.travaux.duree_travaux_mois) or 1)

        _dp_to_session(dp)
        return redirect(url_for("etape", num=3))

    return render_template("step2_type_travaux.html", dp=dp, step=2, total_steps=5)


# ─── ÉTAPE 3 : Photos par paires (avant/après) ────────────────────
@app.route("/etape/3", methods=["GET", "POST"])
def etape_3():
    if "dp_data" not in session:
        return redirect(url_for("nouvelle_declaration"))
    dp = _session_to_dp()

    if request.method == "POST":
        photo_sets = []
        labels = request.form.getlist("set_label")
        avant_files = request.files.getlist("set_avant")
        apres_files = request.files.getlist("set_apres")

        count = max(len(labels), len(avant_files), len(apres_files))

        for i in range(count):
            label = labels[i] if i < len(labels) else f"Vue {i+1}"
            
            chemin_avant = ""
            chemin_apres = ""

            if i < len(avant_files):
                f_avant = avant_files[i]
                if f_avant and f_avant.filename and allowed_file(f_avant.filename):
                    unique = f"{uuid.uuid4().hex[:8]}_{f_avant.filename}"
                    chemin_avant = os.path.join(UPLOAD_FOLDER, unique)
                    f_avant.save(chemin_avant)

            if i < len(apres_files):
                f_apres = apres_files[i]
                if f_apres and f_apres.filename and allowed_file(f_apres.filename):
                    unique = f"{uuid.uuid4().hex[:8]}_{f_apres.filename}"
                    chemin_apres = os.path.join(UPLOAD_FOLDER, unique)
                    f_apres.save(chemin_apres)

            if chemin_avant or chemin_apres:
                photo_sets.append(PhotoSet(
                    label=label.strip() or f"Vue {i+1}",
                    chemin_avant=chemin_avant,
                    chemin_apres=chemin_apres,
                    description_avant=f"{label} — État existant" if chemin_avant else "",
                    description_apres=f"{label} — État projeté" if chemin_apres else "",
                ))

        if photo_sets:
            dp.photo_sets = photo_sets
            dp.pieces_jointes["DP7"]["fourni"] = any(ps.chemin_avant for ps in photo_sets)
            dp.pieces_jointes["DP8"]["fourni"] = any(ps.chemin_apres for ps in photo_sets)

        _dp_to_session(dp)
        return redirect(url_for("etape", num=4))

    return render_template("step3_photos.html", dp=dp, step=3, total_steps=5)


# ─── ÉTAPE 4 : Analyse IA + Revue ─────────────────────────────────
@app.route("/etape/4", methods=["GET", "POST"])
def etape_4():
    if "dp_data" not in session:
        return redirect(url_for("nouvelle_declaration"))
    dp = _session_to_dp()

    if request.method == "POST":
        # Save reviewed/edited AI descriptions (NoticeDescriptive)
        for field_name in [
            "etat_initial", "etat_projete", "justification", "insertion_paysagere", 
            "impact_environnemental", "modifications_detaillees", "modification_volume", 
            "modification_emprise_au_sol", "modification_surface_plancher",
            "hauteur_estimee_existante", "hauteur_estimee_projete",
            "coherence_architecturale", "risques_reglementaires_potentiels", "niveau_confiance_global"
        ]:
            val = request.form.get(field_name)
            if val is not None:
                setattr(dp.notice, field_name, val)

        # Save aspect extérieur
        for field_name in [
            "facade_materiaux_existants", "facade_materiaux_projetes",
            "menuiseries_existantes", "menuiseries_projetees",
            "toiture_materiaux_existants", "toiture_materiaux_projetes",
            "couleur_facade", "couleur_menuiseries", "couleur_volets", "couleur_toiture",
            "nombre_ouvertures_existantes", "nombre_ouvertures_projetees"
        ]:
            val = request.form.get(field_name)
            if val is not None:
                setattr(dp.aspect_exterieur, field_name, val)

        _dp_to_session(dp)
        return redirect(url_for("etape", num=5))

    default_prompt = ""
    try:
        from ai_service import _build_analysis_prompt
        photos_avant = [ps.chemin_avant for ps in dp.photo_sets if ps.chemin_avant]
        photos_apres = [ps.chemin_apres for ps in dp.photo_sets if ps.chemin_apres]
        projet_info = {
            "adresse": dp.terrain.adresse,
            "commune": dp.terrain.commune,
            "code_postal": dp.terrain.code_postal,
            "zone_plu": dp.terrain.zone_plu,
            "type_travaux": dp.travaux.type_travaux,
            "description": dp.travaux.description_courte,
            "surface_existante": dp.travaux.surface_plancher_existante,
        }
        default_prompt = _build_analysis_prompt(len(photos_avant), len(photos_apres), projet_info)
    except Exception as e:
        pass

    return render_template("step4_ai_review.html", dp=dp, step=4, total_steps=5,
                           models=get_available_models(), default_model=get_default_model(),
                           default_prompt=default_prompt)


# ─── ÉTAPE 5 : Récapitulatif + PDF ────────────────────────────────
@app.route("/etape/5", methods=["GET"])
def etape_5():
    if "dp_data" not in session:
        return redirect(url_for("nouvelle_declaration"))
    dp = _session_to_dp()
    return render_template("step5_summary.html", dp=dp, step=5, total_steps=5)


# ─── Generic route dispatcher ─────────────────────────────────────
@app.route("/etape/<int:num>", methods=["GET", "POST"])
def etape(num):
    route_map = {
        1: etape_1,
        2: etape_2,
        3: etape_3,
        4: etape_4,
        5: etape_5,
    }
    handler = route_map.get(num)
    if handler:
        return handler()
    return redirect(url_for("index"))


# ═══════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/analyser-photos", methods=["POST"])
def api_analyser_photos():
    """Analyse les photos via l'IA et retourne descriptions + aspect extérieur."""
    dp = _session_to_dp()

    photos_avant = [ps.chemin_avant for ps in dp.photo_sets if ps.chemin_avant and os.path.exists(ps.chemin_avant)]
    photos_apres = [ps.chemin_apres for ps in dp.photo_sets if ps.chemin_apres and os.path.exists(ps.chemin_apres)]

    print(f"\n{'='*60}")
    print(f"[API] {len(photos_avant)} avant + {len(photos_apres)} apres photos")

    if not photos_avant and not photos_apres:
        return jsonify({"error": "Aucune photo trouvée. Retournez à l'étape précédente pour en ajouter."}), 400

    try:
        # Pass project context from previous steps
        projet_info = {
            "adresse": dp.terrain.adresse,
            "commune": dp.terrain.commune,
            "code_postal": dp.terrain.code_postal,
            "zone_plu": dp.terrain.zone_plu,
            "type_travaux": dp.travaux.type_travaux,
            "description": dp.travaux.description_courte,
            "surface_existante": dp.travaux.surface_plancher_existante,
            "hauteur": dp.travaux.hauteur_existante,
        }

        # Get model selection from request
        req_data = request.get_json(silent=True) or {}
        model_key = req_data.get("model", get_default_model())
        print(f"[API] Using model: {model_key}")

        # Single AI call with model selection
        analysis = analyser_photos(photos_avant, photos_apres, projet_info=projet_info, model_key=model_key)

        # Map ALL fields from the flat analysis result
        notice_fields = [
            "etat_initial", "etat_projete", "justification", "insertion_paysagere", 
            "impact_environnemental", "modifications_detaillees", "modification_volume", 
            "modification_emprise_au_sol", "modification_surface_plancher",
            "hauteur_estimee_existante", "hauteur_estimee_projete",
            "coherence_architecturale", "risques_reglementaires_potentiels", "niveau_confiance_global"
        ]
        aspect_fields = [
            "facade_materiaux_existants", "facade_materiaux_projetes",
            "menuiseries_existantes", "menuiseries_projetees",
            "toiture_materiaux_existants", "toiture_materiaux_projetes",
            "couleur_facade", "couleur_menuiseries", "couleur_volets", "couleur_toiture",
            "nombre_ouvertures_existantes", "nombre_ouvertures_projetees"
        ]

        for f in notice_fields:
            val = analysis.get(f, "")
            if isinstance(val, str) and val.strip():
                setattr(dp.notice, f, val.strip())

        for f in aspect_fields:
            val = analysis.get(f, "")
            if isinstance(val, str) and val.strip():
                setattr(dp.aspect_exterieur, f, val.strip())
            elif isinstance(val, list):
                joined = ", ".join(str(v) for v in val)
                if joined:
                    setattr(dp.aspect_exterieur, f, joined)

        _dp_to_session(dp)

        response_data = {
            "success": True,
            "notice": {f: getattr(dp.notice, f) for f in notice_fields},
            "aspect": {f: getattr(dp.aspect_exterieur, f) for f in aspect_fields},
        }

        filled = sum(1 for v in response_data["notice"].values() if v) + sum(1 for v in response_data["aspect"].values() if v)
        print(f"[API] {filled}/15 fields populated")
        print(f"{'='*60}\n")

        return jsonify(response_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─── PDF Download ──────────────────────────────────────────────────
@app.route("/telecharger-pdf")
def telecharger_pdf():
    """Génère et télécharge le PDF du dossier complet."""
    if "dp_data" not in session:
        return redirect(url_for("index"))

    dp = _session_to_dp()

    try:
        # Get selected theme from query params
        theme = request.args.get("theme", "classique")
        
        # Generate PDF to a temp file with a clean ASCII name
        clean_nom = "".join(c for c in dp.demandeur.nom if c.isalnum() or c == "_")
        clean_prenom = "".join(c for c in dp.demandeur.prenom if c.isalnum() or c == "_")
        download_name = f"Declaration_Prealable_{clean_nom}_{clean_prenom}.pdf"

        # Write to a temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_path = tmp.name
        tmp.close()

        generer_pdf(dp, output_path=tmp_path, theme_name=theme)

        # Read bytes and clean up
        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()

        try:
            os.unlink(tmp_path)
        except OSError:
            pass

        response = make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
        response.headers["Content-Length"] = len(pdf_bytes)
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"Erreur lors de la génération du PDF : {str(e)}", "error")
        return redirect(url_for("etape", num=5))


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=5000)
