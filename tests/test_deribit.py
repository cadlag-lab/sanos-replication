"""The loader, on a hand-made book and on the frozen snapshots."""

import hashlib
import json
from datetime import UTC, datetime

import numpy as np
import pytest

from sanos.black_scholes import call
from sanos.deribit import CHECKSUMS, FOLDER, MIN_QUOTES, YEAR, load

SNAPSHOTS = sorted(FOLDER.glob("*.json"))
FORWARD = 50_000.0
STRIKES = np.arange(30_000.0, 72_000.0, 1_000.0)  # 42 strikes, 20 below the forward


def write_book(folder, rows, name="BTC_test.json"):
    """A book captured on 2026-01-01 08:00 UTC, so 31JAN26 expires in 30 days."""
    captured = datetime(2026, 1, 1, 8, tzinfo=UTC).timestamp()
    raw = json.dumps({"usOut": int(captured * 1e6), "result": rows}).encode()
    (folder / name).write_bytes(raw)
    (folder / CHECKSUMS).write_text(f"{hashlib.sha256(raw).hexdigest()}  {name}\n")
    return folder / name


def row(strike, kind, bid, ask, expiry="31JAN26"):
    return {
        "instrument_name": f"BTC-{expiry}-{strike:.0f}-{kind}",
        "bid_price": bid,
        "ask_price": ask,
        "underlying_price": FORWARD,
    }


def full_book():
    rows = []
    for strike in STRIKES:
        rows.append(row(strike, "C", 0.010, 0.011))
        rows.append(row(strike, "P", 0.020, 0.022))
    return rows


def test_out_of_the_money_quotes_become_pure_calls(tmp_path):
    snapshot = load(write_book(tmp_path, full_book()))
    (q,) = snapshot.quotes
    assert snapshot.labels == ["31JAN26"] and snapshot.forwards == [FORWARD]
    assert np.isclose(q.expiry, 30 / 365)
    assert np.allclose(q.strikes, STRIKES / FORWARD)
    put = q.strikes < 1  # puts below the forward, by parity C = P + 1 - k
    assert np.allclose(q.bid[put], 0.020 + 1 - q.strikes[put])
    assert np.allclose(q.ask[put], 0.022 + 1 - q.strikes[put])
    assert np.allclose(q.bid[~put], 0.010) and np.allclose(q.ask[~put], 0.011)
    assert snapshot.filtered["kept"] == len(STRIKES)


def test_filters(tmp_path):
    rows = full_book()
    rows[1]["bid_price"] = None  # the put at the lowest strike
    rows[3]["bid_price"] = 0.0001  # the next put: a bid at the minimum tick
    rows += [row(k, "C", 0.01, 0.02, "28FEB26") for k in STRIKES[-(MIN_QUOTES - 1) :]]
    rows += [row(50_000, "C", 0.01, 0.02, "1JAN26")]  # expires at the capture time
    snapshot = load(write_book(tmp_path, rows))
    assert snapshot.labels == ["31JAN26"]
    assert snapshot.filtered == {
        "out-of-the-money quotes": len(STRIKES) + MIN_QUOTES - 1,
        "no bid": 1,
        "bid at the minimum tick": 1,
        "expiry too thin": MIN_QUOTES - 1,
        "kept": len(STRIKES) - 2,
    }


def test_an_edited_snapshot_is_refused(tmp_path):
    path = write_book(tmp_path, full_book())
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash"):
        load(path)


@pytest.mark.parametrize("path", SNAPSHOTS, ids=lambda p: p.stem)
def test_btc_quotes_are_pure_prices(path):
    # Deribit's own mark price of every out-of-the-money option is the Black-Scholes
    # price at its mark volatility with spot 1 and strike K / F, in calendar time to
    # 08:00 UTC. Typically to a twentieth of a tick, always within two ticks.
    snapshot, errors = load(path), []
    forward = dict(zip(snapshot.labels, snapshot.forwards, strict=True))
    for r in json.loads(path.read_bytes())["result"]:
        _, label, strike, kind = r["instrument_name"].split("-")
        if label not in forward:
            continue
        expiry = datetime.strptime(label, "%d%b%y").replace(hour=8, tzinfo=UTC)
        years = (expiry - snapshot.captured).total_seconds() / YEAR
        k = float(strike) / forward[label]
        if (kind == "C") != (k >= 1):
            continue
        price = float(call(1.0, k, (r["mark_iv"] / 100) ** 2 * years))
        errors.append(abs(price - (1 - k if kind == "P" else 0) - r["mark_price"]))
    assert len(errors) > 100
    assert np.median(errors) < 1e-5 and max(errors) < 2e-4
