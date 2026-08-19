"""100xPortfolio Flask application factory."""

import os

from flask import Flask, jsonify, render_template, request, send_from_directory

from . import config
from .data import ERAS, INDUSTRIES
from .game import (
    LOCATIONS, cell_stocks, daily_rounds, era_label, learn_data, practice_seed, score, today_str,
)

# templates/ and static/ live one level up from this package.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Holds the last day this browser scored the daily. One daily per day per
# browser; clearing it just means being dealt the daily again.
DAILY_COOKIE = "100x_daily"
_COOKIE_MAX_AGE = 400 * 24 * 60 * 60  # 400 days, the ceiling browsers allow


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
        # An explicit seed replays that exact board (resume, or a practice roll).
        # Otherwise the day's shared board, until this browser has scored it.
        seed = request.args.get("seed")
        if not seed:
            played_today = request.cookies.get(DAILY_COOKIE) == today_str()
            seed = practice_seed() if played_today else today_str()
        resp = jsonify(daily_rounds(seed))
        resp.headers["Cache-Control"] = "private, no-store"  # the answer depends on the cookie
        return resp

    @app.route("/api/cell")
    def api_cell():
        # One (era, location) cell, fetched when a skip re-rolls into it.
        era, loc = request.args.get("era"), request.args.get("location")
        stocks = cell_stocks(era, loc)
        if not stocks:
            return jsonify({"error": "unknown cell"}), 404
        return jsonify({"era": era, "eraLabel": era_label(era), "location": loc, "stocks": stocks})

    @app.route("/api/learn")
    def api_learn():
        return jsonify(learn_data())

    @app.route("/api/config")
    def api_config():
        # Single source of truth the front end reads instead of hard-coding.
        return jsonify({
            "startingStake": config.STARTING_STAKE,
            "numRounds": config.NUM_ROUNDS,
            "industryColors": config.INDUSTRY_COLORS,
            "industryBlurbs": config.INDUSTRY_BLURBS,
            "eras": ERAS,
            "eraLabels": {e: era_label(e) for e in ERAS},
            "industries": INDUSTRIES,
            "locations": LOCATIONS,
        })

    @app.route("/api/score", methods=["POST"])
    def api_score():
        body = request.get_json(silent=True) or {}
        picks = body.get("picks")
        if not isinstance(picks, list):
            return jsonify({"error": "picks must be a list"}), 400
        try:
            result = score(picks, body.get("seed") or body.get("day"))
        except (ValueError, KeyError, TypeError) as e:
            return jsonify({"error": str(e)}), 400

        resp = jsonify(result)
        if result["mode"] == "daily":
            # The daily is spent on scoring, not on being dealt, so an abandoned
            # run is still there when they come back.
            resp.set_cookie(DAILY_COOKIE, result["day"], max_age=_COOKIE_MAX_AGE,
                            httponly=True, samesite="Lax", secure=request.is_secure)
        return resp

    return app


app = create_app()
