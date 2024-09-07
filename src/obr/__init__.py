import sys
import argparse
import webbrowser
from pathlib import Path
from .util import build
from .outbreaks import OUTBREAKS


def abort(msg):
    print(msg)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Global.health outbreak report creator"
    )

    subparsers = parser.add_subparsers(dest="command")

    report_parser = subparsers.add_parser("report", help="Generate briefing report")
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


if __name__ == "__main__":
    main()
