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
    parser.add_argument("outbreak", help="Outbreak name")
    parser.add_argument("url", help="Data URL")
    parser.add_argument("-b", "--bucket", help="S3 bucket to write outbreak report to")
    parser.add_argument(
        "--cloudfront", help="Cloudfront distribution which should be invalidated"
    )
    parser.add_argument(
        "-o", "--open", action="store_true", help="Open local file in web browser"
    )

    args = parser.parse_args()
    if args.outbreak not in OUTBREAKS:
        abort(f"Outbreak not supported: {args.outbreak}")

    build(
        args.outbreak,
        args.url,
        OUTBREAKS[args.outbreak]["plots"],
        date_columns=OUTBREAKS[args.outbreak].get("additional_date_columns", []),
        output_bucket=args.bucket,
        cloudfront_distribution=args.cloudfront,
    )
    if args.open and (Path(args.outbreak + ".html")).exists():
        webbrowser.open("file://" + str(Path.cwd() / (args.outbreak + ".html")))


if __name__ == "__main__":
    main()
