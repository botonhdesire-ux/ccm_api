"""
============================================================
  API-BENIN CCM Analyser — Générateur de Rapports PDF
  Utilise ReportLab pour produire des rapports complets :
    - En-tête officiel API-BENIN
    - Paramètres d'analyse
    - Image plaque annotée
    - Tableau Rf détaillé
    - Section identification
    - Bloc signature + QR code
============================================================
"""

import os
import io
import base64
import qrcode
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, HRFlowable, KeepTogether, PageBreak
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF

# ── Palette couleurs ────────────────────────────────────────
DARK_BG    = colors.HexColor("#0f1318")
PRIMARY    = colors.HexColor("#4fb3ff")
GREEN      = colors.HexColor("#3fffa2")
AMBER      = colors.HexColor("#ffb84f")
RED        = colors.HexColor("#ff5f72")
VIOLET     = colors.HexColor("#b97aff")
WHITE      = colors.white
GRAY_LIGHT = colors.HexColor("#e8f0fe")
GRAY_MID   = colors.HexColor("#8da4c4")
GRAY_DARK  = colors.HexColor("#4d6080")
BORDER_COL = colors.HexColor("#1f2840")
TABLE_HDR  = colors.HexColor("#151b24")
TABLE_ROW1 = colors.HexColor("#0f1318")
TABLE_ROW2 = colors.HexColor("#1a2130")
ACCENT_TXT = colors.HexColor("#e8f0fe")

PAGE_W, PAGE_H = A4
MARGIN_H = 1.8 * cm
MARGIN_V = 2.0 * cm


# ════════════════════════════════════════════════════════════
#  STYLES
# ════════════════════════════════════════════════════════════
def _build_styles():
    styles = getSampleStyleSheet()

    base = dict(fontName="Helvetica", textColor=GRAY_LIGHT,
                backColor=None, borderPadding=0)

    S = {
        "title": ParagraphStyle("title",
            fontSize=20, fontName="Helvetica-Bold",
            textColor=WHITE, leading=24, spaceAfter=4,
            alignment=TA_LEFT),

        "subtitle": ParagraphStyle("subtitle",
            fontSize=9, fontName="Helvetica",
            textColor=GRAY_MID, leading=12, spaceAfter=2,
            alignment=TA_LEFT),

        "section_head": ParagraphStyle("section_head",
            fontSize=10, fontName="Helvetica-Bold",
            textColor=PRIMARY, leading=14, spaceBefore=14, spaceAfter=6,
            alignment=TA_LEFT),

        "body": ParagraphStyle("body",
            fontSize=9, fontName="Helvetica",
            textColor=GRAY_LIGHT, leading=13, spaceAfter=4,
            alignment=TA_JUSTIFY),

        "mono": ParagraphStyle("mono",
            fontSize=8, fontName="Courier",
            textColor=PRIMARY, leading=11,
            alignment=TA_LEFT),

        "label": ParagraphStyle("label",
            fontSize=7.5, fontName="Helvetica-Bold",
            textColor=GRAY_MID, leading=10,
            alignment=TA_LEFT),

        "value": ParagraphStyle("value",
            fontSize=9, fontName="Helvetica",
            textColor=WHITE, leading=12,
            alignment=TA_LEFT),

        "tag_green": ParagraphStyle("tag_green",
            fontSize=8, fontName="Helvetica-Bold",
            textColor=GREEN, alignment=TA_CENTER),

        "tag_amber": ParagraphStyle("tag_amber",
            fontSize=8, fontName="Helvetica-Bold",
            textColor=AMBER, alignment=TA_CENTER),

        "tag_red": ParagraphStyle("tag_red",
            fontSize=8, fontName="Helvetica-Bold",
            textColor=RED, alignment=TA_CENTER),

        "footer": ParagraphStyle("footer",
            fontSize=7, fontName="Helvetica",
            textColor=GRAY_DARK, leading=9, alignment=TA_CENTER),

        "sig_label": ParagraphStyle("sig_label",
            fontSize=7.5, fontName="Helvetica-Bold",
            textColor=GRAY_MID, alignment=TA_CENTER),

        "sig_value": ParagraphStyle("sig_value",
            fontSize=9, fontName="Helvetica",
            textColor=WHITE, leading=12, alignment=TA_CENTER),

        "conclusion": ParagraphStyle("conclusion",
            fontSize=9, fontName="Helvetica",
            textColor=GRAY_LIGHT, leading=13,
            alignment=TA_JUSTIFY,
            borderPadding=(8, 8, 8, 8)),
    }
    return S


# ════════════════════════════════════════════════════════════
#  HEADER PAGE (callback)
# ════════════════════════════════════════════════════════════
class _PageDecorator:
    def __init__(self, lab: str, doc_id: str, date_str: str):
        self.lab     = lab
        self.doc_id  = doc_id
        self.date_str = date_str
        self._page = 0

    def __call__(self, canvas, doc):
        self._page += 1
        canvas.saveState()

        # ── Bande haute ──────────────────────────────────
        canvas.setFillColor(TABLE_HDR)
        canvas.rect(0, PAGE_H - 1.4*cm, PAGE_W, 1.4*cm, fill=1, stroke=0)

        canvas.setFillColor(PRIMARY)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(MARGIN_H, PAGE_H - 0.9*cm, "CCM ANALYSER")

        canvas.setFillColor(GRAY_MID)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(MARGIN_H, PAGE_H - 1.15*cm, self.lab)

        # ID + date (droite)
        canvas.setFillColor(PRIMARY)
        canvas.setFont("Courier-Bold", 9)
        id_w = canvas.stringWidth(self.doc_id, "Courier-Bold", 9)
        canvas.drawString(PAGE_W - MARGIN_H - id_w, PAGE_H - 0.9*cm, self.doc_id)

        canvas.setFillColor(GRAY_MID)
        canvas.setFont("Helvetica", 8)
        date_w = canvas.stringWidth(self.date_str, "Helvetica", 8)
        canvas.drawString(PAGE_W - MARGIN_H - date_w, PAGE_H - 1.15*cm, self.date_str)

        # ── Bande basse ──────────────────────────────────
        canvas.setFillColor(TABLE_HDR)
        canvas.rect(0, 0, PAGE_W, 1.0*cm, fill=1, stroke=0)

        # Ligne fine
        canvas.setStrokeColor(BORDER_COL)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_H, 1.0*cm, PAGE_W - MARGIN_H, 1.0*cm)

        canvas.setFillColor(GRAY_DARK)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(
            PAGE_W / 2, 0.35*cm,
            f"API-BENIN — Laboratoire de Contrôle Qualité Phytomédicaments — Page {self._page}"
        )

        canvas.restoreState()


# ════════════════════════════════════════════════════════════
#  HELPERS VISUELS
# ════════════════════════════════════════════════════════════
def _section_title(text: str, styles: dict) -> list:
    """Retourne [HRFlowable, Paragraph] pour un titre de section."""
    return [
        HRFlowable(width="100%", thickness=0.5, color=BORDER_COL, spaceAfter=6),
        Paragraph(text.upper(), styles["section_head"]),
    ]


def _kv_table(pairs: list[tuple], styles: dict, cols: int = 3) -> Table:
    """Génère un tableau clé/valeur en grille N colonnes."""
    # Padding pairs pour aligner
    while len(pairs) % cols:
        pairs.append(("", ""))

    rows = []
    for i in range(0, len(pairs), cols):
        row_labels = []
        row_values = []
        for k, v in pairs[i:i+cols]:
            row_labels.append(Paragraph(k, styles["label"]) if k else Paragraph("", styles["label"]))
            row_values.append(Paragraph(str(v) if v else "—", styles["value"]) if k else Paragraph("", styles["value"]))
        rows.append(row_labels)
        rows.append(row_values)

    col_w = (PAGE_W - 2 * MARGIN_H) / cols
    tbl = Table(rows, colWidths=[col_w] * cols, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [TABLE_ROW1, TABLE_ROW2]),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 4),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",           (0, 0), (-1, -1), 0.3, BORDER_COL),
        ("ROUNDEDCORNERS", (0, 0), (-1, -1), [3, 3, 3, 3]),
    ]))
    return tbl


def _rf_table(spots: list[dict], styles: dict) -> Table:
    """Tableau détaillé des spots et valeurs Rf."""
    headers = ["#", "X (%)", "Y (%)", "Rf", "Intensité (%)", "Alcaloïde identifié", "Confiance", "Statut"]
    col_widths = [0.8*cm, 1.5*cm, 1.5*cm, 2.0*cm, 2.2*cm, 5.2*cm, 2.2*cm, 2.2*cm]

    rows = [[Paragraph(h, ParagraphStyle("th",
                fontSize=7.5, fontName="Helvetica-Bold",
                textColor=GRAY_MID, alignment=TA_CENTER)) for h in headers]]

    for s in spots:
        statut = s.get("statut", "probable")
        if statut == "confirmed":
            statut_p = Paragraph("✓ Confirmé", styles["tag_green"])
        elif statut == "absent":
            statut_p = Paragraph("✗ Absent",   styles["tag_red"])
        else:
            statut_p = Paragraph("~ Probable", styles["tag_amber"])

        conf_val = s.get("confidence", 0)
        conf_col = GREEN if conf_val >= 80 else AMBER if conf_val >= 50 else RED

        rows.append([
            Paragraph(str(s.get("id", "?")),
                      ParagraphStyle("ctr", fontSize=8, fontName="Helvetica-Bold",
                                     textColor=WHITE, alignment=TA_CENTER)),
            Paragraph(f"{s.get('x', 0):.1f}",
                      ParagraphStyle("ctr", fontSize=8, fontName="Courier",
                                     textColor=GRAY_MID, alignment=TA_CENTER)),
            Paragraph(f"{s.get('y', 0):.1f}",
                      ParagraphStyle("ctr", fontSize=8, fontName="Courier",
                                     textColor=GRAY_MID, alignment=TA_CENTER)),
            Paragraph(f"{s.get('rf', 0):.4f}",
                      ParagraphStyle("rf", fontSize=9, fontName="Courier-Bold",
                                     textColor=PRIMARY, alignment=TA_CENTER)),
            Paragraph(f"{s.get('intensite', 0):.1f}",
                      ParagraphStyle("ctr", fontSize=8, fontName="Courier",
                                     textColor=GRAY_MID, alignment=TA_CENTER)),
            Paragraph(s.get("alcaloide", "Inconnu"),
                      ParagraphStyle("alc", fontSize=8.5, fontName="Helvetica-Bold",
                                     textColor=WHITE, alignment=TA_LEFT)),
            Paragraph(f"{conf_val:.0f}%",
                      ParagraphStyle("conf", fontSize=8.5, fontName="Helvetica-Bold",
                                     textColor=conf_col, alignment=TA_CENTER)),
            statut_p,
        ])

    tbl = Table(rows, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    tbl.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), TABLE_HDR),
        ("TOPPADDING",    (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        # Body rows
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [TABLE_ROW1, TABLE_ROW2]),
        ("TOPPADDING",    (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER_COL),
        ("LINEBELOW",     (0, 0), (-1, 0),  0.8, PRIMARY),
    ]))
    return tbl


def _make_qr(data: str, size: int = 90) -> Optional[RLImage]:
    """Génère un QR code ReportLab à partir d'une chaîne."""
    try:
        qr = qrcode.QRCode(version=1, box_size=4, border=2,
                            error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(data)
        qr.make(fit=True)
        pil_img = qr.make_image(fill_color="white", back_color="#0f1318")
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)
        return RLImage(buf, width=size, height=size)
    except Exception:
        return None


def _plate_image(path: str, max_w: float, max_h: float) -> Optional[RLImage]:
    """Charge l'image de la plaque, redimensionnée pour le PDF."""
    if not path or not os.path.exists(path):
        return None
    try:
        from PIL import Image as PILImage
        with PILImage.open(path) as pil:
            iw, ih = pil.size
        ratio = min(max_w / iw, max_h / ih)
        return RLImage(path, width=iw * ratio, height=ih * ratio)
    except Exception:
        return None


# ════════════════════════════════════════════════════════════
#  GÉNÉRATION PRINCIPALE
# ════════════════════════════════════════════════════════════
def generate_pdf(analysis: dict, options: dict, output_path: str) -> str:
    """
    Génère le rapport PDF complet.

    Args:
        analysis: dict sérialisé de l'analyse (to_dict())
        options:  {title, lab, responsable, conclusion,
                   include_params, include_plate, include_rf,
                   include_id, include_concl, include_qr}
        output_path: chemin du fichier PDF à créer

    Returns:
        output_path
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    styles = _build_styles()
    spots  = analysis.get("spots", [])
    lab    = options.get("lab", "Laboratoire API-BENIN")
    title  = options.get("title", f"Rapport CCM — {analysis.get('id', '?')}")
    resp   = options.get("responsable", "—")
    concl  = options.get("conclusion", "")
    ana_id = analysis.get("id", "CCM-???")
    date_raw = analysis.get("date", "")
    try:
        dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
        date_str = dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        date_str = date_raw or datetime.now().strftime("%d/%m/%Y %H:%M")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN_H, rightMargin=MARGIN_H,
        topMargin=1.8*cm, bottomMargin=1.4*cm,
        title=title,
        author=lab,
        subject="Analyse CCM — Alcaloïdes",
        creator="CCM Analyser v1.0 — API-BENIN",
    )

    decorator = _PageDecorator(lab, ana_id, date_str)
    story     = []
    avail_w   = PAGE_W - 2 * MARGIN_H

    # ── TITRE ──────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))

    # Bloc titre stylisé
    title_tbl = Table(
        [[Paragraph("🔬", ParagraphStyle("ico", fontSize=26, alignment=TA_CENTER)),
          [Paragraph(title, styles["title"]),
           Paragraph(f"{lab}  ·  {date_str}", styles["subtitle"])]]],
        colWidths=[1.2*cm, avail_w - 1.2*cm],
        hAlign="LEFT"
    )
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), TABLE_HDR),
        ("TOPPADDING",   (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 14),
        ("LEFTPADDING",  (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",    (0, 0), (-1, 0),  2, PRIMARY),
        ("ROUNDEDCORNERS",(0,0), (-1,-1),  [5, 5, 5, 5]),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── RÉSUMÉ RAPIDE ──────────────────────────────────────
    confirmed = sum(1 for s in spots if s.get("statut") == "confirmed")
    summary_data = [
        [Paragraph("ID Analyse", styles["label"]),
         Paragraph("Nb. Spots", styles["label"]),
         Paragraph("Identifiés", styles["label"]),
         Paragraph("Opérateur", styles["label"])],
        [Paragraph(ana_id, styles["mono"]),
         Paragraph(str(len(spots)), ParagraphStyle("v", fontSize=13,
              fontName="Helvetica-Bold", textColor=PRIMARY, alignment=TA_CENTER)),
         Paragraph(str(confirmed), ParagraphStyle("v", fontSize=13,
              fontName="Helvetica-Bold", textColor=GREEN, alignment=TA_CENTER)),
         Paragraph(analysis.get("operateur", "—"), styles["value"])],
    ]
    sum_tbl = Table(summary_data,
                    colWidths=[avail_w * 0.35, avail_w * 0.18,
                               avail_w * 0.18, avail_w * 0.29])
    sum_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), TABLE_ROW2),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER_COL),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (2, -1),  "CENTER"),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── PARAMÈTRES ─────────────────────────────────────────
    if options.get("include_params", True):
        story += _section_title("Paramètres de l'analyse", styles)
        params_pairs = [
            ("Échantillon",     analysis.get("echantillon", "—")),
            ("Phytomédicament", analysis.get("phyto", "—")),
            ("Numéro de lot",   analysis.get("lot", "—")),
            ("Origine",         analysis.get("origine", "—")),
            ("Date d'analyse",  date_str),
            ("Opérateur",       analysis.get("operateur", "—")),
            ("Système de solvant", analysis.get("solvantLabel", "—")),
            ("Révélateur",      analysis.get("revelateurLabel", "—")),
            ("Type de plaque",  analysis.get("plaque", "—")),
            ("Méthode de détection", analysis.get("methodeLabel", "—")),
            ("Nb. dépôts",      str(analysis.get("depots", 2))),
            ("Standard référence", analysis.get("ref", "—")),
        ]
        story.append(_kv_table(params_pairs, styles, cols=3))
        story.append(Spacer(1, 0.15*cm))

        if analysis.get("notes"):
            story.append(Paragraph("<b>Notes :</b> " + analysis["notes"], styles["body"]))
        story.append(Spacer(1, 0.2*cm))

    # ── IMAGE PLAQUE ────────────────────────────────────────
    if options.get("include_plate", True):
        story += _section_title("Image de la plaque CCM annotée", styles)

        # Préférer l'image annotée
        img_path = analysis.get("imageAnnoteePath") or analysis.get("imagePath")
        plate_img = _plate_image(img_path, avail_w * 0.65, 12 * cm) if img_path else None

        if plate_img:
            # Légende à côté de l'image
            legend_items = [
                ("Front du solvant",  "→ Ligne de référence supérieure", AMBER),
                ("Ligne de dépôt",    "→ Ligne de référence inférieure", PRIMARY),
                ("Spots détectés",    f"→ {len(spots)} spot(s) sur cette plaque", GREEN),
                ("Front Y",           f"→ {analysis.get('frontY', 0)*100:.1f}% de la hauteur", GRAY_MID),
                ("Dépôt Y",           f"→ {analysis.get('depotY', 0)*100:.1f}% de la hauteur", GRAY_MID),
            ]

            leg_rows = []
            for label, detail, col in legend_items:
                # hexval() retourne '0xrrggbb', on prend les 6 derniers chars
                hex6 = col.hexval()[-6:]
                leg_rows.append([
                    Paragraph(f"<font color='#{hex6}'>■</font>",
                               ParagraphStyle("dot", fontSize=10, alignment=TA_CENTER)),
                    Paragraph(f"<b>{label}</b><br/><font size='7'>{detail}</font>",
                               ParagraphStyle("leg", fontSize=8, fontName="Helvetica",
                                              textColor=GRAY_LIGHT, leading=11)),
                ])

            leg_tbl = Table(leg_rows, colWidths=[0.6*cm, (avail_w * 0.32) - 0.6*cm])
            leg_tbl.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, -1), TABLE_ROW2),
                ("TOPPADDING",   (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
                ("LEFTPADDING",  (0, 0), (-1, -1), 6),
                ("GRID",         (0, 0), (-1, -1), 0.3, BORDER_COL),
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ]))

            plate_layout = Table(
                [[plate_img, leg_tbl]],
                colWidths=[avail_w * 0.65, avail_w * 0.33],
            )
            plate_layout.setStyle(TableStyle([
                ("VALIGN",      (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",(0, 0), (-1, -1), 0),
                ("TOPPADDING",  (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING",(0,0), (-1,-1),  0),
            ]))
            story.append(plate_layout)
        else:
            story.append(Paragraph(
                "⚠ Image non disponible pour ce rapport.", styles["body"]
            ))
        story.append(Spacer(1, 0.3*cm))

    # ── TABLEAU Rf ──────────────────────────────────────────
    if options.get("include_rf", True) and spots:
        story += _section_title("Valeurs Rf calculées — Tableau détaillé", styles)
        story.append(_rf_table(spots, styles))
        story.append(Spacer(1, 0.2*cm))

        # Méthode de calcul
        story.append(Paragraph(
            "<b>Méthode de calcul :</b> Rf = d(spot→ligne dépôt) / d(front→ligne dépôt). "
            f"Lignes de référence détectées automatiquement (front: {analysis.get('frontY',0)*100:.1f}%, "
            f"dépôt: {analysis.get('depotY',0)*100:.1f}% de la hauteur de l'image).",
            styles["body"]
        ))
        story.append(Spacer(1, 0.2*cm))

    # ── IDENTIFICATION ──────────────────────────────────────
    if options.get("include_id", True) and spots:
        story += _section_title("Identification des alcaloïdes", styles)

        for s in spots:
            statut  = s.get("statut", "probable")
            conf    = s.get("confidence", 0)
            alcal   = s.get("alcaloide", "Inconnu")
            rf_val  = s.get("rf", 0)

            if statut == "confirmed":
                icon = "✓"; col_h = GREEN
            elif statut == "absent":
                icon = "✗"; col_h = RED
            else:
                icon = "~"; col_h = AMBER

            row = Table([[
                Paragraph(icon, ParagraphStyle("icon", fontSize=14,
                           fontName="Helvetica-Bold", textColor=col_h, alignment=TA_CENTER)),
                [
                    Paragraph(f"<b>Spot #{s.get('id')} — {alcal}</b>",
                               ParagraphStyle("iname", fontSize=10, fontName="Helvetica-Bold",
                                              textColor=WHITE)),
                    Paragraph(f"Rf = {rf_val:.4f}  ·  Intensité = {s.get('intensite',0):.1f}%  "
                               f"·  Position X={s.get('x',0):.1f}%  Y={s.get('y',0):.1f}%",
                               ParagraphStyle("idet", fontSize=8, fontName="Helvetica",
                                              textColor=GRAY_MID)),
                ],
                Paragraph(f"{conf:.0f}%",
                           ParagraphStyle("iconf", fontSize=14, fontName="Helvetica-Bold",
                                          textColor=col_h, alignment=TA_CENTER)),
                Paragraph("confiance", ParagraphStyle("icl", fontSize=7, fontName="Helvetica",
                                                       textColor=GRAY_DARK, alignment=TA_CENTER)),
            ]], colWidths=[0.9*cm, avail_w - 3.2*cm, 1.6*cm, 1.5*cm])
            row.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), TABLE_ROW2),
                ("TOPPADDING",    (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("GRID",          (0, 0), (-1, -1), 0.3, BORDER_COL),
                ("LINEBEFORE",    (0, 0), (0, -1),  3, col_h),
            ]))
            story.append(KeepTogether([row, Spacer(1, 0.15*cm)]))
        story.append(Spacer(1, 0.1*cm))

    # ── CONCLUSION ──────────────────────────────────────────
    if options.get("include_concl", True):
        story += _section_title("Conclusion et interprétation", styles)
        if concl:
            conclusion_tbl = Table(
                [[Paragraph(concl, styles["conclusion"])]],
                colWidths=[avail_w]
            )
            conclusion_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), TABLE_ROW2),
                ("TOPPADDING",    (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING",   (0, 0), (-1, -1), 14),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
                ("GRID",          (0, 0), (-1, -1), 0.3, PRIMARY),
                ("LINEBEFORE",    (0, 0), (0, -1),  3, PRIMARY),
            ]))
            story.append(conclusion_tbl)
        else:
            story.append(Paragraph(
                "Aucune conclusion renseignée pour cette analyse.", styles["body"]
            ))
        story.append(Spacer(1, 0.4*cm))

    # ── SIGNATURES ──────────────────────────────────────────
    story += _section_title("Validation et signatures", styles)

    qr_cell = _make_qr(
        f"API-BENIN|CCM|{ana_id}|{date_str}", size=70
    ) if options.get("include_qr", False) else Paragraph("", styles["body"])

    sig_w  = (avail_w - 1.5*cm) / 3
    sig_data = [[
        [Paragraph("Opérateur",        styles["sig_label"]),
         Spacer(1, 0.8*cm),
         HRFlowable(width=sig_w * 0.8, color=GRAY_DARK),
         Paragraph(analysis.get("operateur", "—"), styles["sig_value"])],
        [Paragraph("Responsable qualité", styles["sig_label"]),
         Spacer(1, 0.8*cm),
         HRFlowable(width=sig_w * 0.8, color=GRAY_DARK),
         Paragraph(resp, styles["sig_value"])],
        [Paragraph("Date de validation", styles["sig_label"]),
         Spacer(1, 0.8*cm),
         HRFlowable(width=sig_w * 0.8, color=GRAY_DARK),
         Paragraph(datetime.now().strftime("%d/%m/%Y"), styles["sig_value"])],
    ]]

    sig_tbl = Table(sig_data, colWidths=[sig_w, sig_w, sig_w])
    sig_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), TABLE_ROW2),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER_COL),
        ("LINEABOVE",     (0, 0), (-1, 0),  1.5, PRIMARY),
    ]))

    if options.get("include_qr", False) and qr_cell:
        qr_layout = Table([[sig_tbl, qr_cell]],
                           colWidths=[avail_w - 1.8*cm, 1.8*cm])
        qr_layout.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0,0),(-1,-1), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), 0),
        ]))
        story.append(qr_layout)
    else:
        story.append(sig_tbl)

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} "
        f"par CCM Analyser v1.0 — API-BENIN. "
        f"Réf: {ana_id}.",
        styles["footer"]
    ))

    # ── COMPILATION ─────────────────────────────────────────
    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    return output_path