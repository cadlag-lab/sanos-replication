# sanos-replication

A research replication of SANOS, *Smooth strictly Arbitrage-free Non-parametric Option Surfaces*
(Buehler, Horvath, Kratsios, Limmer, Saqur; [arXiv:2601.11209v4](https://arxiv.org/abs/2601.11209)),
on Deribit option quotes.

This is research code. It is written to be read and checked, not deployed.

- [CLAIMS.md](CLAIMS.md): the paper's claims we test, and what we found.
- [DEVIATIONS.md](DEVIATIONS.md): where we differ from the paper.
- [note/note.pdf](note/note.pdf): the write-up.
- `results/`: the numbers and figures behind the claims, one folder per data set.

## Running

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run pytest
uv run ruff check

uv run python experiments/e0_synthetic.py  # E0, synthetic quotes
uv run python experiments/deribit.py       # E1 to E6, every frozen snapshot
uv run python -m sanos.deribit BTC         # freeze a new snapshot into data/deribit/
latexmk -pdf -cd note/note.tex             # the note
```

Snapshots in `data/deribit/` are the exchange's responses, byte for byte, with their
hashes in `SHA256SUMS`. They are never edited; `sanos.deribit.load` refuses one that
does not match its hash.
