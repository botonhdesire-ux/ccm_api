"""
============================================================
  API-BENIN CCM Analyser — Application Flask principale
  Lance le serveur avec :  python app.py
  ou en production :       gunicorn app:create_app()
============================================================
"""

import os
import sys
import logging
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

# ── Ajout du répertoire courant au path Python ────────────
sys.path.insert(0, os.path.dirname(__file__))

# ── Configuration du logging ──────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_app(config: dict = None) -> Flask:
    """
    Factory Flask — crée et configure l'application.
    """
    # ── Chemins absolus ────────────────────────────────────
    base_dir   = os.path.dirname(os.path.abspath(__file__))
    root_dir   = os.path.dirname(base_dir)              # dossier parent (ccm-api-benin/)
    static_dir = os.path.join(root_dir, "ccm-api-benin") # frontend

    upload_dir = os.path.join(base_dir, "uploads")
    export_dir = os.path.join(base_dir, "exports")
    db_dir     = os.path.join(base_dir, "db")

    for d in [upload_dir, export_dir, db_dir]:
        os.makedirs(d, exist_ok=True)

    # ── Création Flask ─────────────────────────────────────
    app = Flask(
        __name__,
        static_folder=static_dir,
        static_url_path="",
    )

    # ── Configuration ──────────────────────────────────────
    app.config.update(
        SECRET_KEY          = os.environ.get("SECRET_KEY", "ccm-apibenin-dev-key-change-in-prod"),
        MAX_CONTENT_LENGTH  = 100 * 1024 * 1024,  # 100 MB max upload
        UPLOAD_DIR          = upload_dir,
        EXPORT_DIR          = export_dir,
        JSON_ENSURE_ASCII   = False,
        JSON_SORT_KEYS      = False,
    )

    if config:
        app.config.update(config)

    # ── CORS (permettre le frontend de différentes origines) ──
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Initialisation BDD ─────────────────────────────────
    from models.database import init_db
    init_db()
    logger.info("Base de données initialisée")

    # ── Enregistrement des routes API ─────────────────────
    from api.routes import api as api_blueprint
    app.register_blueprint(api_blueprint)
    logger.info("Routes API enregistrées")

    # ── Routes frontend (servir les fichiers statiques) ────
    @app.route("/")
    def index():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(static_dir, "index.html")
        return jsonify({"status": "ok", "message": "CCM Analyser API — API-BENIN",
                         "frontend": "Placer les fichiers HTML dans ../ccm-api-benin/"}), 200

    @app.route("/<path:filename>")
    def static_files(filename):
        """Sert les fichiers statiques du frontend."""
        if static_dir and os.path.exists(os.path.join(static_dir, filename)):
            return send_from_directory(static_dir, filename)
        return jsonify({"error": f"Fichier '{filename}' introuvable"}), 404

    # ── Gestion des erreurs ────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Ressource introuvable", "path": str(e)}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Méthode HTTP non autorisée"}), 405

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "Fichier trop volumineux (max 100 Mo)"}), 413

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Erreur interne : {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

    logger.info(f"Application CCM Analyser prête — static: {static_dir}")
    return app


# ════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CCM Analyser — Serveur API-BENIN")
    parser.add_argument("--host",  default="0.0.0.0",  help="Adresse d'écoute (défaut: 0.0.0.0)")
    parser.add_argument("--port",  default=5000, type=int, help="Port (défaut: 5000)")
    parser.add_argument("--debug", action="store_true",   help="Mode debug Flask")
    args = parser.parse_args()

    app = create_app()

    logger.info("=" * 60)
    logger.info("  CCM Analyser — API-BENIN")
    logger.info(f"  Serveur démarré → http://{args.host}:{args.port}")
    logger.info(f"  API disponible  → http://{args.host}:{args.port}/api/health")
    logger.info("=" * 60)

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=False,
    )