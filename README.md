# obr

Tool to generate OutBreak Reports

## Installation

Installation can be done via `pip`

```shell
git clone https://github.com/globaldothealth/obr && cd obr
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Recommended method is to use [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

```shell
git clone https://github.com/globaldothealth/obr && cd obr
uv sync
uv run obr
```

## Usage

`obr` is customised for Global.health usage, so may not work on
arbitrary line lists. Outbreak reports are generated using
[presets](src/obr/outbreaks/__init__.py). To see a list of presets:

```shell
$ uv run obr list
marburg      Marburg 2023 [GHL2023.D11.1D60.1]
mpox-2024    Mpox 2024 [GHL2024.D11.1E71]
```

To generate a report for a particular outbreak, run

```shell
uv run obr report <outbreak> <url>
```

where `<url>` is the data link on the [outbreak information page](https://github.com/globaldothealth/outbreak-data/wiki)
