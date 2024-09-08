import sys
import argparse
import webbrowser
import urllib
from pathlib import Path
from .util import build
from .outbreaks import OUTBREAKS

USAGE = """olm: Office for Linelist Management

olm is a tool to operate on linelists provided from Global.health (G.h).
Linelists are epidemiological datasets with information about a disease
outbreak organised into one row per case. Currently it supports
generating briefing reports, fetching linelists and checking linelists
against a provided schema.

olm is organised into subcommands:

list        lists G.h outbreaks that olm supports
get         saves linelist data to disk
report      generates briefing report for an outbreak
lint        lints (checks) an outbreak linelist for errors
"""


def abort(msg):
    print(msg)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Global.health outbreak report creator"
    )

    subparsers = parser.add_subparsers(dest="command")

    report_parser = subparsers.add_parser("report", help="Generate briefing report")
    get_parser = subparsers.add_parser("get", help="Get data for outbreak")
    get_parser.add_argument("outbreak", help="Outbreak name")
    _ = subparsers.add_parser("list", help="List outbreaks known to obr")
    report_parser.add_argument("outbreak", help="Outbreak name")
    report_parser.add_argument("--data", help="Data URL")
    report_parser.add_argument(
        "-b", "--bucket", help="S3 bucket to write outbreak report to"
    )
    report_parser.add_argument(
        "--cloudfront", help="Cloudfront distribution which should be invalidated"
    )
    report_parser.add_argument(
        "-o", "--open", action="store_true", help="Open local file in web browser"
    )

    args = parser.parse_args()
    match args.command:
        case "list":
            for outbreak in OUTBREAKS:
                print(
                    f"\033[1m{outbreak:12s} \033[0m{OUTBREAKS[outbreak]['description']}"
                )
        case "get":
            if args.outbreak not in OUTBREAKS:
                abort("Outbreak not known. Choose from: " + ", ".join(OUTBREAKS))
            if "url" not in OUTBREAKS[args.outbreak]:
                abort(f"No data URL found for: {args.outbreak}")
            output_file = f"{args.outbreak}.csv"
            with urllib.request.urlopen(OUTBREAKS[args.outbreak]["url"]) as f:
                Path(output_file).write_bytes(f.read())
                print("wrote", output_file)
        case "report":
            if args.outbreak not in OUTBREAKS:
                abort(f"Outbreak not supported: {args.outbreak}")
            build(
                args.outbreak,
                args.data or OUTBREAKS[args.outbreak]["url"],
                OUTBREAKS[args.outbreak]["plots"],
                date_columns=OUTBREAKS[args.outbreak].get(
                    "additional_date_columns", []
                ),
                output_bucket=args.bucket,
                cloudfront_distribution=args.cloudfront,
            )
            if args.open and (Path(args.outbreak + ".html")).exists():
                webbrowser.open("file://" + str(Path.cwd() / (args.outbreak + ".html")))
        case None:
            print(USAGE)


if __name__ == "__main__":
    main()
