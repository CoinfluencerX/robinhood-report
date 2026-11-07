"""JEV step: classify each ticker's on-chain setup from a compact, supplied state; then sort by confidence.

JEV only picks a label (advisory, grants no authority). Sorting, arithmetic and everything else is
deterministic code here. The real client is Operation Jarvis's DecisionClient (budgeted ledger), run on
Franklin's Mac via scripts/jev_classify.py. Tests use OFFLINE FIXTURES only.
"""

QUESTION = ("Which label best describes this tokenized stock's on-chain activity in this snapshot, compared with "
            "the peer medians supplied? Use only the numbers in the state.")

CATEGORIES = {
    "short_demand": "Borrowing of the stock token is high relative to peers (utilization or borrow APR well above the "
                    "peer median), consistent with on-chain demand to short it.",
    "organic_accumulation": "Non-faucet transfers and lending supply stand out versus peers; users are deliberately "
                            "moving or supplying the token, not just receiving faucet mints.",
    "faucet_noise": "Activity is mostly faucet mints and lending metrics are near the peer median; little evidence "
                    "of deliberate positioning.",
    "quiet": "Low organic activity and unremarkable lending metrics versus peers.",
}


def state_for(ticker, snap, derived):
    r = snap["tickers"][ticker]
    a = r["activity"]
    d = derived["tickers"][ticker]
    peer = derived["peer_median"]
    return {
        "ticker": ticker,
        "network": "Robinhood Chain testnet (test tokens, not real shares)",
        "utilization": r["utilization"],
        "borrow_apr": r["borrow_apr"],
        "borrowers": r["borrowers"],
        "suppliers": r["suppliers"],
        "mint_share_of_recent_transfers": a["mint_share"],
        "organic_transfers_per_hour": a["organic_per_hour"],
        "recent_edel_actions": a["edel_methods"],
        "utilization_rank_of_5": d["utilization_rank"],
        "peer_median": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in peer.items()},
    }


def classify_all(client, snap, derived):
    """client.classify(state, question, categories) -> dict with status/decision/confidence (jarvis shape)."""
    results = {}
    for t in snap["tickers"]:
        res = client.classify(state_for(t, snap, derived), QUESTION, CATEGORIES)
        results[t] = {k: res.get(k) for k in ("status", "decision", "probability", "confidence", "served_model",
                                               "cost_usd", "reason")}
        results[t]["advisory_only"] = True
    return results


def sort_by_confidence(decisions):
    """Decided labels first, highest confidence first; holds and failures last, alphabetical. Deterministic."""
    def key(item):
        t, d = item
        ok = d.get("status") == "decided" and d.get("decision") in CATEGORIES and isinstance(d.get("confidence"), (int, float))
        return (0 if ok else 1, -(d.get("confidence") or 0) if ok else 0, t)
    return [t for t, _ in sorted(decisions.items(), key=key)]
