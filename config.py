import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("ARCANA_SECRET_KEY", "dev-only-change-me")
    # Relative sqlite paths resolve inside ./instance/ with Flask-SQLAlchemy 3.x
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///financial_arcana.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DATA_RAW = os.path.join(BASE_DIR, "data", "raw")
    DATA_PROCESSED = os.environ.get("ARCANA_PROCESSED", os.path.join(BASE_DIR, "data", "processed"))
