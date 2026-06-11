"""100xPortfolio Flask application factory."""

import os

from flask import Flask, jsonify, render_template, request, send_from_directory

from .game import daily_rounds, learn_data, score

# templates/ and static/ live one level up from this package.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(_ROOT, "templates"),
        static_folder=os.path.join(_ROOT, "static"),
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/favicon.ico")
    def favicon():
        # Browsers request /favicon.ico at the site root regardless of <link>s.
        return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/x-icon")

    @app.route("/api/daily")
    def api_daily():
        # No seed -> today's shared daily spin; a random seed -> a fresh replay.
        return jsonify(daily_rounds(request.args.get("seed")))

    @app.route("/api/learn")
    def api_learn():
        return jsonify(learn_data())

    @app.route("/api/score", methods=["POST"])
    def api_score():
        body = request.get_json(silent=True) or {}
        picks = body.get("picks")
        if not isinstance(picks, list):
            return jsonify({"error": "picks must be a list"}), 400
        try:
            return jsonify(score(picks, body.get("seed") or body.get("day")))
        except (ValueError, KeyError, TypeError) as e:
            return jsonify({"error": str(e)}), 400

    return app


app = create_app()
