# sanos-replication

A research replication of SANOS, *Smooth strictly Arbitrage-free Non-parametric Option Surfaces*
(Buehler, Horvath, Kratsios, Limmer, Saqur; [arXiv:2601.11209v4](https://arxiv.org/abs/2601.11209)),
on Deribit option quotes.

This is research code. It is written to be read and checked, not deployed.

- [CLAIMS.md](CLAIMS.md): the paper's claims we test, and what we found.
- [DEVIATIONS.md](DEVIATIONS.md): where we differ from the paper.

## Running

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run pytest
uv run ruff check
```
