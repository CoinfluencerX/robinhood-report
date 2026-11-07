"""Deterministic signals from a snapshot (and the previous one, when there is one). No model involved."""
import statistics


def _median(values):
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def derive(snap, prev=None):
    rows = snap["tickers"]
    peer = {
        "utilization": _median(r["utilization"] for r in rows.values()),
        "borrow_apr": _median(r["borrow_apr"] for r in rows.values()),
        "organic_per_hour": _median(r["activity"]["organic_per_hour"] for r in rows.values()),
        "mint_share": _median(r["activity"]["mint_share"] for r in rows.values()),
    }
    by_util = sorted(rows, key=lambda t: rows[t]["utilization"] or 0, reverse=True)
    out = {}
    for t, r in rows.items():
        a = r["activity"]
        em = a.get("edel_methods", {})
        d = {
            "utilization_rank": by_util.index(t) + 1,
            "utilization_vs_peer_median_pp": round(100 * (r["utilization"] - peer["utilization"]), 1)
            if r["utilization"] is not None and peer["utilization"] is not None else None,
            "borrow_apr_vs_peer_median_pp": round(100 * (r["borrow_apr"] - peer["borrow_apr"]), 2),
            "organic_vs_peer_median": round(a["organic_per_hour"] / peer["organic_per_hour"], 2)
            if a["organic_per_hour"] and peer["organic_per_hour"] else None,
            "sample_net_borrows": em.get("borrow", 0) - em.get("repay", 0),
            "sample_net_supplies": em.get("supply", 0) - em.get("withdraw", 0),
        }
        if prev and t in prev.get("tickers", {}):
            p = prev["tickers"][t]
            d["since_prev"] = {
                "from": prev["as_of"],
                "holders": r["holders"] - p["holders"],
                "borrowed": round(r["borrowed"] - p["borrowed"], 4),
                "utilization_pp": round(100 * (r["utilization"] - p["utilization"]), 2),
                "borrow_apr_pp": round(100 * (r["borrow_apr"] - p["borrow_apr"]), 2),
            }
        out[t] = d
    return {"peer_median": peer, "tickers": out}
