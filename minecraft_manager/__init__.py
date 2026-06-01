from pathlib import Path

from flask import Flask

from .env import load_env
from .db import close_db, init_db
from .routes import bp


def create_app(config=None) -> Flask:
    load_env(Path(__file__).resolve().parent.parent / ".env")
    if config is None:
        from .config import Config

        config = Config

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["BACKUP_DIR"]).mkdir(parents=True, exist_ok=True)

    app.teardown_appcontext(close_db)
    app.register_blueprint(bp)

    with app.app_context():
        init_db()

    return app
