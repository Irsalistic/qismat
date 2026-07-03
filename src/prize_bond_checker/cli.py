"""Command-line interface."""



from __future__ import annotations



import argparse

import re

import sys

from pathlib import Path



import requests



from prize_bond_checker.ai.ask import parse_natural_language

from prize_bond_checker.ai.client import get_ai_provider, provider_label

from prize_bond_checker.ai.summary import generate_summary

from prize_bond_checker.bonds import load_bonds

from prize_bond_checker.checker import find_wins

from prize_bond_checker.constants import BASE_URL, PRIZE_SLOTS, SUPPORTED_DENOMINATIONS

from prize_bond_checker.latest import fetch_latest_draw_date

from prize_bond_checker.scraper import fetch_draw_html, parse_draw_html



DEFAULT_BONDS_FILE = "bonds.txt"
DEFAULT_DENOMINATION = 200
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")





def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(

        prog="prize-bond-checker",

        description="Check your Pakistani prize bonds against draw results from allprizebond.pk",

        epilog=(

            "Examples:\n"

            "  prize-bond-checker -d 2026-03-16 -b 200\n"

            "  prize-bond-checker --latest -b 200\n"

            "  prize-bond-checker --latest -b 200 --summary\n"

            "  prize-bond-checker --ask \"check my 200 bonds for the latest draw\"\n"

            "  prize-bond-checker -d 2026-03-16 -b 200 --ai-provider ollama --summary"

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

        "positional",

        nargs="*",

        help="Optional shorthand: denomination date  OR  date denomination",

    )

    return parser





def resolve_bonds_file(args: argparse.Namespace) -> Path:

    if args.bonds_file:

        return args.bonds_file



    cwd_file = Path.cwd() / DEFAULT_BONDS_FILE

    if cwd_file.exists():

        return cwd_file



    package_root = Path(__file__).resolve().parents[2]

    return package_root / DEFAULT_BONDS_FILE





def resolve_from_ask(args: argparse.Namespace) -> tuple[int, str | None, bool, bool]:

    preferred = "none" if args.ai_provider == "none" else args.ai_provider

    provider = get_ai_provider(preferred) if preferred != "none" else None



    try:

        parsed = parse_natural_language(args.ask, provider)

    except ValueError as exc:

        raise SystemExit(str(exc)) from exc



    return parsed.denomination, parsed.draw_date, parsed.use_latest, parsed.want_summary





def resolve_settings(args: argparse.Namespace) -> tuple[int, str, bool]:

    denomination = args.denomination

    draw_date = args.date

    want_summary = args.summary



    if args.ask:
        denomination, draw_date, use_latest, want_summary = resolve_from_ask(args)
        args.latest = use_latest
    elif args.positional:
        if len(args.positional) != 2:
            raise SystemExit(
                "Use either flags or exactly 2 positional values.\n"
                "Example: prize-bond-checker 200 2026-03-16"
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
                "Example: prize-bond-checker 200 2026-03-16"
            )

    # Bare `python check_prize_bonds.py` → latest Rs. 200 + summary
    if (
        denomination is None
        and draw_date is None
        and not args.latest
        and not args.ask
        and not args.positional
    ):
        denomination = DEFAULT_DENOMINATION
        args.latest = True
        want_summary = True
        print("No options given — using latest Rs. 200 draw with summary.")
    elif denomination is None:
        denomination = DEFAULT_DENOMINATION

    if denomination not in SUPPORTED_DENOMINATIONS:

        supported = ", ".join(map(str, SUPPORTED_DENOMINATIONS))

        raise SystemExit(f"Unsupported denomination {denomination}. Supported: {supported}")



    if args.latest:

        try:

            draw_date = fetch_latest_draw_date(denomination)

        except (requests.RequestException, ValueError) as exc:

            raise SystemExit(f"Could not find latest draw: {exc}") from exc

        print(f"Latest draw found: {draw_date}")

    elif draw_date is None:

        raise SystemExit(

            "Provide --date YYYY-MM-DD or use --latest.\n"

            "Example: prize-bond-checker --latest -b 200"

        )



    if not DATE_PATTERN.match(draw_date):

        raise SystemExit("Date must be in YYYY-MM-DD format.")



    return denomination, draw_date, want_summary





def print_header(bond_count: int, denomination: int, draw_date: str) -> None:

    print(f"Checking {bond_count} bond(s) against Rs. {denomination} draw on {draw_date}")





def print_draw_info(draw, show_winners: bool) -> None:

    url = BASE_URL.format(denomination=draw.denomination, draw_date=draw.draw_date)

    print(f"\nSource: {url}")



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

            joined = ", ".join(numbers)

            print(f"  {tier}: {joined}")





def print_results(wins) -> None:

    if not wins:

        print("\nNo matches found.")

        return



    print("\nYou won!")

    for win in wins:

        print(f"  {win.bond}  ->  {win.tier} prize ({win.amount})")





def print_summary(

    bond_count: int,

    draw,

    wins,

    want_summary: bool,

    ai_provider_choice: str,

) -> None:

    if not want_summary:

        return



    preferred = "none" if ai_provider_choice == "none" else ai_provider_choice

    provider = get_ai_provider(preferred) if preferred != "none" else None



    summary, used_ai = generate_summary(bond_count, draw, wins, provider)

    print("\n--- Summary ---")

    print(summary)

    if used_ai and provider is not None:

        print(f"\n(AI provider: {provider_label(provider)})")

    else:

        print("\n(AI not available — using built-in summary)")





def main(argv: list[str] | None = None) -> int:

    parser = build_parser()

    args = parser.parse_args(argv)



    try:

        denomination, draw_date, want_summary = resolve_settings(args)

        bonds_file = resolve_bonds_file(args)

        bonds = load_bonds(bonds_file)

    except (FileNotFoundError, ValueError) as exc:

        print(f"Error: {exc}", file=sys.stderr)

        return 1

    except SystemExit as exc:

        if exc.code:

            print(exc, file=sys.stderr)

        return int(exc.code or 0)



    print_header(len(bonds), denomination, draw_date)



    try:

        html = fetch_draw_html(denomination, draw_date)

        draw = parse_draw_html(html, denomination, draw_date)

    except requests.RequestException as exc:

        print(f"\nFailed to fetch draw: {exc}", file=sys.stderr)

        return 1

    except ValueError as exc:

        print(f"\nParse error: {exc}", file=sys.stderr)

        return 1



    print_draw_info(draw, args.show_winners)

    wins = find_wins(bonds, draw)

    print_results(wins)

    print_summary(len(bonds), draw, wins, want_summary, args.ai_provider)

    return 0





if __name__ == "__main__":

    raise SystemExit(main())


