from flask import Flask
from fake_library.db import init_db
from fake_library.routes.auth import auth_bp
from fake_library.routes.users import users_bp
from fake_library.routes.books import books_bp
from fake_library.routes.files import files_bp, UPLOAD_DIR
from fake_library.routes.integrations import integrations_bp
from fake_library.routes.admin import admin_bp
from fake_library.routes.misc import misc_bp


def create_app() -> Flask:
    app = Flask(__name__)

    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize DB and seed data
    init_db()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(misc_bp)

    return app


def main() -> None:
    app = create_app()
    app.run(debug=True, port=5000)
