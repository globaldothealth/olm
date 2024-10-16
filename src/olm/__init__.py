import sys
import argparse
import webbrowser
from pathlib import Path

import requests

from .util import msg_ok, msg_fail, bold_brackets
from .outbreaks import OUTBREAKS, OUTBREAKS_PATH, Outbreak

USAGE = """[olm]: [O]ffice for [L]inelist [M]anagement

[olm] is a tool to operate on linelists provided from Global.health (G.h).
Linelists are epidemiological datasets with information about a disease
outbreak organised into one row per case. Currently it supports
generating briefing reports, fetching linelists and checking linelists
against a provided schema.

olm is organised into subcommands:

  [get]         saves linelist data to disk
  [lint]        lints (checks) an outbreak linelist for errors
  [list]        lists G.h outbreaks that olm supports
  [report]      generates briefing report for an outbreak
"""


def abort(msg):
    msg_fail("cli", msg)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Global.health outbreak report creator"
    )

    subparsers = parser.add_subparsers(dest="command")

    lint_parser = subparsers.add_parser(
        "lint", help="Lint outbreak data according to schema"
    )
    lint_parser.add_argument("outbreak", help="Outbreak name")
    lint_parser.add_argument("--data", help="Data URL")
    lint_parser.add_argument("--schema", help="Data schema path or URL")
    lint_parser.add_argument("--ignore", help="Ignore fields, comma-separated")

    get_parser = subparsers.add_parser("get", help="Get data for outbreak")
    get_parser.add_argument("outbreak", help="Outbreak name")

    _ = subparsers.add_parser("list", help="List outbreaks managed by olm")

    report_parser = subparsers.add_parser("report", help="Generate briefing report")
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
    if args.command and args.command != "list" and args.outbreak not in OUTBREAKS:
        abort(
            "outbreak not known, choose from: \033[1m"
            + ", ".join(OUTBREAKS)
            + "\033[0m"
        )
    try:
        bold_outbreak = f"\033[1m{args.outbreak}\033[0m"
    except AttributeError:
        bold_outbreak = None

    match args.command:
        case "list":
            for outbreak in OUTBREAKS:
                outbreak = Outbreak(OUTBREAKS_PATH / f"{outbreak}.yml")
                print(
                    f"\033[1m{outbreak:12s} \033[0m{outbreak.description} [{outbreak.id}]"
                )
        case "get":
            outbreak = Outbreak(OUTBREAKS_PATH / f"{args.outbreak}.yml")
            if outbreak.url is None:
                abort(f"no data URL found for {bold_outbreak}")
            output_file = f"{args.outbreak}.csv"
            if (res := requests.get(outbreak.url)).status_code == 200:
                Path(output_file).write_text(res.text)
                msg_ok("get", "wrote " + output_file)
        case "lint":
            outbreak = Outbreak(OUTBREAKS_PATH / f"{args.outbreak}.yml", args.data)
            ignore_keys = args.ignore.split(",") if args.ignore is not None else []
            if (lint_result := outbreak.lint(ignore_keys)).ok:
                msg_ok("lint", "succeeded for " + bold_outbreak)
            else:
                msg_fail("lint", "failed for " + bold_outbreak)
                print(lint_result)
                sys.exit(2)
        case "report":
            outbreak = Outbreak(OUTBREAKS_PATH / f"{args.outbreak}.yml", args.data)
            outbreak.make_report(
                args.bucket,
                args.cloudfront,
            )
            if args.open and (Path(args.outbreak + ".html")).exists():
                webbrowser.open("file://" + str(Path.cwd() / (args.outbreak + ".html")))
        case None:
            print(bold_brackets(USAGE))


if __name__ == "__main__":
    main()
