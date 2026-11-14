# Deviations from the paper

Every place this replication differs from the paper. Each entry is written when the choice
is made, with its reason. The data entries below were written after looking at the quotes
of the first snapshot and before running any fit on them.

## Data

- **Market.** The paper uses end-of-day SPX options from OptionMetrics IvyDB. We use
  snapshots of the Deribit BTC option book (bid and ask at one instant). Numerical results
  are therefore compared qualitatively.
- **Pure prices.** The paper divides strikes by the forward and prices by discount factor
  times forward. Deribit BTC options are quoted in BTC, which is already a price per unit
  of forward, so the quote is used as the pure price at pure strike K / F with no discount
  factor. This is the exchange's own convention: its mark prices of out-of-the-money
  options are reproduced from its mark volatilities to a median of 4e-6 BTC and a maximum
  of 2e-4 BTC, against a tick of 1e-4 (`tests/test_deribit.py`).
- **Forward.** The forward of an expiry is the `underlying_price` the exchange reports
  (median over the expiry's instruments, which agree to 4e-5). The paper does not say how
  its forwards are obtained. The forward implied by put-call parity at the three strikes
  nearest the money differs from it by a median of 1.4e-4 and at most 6e-4, and the
  exchange's forward is inside the parity bid/ask at all 30 strikes checked.
- **Time to expiry.** Calendar time to 08:00 UTC over 365 days, because the market trades
  every day. The paper counts business days, plus 20% of a day for AM-settled options.
- **Filters.** The paper keeps out-of-the-money options with at least 100 lots traded on
  the day and Vega/√T of at least 0.1%, expiries with at least 20 such options, and in
  section 5 the 1000 options nearest the money within two standard deviations. We keep
  out-of-the-money options that have a bid above the minimum tick of 1e-4 BTC, and
  expiries with at least 20 of them. A bid at the minimum tick is dropped because it is
  the lowest possible bid and does not locate the price; this plays the role of the
  paper's Vega filter. There is no volume filter, because the quotes are a live book and
  not end-of-day prices, and no distance-to-the-money filter.

## Model grid

- **Boundary strikes.** Footnote 9 extends the first and last segment of the mid prices
  to find K_min and K_max. Real mids move in ticks, so the outermost two can be tied or
  out of order and the segment has no usable slope. The line then goes through the nearest
  quote that gives one (`boundary_strikes`).
- **Added model strikes.** The paper adds strikes where market strikes are more than some
  dx apart, and some outside the quoted range, without giving the rule. We fill gaps
  larger than a tenth of the at-the-money standard deviation √V_j, up to two standard
  deviations beyond the outermost quotes. E0 showed that the grid has to be finer than the
  smoothing width √(ηV_j), which is a quarter to a half of √V_j for the η we use.
- **Backbone variances.** The paper takes the at-the-money implied variances of the bids.
  When strike 1 is not quoted we interpolate the bid implied variances linearly in strike,
  and a running maximum makes them non-decreasing across expiries.
