"""Local family dashboard for prize bond checks."""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from prize_bond_checker.constants import (
    CLAIM_NOTE,
    DEFAULT_BONDS_FILE,
    DEFAULT_DENOMINATION,
    SUPPORTED_DENOMINATIONS,
    WEB_PORT,
)
from prize_bond_checker.actions import add_from_speech
from prize_bond_checker.history import HistoryStore
from prize_bond_checker.notify import configured_channels, format_alert, send_alerts
from prize_bond_checker.portfolio import add_holding, load_portfolio, remove_holding
from prize_bond_checker.service import check_portfolio


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "prize_bond_checker" / "web"
    return Path(__file__).resolve().parent


def create_app(bonds_file: Path, history_file: Path | None = None) -> Flask:
    root = _bundle_dir()
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "prize-bond-checker-local")
    app.config["BONDS_FILE"] = bonds_file
    app.config["HISTORY_FILE"] = history_file or bonds_file.with_name("history.sqlite")

    def history_store() -> HistoryStore:
        return HistoryStore(app.config["HISTORY_FILE"])

    def load_or_empty():
        path = app.config["BONDS_FILE"]
        if not path.exists():
            return None
        try:
            return load_portfolio(path)
        except ValueError:
            return None

    @app.context_processor
    def inject_defaults():
        return {
            "supported": SUPPORTED_DENOMINATIONS,
            "claim_note": CLAIM_NOTE,
            "bonds_file": app.config["BONDS_FILE"],
            "speak_text": "",
        }

    @app.get("/")
    def dashboard():
        portfolio = load_or_empty()
        grouped = portfolio.grouped() if portfolio else {}
        store = history_store()
        last_check = request.args.get("checked")
        speak = request.args.get("speak") or ""
        bond_count = sum(len(items) for items in grouped.values())
        return render_template(
            "index.html",
            portfolio=portfolio,
            grouped=grouped,
            bond_count=bond_count,
            stats=store.stats(),
            history=store.recent_checks(20),
            wins=store.all_wins(50),
            channels=configured_channels(),
            last_results=None,
            just_checked=bool(last_check),
            speak_text=speak if speak and speak != "0" else "",
            default_denomination=DEFAULT_DENOMINATION,
        )

    @app.post("/check")
    def run_check():
        path = app.config["BONDS_FILE"]
        if not path.exists():
            flash("Add at least one bond before checking.", "error")
            return redirect(url_for("dashboard"))

        try:
            portfolio = load_portfolio(path)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("dashboard"))

        force = request.form.get("force") == "1"
        notify = request.form.get("notify") == "1"
        outcomes = check_portfolio(
            portfolio,
            check_all=True,
            use_latest=True,
            history=history_store(),
            skip_checked=not force,
        )

        errors = [item.error for item in outcomes if item.error]
        wins = sum(len(item.wins) for item in outcomes if not item.skipped)
        skipped = sum(1 for item in outcomes if item.skipped)

        if errors:
            flash(" ".join(errors), "error")
        elif wins:
            flash(f"You won — {wins} matching bond(s) found.", "win")
        elif skipped == len(outcomes):
            flash("Those draws were already checked. Use Re-check to fetch again.", "info")
        else:
            flash("Check complete. No matches this time.", "ok")

        if notify and configured_channels() and any(not item.skipped for item in outcomes):
            results = send_alerts(format_alert(outcomes))
            failed = [item for item in results if not item.ok]
            if failed:
                flash("Alert failed: " + "; ".join(f"{item.channel}: {item.detail}" for item in failed), "error")
            else:
                flash("Alert sent: " + ", ".join(item.channel for item in results), "ok")

        store = history_store()
        grouped = portfolio.grouped()
        bond_count = sum(len(items) for items in grouped.values())
        return render_template(
            "index.html",
            portfolio=portfolio,
            grouped=grouped,
            bond_count=bond_count,
            stats=store.stats(),
            history=store.recent_checks(20),
            wins=store.all_wins(50),
            channels=configured_channels(),
            last_results=outcomes,
            just_checked=True,
            default_denomination=DEFAULT_DENOMINATION,
        )

    @app.post("/bonds")
    def create_bond():
        number = (request.form.get("number") or "").strip()
        owner = (request.form.get("owner") or "").strip() or None
        try:
            denomination = int(request.form.get("denomination") or DEFAULT_DENOMINATION)
            added = add_holding(app.config["BONDS_FILE"], number, denomination, owner)
        except (ValueError, TypeError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("dashboard"))
        flash("Bond added." if added else "That bond is already in the list.", "ok" if added else "info")
        return redirect(url_for("dashboard"))

    @app.post("/bonds/voice")
    def create_bond_from_voice():
        transcript = (request.form.get("transcript") or "").strip()
        owner = (request.form.get("owner") or "").strip() or None
        try:
            denomination = int(request.form.get("denomination") or DEFAULT_DENOMINATION)
            result = add_from_speech(app.config["BONDS_FILE"], transcript, denomination, owner)
        except (ValueError, TypeError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("dashboard", speak="0"))
        flash(result.message, "ok" if result.added else "info")
        return redirect(url_for("dashboard", speak=result.confirmation))

    @app.post("/bonds/delete")
    def delete_bond():
        number = (request.form.get("number") or "").strip()
        denom_raw = request.form.get("denomination") or ""
        try:
            denomination = int(denom_raw) if denom_raw else None
            removed = remove_holding(app.config["BONDS_FILE"], number, denomination)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("dashboard"))
        flash("Bond removed." if removed else "Bond not found.", "ok" if removed else "info")
        return redirect(url_for("dashboard"))

    @app.post("/notify-test")
    def notify_test():
        if not configured_channels():
            flash("No alert channels configured. Add Telegram or WhatsApp settings to .env first.", "error")
            return redirect(url_for("dashboard"))
        results = send_alerts(
            "Prize Bond Checker test message.\nIf you can read this, alerts are working."
        )
        failed = [item for item in results if not item.ok]
        if failed:
            flash("Test alert failed: " + "; ".join(f"{item.channel}: {item.detail}" for item in failed), "error")
        else:
            flash("Test alert sent: " + ", ".join(item.channel for item in results), "ok")
        return redirect(url_for("dashboard"))

    return app


def run_dashboard(
    bonds_file: Path,
    *,
    host: str = "127.0.0.1",
    port: int = WEB_PORT,
    open_browser: bool = False,
) -> None:
    app = create_app(bonds_file)
    url = f"http://{host}:{port}"
    print(f"Prize Bond Checker dashboard: {url}")
    print("This page is only reachable on this computer.")
    print(f"Bond file: {bonds_file}")
    if open_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=False, use_reloader=False)
