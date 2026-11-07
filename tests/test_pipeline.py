"""Offline tests. All chain data here is OFFLINE FIXTURES (tests/helpers.py), never published."""
import csv
import io
import json
import os
import unittest
from datetime import datetime, timezone

from rhreport import build as B
from rhreport import chain, collect, jev, metrics, story
from rhreport import registry as R

from .helpers import fixture_chain, tr

NOW = datetime(2026, 11, 7, 2, 0, tzinfo=timezone.utc)


def snap(**kw):
    return collect.snapshot(fixture_chain(**kw), sample=50, now=NOW)


class Collect(unittest.TestCase):
    def test_classify_transfer(self):
        m = R.TICKERS["TSLA"]
        self.assertEqual(collect.classify_transfer(tr(R.ZERO, "0x" + "1" * 40, "x", ""), m), "mint")
        self.assertEqual(collect.classify_transfer(tr("0x" + "1" * 40, R.ZERO, "x", ""), m), "burn")
        self.assertEqual(collect.classify_transfer(tr("0x" + "1" * 40, m["e_token"], "transfer", ""), m), "edel")
        self.assertEqual(collect.classify_transfer(tr("0x" + "1" * 40, "0x" + "2" * 40, "borrow", ""), m), "edel")
        self.assertEqual(collect.classify_transfer(tr("0x" + "1" * 40, "0x" + "2" * 40, "transfer", ""), m), "organic")

    def test_snapshot_values(self):
        s = snap()
        r = s["tickers"]["TSLA"]
        self.assertEqual(s["chain"]["id"], 46630)
        self.assertEqual(r["utilization"], 0.25)
        self.assertEqual(r["borrow_apr"], 0.05)
        self.assertEqual(r["supply_apr"], 0.01)
        self.assertEqual(r["oracle_price_usd"], 10.0)
        self.assertEqual(r["borrowed_usd"], 250.0)
        a = r["activity"]
        self.assertEqual(a["sample_size"], 8)
        self.assertEqual(a["window_hours"], 1.0)
        self.assertEqual(a["mint_share"], 0.5)
        self.assertEqual(a["organic_per_hour"], 3.0)
        self.assertEqual(a["edel_methods"], {"supply": 1})

    def test_refuses_wrong_chain(self):
        with self.assertRaises(collect.IntegrityError):
            collect.snapshot(fixture_chain(chain_id="0x1"), now=NOW)

    def test_refuses_changed_underlying(self):
        with self.assertRaises(collect.IntegrityError):
            collect.snapshot(fixture_chain(bad_underlying="NFLX"), now=NOW)

    def test_rpc_is_read_only(self):
        with self.assertRaises(chain.ChainError):
            chain.LiveChain(rpc="http://127.0.0.1:1").rpc_call("eth_sendRawTransaction", ["0x00"])


class Derive(unittest.TestCase):
    def test_since_prev(self):
        d = metrics.derive(snap(borrowed=30.0), prev=snap(borrowed=25.0))
        sp = d["tickers"]["AMD"]["since_prev"]
        self.assertEqual(sp["utilization_pp"], 5.0)
        self.assertEqual(sp["borrowed"], 5.0)


class FakeJev:
    """OFFLINE FIXTURE decision client with the Jarvis DecisionClient result shape."""

    def __init__(self, table):
        self.table, self.states = table, []

    def classify(self, state, question, categories):
        self.states.append(state)
        status, label, conf = self.table[state["ticker"]]
        return {"status": status, "kind": "classify", "decision": label, "probability": conf, "confidence": conf,
                "served_model": "fixture", "cost_usd": "0", "reason": None if status == "decided" else "uncertain",
                "advisory_only": True, "grants_authority": False}


class Jev(unittest.TestCase):
    def setUp(self):
        self.s = snap()
        self.d = metrics.derive(self.s)
        self.fake = FakeJev({"TSLA": ("decided", "quiet", 0.6), "AMZN": ("hold", None, None),
                             "PLTR": ("decided", "organic_accumulation", 0.9), "AMD": ("decided", "faucet_noise", 0.6),
                             "NFLX": ("decided", "short_demand", 0.8)})

    def test_sorted_by_confidence_holds_last(self):
        dec = jev.classify_all(self.fake, self.s, self.d)
        self.assertEqual(jev.sort_by_confidence(dec), ["PLTR", "NFLX", "AMD", "TSLA", "AMZN"])

    def test_state_is_small_and_supplied_only(self):
        jev.classify_all(self.fake, self.s, self.d)
        for st in self.fake.states:
            self.assertLess(len(json.dumps(st)), 2000)
            self.assertNotIn("0x", json.dumps(st))  # no addresses or hashes sent to the model

    def test_categories_fit_jarvis_limits(self):
        self.assertTrue(2 <= len(jev.CATEGORIES) <= 8)
        self.assertTrue(all(len(k) <= 64 for k in jev.CATEGORIES))


class Story(unittest.TestCase):
    def setUp(self):
        self.s = snap()
        self.data = {"snapshot": self.s, "derived": metrics.derive(self.s), "jev": None}

    def test_supported_numbers_pass(self):
        md = "TSLA utilization is 25% and borrowers pay 5% APR; price $10. 3 stocks. Block 2026-11-07, tx `0xdeadbeef1234`."
        self.assertEqual(story.check(md, self.data), [])

    def test_invented_number_caught(self):
        self.assertEqual(story.check("Borrowing jumped 73% this week.", self.data), ["73%"])

    def test_report_rejects_invented_story(self):
        built = B.build(self.s)
        with self.assertRaises(ValueError):
            B.report(built, story_md="NFLX will rally 40%.")

    def test_report_rejects_stale_jev(self):
        built = B.build(self.s)
        with self.assertRaises(ValueError):
            B.report(built, jev_out={"snapshot_as_of": "2020-01-01T00:00:00Z", "decisions": {"TSLA": {}}})


class Export(unittest.TestCase):
    def test_report_without_jev_is_labelled(self):
        rep = B.report(B.build(snap()))
        self.assertIsNone(rep["jev"])
        self.assertIn("JEV not run", rep["order_basis"])
        self.assertIn("not real shares", rep["disclaimer"])

    def test_paused_jev_is_labelled(self):
        rep = B.report(B.build(snap()), jev_status={"state": "paused", "paused_on": "2026-11-08"})
        self.assertIsNone(rep["jev"])
        self.assertEqual(rep["order_basis"], "utilization (JEV paused since 2026-11-08)")
        self.assertEqual(rep["jev_status"]["state"], "paused")

    def test_jev_order_used_when_present(self):
        s = snap()
        built = B.build(s)
        fake = FakeJev({"TSLA": ("decided", "quiet", 0.95), "AMZN": ("hold", None, None),
                        "PLTR": ("decided", "organic_accumulation", 0.99), "AMD": ("decided", "faucet_noise", 0.91),
                        "NFLX": ("decided", "short_demand", 0.97)})
        dec = jev.classify_all(fake, s, built["derived"])
        rep = B.report(built, jev_out={"snapshot_as_of": s["as_of"], "decisions": dec, "model": "fixture"})
        self.assertEqual(rep["order"], ["PLTR", "NFLX", "TSLA", "AMD", "AMZN"])
        self.assertEqual(rep["order_basis"], "jev_confidence")

    def test_metrics_long_csv(self):
        rows = list(csv.DictReader(io.StringIO(B.metrics_long_csv(snap()))))
        self.assertEqual(len(rows), 5 * (len(B.METRIC_FIELDS) + len(B.ACTIVITY_FIELDS)))
        self.assertTrue(all(r["as_of"] == "2026-11-07T02:00:00Z" and r["metric"].startswith("rhc_") for r in rows))


@unittest.skipUnless(os.environ.get("RHREPORT_LIVE") == "1", "set RHREPORT_LIVE=1 to read the real testnet")
class Live(unittest.TestCase):
    def test_live_registry_still_matches_chain(self):
        collect.verify_registry(chain.LiveChain())


if __name__ == "__main__":
    unittest.main()
