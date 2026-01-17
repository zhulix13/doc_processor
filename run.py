import os
from app import create_app

# Load .env ONLY in local development
if os.getenv("RENDER") is None:
    from dotenv import load_dotenv
    load_dotenv()

# Determine config
config_name = os.getenv("FLASK_ENV", "development").strip()

# Create app
app = create_app(config_name)

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=app.config["DEBUG"],
    )
