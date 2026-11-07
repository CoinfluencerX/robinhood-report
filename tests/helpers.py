"""OFFLINE FIXTURES: a fake Robinhood Chain built in memory for tests. Made-up numbers, never published."""
from rhreport import registry as R
from rhreport.chain import FixtureChain, pad_address


def w(n):
    return format(n, "064x")


def tr(frm, to, method, ts, tx="0xabc"):
    return {"from": {"hash": frm}, "to": {"hash": to}, "method": method, "timestamp": ts, "transaction_hash": tx}


def transfers(meta, n_mint=4, n_org=3, n_edel=1):
    items, i = [], 0
    for _ in range(n_mint):
        items.append(tr(R.ZERO, "0x" + "a" * 40, "sendTokensAndEther", f"2026-11-07T01:{59 - i:02d}:00Z")); i += 1
    for k in range(n_org):
        items.append(tr("0x" + "b" * 40, "0x" + f"{k + 1:040x}", "transfer", f"2026-11-07T01:{59 - i:02d}:00Z")); i += 1
    for _ in range(n_edel):
        items.append(tr("0x" + "c" * 40, meta["e_token"], "supply", f"2026-11-07T01:{59 - i:02d}:00Z")); i += 1
    items[-1]["timestamp"] = "2026-11-07T00:59:00Z"  # newest 01:59 -> oldest 00:59 = 1 hour window
    return items


def fixture_chain(supplied=100.0, borrowed=25.0, price=10.0, chain_id="0xb626", bad_underlying=None):
    explorer, calls = {}, {}
    for t, m in R.TICKERS.items():
        explorer[f"tokens/{m['token']}"] = {"holders_count": "1000"}
        explorer[f"tokens/{m['token']}/counters"] = {"transfers_count": "5000"}
        explorer[f"tokens/{m['e_token']}"] = {"holders_count": "40"}
        explorer[f"tokens/{m['debt_token']}"] = {"holders_count": "12"}
        explorer[f"tokens/{m['token']}/transfers"] = {"items": transfers(m), "next_page_params": None}
        under = m["token"] if t != bad_underlying else "0x" + "9" * 40
        for k in ("e_token", "debt_token"):
            calls[f"{m[k].lower()}:{R.SEL_UNDERLYING}"] = "0x" + pad_address(under)
        calls[f"{m['e_token'].lower()}:{R.SEL_POOL}"] = "0x" + pad_address(R.EDEL_POOL)
        calls[f"{m['e_token'].lower()}:{R.SEL_TOTAL_SUPPLY}"] = "0x" + w(int(supplied * 10 ** 18))
        calls[f"{m['debt_token'].lower()}:{R.SEL_TOTAL_SUPPLY}"] = "0x" + w(int(borrowed * 10 ** 18))
        rd = [0, R.RAY, int(0.01 * R.RAY), R.RAY, int(0.05 * R.RAY)] + [0] * 10
        calls[f"{R.EDEL_POOL.lower()}:{R.SEL_RESERVE_DATA}{pad_address(m['token'])}"] = "0x" + "".join(w(x) for x in rd)
        calls[f"{R.EDEL_ORACLE.lower()}:{R.SEL_ASSET_PRICE}{pad_address(m['token'])}"] = "0x" + w(int(price * 10 ** 8))
    fc = FixtureChain(explorer, calls, chain_id=chain_id)
    orig = fc.rpc_call
    fc.rpc_call = lambda method, params: "0x10" if method == "eth_blockNumber" else orig(method, params)
    return fc
