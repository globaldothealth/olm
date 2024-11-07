#!/bin/sh
set -eou pipefail
if [ -z "$1" ]; then
    echo "upload.sh: specify outbreak"
    exit 1
fi

outbreak="$1"
if [ ! -f "${outbreak}.html" ]; then
    cat << EOF
upload.sh: missing file ${outbreak}.html
Reports can be generated using:
  uv run olm report ${outbreak}
EOF
    exit 1
fi

report_date=$(grep 202 "${outbreak}.html" | head -n1 | sed -E 's/.*([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/')

if [ -z "${report_date}" ]; then
    echo "upload.sh: could not determine report date, exiting."
    exit 1
fi

aws s3 cp "${outbreak}.html" "s3://reports.global.health/${outbreak}/index.html"
aws s3 cp "${outbreak}.html" "s3://reports.global.health/${outbreak}/${report_date}.html"
cat << EOF
report available at
  https://reports.global.health/${outbreak}/
  https://reports.global.health/${outbreak}/${report_date}.html
EOF
