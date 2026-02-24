"""
Générateur de PDF professionnel pour la Déclaration Préalable de Travaux.
Produit un dossier complet avec mise en page officielle, conforme aux 
exigences administratives françaises.
Photos présentées en comparaison avant/après côte à côte.
"""

import os
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from PIL import Image as PILImage

from models import DeclarationPrealable, PhotoSet


# ─── Configuration des thèmes ────────────────────────────────────────
def _get_theme_config(theme_name: str = "classique") -> dict:
    themes = {
        "classique": {
            "primary": HexColor("#000091"),      # Bleu France
            "secondary": HexColor("#E1000F"),    # Rouge Marianne
            "text_title": HexColor("#1E1E1E"),
            "text_body": HexColor("#3A3A3A"),
            "border": HexColor("#CCCCCC"),
            "bg_light": HexColor("#F5F5F5"),
            "bg_header1": HexColor("#E8EDFF"),   # Light blue
            "bg_header2": HexColor("#E8FFE8"),   # Light green
            "bandeau_style": "tricolore",
        },
        "moderne": {
            "primary": HexColor("#222831"),      # Dark Slate
            "secondary": HexColor("#00ADB5"),    # Teal
            "text_title": HexColor("#222831"),
            "text_body": HexColor("#393E46"),
            "border": HexColor("#EEEEEE"),
            "bg_light": HexColor("#F8F9FA"),
            "bg_header1": HexColor("#E4E9F2"),
            "bg_header2": HexColor("#EEEEEE"),
            "bandeau_style": "solid",
        },
        "nature": {
            "primary": HexColor("#2D6A4F"),      # Forest Green
            "secondary": HexColor("#D8F3DC"),    # Light Earth
            "text_title": HexColor("#1B4332"),
            "text_body": HexColor("#403D39"),
            "border": HexColor("#D4D4D4"),
            "bg_light": HexColor("#F9F9F9"),
            "bg_header1": HexColor("#E9F5E9"),
            "bg_header2": HexColor("#F0F5E9"),
            "bandeau_style": "solid",
        },
        "architecte": {
            "primary": HexColor("#14213d"),      # Deep Navy
            "secondary": HexColor("#fca311"),    # Accent Orange
            "text_title": HexColor("#000000"),
            "text_body": HexColor("#333333"),
            "border": HexColor("#e5e5e5"),
            "bg_light": HexColor("#fafafa"),
            "bg_header1": HexColor("#f2f4f7"),
            "bg_header2": HexColor("#f8f9fa"),
            "bandeau_style": "solid",
        }
    }
    return themes.get(theme_name, themes["classique"])


# ─── Styles personnalisés dynamiques ───────────────────────────────
def _get_styles(theme: dict):
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='TitreDocument',
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=28,
        textColor=theme["primary"],
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
    ))
    
    styles.add(ParagraphStyle(
        name='SousTitre',
        fontName='Helvetica',
        fontSize=13,
        leading=17,
        textColor=theme["text_body"],
        alignment=TA_CENTER,
        spaceAfter=10 * mm,
    ))
    
    styles.add(ParagraphStyle(
        name='SectionTitre',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=20,
        textColor=theme["primary"],
        spaceBefore=8 * mm,
        spaceAfter=4 * mm,
        borderWidth=0,
        borderPadding=0,
    ))
    
    styles.add(ParagraphStyle(
        name='SousSectionTitre',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=theme["text_title"],
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    ))
    
    styles.add(ParagraphStyle(
        name='Champ',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=theme["text_body"],
    ))
    
    styles.add(ParagraphStyle(
        name='Valeur',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=theme["text_title"],
    ))
    
    styles.add(ParagraphStyle(
        name='CorpsTexte',
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=theme["text_body"],
        alignment=TA_JUSTIFY,
        spaceAfter=3 * mm,
    ))
    
    styles.add(ParagraphStyle(
        name='PiedPage',
        fontName='Helvetica',
        fontSize=7,
        leading=10,
        textColor=theme["border"],
        alignment=TA_CENTER,
    ))
    
    styles.add(ParagraphStyle(
        name='PhotoCaption',
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        textColor=theme["text_body"],
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    ))
    
    styles.add(ParagraphStyle(
        name='CompareLabel',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=theme["primary"],
        alignment=TA_CENTER,
        spaceAfter=2 * mm,
    ))
    
    return styles


# ─── En-tête et pied de page ──────────────────────────────────────
class _PDFTemplate:
    def __init__(self, dp: DeclarationPrealable, theme: dict):
        self.dp = dp
        self.theme = theme
    
    def header_footer(self, canvas_obj, doc):
        canvas_obj.saveState()
        width, height = A4
        
        band_height = 3 * mm
        if self.theme["bandeau_style"] == "tricolore":
            canvas_obj.setFillColor(self.theme["primary"])
            canvas_obj.rect(0, height - band_height, width / 3, band_height, fill=True, stroke=0)
            canvas_obj.setFillColor(colors.white)
            canvas_obj.rect(width / 3, height - band_height, width / 3, band_height, fill=True, stroke=0)
            canvas_obj.setFillColor(self.theme["secondary"])
            canvas_obj.rect(2 * width / 3, height - band_height, width / 3, band_height, fill=True, stroke=0)
        else:
            canvas_obj.setFillColor(self.theme["primary"])
            canvas_obj.rect(0, height - band_height, width, band_height, fill=True, stroke=0)
        
        # Référence
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.setFillColor(self.theme["text_body"])
        canvas_obj.drawRightString(width - 15 * mm, height - 12 * mm, f"Ref. {self.dp.reference}")
        
        # Pied de page
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.setFillColor(self.theme["border"])
        canvas_obj.drawCentredString(
            width / 2, 10 * mm,
            f"Declaration Prealable - {self.dp.demandeur.nom} {self.dp.demandeur.prenom} - "
            f"Generee le {self.dp.date_creation} - Page {doc.page}"
        )
        
        # Ligne fine
        canvas_obj.setStrokeColor(self.theme["primary"])
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(15 * mm, 15 * mm, width - 15 * mm, 15 * mm)
        
        canvas_obj.restoreState()


# ─── Helpers ───────────────────────────────────────────────────────
def _section_header(title: str, styles, theme: dict) -> list:
    return [
        HRFlowable(width="100%", thickness=1, color=theme["primary"], spaceAfter=2 * mm),
        Paragraph(title, styles['SectionTitre']),
    ]


def _field_row(label: str, value: str, styles, theme: dict) -> Table:
    t = Table(
        [[Paragraph(label, styles['Champ']), Paragraph(str(value), styles['Valeur'])]],
        colWidths=[55 * mm, 115 * mm],
        hAlign='LEFT'
    )
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, theme["border"]),
    ]))
    return t


def _fit_image(path: str, max_width: float, max_height: float):
    """Redimensionne une image pour s'adapter aux dimensions maximales."""
    try:
        pil_img = PILImage.open(path)
        img_w, img_h = pil_img.size
        ratio = min(max_width / img_w, max_height / img_h)
        return Image(path, width=img_w * ratio, height=img_h * ratio)
    except Exception:
        return Paragraph(f"[Image non trouvee : {os.path.basename(path)}]", _get_styles()['Champ'])


def _resolve_photo_path(chemin):
    """Resolve photo path — handles both absolute and relative paths."""
    if not chemin:
        return None
    if os.path.isabs(chemin) and os.path.exists(chemin):
        return chemin
    base_dir = os.path.dirname(os.path.abspath(__file__))
    rel_path = os.path.join(base_dir, chemin)
    if os.path.exists(rel_path):
        return rel_path
    return None


# ─── Génération du PDF ─────────────────────────────────────────────
def generer_pdf(dp: DeclarationPrealable, output_path: str = None, output_dir: str = "output", theme_name: str = "classique"):
    """
    Génère le dossier PDF complet de Déclaration Préalable.
    
    Args:
        dp: L'objet DeclarationPrealable rempli
        output_path: Chemin direct vers le fichier de sortie (prioritaire)
        output_dir: Répertoire de sortie (utilisé si output_path non fourni)
        theme_name: Le nom du thème visuel à utiliser (classique, moderne, nature, architecte)
        
    Returns:
        Chemin vers le fichier PDF généré
    """
    if output_path:
        filepath = output_path
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    else:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"DP_{dp.demandeur.nom}_{dp.demandeur.prenom}_{dp.reference}.pdf"
        filepath = os.path.join(output_dir, filename)
    
    theme = _get_theme_config(theme_name)
    styles = _get_styles(theme)
    template = _PDFTemplate(dp, theme)
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        title=f"Declaration Prealable - {dp.reference}",
        author=f"{dp.demandeur.prenom} {dp.demandeur.nom}",
    )
    
    elements = []
    
    # ═════════════════════════════════════════════════════════════
    # PAGE DE GARDE
    # ═════════════════════════════════════════════════════════════
    elements.append(Spacer(1, 30 * mm))
    
    elements.append(Paragraph("REPUBLIQUE FRANCAISE", ParagraphStyle(
        'Republique', fontName='Helvetica-Bold', fontSize=11,
        textColor=theme["primary"], alignment=TA_CENTER, spaceAfter=2 * mm
    )))
    elements.append(Paragraph("Liberte - Egalite - Fraternite", ParagraphStyle(
        'Devise', fontName='Helvetica-Oblique', fontSize=9,
        textColor=theme["text_body"], alignment=TA_CENTER, spaceAfter=15 * mm
    )))
    
    elements.append(HRFlowable(width="40%", thickness=2, color=theme["primary"], spaceAfter=10 * mm))
    
    elements.append(Paragraph("DECLARATION PREALABLE", styles['TitreDocument']))
    elements.append(Paragraph("DE TRAVAUX", styles['TitreDocument']))
    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph(
        "Cerfa n 13703*09 - Articles R.421-9 a R.421-12 du Code de l'urbanisme",
        styles['SousTitre']
    ))
    
    elements.append(Spacer(1, 10 * mm))
    
    info_data = [
        ["Reference :", dp.reference],
        ["Date :", dp.date_creation],
        ["Demandeur :", f"{dp.demandeur.civilite} {dp.demandeur.prenom} {dp.demandeur.nom}"],
        ["Terrain :", f"{dp.terrain.adresse}, {dp.terrain.code_postal} {dp.terrain.commune}"],
        ["Objet :", dp.travaux.description_courte],
    ]
    
    info_table = Table(info_data, colWidths=[40 * mm, 130 * mm], hAlign='CENTER')
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), theme["primary"]),
        ('TEXTCOLOR', (1, 0), (1, -1), theme["text_title"]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, theme["border"]),
    ]))
    elements.append(info_table)
    
    elements.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════
    # SECTION 1 : IDENTITÉ DU DEMANDEUR
    # ═════════════════════════════════════════════════════════════
    elements.extend(_section_header("1 - IDENTITE DU DEMANDEUR", styles))
    
    dem = dp.demandeur
    elements.append(_field_row("Civilite :", dem.civilite, styles))
    elements.append(_field_row("Nom :", dem.nom, styles))
    elements.append(_field_row("Prenom :", dem.prenom, styles))
    elements.append(_field_row("Date de naissance :", dem.date_naissance, styles))
    elements.append(_field_row("Lieu de naissance :", dem.lieu_naissance, styles))
    elements.append(_field_row("Adresse :", f"{dem.adresse}, {dem.code_postal} {dem.ville}", styles))
    elements.append(_field_row("Telephone :", dem.telephone, styles))
    elements.append(_field_row("Email :", dem.email, styles))
    elements.append(_field_row("Qualite :", dem.qualite, styles))
    
    elements.append(Spacer(1, 5 * mm))
    
    # ═════════════════════════════════════════════════════════════
    # SECTION 2 : LOCALISATION DU TERRAIN
    # ═════════════════════════════════════════════════════════════
    elements.extend(_section_header("2 - LOCALISATION DU TERRAIN", styles))
    
    ter = dp.terrain
    elements.append(_field_row("Adresse du terrain :", f"{ter.adresse}, {ter.code_postal} {ter.commune}", styles))
    if ter.lieu_dit:
        elements.append(_field_row("Lieu-dit :", ter.lieu_dit, styles))
    elements.append(_field_row("References cadastrales :", f"Section {ter.section_cadastrale}, Parcelle n {ter.numero_parcelle}", styles))
    elements.append(_field_row("Superficie :", f"{ter.superficie_terrain} m2", styles))
    elements.append(_field_row("Zone PLU :", ter.zone_plu, styles))
    
    situations = []
    if ter.est_lotissement:
        situations.append("Terrain situe dans un lotissement")
    if ter.est_zone_protegee:
        situations.append("Zone protegee")
    if ter.est_monument_historique:
        situations.append("Perimetre de monument historique")
    if not situations:
        situations.append("Aucune situation particuliere")
    elements.append(_field_row("Situation particuliere :", " - ".join(situations), styles))
    
    elements.append(Spacer(1, 5 * mm))
    
    # ═════════════════════════════════════════════════════════════
    # SECTION 3 : NATURE DES TRAVAUX
    # ═════════════════════════════════════════════════════════════
    elements.extend(_section_header("3 - NATURE ET IMPORTANCE DES TRAVAUX", styles))
    
    trv = dp.travaux
    elements.append(_field_row("Type de travaux :", trv.type_travaux, styles))
    elements.append(_field_row("Description :", trv.description_courte, styles))
    elements.append(_field_row("Surface plancher existante :", f"{trv.surface_plancher_existante} m2", styles))
    elements.append(_field_row("Surface plancher creee :", f"{trv.surface_plancher_creee} m2", styles))
    elements.append(_field_row("Emprise au sol existante :", f"{trv.emprise_au_sol_existante} m2", styles))
    elements.append(_field_row("Emprise au sol creee :", f"{trv.emprise_au_sol_creee} m2", styles))
    elements.append(_field_row("Hauteur existante :", f"{trv.hauteur_existante} m", styles))
    elements.append(_field_row("Hauteur projetee :", f"{trv.hauteur_projetee} m", styles))
    elements.append(_field_row("Date debut prevue :", trv.date_debut_prevue, styles))
    elements.append(_field_row("Duree estimee :", f"{trv.duree_travaux_mois} mois", styles))
    
    elements.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════
    # SECTION 4 : ASPECT EXTÉRIEUR
    # ═════════════════════════════════════════════════════════════
    elements.extend(_section_header("4 - ASPECT EXTERIEUR DES CONSTRUCTIONS", styles))
    
    asp = dp.aspect_exterieur
    
    elements.append(Paragraph("Ouvertures et Menuiseries", styles['SousSectionTitre']))
    elements.append(_field_row("Nombre existant :", asp.nombre_ouvertures_existantes or "—", styles, theme))
    elements.append(_field_row("Nombre projete :", asp.nombre_ouvertures_projetees or "—", styles, theme))
    elements.append(_field_row("Types existants :", asp.menuiseries_existantes or "—", styles, theme))
    elements.append(_field_row("Types projetes :", asp.menuiseries_projetees or "—", styles, theme))

    elements.append(Paragraph("Facades", styles['SousSectionTitre']))
    elements.append(_field_row("Materiaux existants :", asp.facade_materiaux_existants or "—", styles, theme))
    elements.append(_field_row("Materiaux projetes :", asp.facade_materiaux_projetes or "—", styles, theme))
    
    elements.append(Paragraph("Toiture", styles['SousSectionTitre']))
    elements.append(_field_row("Materiaux existants :", asp.toiture_materiaux_existants or "—", styles, theme))
    elements.append(_field_row("Materiaux projetes :", asp.toiture_materiaux_projetes or "—", styles, theme))
    
    elements.append(Paragraph("Cloture", styles['SousSectionTitre']))
    elements.append(_field_row("Existante :", asp.cloture_existante or "—", styles, theme))
    elements.append(_field_row("Projetee :", asp.cloture_projetee or "—", styles, theme))
    
    elements.append(Paragraph("Palette de couleurs", styles['SousSectionTitre']))
    
    couleurs_data = [
        ["Element", "Couleur"],
        ["Facade", asp.couleur_facade or "—"],
        ["Menuiseries", asp.couleur_menuiseries or "—"],
        ["Volets", asp.couleur_volets or "—"],
        ["Toiture", asp.couleur_toiture or "—"],
    ]
    couleurs_table = Table(couleurs_data, colWidths=[55 * mm, 115 * mm], hAlign='LEFT')
    couleurs_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), theme["primary"]),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), theme["text_title"]),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, theme["border"]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(couleurs_table)
    
    elements.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════
    # SECTION 5 : NOTICE DESCRIPTIVE
    # ═════════════════════════════════════════════════════════════
    elements.extend(_section_header("5 - NOTICE DESCRIPTIVE DU PROJET", styles))
    
    notice = dp.notice
    
    elements.append(Paragraph("5.1 - Etat initial du terrain et de la construction", styles['SousSectionTitre']))
    elements.append(Paragraph(notice.etat_initial or "Non renseigne", styles['CorpsTexte']))
    
    elements.append(Paragraph("5.2 - Description du projet", styles['SousSectionTitre']))
    elements.append(Paragraph(notice.etat_projete or "Non renseigne", styles['CorpsTexte']))
    
    elements.append(Paragraph("5.3 - Analyse technique estimee", styles['SousSectionTitre']))
    elements.append(Paragraph(notice.modifications_detaillees or "—", styles['CorpsTexte']))
    elements.append(_field_row("Surface plancher :", notice.modification_surface_plancher or "—", styles, theme))
    elements.append(_field_row("Emprise au sol :", notice.modification_emprise_au_sol or "—", styles, theme))
    elements.append(_field_row("Volume :", notice.modification_volume or "—", styles, theme))
    elements.append(_field_row("Hauteur existante :", notice.hauteur_estimee_existante or "—", styles, theme))
    elements.append(_field_row("Hauteur projetee :", notice.hauteur_estimee_projete or "—", styles, theme))
    
    elements.append(Paragraph("5.4 - Analyse reglementaire", styles['SousSectionTitre']))
    elements.append(Paragraph(f"Coherence architecturale (Zone {dp.terrain.zone_plu}) :", styles['SousSectionTitre']))
    elements.append(Paragraph(notice.coherence_architecturale or '—', styles['CorpsTexte']))
    elements.append(Paragraph("Risques reglementaires potentiels :", styles['SousSectionTitre']))
    elements.append(Paragraph(notice.risques_reglementaires_potentiels or '—', styles['CorpsTexte']))
    elements.append(Paragraph(f"Niveau de confiance IA : {notice.niveau_confiance_global or '—'}", styles['CorpsTexte']))

    elements.append(Paragraph("5.5 - Justification du projet", styles['SousSectionTitre']))
    elements.append(Paragraph(notice.justification or "Non renseigne", styles['CorpsTexte']))
    
    elements.append(Paragraph("5.6 - Insertion paysagere", styles['SousSectionTitre']))
    elements.append(Paragraph(notice.insertion_paysagere or "Non renseigne", styles['CorpsTexte']))
    
    elements.append(Paragraph("5.7 - Impact environnemental", styles['SousSectionTitre']))
    elements.append(Paragraph(notice.impact_environnemental or "Non renseigne", styles['CorpsTexte']))
    
    elements.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════
    # SECTION 6 : PHOTOGRAPHIES — Comparaison avant/après
    # ═════════════════════════════════════════════════════════════
    elements.extend(_section_header("6 - REPORTAGE PHOTOGRAPHIQUE - COMPARAISON AVANT/APRES", styles, theme))
    
    col_width = 82 * mm  # Width for each photo column
    max_img_height = 90 * mm
    
    for i, photo_set in enumerate(dp.photo_sets):
        # Set label header
        elements.append(Paragraph(
            f"Comparaison {i+1} : {photo_set.label}",
            styles['SousSectionTitre']
        ))
        
        # Build side-by-side table
        avant_path = _resolve_photo_path(photo_set.chemin_avant)
        apres_path = _resolve_photo_path(photo_set.chemin_apres)
        
        # Header row
        header_row = [
            Paragraph("AVANT TRAVAUX (DP7)", styles['CompareLabel']),
            Paragraph("APRES TRAVAUX (DP8)", styles['CompareLabel']),
        ]
        
        # Image row
        img_avant = _fit_image(avant_path, col_width - 4*mm, max_img_height) if avant_path else Paragraph("[Pas de photo avant]", styles['Champ'])
        img_apres = _fit_image(apres_path, col_width - 4*mm, max_img_height) if apres_path else Paragraph("[Pas de photo apres]", styles['Champ'])
        img_row = [img_avant, img_apres]
        
        # Caption row
        caption_avant = Paragraph(photo_set.description_avant or photo_set.label, styles['PhotoCaption'])
        caption_apres = Paragraph(photo_set.description_apres or photo_set.label, styles['PhotoCaption'])
        caption_row = [caption_avant, caption_apres]
        
        comparison_table = Table(
            [header_row, img_row, caption_row],
            colWidths=[col_width, col_width],
            hAlign='CENTER'
        )
        comparison_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            # Header background
            ('BACKGROUND', (0, 0), (0, 0), theme["bg_header1"]),
            ('BACKGROUND', (1, 0), (1, 0), theme["bg_header2"]),
            # Borders
            ('BOX', (0, 0), (0, -1), 0.5, theme["border"]),
            ('BOX', (1, 0), (1, -1), 0.5, theme["border"]),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, theme["border"]),
        ]))
        
        elements.append(comparison_table)
        elements.append(Spacer(1, 8 * mm))
        
        # Page break between sets (except last)
        if i < len(dp.photo_sets) - 1:
            elements.append(PageBreak())
    
    if not dp.photo_sets:
        elements.append(Paragraph("Aucune photographie fournie.", styles['CorpsTexte']))
    
    elements.append(PageBreak())
    
    # ═════════════════════════════════════════════════════════════
    # SECTION 7 : INDEX DES PIÈCES JOINTES
    # ═════════════════════════════════════════════════════════════
    elements.extend(_section_header("7 - INDEX DES PIECES JOINTES", styles, theme))
    
    elements.append(Paragraph(
        "Liste des pieces constitutives du dossier conformement aux articles "
        "R.431-35 et suivants du Code de l'urbanisme :",
        styles['CorpsTexte']
    ))
    elements.append(Spacer(1, 3 * mm))
    
    pieces_data = [["Ref.", "Designation", "Statut"]]
    for ref, info in dp.pieces_jointes.items():
        statut = "Fourni" if info["fourni"] else "Non fourni"
        pieces_data.append([ref, info["nom"], statut])
    
    pieces_table = Table(pieces_data, colWidths=[18 * mm, 120 * mm, 32 * mm], hAlign='LEFT')
    pieces_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), theme["primary"]),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), theme["text_title"]),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, theme["border"]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, theme["bg_light"]]),
    ]))
    elements.append(pieces_table)
    
    elements.append(Spacer(1, 15 * mm))
    
    # Signature
    elements.append(HRFlowable(width="100%", thickness=0.5, color=theme["border"], spaceAfter=5 * mm))
    elements.append(Paragraph(
        f"Fait a {dp.terrain.commune}, le {dp.date_creation}",
        ParagraphStyle('Signature', fontName='Helvetica', fontSize=10,
                       textColor=theme["text_title"], alignment=TA_LEFT, spaceAfter=15 * mm)
    ))
    elements.append(Paragraph(
        f"Le demandeur : {dp.demandeur.civilite} {dp.demandeur.prenom} {dp.demandeur.nom}",
        ParagraphStyle('SignatureNom', fontName='Helvetica-Bold', fontSize=10,
                       textColor=theme["text_title"], alignment=TA_LEFT, spaceAfter=3 * mm)
    ))
    elements.append(Paragraph(
        "Signature :",
        ParagraphStyle('SignatureLabel', fontName='Helvetica', fontSize=9,
                       textColor=theme["text_body"], alignment=TA_LEFT)
    ))
    
    # ── Build ──
    doc.build(elements, onFirstPage=template.header_footer, onLaterPages=template.header_footer)
    
    return filepath


# ─── Script de test direct ─────────────────────────────────────────
if __name__ == "__main__":
    from models import get_dummy_declaration
    dp = get_dummy_declaration()
    path = generer_pdf(dp)
    print(f"PDF genere : {path}")
