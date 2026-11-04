import os

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory

from . import config
from .data import ERAS, INDUSTRIES
from .game import (
    LOCATIONS, cell_stocks, daily_rounds, day_number, era_label, learn_data, practice_seed, score,
    today_str,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Last day this browser scored the daily.
DAILY_COOKIE = "100x_daily"
_COOKIE_MAX_AGE = 400 * 24 * 60 * 60  # browser max


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(_ROOT, "templates"),
        static_folder=os.path.join(_ROOT, "static"),
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/d/<int:n>")
    def daily_page(n):
        today = day_number(today_str())
        if n != today:  # only today's board is playable
            return redirect(f"/d/{today}")
        return render_template("index.html", day=n)

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/x-icon")

    @app.route("/api/daily")
    def api_daily():
        seed = request.args.get("seed")
        if not seed:
            played_today = request.cookies.get(DAILY_COOKIE) == today_str()
            seed = practice_seed() if played_today else today_str()
        resp = jsonify(daily_rounds(seed))
        resp.headers["Cache-Control"] = "private, no-store"  # varies by cookie
        return resp

    @app.route("/api/cell")
    def api_cell():
        # Skip re-roll target.
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
            # Spent on score, not on deal, so an abandoned run survives.
            resp.set_cookie(DAILY_COOKIE, result["day"], max_age=_COOKIE_MAX_AGE,
                            httponly=True, samesite="Lax", secure=request.is_secure)
        return resp

    return app


app = create_app()
