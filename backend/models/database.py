"""
============================================================
  API-BENIN CCM Analyser — Database Models
  SQLAlchemy ORM — SQLite (facilement migreable vers PostgreSQL)
============================================================
"""

import os
import json
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    Text, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

# ── Base ──────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

# ── Analyse ───────────────────────────────────────────────────
class Analyse(Base):
    """Représente une analyse CCM complète."""
    __tablename__ = "analyses"

    id            = Column(String(32),  primary_key=True)
    date          = Column(DateTime,    nullable=False, default=lambda: datetime.now(timezone.utc))
    status        = Column(String(16),  nullable=False, default="done")  # done | pending
    exported      = Column(Boolean,     nullable=False, default=False)
    validated_at  = Column(DateTime,    nullable=True)

    # Informations échantillon
    echantillon   = Column(String(128), nullable=False)
    phyto         = Column(String(256), nullable=False)
    origine       = Column(String(256), nullable=True)
    lot           = Column(String(128), nullable=True)
    operateur     = Column(String(128), nullable=True)
    notes         = Column(Text,        nullable=True)
    depots        = Column(Integer,     nullable=True, default=2)
    ref           = Column(String(128), nullable=True)

    # Paramètres CCM
    solvant       = Column(String(16),  nullable=True)
    solvant_label = Column(String(256), nullable=True)
    revelateur    = Column(String(32),  nullable=True)
    revelateur_label = Column(String(256), nullable=True)
    plaque        = Column(String(64),  nullable=True)
    methode       = Column(String(32),  nullable=True)
    methode_label = Column(String(128), nullable=True)

    # Calibration lignes
    front_y       = Column(Float,       nullable=True, default=0.05)
    depot_y       = Column(Float,       nullable=True, default=0.92)

    # Image (chemin relatif)
    image_path    = Column(String(512), nullable=True)
    image_annotee_path = Column(String(512), nullable=True)

    # Relations
    spots         = relationship("Spot", back_populates="analyse",
                                 cascade="all, delete-orphan", order_by="Spot.spot_id")

    def to_dict(self, include_image_b64: bool = False) -> dict:
        """Sérialise pour l'API JSON (compatible frontend)."""
        import base64

        image_data_url = None
        if include_image_b64 and self.image_path and os.path.exists(self.image_path):
            with open(self.image_path, "rb") as f:
                raw = f.read()
            ext = os.path.splitext(self.image_path)[1].lower().lstrip(".")
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "png": "image/png", "tiff": "image/tiff",
                    "bmp": "image/bmp"}.get(ext, "image/png")
            image_data_url = f"data:{mime};base64,{base64.b64encode(raw).decode()}"

        return {
            "id":             self.id,
            "date":           self.date.isoformat() if self.date else None,
            "status":         self.status,
            "exported":       self.exported,
            "validatedAt":    self.validated_at.isoformat() if self.validated_at else None,

            # Échantillon
            "echantillon":    self.echantillon,
            "phyto":          self.phyto,
            "origine":        self.origine or "",
            "lot":            self.lot or "",
            "operateur":      self.operateur or "",
            "notes":          self.notes or "",
            "depots":         self.depots or 2,
            "ref":            self.ref or "",

            # Paramètres
            "solvant":        self.solvant or "",
            "solvantLabel":   self.solvant_label or "",
            "revelateur":     self.revelateur or "",
            "revelateurLabel": self.revelateur_label or "",
            "plaque":         self.plaque or "",
            "methode":        self.methode or "",
            "methodeLabel":   self.methode_label or "",

            # Calibration
            "frontY":         self.front_y,
            "depotY":         self.depot_y,

            # Image
            "imageDataUrl":   image_data_url,
            "imagePath":      self.image_path,
            "imageAnnoteePath": self.image_annotee_path,

            # Spots
            "spots":          [s.to_dict() for s in self.spots],
            "nbSpots":        len(self.spots),
        }


# ── Spot ──────────────────────────────────────────────────────
class Spot(Base):
    """Représente un spot détecté sur la plaque CCM."""
    __tablename__ = "spots"

    id          = Column(Integer,     primary_key=True, autoincrement=True)
    analyse_id  = Column(String(32),  ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    spot_id     = Column(Integer,     nullable=False)   # numéro sur la plaque (1, 2, 3…)

    # Positions (% de la hauteur/largeur de l'image)
    x           = Column(Float,       nullable=False)
    y           = Column(Float,       nullable=False)

    # Valeurs calculées
    rf          = Column(Float,       nullable=False)
    intensite   = Column(Float,       nullable=True, default=0.0)   # 0-100
    area        = Column(Float,       nullable=True)                  # aire en pixels²
    perimeter   = Column(Float,       nullable=True)

    # Identification
    alcaloide   = Column(String(256), nullable=True)
    confidence  = Column(Float,       nullable=True)    # 0-100
    statut      = Column(String(16),  nullable=True)    # confirmed | probable | absent
    color       = Column(String(16),  nullable=True)    # couleur d'affichage hex

    # Relation
    analyse     = relationship("Analyse", back_populates="spots")

    def to_dict(self) -> dict:
        return {
            "id":         self.spot_id,
            "x":          round(self.x, 2),
            "y":          round(self.y, 2),
            "rf":         round(self.rf, 6),
            "intensite":  round(self.intensite or 0, 2),
            "area":       self.area,
            "perimeter":  self.perimeter,
            "alcaloide":  self.alcaloide or "",
            "confidence": round(self.confidence or 0, 1),
            "statut":     self.statut or "probable",
            "color":      self.color or "#4fb3ff",
        }


# ── Engine & Session factory ───────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "ccm_apibenin.db")
DB_URL  = f"sqlite:///{os.path.abspath(DB_PATH)}"

engine  = create_engine(DB_URL, connect_args={"check_same_thread": False}, echo=False)
Session = sessionmaker(bind=engine, autoflush=True, autocommit=False)


def init_db():
    """Crée toutes les tables si elles n'existent pas."""
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    Base.metadata.create_all(engine)


def get_session():
    """Retourne une session SQLAlchemy (à fermer après usage)."""
    return Session()