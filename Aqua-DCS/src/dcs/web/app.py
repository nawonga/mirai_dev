"""Flask app factory for aqua-dcs."""

from __future__ import annotations

from flask import Flask

from dcs.web.routes_api import api_bp
from dcs.web.routes_ui import ui_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(ui_bp)
    return app


if __name__ == "__main__":
    # NOTE: when running under systemd, debug/reloader should be off.
    # The reloader forks a child process and can confuse service managers.
    create_app().run(host="0.0.0.0", port=8000, debug=False)
