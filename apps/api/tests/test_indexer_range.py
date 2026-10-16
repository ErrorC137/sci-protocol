"""The indexer adapts to RPC nodes that cap eth_getLogs block ranges (public Avalanche nodes: 100 blocks)."""

from app.chain import indexer as ix_mod
from app.chain.indexer import Indexer, _is_range_error

DEP = {"startBlock": 1000, "ProjectRegistry": "0x" + "11" * 20}


class CappedRpc:
    def __init__(self, head: int, cap: int):
        self.head, self.cap, self.ranges = head, cap, []

    def __call__(self, method, params):
        if method == "eth_getBlockByNumber":
            return {"number": hex(self.head)}
        if method == "eth_getLogs":
            lo, hi = int(params[0]["fromBlock"], 16), int(params[0]["toBlock"], 16)
            if hi - lo + 1 > self.cap:
                raise RuntimeError({"code": -32602, "message": f"block range too large: exceeds the maximum of {self.cap} blocks"})
            self.ranges.append((lo, hi))
            return []
        raise AssertionError(method)


def make(monkeypatch, tmp_path, chunk, head=1999, cap=100):
    abis = tmp_path / "abis.json"
    abis.write_text("{}")
    monkeypatch.setattr(ix_mod, "ABIS_PATH", abis)
    monkeypatch.setattr(ix_mod.EventDecoder, "__init__", lambda self, abis: None)
    ix = Indexer("http://rpc.invalid", DEP, chunk=chunk)
    rpc = CappedRpc(head, cap)
    monkeypatch.setattr(ix, "_rpc", rpc)
    return ix, rpc


def test_halves_range_until_the_node_accepts_it(monkeypatch, tmp_path):
    ix, rpc = make(monkeypatch, tmp_path, chunk=2000)
    ix.poll_once()
    assert ix.chunk <= 100
    assert ix.next_block == 2000  # caught up to head + 1
    covered = sorted(rpc.ranges)
    assert covered[0][0] == 1000 and covered[-1][1] == 1999
    assert all(b[0] == a[1] + 1 for a, b in zip(covered, covered[1:]))  # no gaps, no overlaps


def test_other_rpc_errors_still_raise(monkeypatch, tmp_path):
    ix, rpc = make(monkeypatch, tmp_path, chunk=50)

    def boom(method, params):
        if method == "eth_getLogs":
            raise RuntimeError({"code": -32000, "message": "header not found"})
        return rpc(method, params)

    monkeypatch.setattr(ix, "_rpc", boom)
    try:
        ix.poll_once()
        raise AssertionError("expected an error")
    except RuntimeError as ex:
        assert "header not found" in str(ex)
    assert ix.chunk == 50 and ix.next_block == 1000


def test_range_error_detection():
    assert _is_range_error(RuntimeError("block range too large: total block range exceeds the maximum of 100 blocks"))
    assert _is_range_error(RuntimeError("query returned more than 10000 results"))
    assert not _is_range_error(RuntimeError("header not found"))
