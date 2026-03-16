from flask import Flask
from config import Config
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024
app.config["SECRET_KEY"] = Config.SECRET_KEY
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    app.run(debug=True)