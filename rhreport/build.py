"""Assemble the public report and the alpha-engine dataset from a snapshot (+ optional JEV and story)."""
import csv
import io

from . import jev, metrics, story

SCHEMA = "robinhood-report/v1"
DISCLAIMER = ("Robinhood Chain testnet: these are test tokens handed out by faucets, not real shares, and testnet "
              "users are often farming rewards. Treat every pattern here as a hypothesis to test, not a signal to "
              "trade. Independent research, not affiliated with Robinhood. Not investment advice.")


def build(snap, prev=None):
    return {"snapshot": snap, "derived": metrics.derive(snap, prev)}


def report(built, jev_out=None, story_md=None, jev_status=None):
    snap, derived = built["snapshot"], built["derived"]
    decisions = (jev_out or {}).get("decisions")
    if decisions and jev_out.get("snapshot_as_of") != snap["as_of"]:
        raise ValueError("JEV decisions are for a different snapshot")
    order = jev.sort_by_confidence(decisions) if decisions else sorted(
        snap["tickers"], key=lambda t: derived["tickers"][t]["utilization_rank"])
    if decisions:
        basis = "jev_confidence"
    elif jev_status and jev_status.get("state") == "paused":
        basis = f"utilization (JEV paused since {jev_status.get('paused_on')})"
    else:
        basis = "utilization (JEV not run for this snapshot)"
    data_for_check = {"snapshot": snap, "derived": derived, "jev": decisions}
    story_block = None
    if story_md is not None:
        unsupported = story.check(story_md, data_for_check)
        if unsupported:
            raise ValueError(f"story has numbers not found in the data: {unsupported}")
        story_block = {"markdown": story_md, "numbers_checked": True}
    return {
        "schema": SCHEMA,
        "title": "franklineth's Robinhood Report",
        "as_of": snap["as_of"],
        "chain": snap["chain"],
        "edel": snap["edel"],
        "order": order,
        "order_basis": basis,
        "jev": {"model": jev_out.get("model"), "ran_at": jev_out.get("ran_at"), "decisions": decisions} if decisions else None,
        "jev_status": jev_status,
        "tickers": snap["tickers"],
        "derived": derived,
        "story": story_block,
        "disclaimer": DISCLAIMER,
    }


METRIC_FIELDS = ["holders", "lifetime_transfers", "suppliers", "borrowers", "oracle_price_usd", "supplied", "borrowed",
                 "utilization", "supplied_usd", "borrowed_usd", "supply_apr", "borrow_apr"]
ACTIVITY_FIELDS = ["transfers_per_hour", "mint_share", "edel_share", "organic_share", "organic_per_hour",
                   "organic_unique_addresses"]


def metrics_long_csv(snap):
    """Long-format rows for alpha-engine's `metrics` table. as_of = when the snapshot was read (point-in-time)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["as_of", "ticker", "metric", "value", "source"])
    src = f"robinhood_chain_testnet:{snap['chain']['block']}"
    for t in sorted(snap["tickers"]):
        r = snap["tickers"][t]
        for f in METRIC_FIELDS:
            w.writerow([snap["as_of"], t, f"rhc_{f}", r[f], src])
        for f in ACTIVITY_FIELDS:
            w.writerow([snap["as_of"], t, f"rhc_{f}", r["activity"][f], src])
    return buf.getvalue()
