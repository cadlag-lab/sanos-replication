"""Deribit option quotes: freezing a snapshot of the book, and reading one.

Capture with `uv run python -m sanos.deribit BTC`. A snapshot is the response of the
exchange, byte for byte. All cleaning happens in `load`, so it can be read and redone.

Deribit options are inverse: an option on BTC/USD is quoted and settled in BTC. With F
the forward of the expiry, a quote of p BTC is worth p * F dollars at expiry, so p is
already a price per unit of forward and the "pure" call price of the paper is the BTC
quote itself, at pure strike K / F. No discount factor enters: this is the exchange's
own convention, and `tests/test_deribit.py` checks it against its mark prices.
"""

import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from urllib.request import urlopen

import numpy as np

from sanos.quotes import ExpiryQuotes

URL = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={}&kind=option"
FOLDER = Path(__file__).parents[2] / "data" / "deribit"
CHECKSUMS = "SHA256SUMS"

# The filters. They were fixed from properties of the quotes (see DEVIATIONS.md) before
# any fit was run on them.
MIN_TICK = 1e-4  # smallest price step of a BTC option, in BTC
MIN_QUOTES = 20  # per expiry, as in the paper
YEAR = 365 * 24 * 3600  # seconds; the market trades every day, so calendar time


def capture(currency: str, folder: Path = FOLDER) -> Path:
    """Save the current book summary of all options on `currency`, with its hash."""
    with urlopen(URL.format(currency), timeout=30) as response:
        raw = response.read()
    captured = datetime.fromtimestamp(json.loads(raw)["usOut"] / 1e6, UTC)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{currency}_{captured:%Y%m%dT%H%M%SZ}.json"
    with path.open("xb") as file:  # "x": a snapshot is never overwritten
        file.write(raw)
    with (folder / CHECKSUMS).open("a") as file:
        file.write(f"{hashlib.sha256(raw).hexdigest()}  {path.name}\n")
    return path


@dataclass(frozen=True)
class Snapshot:
    name: str
    sha256: str
    captured: datetime
    labels: list[str]  # Deribit's code of each kept expiry, e.g. "27NOV26"
    forwards: list[float]
    quotes: list[ExpiryQuotes]
    filtered: dict[str, int]  # how many quotes each filter removed, and how many remain


def load(path: Path) -> Snapshot:
    """Read a frozen snapshot into pure call quotes, one `ExpiryQuotes` per expiry.

    Per expiry and strike the out-of-the-money option is used: the call at or above
    the forward, the put below it, turned into a call by parity, C = P + 1 - k.
    The forward is the median `underlying_price` the exchange reports for the expiry.
    """
    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    recorded = dict(
        reversed(line.split())
        for line in (path.parent / CHECKSUMS).read_text().splitlines()
    )
    if recorded.get(path.name) != sha256:
        raise ValueError(f"{path.name} does not match its recorded hash")
    body = json.loads(raw)
    captured = datetime.fromtimestamp(body["usOut"] / 1e6, UTC)

    by_expiry = defaultdict(list)
    for row in body["result"]:
        _, label, strike, kind = row["instrument_name"].split("-")
        by_expiry[label].append((float(strike), kind, row))

    def years_to(label: str) -> float:
        expiry = datetime.strptime(label, "%d%b%y").replace(hour=8, tzinfo=UTC)
        return (expiry - captured).total_seconds() / YEAR

    labels, forwards, quotes = [], [], []
    filtered = dict.fromkeys(
        [
            "out-of-the-money quotes",
            "no bid",
            "bid at the minimum tick",
            "expiry too thin",
        ],
        0,
    )
    for label in sorted(by_expiry, key=years_to):
        if years_to(label) <= 0:
            continue
        forward = median(row["underlying_price"] for _, _, row in by_expiry[label])
        kept = []
        for strike, kind, row in sorted(by_expiry[label], key=lambda x: x[0]):
            if kind != ("C" if strike >= forward else "P"):
                continue
            filtered["out-of-the-money quotes"] += 1
            if row["bid_price"] is None or row["ask_price"] is None:
                filtered["no bid"] += 1
            elif row["bid_price"] < 1.5 * MIN_TICK:
                # the lowest possible bid says nothing about where the price is
                filtered["bid at the minimum tick"] += 1
            else:
                k = strike / forward
                to_call = 1 - k if kind == "P" else 0.0
                kept.append((k, row["bid_price"] + to_call, row["ask_price"] + to_call))
        if len(kept) < MIN_QUOTES:
            filtered["expiry too thin"] += len(kept)
            continue
        k, bid, ask = np.array(kept).T
        labels.append(label)
        forwards.append(forward)
        quotes.append(ExpiryQuotes(years_to(label), k, bid, ask))
    filtered["kept"] = sum(len(q.strikes) for q in quotes)
    return Snapshot(path.stem, sha256, captured, labels, forwards, quotes, filtered)


if __name__ == "__main__":
    print(capture(sys.argv[1]))
