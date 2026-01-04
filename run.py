import os
from app import create_app

# Get environment from env variable
config_name = os.getenv('FLASK_ENV', 'development')

# Create app instance
app = create_app(config_name)

if __name__ == '__main__':
    # Get port from env or use 5000
    port = int(os.getenv('API_PORT', 5000))
    
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=port,
        debug=app.config['DEBUG']
    )