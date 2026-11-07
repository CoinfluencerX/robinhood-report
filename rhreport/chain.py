"""Read-only access to Robinhood Chain: the Blockscout explorer API and JSON-RPC eth_call.

Nothing here signs, sends, or holds keys. The only RPC method used is eth_call (plus eth_chainId).
"""
import json
import time
import urllib.parse
import urllib.request

from . import registry

UA = "robinhood-report/0.1 (read-only research)"
READ_METHODS = {"eth_call", "eth_chainId", "eth_blockNumber"}


class ChainError(Exception):
    pass


def _http(url, body=None, timeout=30, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers={"User-Agent": UA, "Content-Type": "application/json",
                                                                   "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:  # network blips: bounded retry, then fail loudly
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise ChainError(f"{url.split('?')[0]}: {last}")


class LiveChain:
    def __init__(self, api=registry.EXPLORER_API, rpc=registry.RPC_URL):
        self.api, self.rpc = api, rpc

    def explorer(self, path, params=None):
        url = f"{self.api}/{path.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        return _http(url)

    def rpc_call(self, method, params):
        if method not in READ_METHODS:
            raise ChainError(f"refusing non-read RPC method {method}")
        data = _http(self.rpc, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode())
        if "error" in data:
            raise ChainError(f"{method}: {data['error']}")
        return data["result"]

    def eth_call(self, to, data):
        return self.rpc_call("eth_call", [{"to": to, "data": data}, "latest"])


class FixtureChain:
    """OFFLINE FIXTURES: canned explorer/RPC responses for tests. Never used for a published report."""

    def __init__(self, explorer_map, calls_map, chain_id="0xb626"):
        self.explorer_map, self.calls_map, self.chain_id = explorer_map, calls_map, chain_id

    def explorer(self, path, params=None):
        key = path + ("?" + urllib.parse.urlencode(params) if params else "")
        if key not in self.explorer_map:
            raise ChainError(f"fixture missing {key}")
        return self.explorer_map[key]

    def rpc_call(self, method, params):
        if method == "eth_chainId":
            return self.chain_id
        raise ChainError(method)

    def eth_call(self, to, data):
        key = f"{to.lower()}:{data.lower()}"
        if key not in self.calls_map:
            raise ChainError(f"fixture missing call {key}")
        return self.calls_map[key]


def word(hexdata, i):
    h = hexdata[2:] if hexdata.startswith("0x") else hexdata
    chunk = h[64 * i: 64 * (i + 1)]
    if len(chunk) != 64:
        raise ChainError(f"short return data: word {i}")
    return int(chunk, 16)


def as_address(value):
    return "0x" + format(value, "040x")


def pad_address(addr):
    return addr.lower().replace("0x", "").rjust(64, "0")
