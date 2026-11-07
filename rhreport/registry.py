"""Pinned, on-chain-verified addresses (Robinhood Chain testnet, chain 46630).

Every Edel e-token and debt token below was checked on 2026-11-07 with
UNDERLYING_ASSET_ADDRESS() == the stock token, and POOL() == EDEL_POOL.
collect.py re-checks this on every run and refuses to report if it no longer holds.
"""

CHAIN_ID = 46630
CHAIN_NAME = "Robinhood Chain testnet"
RPC_URL = "https://rpc.testnet.chain.robinhood.com"
EXPLORER = "https://explorer.testnet.chain.robinhood.com"
EXPLORER_API = EXPLORER + "/api/v2"

ZERO = "0x0000000000000000000000000000000000000000"

EDEL_POOL = "0x0064394b61942924d63dB20192652CddBCcA745d"
EDEL_ORACLE = "0x1fa39142101f0090BF172c7E607Ed8e76b477C9f"  # pool -> ADDRESSES_PROVIDER -> getPriceOracle()

TICKERS = {
    "TSLA": {"name": "Tesla", "token": "0xC9f9c86933092BbbfFF3CCb4b105A4A94bf3Bd4E",
             "e_token": "0xdCa54Ba552dc8F7dD4296b8d2dF304d9918032Cd", "debt_token": "0x1F29BB87028c757E354403928E86c91F92cC8CD6"},
    "AMZN": {"name": "Amazon", "token": "0x5884aD2f920c162CFBbACc88C9C51AA75eC09E02",
             "e_token": "0xDc21815a25Df02c1040dAD8E1B7d1fFe86bCdd12", "debt_token": "0x48ee8852ab99DdA23Cd2Ff870bEc8c0151573DB2"},
    "PLTR": {"name": "Palantir", "token": "0x1FBE1a0e43594b3455993B5dE5Fd0A7A266298d0",
             "e_token": "0x48927DADd2a7928F90f9B147a2a1294a14526DE5", "debt_token": "0x86A7c42a663181f43B80B96da249A4ce56906D97"},
    "AMD": {"name": "AMD", "token": "0x71178BAc73cBeb415514eB542a8995b82669778d",
            "e_token": "0x2ddA8e6FbC63B4BE0291C9FCfC62A8AbC12Cf16D", "debt_token": "0xaA68D64a7aCa535Ce2DECc70f39D6e33738054B5"},
    "NFLX": {"name": "Netflix", "token": "0x3b8262A63d25f0477c4DDE23F83cfe22Cb768C93",
             "e_token": "0xC0D80AEDCA91682CBDd257DdE7D17bCEb766671b", "debt_token": "0x54a088624aCc3236966207B43a4e4f22f03cD191"},
}

# 4-byte selectors (checked against `cast sig`).
SEL_UNDERLYING = "0xb16a19de"   # UNDERLYING_ASSET_ADDRESS()
SEL_POOL = "0x7535d246"         # POOL()
SEL_TOTAL_SUPPLY = "0x18160ddd"  # totalSupply()
SEL_RESERVE_DATA = "0x35ea6a75"  # getReserveData(address)
SEL_ASSET_PRICE = "0xb3596f07"   # getAssetPrice(address)

RAY = 10 ** 27
TOKEN_DECIMALS = 18
ORACLE_DECIMALS = 8


def tx_url(tx_hash):
    return f"{EXPLORER}/tx/{tx_hash}"


def address_url(address):
    return f"{EXPLORER}/address/{address}"
