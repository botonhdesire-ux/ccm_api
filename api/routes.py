"""
============================================================
  API-BENIN CCM Analyser — Routes API Flask
  Endpoints REST :
    POST   /api/analyse             → traitement image CCM
    GET    /api/analyses            → liste toutes les analyses
    GET    /api/analyse/<id>        → détail d'une analyse
    PUT    /api/analyse/<id>/valider → valider une analyse
    DELETE /api/analyse/<id>        → supprimer
    POST   /api/rapport/pdf         → générer PDF
    GET    /api/rapport/<id>/csv    → export CSV
    GET    /api/rapport/<id>/json   → export JSON
    GET    /api/health              → santé du serveur
    GET    /api/alcaloides          → base Rf connue
============================================================
"""

import os
import json
import base64
import logging
import tempfile
from datetime import datetime, timezone

import cv2
import numpy as np
from flask import Blueprint, request, jsonify, send_file, current_app, abort

from models.database import get_session, Analyse, Spot
from core.image_processor import run_pipeline
from core.pdf_generator import generate_pdf
from core.export_utils import export_csv, export_json

logger = logging.getLogger(__name__)
api    = Blueprint("api", __name__, url_prefix="/api")


# ════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════
def _generate_id() -> str:
    import random, string, time
    ts   = base64.b32encode(int(time.time()).to_bytes(5, "big")).decode().rstrip("=")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"CCM-{ts}-{rand}"


def _json_error(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


def _save_image(file_storage, upload_dir: str) -> str:
    """Sauvegarde l'image uploadée, retourne le chemin absolu."""
    os.makedirs(upload_dir, exist_ok=True)
    ext      = os.path.splitext(file_storage.filename)[1].lower() or ".png"
    filename = f"{_generate_id()}{ext}"
    path     = os.path.join(upload_dir, filename)
    file_storage.save(path)
    return path


def _save_annotated(annotated_bgr: np.ndarray, upload_dir: str, base_id: str) -> str:
    """Sauvegarde l'image annotée par OpenCV."""
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{base_id}_annotated.png"
    path     = os.path.join(upload_dir, filename)
    cv2.imwrite(path, annotated_bgr)
    return path


# ════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ════════════════════════════════════════════════════════════
@api.get("/health")
def health():
    return jsonify({
        "status":  "ok",
        "service": "CCM Analyser — API-BENIN",
        "version": "1.0.0",
        "time":    datetime.now(timezone.utc).isoformat(),
    })


# ════════════════════════════════════════════════════════════
#  BASE DE DONNÉES Rf (alcaloïdes de référence)
# ════════════════════════════════════════════════════════════
@api.get("/alcaloides")
def get_alcaloides():
    """Retourne la base de données Rf des alcaloïdes connus."""
    from core.image_processor import RF_DATABASE
    result = {}
    for compound, solvants in RF_DATABASE.items():
        result[compound] = {
            solv: {"rf_min": v[0], "rf_max": v[1], "rf_mid": round((v[0]+v[1])/2, 4)}
            for solv, v in solvants.items()
        }
    return jsonify({"alcaloides": result, "total": len(result)})


# ════════════════════════════════════════════════════════════
#  POST /api/analyse — TRAITEMENT IMAGE
# ════════════════════════════════════════════════════════════
@api.post("/analyse")
def post_analyse():
    """
    Reçoit : multipart/form-data
      - image   : fichier image (PNG/JPG/TIFF/BMP)
      - params  : JSON string avec les paramètres CCM

    Retourne : JSON analyse complète (compatible frontend)
    """
    # ── Validation image ──
    if "image" not in request.files:
        return _json_error("Fichier image manquant (champ 'image')")

    image_file = request.files["image"]
    if not image_file.filename:
        return _json_error("Nom de fichier vide")

    allowed = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
    ext = os.path.splitext(image_file.filename)[1].lower()
    if ext not in allowed:
        return _json_error(f"Format non supporté : {ext}. Formats acceptés : PNG, JPG, TIFF, BMP")

    # ── Validation paramètres ──
    try:
        params = json.loads(request.form.get("params", "{}"))
    except json.JSONDecodeError:
        return _json_error("Paramètres JSON invalides")

    echantillon = params.get("echantillon", "").strip()
    phyto       = params.get("phyto", "").strip()
    if not echantillon:
        return _json_error("Identifiant de l'échantillon requis")
    if not phyto:
        return _json_error("Nom du phytomédicament requis")

    # ── Sauvegarde image ──
    upload_dir = current_app.config["UPLOAD_DIR"]
    ana_id     = _generate_id()

    try:
        image_path = _save_image(image_file, upload_dir)
        logger.info(f"[{ana_id}] Image sauvegardée → {image_path}")
    except Exception as e:
        logger.error(f"Erreur sauvegarde image : {e}")
        return _json_error("Erreur lors de la sauvegarde de l'image", 500)

    # ── Pipeline de traitement ──
    try:
        front_hint = float(params.get("frontY", 5)) / 100   # % → décimal
        depot_hint = float(params.get("depotY", 92)) / 100
        solvant    = params.get("solvant", "autre")
        methode    = params.get("methode", "auto")

        result = run_pipeline(
            image_path=image_path,
            front_y_hint=front_hint,
            depot_y_hint=depot_hint,
            solvant=solvant,
            methode=methode,
        )
        logger.info(f"[{ana_id}] Pipeline terminé — {len(result['spots'])} spot(s)")
    except Exception as e:
        logger.error(f"[{ana_id}] Erreur pipeline : {e}", exc_info=True)
        return _json_error(f"Erreur lors du traitement de l'image : {str(e)}", 500)

    # ── Sauvegarde image annotée ──
    try:
        annotated_path = _save_annotated(
            result["annotated_img"], upload_dir, ana_id
        )
        logger.info(f"[{ana_id}] Image annotée → {annotated_path}")
    except Exception as e:
        logger.warning(f"[{ana_id}] Sauvegarde image annotée échouée : {e}")
        annotated_path = None

    # ── Persistence en base ──
    session = get_session()
    try:
        # Mappage labels
        solvant_labels = {
            "BEA":  "Butanol / Acide acétique / Eau (4:1:5)",
            "CM":   "Chloroforme / Méthanol (9:1)",
            "EA":   "Éthyl acétate / Ammoniac (9:1)",
            "CEA":  "Chloroforme / Éthanol / Ammoniac (8:2:0.2)",
            "autre":"Autre",
        }
        revelateur_labels = {
            "dragendorff": "Réactif de Dragendorff",
            "mayer":       "Réactif de Mayer",
            "uv254":       "UV 254 nm",
            "uv365":       "UV 365 nm",
            "kmno4":       "KMnO₄",
            "autre":       "Autre",
        }
        methode_labels = {
            "auto":      "Automatique (recommandé)",
            "threshold": "Seuillage adaptatif",
            "contour":   "Détection de contours",
            "hough":     "Transformation de Hough",
        }

        analyse = Analyse(
            id            = ana_id,
            date          = datetime.now(timezone.utc),
            status        = "done",
            exported      = False,
            echantillon   = echantillon,
            phyto         = phyto,
            origine       = params.get("origine", ""),
            lot           = params.get("lot", ""),
            operateur     = params.get("operateur", ""),
            notes         = params.get("notes", ""),
            depots        = int(params.get("depots", 2)),
            ref           = params.get("ref", ""),
            solvant       = solvant,
            solvant_label = params.get("solvantLabel") or solvant_labels.get(solvant, solvant),
            revelateur    = params.get("revelateur", ""),
            revelateur_label = (params.get("revelateurLabel") or
                                revelateur_labels.get(params.get("revelateur", ""), "")),
            plaque        = params.get("plaque", ""),
            methode       = methode,
            methode_label = params.get("methodeLabel") or methode_labels.get(methode, methode),
            front_y       = result["front_y_pct"],
            depot_y       = result["depot_y_pct"],
            image_path    = image_path,
            image_annotee_path = annotated_path,
        )

        # Spots
        for i, s in enumerate(result["spots"], start=1):
            spot = Spot(
                analyse_id = ana_id,
                spot_id    = i,
                x          = s["x_pct"],
                y          = s["y_pct"],
                rf         = s["rf"],
                intensite  = s.get("intensite", 0),
                area       = s.get("area"),
                perimeter  = s.get("perimeter"),
                alcaloide  = s.get("alcaloide", ""),
                confidence = s.get("confidence", 0),
                statut     = s.get("statut", "probable"),
                color      = s.get("color", "#4fb3ff"),
            )
            analyse.spots.append(spot)

        session.add(analyse)
        session.commit()
        logger.info(f"[{ana_id}] Sauvegardé en base")

        # ── Réponse ──
        response_data = analyse.to_dict(include_image_b64=True)
        return jsonify(response_data), 201

    except Exception as e:
        session.rollback()
        logger.error(f"[{ana_id}] Erreur BDD : {e}", exc_info=True)
        return _json_error(f"Erreur lors de la sauvegarde : {str(e)}", 500)
    finally:
        session.close()


# ════════════════════════════════════════════════════════════
#  GET /api/analyses — LISTE
# ════════════════════════════════════════════════════════════
@api.get("/analyses")
def get_analyses():
    """
    Retourne la liste des analyses.
    Query params : ?status=done|pending  &limit=50  &offset=0
    """
    status = request.args.get("status")
    limit  = min(int(request.args.get("limit",  100)), 500)
    offset = int(request.args.get("offset", 0))
    search = request.args.get("q", "").strip()

    session = get_session()
    try:
        q = session.query(Analyse).order_by(Analyse.date.desc())
        if status:
            q = q.filter(Analyse.status == status)
        if search:
            q = q.filter(
                (Analyse.id.contains(search)) |
                (Analyse.echantillon.contains(search)) |
                (Analyse.phyto.contains(search))
            )
        total   = q.count()
        items   = q.offset(offset).limit(limit).all()
        return jsonify({
            "total":    total,
            "limit":    limit,
            "offset":   offset,
            "analyses": [a.to_dict(include_image_b64=False) for a in items],
        })
    finally:
        session.close()


# ════════════════════════════════════════════════════════════
#  GET /api/analyse/<id> — DÉTAIL
# ════════════════════════════════════════════════════════════
@api.get("/analyse/<string:analyse_id>")
def get_analyse(analyse_id: str):
    session = get_session()
    try:
        analyse = session.query(Analyse).filter_by(id=analyse_id).first()
        if not analyse:
            return _json_error(f"Analyse '{analyse_id}' introuvable", 404)
        return jsonify(analyse.to_dict(include_image_b64=True))
    finally:
        session.close()


# ════════════════════════════════════════════════════════════
#  PUT /api/analyse/<id>/valider — VALIDER
# ════════════════════════════════════════════════════════════
@api.put("/analyse/<string:analyse_id>/valider")
def valider_analyse(analyse_id: str):
    session = get_session()
    try:
        analyse = session.query(Analyse).filter_by(id=analyse_id).first()
        if not analyse:
            return _json_error(f"Analyse '{analyse_id}' introuvable", 404)

        data = request.get_json(silent=True) or {}
        analyse.status       = "done"
        analyse.validated_at = datetime.now(timezone.utc)

        # Mise à jour des spots si fournis
        if "spots" in data:
            for spot_data in data["spots"]:
                spot = next((s for s in analyse.spots
                              if s.spot_id == spot_data.get("id")), None)
                if spot:
                    if "alcaloide"  in spot_data: spot.alcaloide  = spot_data["alcaloide"]
                    if "confidence" in spot_data: spot.confidence = spot_data["confidence"]
                    if "statut"     in spot_data: spot.statut     = spot_data["statut"]

        session.commit()
        logger.info(f"[{analyse_id}] Validée")
        return jsonify({"message": "Analyse validée", "id": analyse_id,
                        "validated_at": analyse.validated_at.isoformat()})
    except Exception as e:
        session.rollback()
        return _json_error(str(e), 500)
    finally:
        session.close()


# ════════════════════════════════════════════════════════════
#  DELETE /api/analyse/<id> — SUPPRIMER
# ════════════════════════════════════════════════════════════
@api.delete("/analyse/<string:analyse_id>")
def delete_analyse(analyse_id: str):
    session = get_session()
    try:
        analyse = session.query(Analyse).filter_by(id=analyse_id).first()
        if not analyse:
            return _json_error(f"Analyse '{analyse_id}' introuvable", 404)

        # Supprimer fichiers liés
        for path in [analyse.image_path, analyse.image_annotee_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

        session.delete(analyse)
        session.commit()
        logger.info(f"[{analyse_id}] Supprimée")
        return jsonify({"message": f"Analyse '{analyse_id}' supprimée"})
    except Exception as e:
        session.rollback()
        return _json_error(str(e), 500)
    finally:
        session.close()


# ════════════════════════════════════════════════════════════
#  POST /api/rapport/pdf — GÉNÉRER PDF
# ════════════════════════════════════════════════════════════
@api.post("/rapport/pdf")
def generate_rapport_pdf():
    """
    Body JSON :
      { analysis_id, options: { title, lab, responsable, conclusion,
        include_params, include_plate, include_rf, include_id,
        include_concl, include_qr } }
    """
    data = request.get_json(silent=True)
    if not data:
        return _json_error("Corps JSON requis")

    analyse_id = data.get("analysis_id")
    if not analyse_id:
        return _json_error("'analysis_id' requis")

    options = data.get("options", {})

    session = get_session()
    try:
        analyse = session.query(Analyse).filter_by(id=analyse_id).first()
        if not analyse:
            return _json_error(f"Analyse '{analyse_id}' introuvable", 404)

        ana_dict   = analyse.to_dict(include_image_b64=False)
        export_dir = current_app.config["EXPORT_DIR"]
        os.makedirs(export_dir, exist_ok=True)
        pdf_path   = os.path.join(export_dir, f"{analyse_id}_rapport.pdf")

        generate_pdf(ana_dict, options, pdf_path)

        # Marquer comme exporté
        analyse.exported = True
        session.commit()

        logger.info(f"[{analyse_id}] PDF généré → {pdf_path}")
        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"CCM_{analyse_id}_rapport.pdf",
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur génération PDF : {e}", exc_info=True)
        return _json_error(f"Erreur génération PDF : {str(e)}", 500)
    finally:
        session.close()


# ════════════════════════════════════════════════════════════
#  GET /api/rapport/<id>/csv — EXPORT CSV
# ════════════════════════════════════════════════════════════
@api.get("/rapport/<string:analyse_id>/csv")
def get_csv(analyse_id: str):
    session = get_session()
    try:
        analyse = session.query(Analyse).filter_by(id=analyse_id).first()
        if not analyse:
            return _json_error(f"Analyse '{analyse_id}' introuvable", 404)

        ana_dict = analyse.to_dict(include_image_b64=False)
        content  = export_csv(ana_dict)

        # Marquer exporté
        analyse.exported = True
        session.commit()

        import io
        buf = io.BytesIO(content.encode("utf-8-sig"))
        buf.seek(0)
        return send_file(
            buf,
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name=f"CCM_{analyse_id}.csv",
        )
    finally:
        session.close()


# ════════════════════════════════════════════════════════════
#  GET /api/rapport/<id>/json — EXPORT JSON
# ════════════════════════════════════════════════════════════
@api.get("/rapport/<string:analyse_id>/json")
def get_json_export(analyse_id: str):
    session = get_session()
    try:
        analyse = session.query(Analyse).filter_by(id=analyse_id).first()
        if not analyse:
            return _json_error(f"Analyse '{analyse_id}' introuvable", 404)

        ana_dict = analyse.to_dict(include_image_b64=False)
        options  = {
            "lab":         request.args.get("lab", "Laboratoire API-BENIN"),
            "responsable": request.args.get("responsable", ""),
        }
        content  = export_json(ana_dict, options)

        analyse.exported = True
        session.commit()

        import io
        buf = io.BytesIO(content.encode("utf-8"))
        buf.seek(0)
        return send_file(
            buf,
            mimetype="application/json",
            as_attachment=True,
            download_name=f"CCM_{analyse_id}.json",
        )
    finally:
        session.close()


# ════════════════════════════════════════════════════════════
#  GET /api/rapport/<id>/image — IMAGE ANNOTÉE
# ════════════════════════════════════════════════════════════
@api.get("/rapport/<string:analyse_id>/image")
def get_annotated_image(analyse_id: str):
    """Retourne l'image annotée de la plaque CCM."""
    session = get_session()
    try:
        analyse = session.query(Analyse).filter_by(id=analyse_id).first()
        if not analyse:
            return _json_error(f"Analyse '{analyse_id}' introuvable", 404)

        img_path = analyse.image_annotee_path or analyse.image_path
        if not img_path or not os.path.exists(img_path):
            return _json_error("Image non disponible", 404)

        return send_file(img_path, mimetype="image/png")
    finally:
        session.close()


# ════════════════════════════════════════════════════════════
#  GET /api/stats — STATISTIQUES GLOBALES
# ════════════════════════════════════════════════════════════
@api.get("/stats")
def get_stats():
    """Statistiques globales pour le dashboard."""
    session = get_session()
    try:
        from sqlalchemy import func
        total     = session.query(func.count(Analyse.id)).scalar()
        done      = session.query(func.count(Analyse.id)).filter_by(status="done").scalar()
        pending   = session.query(func.count(Analyse.id)).filter_by(status="pending").scalar()
        exported  = session.query(func.count(Analyse.id)).filter_by(exported=True).scalar()
        nb_spots  = session.query(func.count(Spot.id)).scalar()
        avg_conf  = session.query(func.avg(Spot.confidence)).scalar()

        return jsonify({
            "total_analyses": total,
            "done":           done,
            "pending":        pending,
            "exported":       exported,
            "total_spots":    nb_spots,
            "avg_confidence": round(avg_conf or 0, 1),
        })
    finally:
        session.close()