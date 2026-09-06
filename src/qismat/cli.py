"""Command-line interface."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from qismat.ai.ask import parse_natural_language
from qismat.ai.client import get_ai_provider, provider_label
from qismat.ai.summary import generate_summary
from qismat.actions import add_from_speech, add_numbers
from qismat.constants import (
    CLAIM_NOTE,
    DEFAULT_BONDS_FILE,
    DEFAULT_DENOMINATION,
    HISTORY_FILENAME,
    PRIZE_SLOTS,
    SUPPORTED_DENOMINATIONS,
    WEB_PORT,
)
from qismat.envfile import load_dotenv
from qismat.history import HistoryStore
from qismat.notify import configured_channels, format_alert, send_alerts
from qismat.portfolio import load_portfolio
from qismat.service import CheckOutcome, check_portfolio

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SUBCOMMANDS = {"web", "history", "schedule", "notify-test", "add", "mcp"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qismat",
        description="Check your Pakistani prize bonds against draw results from allprizebond.pk",
        epilog=(
            "Examples:\n"
            "  qismat --latest -b 200\n"
            "  qismat --all --latest --notify\n"
            "  qismat add --say \"four seven seven six seven zero\"\n"
            "  qismat web --open\n"
            "  qismat history\n"
            "  qismat schedule --install\n"
            "  qismat --ask \"check my 200 bonds for the latest draw\"\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-d", "--date", help="Draw date in YYYY-MM-DD format")
    parser.add_argument(
        "-b",
        "--denomination",
        type=int,
        help=f"Bond denomination ({', '.join(map(str, SUPPORTED_DENOMINATIONS))})",
    )
    parser.add_argument(
        "-f",
        "--bonds-file",
        type=Path,
        help=f"Path to bond numbers file (default: ./{DEFAULT_BONDS_FILE})",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use the latest published draw date for the denomination",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="check_all",
        help="Check every denomination in your portfolio",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a friendly summary (uses AI if available, otherwise a simple summary)",
    )
    parser.add_argument(
        "--ask",
        metavar="TEXT",
        help='Natural language command, e.g. "check my 200 bonds for the latest draw"',
    )
    parser.add_argument(
        "--ai-provider",
        choices=["auto", "ollama", "gemini", "openai", "none"],
        default="auto",
        help="AI provider for --summary and --ask (default: auto)",
    )
    parser.add_argument(
        "--show-winners",
        action="store_true",
        help="Print 1st and 2nd prize numbers for the draw",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send Telegram / WhatsApp / email alerts if configured",
    )
    parser.add_argument(
        "--skip-checked",
        action="store_true",
        help="Skip a denomination if that draw date is already in local history",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Do not write this run to history.sqlite",
    )
    parser.add_argument(
        "positional",
        nargs="*",
        help="Optional shorthand: denomination date  OR  date denomination",
    )
    return parser


def resolve_bonds_file(explicit: Path | None = None) -> Path:
    if explicit:
        return explicit
    cwd_file = Path.cwd() / DEFAULT_BONDS_FILE
    if cwd_file.exists():
        return cwd_file
    package_root = Path(__file__).resolve().parents[2]
    return package_root / DEFAULT_BONDS_FILE


def history_file_for(bonds_file: Path) -> Path:
    return bonds_file.with_name(HISTORY_FILENAME)


def resolve_from_ask(args: argparse.Namespace) -> tuple[int, str | None, bool, bool]:
    preferred = "none" if args.ai_provider == "none" else args.ai_provider
    provider = get_ai_provider(preferred) if preferred != "none" else None
    try:
        parsed = parse_natural_language(args.ask, provider)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    return parsed.denomination, parsed.draw_date, parsed.use_latest, parsed.want_summary


def resolve_settings(args: argparse.Namespace, portfolio_has_sections: bool) -> tuple[int | None, str | None, bool, bool]:
    denomination = args.denomination
    draw_date = args.date
    want_summary = args.summary
    check_all = args.check_all

    if args.ask:
        denomination, draw_date, use_latest, want_summary = resolve_from_ask(args)
        args.latest = use_latest
        check_all = False
    elif args.positional:
        if len(args.positional) != 2:
            raise SystemExit(
                "Use either flags or exactly 2 positional values.\n"
                "Example: qismat 200 2026-03-16"
            )
        first, second = args.positional
        if first.isdigit() and len(first) <= 5:
            denomination = int(first)
            draw_date = second
        elif second.isdigit() and len(second) <= 5:
            draw_date = first
            denomination = int(second)
        else:
            raise SystemExit(
                "Could not detect denomination and date.\n"
                "Example: qismat 200 2026-03-16"
            )

    no_options = (
        denomination is None
        and draw_date is None
        and not args.latest
        and not args.ask
        and not args.positional
        and not check_all
    )
    if no_options:
        args.latest = True
        want_summary = True
        if portfolio_has_sections:
            check_all = True
            print("No options given — checking the latest draw for every denomination in your portfolio.")
        else:
            denomination = DEFAULT_DENOMINATION
            print("No options given — using latest Rs. 200 draw with summary.")
    elif denomination is None and not check_all:
        denomination = DEFAULT_DENOMINATION

    if check_all:
        denomination = None
        args.latest = True
        draw_date = None
    elif denomination not in SUPPORTED_DENOMINATIONS:
        supported = ", ".join(map(str, SUPPORTED_DENOMINATIONS))
        raise SystemExit(f"Unsupported denomination {denomination}. Supported: {supported}")

    if not check_all and not args.latest and draw_date is None:
        raise SystemExit(
            "Provide --date YYYY-MM-DD, use --latest, or use --all.\n"
            "Example: qismat --latest -b 200"
        )

    if draw_date is not None and not DATE_PATTERN.match(draw_date):
        raise SystemExit("Date must be in YYYY-MM-DD format.")

    return denomination, draw_date, want_summary, check_all


def print_outcome(outcome: CheckOutcome, show_winners: bool) -> None:
    if outcome.error:
        print(f"\nRs. {outcome.denomination}: {outcome.error}")
        return

    if outcome.skipped:
        print(f"\nRs. {outcome.denomination} · {outcome.draw_date}: already checked — skipped.")
        return

    draw = outcome.draw
    assert draw is not None
    print(f"\nChecking {outcome.bond_count} bond(s) against Rs. {draw.denomination} draw on {draw.draw_date}")
    if outcome.source_url:
        print(f"Source: {outcome.source_url}")

    meta_parts = []
    if draw.draw_number:
        meta_parts.append(f"Draw #{draw.draw_number}")
    if draw.city:
        meta_parts.append(draw.city)
    if meta_parts:
        print("Draw info:", " · ".join(meta_parts))

    print(f"Prize slots parsed: {draw.summary()}")
    slots = PRIZE_SLOTS.get(draw.denomination)
    if slots:
        print(
            f"(Every Rs. {draw.denomination} draw has "
            f"{slots['1st']} + {slots['2nd']} + {slots['3rd']} winners — "
            "the actual numbers change each time.)"
        )

    if show_winners:
        print("\nTop prizes for this draw:")
        for tier, numbers in draw.top_winners().items():
            print(f"  {tier}: {', '.join(numbers)}")

    if not outcome.wins:
        print("\nNo matches found.")
        return

    print("\nYou won!")
    for win in outcome.wins:
        owner = f"  [{win.owner}]" if win.owner else ""
        print(f"  {win.bond}  ->  {win.tier} prize ({win.amount}){owner}")
    print(f"\n{CLAIM_NOTE}")


def print_summary(outcome: CheckOutcome, want_summary: bool, ai_provider_choice: str) -> None:
    if not want_summary or outcome.draw is None or outcome.skipped or outcome.error:
        return
    preferred = "none" if ai_provider_choice == "none" else ai_provider_choice
    provider = get_ai_provider(preferred) if preferred != "none" else None
    summary, used_ai = generate_summary(outcome.bond_count, outcome.draw, outcome.wins, provider)
    print("\n--- Summary ---")
    print(summary)
    if used_ai and provider is not None:
        print(f"\n(AI provider: {provider_label(provider)})")
    else:
        print("\n(AI not available — using built-in summary)")


def run_check_cli(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        bonds_file = resolve_bonds_file(args.bonds_file)
        portfolio = load_portfolio(bonds_file)
        denomination, draw_date, want_summary, check_all = resolve_settings(
            args, portfolio.has_sections
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("Create bonds.txt or pass --bonds-file. See bonds.example.txt.", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        if exc.code:
            print(exc, file=sys.stderr)
        return int(exc.code or 0)

    history = None if args.no_history else HistoryStore(history_file_for(bonds_file))
    if args.latest and not check_all and denomination is not None:
        print("Looking up the latest published draw…")

    outcomes = check_portfolio(
        portfolio,
        denomination=denomination,
        draw_date=draw_date,
        use_latest=args.latest,
        check_all=check_all,
        history=history,
        skip_checked=args.skip_checked,
    )

    for outcome in outcomes:
        if outcome.draw_date and args.latest and not outcome.skipped and not outcome.error:
            print(f"Latest Rs. {outcome.denomination} draw found: {outcome.draw_date}")
        print_outcome(outcome, args.show_winners)
        print_summary(outcome, want_summary, args.ai_provider)

    if args.notify:
        _send_notifications(outcomes)

    return 1 if any(item.error for item in outcomes) else 0


def _send_notifications(outcomes: list[CheckOutcome]) -> None:
    actionable = [item for item in outcomes if not item.skipped]
    if not actionable:
        print("\nNo new draws to notify about.")
        return
    results = send_alerts(format_alert(actionable))
    print("\n--- Alerts ---")
    for item in results:
        status = "sent" if item.ok else "failed"
        print(f"  {item.channel}: {status} ({item.detail})")


def run_history_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="qismat history")
    parser.add_argument("-f", "--bonds-file", type=Path)
    parser.add_argument("-n", "--limit", type=int, default=20)
    args = parser.parse_args(argv)
    bonds_file = resolve_bonds_file(args.bonds_file)
    store = HistoryStore(history_file_for(bonds_file))
    stats = store.stats()
    print(f"Checks recorded: {stats.check_count}")
    print(f"Wins recorded:   {stats.win_count}")
    print(f"Last check:      {stats.last_checked_at or 'never'}")
    if stats.denominations:
        print("Denominations:   " + ", ".join(f"Rs. {item}" for item in stats.denominations))

    wins = store.all_wins(args.limit)
    if wins:
        print("\nWinning bonds")
        for win in wins:
            owner = f" [{win.owner}]" if win.owner else ""
            print(
                f"  {win.draw_date}  Rs. {win.denomination}  {win.bond}{owner}  "
                f"{win.tier} ({win.amount})"
            )
    else:
        print("\nNo wins stored yet.")

    print("\nRecent checks")
    checks = store.recent_checks(args.limit)
    if not checks:
        print("  (none)")
        return 0
    for item in checks:
        extra = []
        if item.draw_number:
            extra.append(f"#{item.draw_number}")
        if item.city:
            extra.append(item.city)
        meta = f" ({' · '.join(extra)})" if extra else ""
        print(
            f"  {item.checked_at}  Rs. {item.denomination}  {item.draw_date}{meta}  "
            f"bonds={item.bond_count} wins={item.win_count}"
        )
    return 0


def run_schedule_cli(argv: list[str]) -> int:
    from qismat.scheduler import (
        cron_line,
        ensure_runner,
        install_windows_task,
        remove_windows_task,
        task_exists,
    )

    parser = argparse.ArgumentParser(prog="qismat schedule")
    parser.add_argument("--install", action="store_true", help="Install a daily Windows scheduled task")
    parser.add_argument("--remove", action="store_true", help="Remove the daily Windows scheduled task")
    parser.add_argument("--hour", type=int, default=20, help="Hour to run (24h clock, default 20)")
    parser.add_argument("--minute", type=int, default=0)
    parser.add_argument("-f", "--bonds-file", type=Path)
    args = parser.parse_args(argv)

    workdir = resolve_bonds_file(args.bonds_file).resolve().parent
    if args.remove:
        if sys.platform != "win32":
            print("Task removal is only implemented for Windows Task Scheduler.")
            return 1
        try:
            print(remove_windows_task())
        except RuntimeError as exc:
            print(f"Could not remove the scheduled task: {exc}", file=sys.stderr)
            return 1
        return 0

    print("Daily auto-check will:")
    print("  • look up the latest draw for every denomination you hold")
    print("  • skip draws already in history.sqlite")
    print("  • send Telegram / WhatsApp / email if those are configured")
    print(f"  • run from: {workdir}")
    print()
    if not configured_channels():
        print("No alert channels configured yet. Copy .env.example to .env and add Telegram or WhatsApp.")
        print()

    if args.install:
        if sys.platform != "win32":
            print("Use this cron line on Linux/macOS:")
            print(cron_line(workdir, args.hour, args.minute))
            return 1
        try:
            print(install_windows_task(workdir, args.hour, args.minute))
        except RuntimeError as exc:
            print(f"Could not install the scheduled task: {exc}", file=sys.stderr)
            print("You can still create it manually with Task Scheduler pointing at:")
            print(f"  {ensure_runner(workdir)}")
            return 1
        print(f"It will run daily at {args.hour:02d}:{args.minute:02d}.")
        return 0

    if sys.platform == "win32":
        print("Windows Task Scheduler runner:")
        print(f"  {ensure_runner(workdir)}")
        print()
        print("Install it with:  qismat schedule --install")
        print(f"Currently installed: {'yes' if task_exists() else 'no'}")
    else:
        print("Cron line:")
        print(f"  {cron_line(workdir, args.hour, args.minute)}")
    return 0


def run_web_cli(argv: list[str]) -> int:
    from qismat.web.app import run_dashboard

    parser = argparse.ArgumentParser(prog="qismat web")
    parser.add_argument("-f", "--bonds-file", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=WEB_PORT)
    parser.add_argument("--open", action="store_true", help="Open the dashboard in your browser")
    args = parser.parse_args(argv)
    bonds_file = resolve_bonds_file(args.bonds_file)
    if not bonds_file.exists():
        print(f"Bond file not found: {bonds_file}", file=sys.stderr)
        print("Copy bonds.example.txt to bonds.txt first.", file=sys.stderr)
        return 1
    run_dashboard(bonds_file, host=args.host, port=args.port, open_browser=args.open)
    return 0


def run_notify_test_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="qismat notify-test")
    parser.parse_args(argv)
    channels = configured_channels()
    print("Configured channels:", ", ".join(channels) if channels else "(none)")
    results = send_alerts("Qismat test message.\nIf you can read this, alerts are working.")
    failed = False
    for item in results:
        status = "sent" if item.ok else "failed"
        print(f"  {item.channel}: {status} ({item.detail})")
        failed = failed or not item.ok
    return 1 if failed else 0


def run_add_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="qismat add")
    parser.add_argument("number", nargs="?", help="6-digit bond number")
    parser.add_argument(
        "--say",
        "-s",
        help='Spoken digits, e.g. "four seven seven six seven zero for parents"',
    )
    parser.add_argument(
        "-b",
        "--denomination",
        type=int,
        default=DEFAULT_DENOMINATION,
        help=f"Fallback denomination (default {DEFAULT_DENOMINATION})",
    )
    parser.add_argument("--owner", help="Optional owner label")
    parser.add_argument("-f", "--bonds-file", type=Path)
    args = parser.parse_args(argv)
    bonds_file = resolve_bonds_file(args.bonds_file)

    try:
        if args.say:
            result = add_from_speech(bonds_file, args.say, args.denomination, args.owner)
        elif args.number:
            result = add_numbers(bonds_file, [args.number], args.denomination, args.owner)
        else:
            print(
                'Provide a number or --say "four seven seven six seven zero".',
                file=sys.stderr,
            )
            return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(result.message)
    if result.heard:
        print(f"Heard: {result.heard}")
    for warning in result.warnings:
        print(f"Note: {warning}")
    return 0


def run_mcp_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="qismat mcp")
    parser.parse_args(argv)
    try:
        from qismat.mcp_server import main as mcp_main
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    mcp_main()
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in SUBCOMMANDS:
        command, rest = args[0], args[1:]
        if command == "web":
            return run_web_cli(rest)
        if command == "history":
            return run_history_cli(rest)
        if command == "schedule":
            return run_schedule_cli(rest)
        if command == "notify-test":
            return run_notify_test_cli(rest)
        if command == "add":
            return run_add_cli(rest)
        if command == "mcp":
            return run_mcp_cli(rest)
    return run_check_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
