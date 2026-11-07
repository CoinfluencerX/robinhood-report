"""Take one read-only snapshot of tokenized-stock activity on Robinhood Chain.

Per ticker: holders, lifetime transfers, the Edel lending market (supplied, borrowed,
utilization, supply/borrow APR, supplier and borrower counts), the protocol's oracle price,
and a sample of the most recent transfers split into faucet mints vs. organic activity.
"""
import collections
from datetime import datetime, timezone

from . import registry as R
from .chain import ChainError, as_address, pad_address, word

EDEL_METHODS = ("supply", "withdraw", "borrow", "repay", "liquidationCall")


class IntegrityError(Exception):
    """The pinned addresses no longer match what the chain says. Refuse to report."""


def _units(raw, decimals=R.TOKEN_DECIMALS):
    return raw / 10 ** decimals


def _parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def verify_registry(chain):
    chain_id = int(chain.rpc_call("eth_chainId", []), 16)
    if chain_id != R.CHAIN_ID:
        raise IntegrityError(f"RPC is chain {chain_id}, expected {R.CHAIN_ID}")
    for t, m in R.TICKERS.items():
        for kind in ("e_token", "debt_token"):
            under = as_address(word(chain.eth_call(m[kind], R.SEL_UNDERLYING), 0))
            if under.lower() != m["token"].lower():
                raise IntegrityError(f"{t} {kind} underlying is {under}, expected {m['token']}")
        pool = as_address(word(chain.eth_call(m["e_token"], R.SEL_POOL), 0))
        if pool.lower() != R.EDEL_POOL.lower():
            raise IntegrityError(f"{t} e_token pool is {pool}, expected {R.EDEL_POOL}")


def classify_transfer(tr, meta):
    frm = tr["from"]["hash"].lower()
    to = tr["to"]["hash"].lower()
    method = tr.get("method") or ""
    e_token = meta["e_token"].lower()
    if frm == R.ZERO:
        return "mint"
    if to == R.ZERO:
        return "burn"
    if method in EDEL_METHODS or e_token in (frm, to):
        return "edel"
    return "organic"


def sample_transfers(chain, token, n):
    items, params = [], None
    while len(items) < n:
        page = chain.explorer(f"tokens/{token}/transfers", params)
        items.extend(page.get("items", []))
        params = page.get("next_page_params")
        if not params or not page.get("items"):
            break
    return items[:n]


def activity(items, meta):
    kinds = collections.Counter(classify_transfer(t, meta) for t in items)
    methods = collections.Counter(t.get("method") or "transfer" for t in items)
    edel_methods = {m: methods.get(m, 0) for m in EDEL_METHODS if methods.get(m)}
    organic_addrs = set()
    for t in items:
        if classify_transfer(t, meta) == "organic":
            organic_addrs.update({t["from"]["hash"].lower(), t["to"]["hash"].lower()})
    if items:
        newest, oldest = _parse_ts(items[0]["timestamp"]), _parse_ts(items[-1]["timestamp"])
        hours = max((newest - oldest).total_seconds() / 3600, 1 / 60)
    else:
        newest = oldest = None
        hours = None
    n = len(items)
    return {
        "sample_size": n,
        "window_start": oldest.isoformat().replace("+00:00", "Z") if oldest else None,
        "window_end": newest.isoformat().replace("+00:00", "Z") if newest else None,
        "window_hours": round(hours, 3) if hours else None,
        "transfers_per_hour": round(n / hours, 1) if hours else None,
        "mint_share": round(kinds["mint"] / n, 3) if n else None,
        "edel_share": round(kinds["edel"] / n, 3) if n else None,
        "organic_share": round(kinds["organic"] / n, 3) if n else None,
        "organic_per_hour": round(kinds["organic"] / hours, 1) if hours else None,
        "organic_unique_addresses": len(organic_addrs),
        "kinds": dict(kinds),
        "edel_methods": edel_methods,
        "example_tx": items[0]["transaction_hash"] if items else None,
    }


def lending(chain, meta):
    supplied = _units(int(chain.eth_call(meta["e_token"], R.SEL_TOTAL_SUPPLY), 16))
    borrowed = _units(int(chain.eth_call(meta["debt_token"], R.SEL_TOTAL_SUPPLY), 16))
    rd = chain.eth_call(R.EDEL_POOL, R.SEL_RESERVE_DATA + pad_address(meta["token"]))
    supply_apr = word(rd, 2) / R.RAY
    borrow_apr = word(rd, 4) / R.RAY
    price = word(chain.eth_call(R.EDEL_ORACLE, R.SEL_ASSET_PRICE + pad_address(meta["token"])), 0) / 10 ** R.ORACLE_DECIMALS
    return {
        "oracle_price_usd": round(price, 4),
        "supplied": round(supplied, 4),
        "borrowed": round(borrowed, 4),
        "utilization": round(borrowed / supplied, 4) if supplied else None,
        "supplied_usd": round(supplied * price, 2),
        "borrowed_usd": round(borrowed * price, 2),
        "supply_apr": round(supply_apr, 6),
        "borrow_apr": round(borrow_apr, 6),
    }


def snapshot(chain, sample=200, now=None):
    verify_registry(chain)
    block = int(chain.rpc_call("eth_blockNumber", []), 16) if hasattr(chain, "rpc_call") else None
    out = {}
    for t, meta in R.TICKERS.items():
        info = chain.explorer(f"tokens/{meta['token']}")
        counters = chain.explorer(f"tokens/{meta['token']}/counters")
        e_info = chain.explorer(f"tokens/{meta['e_token']}")
        d_info = chain.explorer(f"tokens/{meta['debt_token']}")
        row = {
            "name": meta["name"],
            "token": meta["token"],
            "holders": int(info["holders_count"]),
            "lifetime_transfers": int(counters["transfers_count"]),
            "suppliers": int(e_info["holders_count"]),
            "borrowers": int(d_info["holders_count"]),
        }
        row.update(lending(chain, meta))
        row["activity"] = activity(sample_transfers(chain, meta["token"], sample), meta)
        out[t] = row
    now = now or datetime.now(timezone.utc)
    return {
        "schema": "robinhood-report/snapshot/v1",
        "as_of": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "chain": {"id": R.CHAIN_ID, "name": R.CHAIN_NAME, "block": block, "explorer": R.EXPLORER},
        "edel": {"pool": R.EDEL_POOL, "oracle": R.EDEL_ORACLE},
        "sample_per_ticker": sample,
        "tickers": out,
    }
