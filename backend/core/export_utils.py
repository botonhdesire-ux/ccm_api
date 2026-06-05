"""
============================================================
  API-BENIN CCM Analyser — Export CSV & JSON
============================================================
"""

import csv
import json
import io
import os
from datetime import datetime
from typing import Optional


def export_csv(analysis: dict) -> str:
    """
    Génère le contenu CSV complet d'une analyse.
    Retourne la chaîne CSV encodée UTF-8-sig (compatible Excel).
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)

    # ── Méta-données ──
    writer.writerow(["# RAPPORT CCM — API-BENIN"])
    writer.writerow(["# Généré le", datetime.now().strftime("%d/%m/%Y %H:%M")])
    writer.writerow(["# ID",         analysis.get("id", "")])
    writer.writerow(["# Échantillon",analysis.get("echantillon", "")])
    writer.writerow(["# Phytomédicament", analysis.get("phyto", "")])
    writer.writerow(["# Lot",         analysis.get("lot", "")])
    writer.writerow(["# Origine",     analysis.get("origine", "")])
    writer.writerow(["# Date",        analysis.get("date", "")])
    writer.writerow(["# Opérateur",   analysis.get("operateur", "")])
    writer.writerow(["# Solvant",     analysis.get("solvantLabel", "")])
    writer.writerow(["# Révélateur",  analysis.get("revelateurLabel", "")])
    writer.writerow(["# Plaque",      analysis.get("plaque", "")])
    writer.writerow(["# Méthode",     analysis.get("methodeLabel", "")])
    writer.writerow(["# Front_Y_pct", analysis.get("frontY", "")])
    writer.writerow(["# Depot_Y_pct", analysis.get("depotY", "")])
    writer.writerow(["#"])

    # ── Données spots ──
    headers = [
        "Spot_ID", "Position_X_pct", "Position_Y_pct",
        "Rf", "Intensite_pct", "Aire_px2", "Perimetre_px",
        "Alcaloide_identifie", "Confiance_pct", "Statut", "Couleur"
    ]
    writer.writerow(headers)

    for s in analysis.get("spots", []):
        writer.writerow([
            s.get("id", ""),
            f"{s.get('x', 0):.2f}",
            f"{s.get('y', 0):.2f}",
            f"{s.get('rf', 0):.6f}",
            f"{s.get('intensite', 0):.2f}",
            f"{s.get('area', '') if s.get('area') else ''}",
            f"{s.get('perimeter', '') if s.get('perimeter') else ''}",
            s.get("alcaloide", ""),
            f"{s.get('confidence', 0):.1f}",
            s.get("statut", ""),
            s.get("color", ""),
        ])

    # UTF-8-BOM pour Excel
    return "\ufeff" + output.getvalue()


def export_json(analysis: dict, options: dict = None) -> str:
    """
    Génère le JSON d'export complet (sans imageDataUrl pour économiser la taille).
    """
    options = options or {}

    export = {
        "meta": {
            "exported_at":   datetime.now().isoformat(),
            "exported_by":   options.get("responsable", ""),
            "laboratory":    options.get("lab", "Laboratoire API-BENIN"),
            "software":      "CCM Analyser v1.0 — API-BENIN",
            "format_version": "1.0",
        },
        "analysis": {
            "id":              analysis.get("id"),
            "date":            analysis.get("date"),
            "status":          analysis.get("status"),
            "exported":        analysis.get("exported", False),
            "validated_at":    analysis.get("validatedAt"),

            # Échantillon
            "echantillon":     analysis.get("echantillon"),
            "phyto":           analysis.get("phyto"),
            "origine":         analysis.get("origine"),
            "lot":             analysis.get("lot"),
            "operateur":       analysis.get("operateur"),
            "notes":           analysis.get("notes"),
            "depots":          analysis.get("depots"),
            "ref":             analysis.get("ref"),

            # Paramètres CCM
            "solvant":         analysis.get("solvant"),
            "solvant_label":   analysis.get("solvantLabel"),
            "revelateur":      analysis.get("revelateur"),
            "revelateur_label": analysis.get("revelateurLabel"),
            "plaque":          analysis.get("plaque"),
            "methode":         analysis.get("methode"),
            "methode_label":   analysis.get("methodeLabel"),

            # Calibration
            "front_y":         analysis.get("frontY"),
            "depot_y":         analysis.get("depotY"),
        },
        "spots": [
            {
                "id":          s.get("id"),
                "x":           s.get("x"),
                "y":           s.get("y"),
                "rf":          s.get("rf"),
                "intensite":   s.get("intensite"),
                "area":        s.get("area"),
                "perimeter":   s.get("perimeter"),
                "alcaloide":   s.get("alcaloide"),
                "confidence":  s.get("confidence"),
                "statut":      s.get("statut"),
                "color":       s.get("color"),
            }
            for s in analysis.get("spots", [])
        ],
        "summary": {
            "nb_spots":          len(analysis.get("spots", [])),
            "nb_confirmed":      sum(1 for s in analysis.get("spots", [])
                                     if s.get("statut") == "confirmed"),
            "nb_probable":       sum(1 for s in analysis.get("spots", [])
                                     if s.get("statut") == "probable"),
            "rf_min":            min((s["rf"] for s in analysis.get("spots", [])
                                      if s.get("rf") is not None), default=None),
            "rf_max":            max((s["rf"] for s in analysis.get("spots", [])
                                      if s.get("rf") is not None), default=None),
            "avg_confidence":    (
                sum(s.get("confidence", 0) for s in analysis.get("spots", [])) /
                len(analysis.get("spots", [])) if analysis.get("spots") else 0
            ),
            "conclusion":        options.get("conclusion", ""),
        },
    }

    return json.dumps(export, ensure_ascii=False, indent=2)


def write_csv_file(analysis: dict, output_path: str) -> str:
    """Écrit le CSV sur disque et retourne le chemin."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    content = export_csv(analysis)
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(content)
    return output_path


def write_json_file(analysis: dict, options: dict, output_path: str) -> str:
    """Écrit le JSON sur disque et retourne le chemin."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    content = export_json(analysis, options)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path