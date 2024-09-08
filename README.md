# olm -- Office for Linelist Management

`olm` is a tool to operate on linelists provided from Global.health
(G.h). Linelists are epidemiological datasets with information about a
disease outbreak organised into one row per case. Currently it supports
generating briefing reports, fetching linelists and checking linelists
against a provided schema.

## Installation

Installation can be done via `pip`

```shell
git clone https://github.com/globaldothealth/olm && cd olm
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Recommended method is to use [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

```shell
git clone https://github.com/globaldothealth/olm && cd olm
uv sync
uv run olm
```

## Usage

`olm` is customised for Global.health usage, so may not work on
arbitrary line lists. Outbreak reports are generated using
[presets](src/olm/outbreaks/__init__.py). To see a list of presets:

```shell
$ uv run olm list
marburg      Marburg 2023 [GHL2023.D11.1D60.1]
mpox-2024    Mpox 2024 [GHL2024.D11.1E71]
```

To generate a report for a particular outbreak, run

```shell
uv run olm report <outbreak> [<url>]
```

where `<url>` is the data link on the [outbreak information
page](https://github.com/globaldothealth/outbreak-data/wiki). By default
`olm` will use the latest data file specified in the outbreak
configuration to build the report.
