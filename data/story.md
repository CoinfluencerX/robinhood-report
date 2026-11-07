## The headline
Netflix is the most-borrowed tokenized stock on Robinhood Chain: 58% of the NFLX supplied to the Edel lending market is borrowed out, at a 66% borrow APR. JEV, the decision model that labels each stock, called it "short demand" with 99% confidence. Borrowing a stock token is how you'd short it on-chain, so this is the closest thing the chain has to a short-interest number.

## What the chain shows
**NFLX: short demand (JEV, 99%).** Utilization sits 33.4 points above the peer median of 24.7%. Borrowers (10,807) outnumber suppliers (4,463), and the rate curve has pushed lenders' yield to 33%. That's what a crowded borrow looks like.

**AMD: short demand (JEV, 91%).** Second on borrow demand, at 41% utilization and a 6.4% borrow APR, and again more borrowers (12,237) than suppliers (7,431).

**AMZN: JEV held.** Right at the peer median: 24.7% utilization and a 3.8% borrow APR. It has the most holders of any stock token, at 304,844. Nothing stands out, and the model declined to force a label.

**PLTR: JEV held.** The lending book is ordinary (23.9% utilization), but the wallets aren't: 41.2 organic transfers an hour, 1.91 times the peer median of 21.6. The model saw both stories and held, which is the honest answer.

**TSLA: JEV held (85%, below its bar).** The deepest market ($425 oracle price, the most supplied) and the least borrowed, at 15% utilization and a 2.3% borrow APR. Lots of collateral, little demand to short it.

JEV labels are advisory. Code does the sorting, and a hold is shown as a hold.

## How you could get alpha from this
1. **Weekend borrow demand leads Monday.** Tokenized stocks can be borrowed while Nasdaq is closed. If a stock token's utilization rises over a weekend, the stock underperforms SPY on Monday. Wrong if, across twenty weekends of mainnet data, weekend utilization changes show no rank correlation with Monday's excess return.
2. **Borrow-rate spikes mark crowding.** When a token's borrow APR jumps far above its peers (NFLX today), the stock outperforms SPY over the next five trading days as the crowded side unwinds. Wrong if spike days do no better than random days.
3. **Organic activity is attention.** Names with organic transfer rates well above the peer median (PLTR today) see above-normal Nasdaq volume the following week. Wrong if the two are unrelated.

## What this can't tell you
This is a testnet. The tokens come from faucets (60% of recent transfers, at the median, were faucet mints), people farm testnet rewards, and nobody has real money at risk. This is also an early snapshot of the latest 200 transfers per stock. Treat all of it as hypotheses to test once Robinhood Chain mainnet has real flows, not as signals.
