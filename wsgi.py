from app import create_app
import os

config_name = os.getenv("FLASK_ENV", "development").strip()
app = create_app(config_name)
