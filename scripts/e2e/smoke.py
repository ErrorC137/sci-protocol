"""Browser smoke test of the full demo story against a LOCAL stack.

Prereqs (see docs/DEPLOY.md "Local end-to-end"):
  1. anvil + contracts + seeded demo projects:   FAIL_DELAY=300 bash scripts/dev-chain.sh
  2. API with indexer:   CHAIN_ID=31337 RPC_URL=http://127.0.0.1:8545 INDEXER_ENABLED=true uvicorn app.main:app
  3. web built for chain 31337:   NEXT_PUBLIC_CHAIN_ID=31337 NEXT_PUBLIC_RPC_URL=http://127.0.0.1:8545 npm run build && npm start
  4. pip install playwright  (and a Chromium; set CHROMIUM=/path/to/chrome if not on PATH)

    python scripts/e2e/smoke.py [--shots DIR]

A tiny injected EIP-1193 wallet forwards to anvil, whose dev accounts are unlocked, so no extension is needed.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

WEB = os.environ.get("WEB_URL", "http://localhost:3000")
API = os.environ.get("API_URL", "http://localhost:8000")
RPC = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
ACCOUNTS = {  # anvil dev mnemonic, indices 0..2
    "attestor": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    "researcher": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    "funder": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
}

WALLET_JS = """
(() => {
  const RPC = %(rpc)s; const ACCOUNT = %(account)s;
  const listeners = {}; let id = 0;
  const provider = {
    isMetaMask: true,
    request: async ({ method, params }) => {
      if (method === "eth_requestAccounts" || method === "eth_accounts") return [ACCOUNT];
      if (method === "eth_chainId") return "0x7a69";
      if (method === "net_version") return "31337";
      if (method === "wallet_switchEthereumChain" || method === "wallet_addEthereumChain") return null;
      if (method === "wallet_requestPermissions" || method === "wallet_getPermissions") return [{ parentCapability: "eth_accounts" }];
      const r = await fetch(RPC, { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }) });
      const j = await r.json();
      if (j.error) { const e = new Error(j.error.message); e.code = j.error.code; e.data = j.error.data; throw e; }
      return j.result;
    },
    on: (ev, fn) => { (listeners[ev] ||= []).push(fn); return provider; },
    removeListener: (ev, fn) => { listeners[ev] = (listeners[ev] || []).filter((f) => f !== fn); return provider; },
  };
  window.ethereum = provider;
  const info = { uuid: "sci-test-wallet", name: "SCI Test Wallet", rdns: "io.sci.testwallet",
    icon: "data:image/svg+xml,%%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32'/%%3E" };
  const announce = () => window.dispatchEvent(new CustomEvent("eip6963:announceProvider", { detail: Object.freeze({ info, provider }) }));
  window.addEventListener("eip6963:requestProvider", announce); announce();
})();
"""


def api(path: str):
    return json.loads(urllib.request.urlopen(API + path).read())


class Run:
    def __init__(self, browser, shots: Path | None):
        self.browser, self.shots, self.pages = browser, shots, {}

    def page(self, role: str) -> Page:
        if role not in self.pages:
            ctx = self.browser.new_context(viewport={"width": 1360, "height": 900})
            ctx.add_init_script(WALLET_JS % {"rpc": json.dumps(RPC), "account": json.dumps(ACCOUNTS[role])})
            self.pages[role] = ctx.new_page()
        return self.pages[role]

    def shot(self, page: Page, name: str):
        if self.shots:
            page.screenshot(path=str(self.shots / f"{name}.png"), full_page=True)

    def connect(self, page: Page):
        btn = page.get_by_role("button", name="Connect Wallet").first
        if btn.count() and btn.is_visible():
            btn.click()
            page.get_by_text("Browser Wallet").or_(page.get_by_text("SCI Test Wallet")).or_(page.get_by_text("Injected Wallet")).first.click()
            expect(page.get_by_role("button", name="Connect Wallet")).to_have_count(0, timeout=15_000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=Path)
    ap.add_argument("--only", choices=["vault"], help="run a single step against an already-used chain")
    args = ap.parse_args()
    if args.shots:
        args.shots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
        r = Run(browser, args.shots)

        pg = r.page("researcher")
        if args.only == "vault":
            pg.goto(WEB)
            vault(r, pg)
            browser.close()
            print("ALL GOOD")
            return

        # 1. Intake wizard -> matches (no wallet needed)
        pg.goto(f"{WEB}/profile")
        pg.get_by_role("button", name="Load demo researcher").click()
        for _ in range(4):
            pg.get_by_role("button", name="Next").click()
        expect(pg.get_by_text("stays on this device")).to_be_visible()
        r.shot(pg, "01-profile-privacy")
        pg.get_by_role("button", name="Find matches →").click()
        expect(pg.get_by_text("eligible", exact=False).first).to_be_visible(timeout=20_000)
        expect(pg.get_by_text("Why this matched:").first).to_be_visible(timeout=60_000)
        expect(pg.get_by_text("Register a company (startup)")).to_be_visible()
        r.shot(pg, "02-matches")
        print("✓ profile -> matches with explanations and unlocks")

        # 2. Application pre-fill + review gate
        grant = next(i["grant"] for i in api("/grants?limit=200")["items"] if i["grant"]["source_ref"] == "tedfund-young-startup")
        pg.goto(f"{WEB}/apply/{grant['id']}")
        pg.get_by_role("button", name="Generate pre-filled draft").click()
        expect(pg.get_by_text("pre-filled (33 fields)")).to_be_visible(timeout=30_000)
        expect(pg.get_by_text("Locked until review is complete.")).to_be_visible()
        r.shot(pg, "03-application-review")
        print("✓ application pre-filled; export locked until review")

        # 3. Funder completes project A's raise
        f = r.page("funder")
        f.goto(f"{WEB}/raise/1")
        r.connect(f)
        f.get_by_role("button", name="Get 10,000 test mUSDC").click()
        expect(f.get_by_text("Get test mUSDC confirmed")).to_be_visible(timeout=30_000)
        f.get_by_role("button", name="fill remaining").click()
        f.get_by_role("button", name="Contribute").click()
        expect(f.get_by_text("Fully funded - money is in milestone escrow.")).to_be_visible(timeout=40_000)
        r.shot(f, "04-raise-funded")
        print("✓ funder contributed; raise finalized into escrow")

        # 4. Researcher submits evidence, attestor approves, anyone releases
        pg.goto(f"{WEB}/raise/1")
        r.connect(pg)
        pg.get_by_placeholder("Evidence summary").fill("Pilot batch report: https://example.org/report.pdf")
        pg.get_by_role("button", name="Submit evidence").click()
        expect(pg.get_by_text("Submit evidence for milestone 1 confirmed")).to_be_visible(timeout=30_000)
        a = r.page("attestor")
        a.goto(f"{WEB}/raise/1")
        r.connect(a)
        a.get_by_role("button", name="Approve").click()
        expect(a.get_by_role("button", name="Release 3,000 mUSDC to researcher")).to_be_visible(timeout=30_000)
        a.get_by_role("button", name="Release 3,000 mUSDC to researcher").click()
        expect(a.get_by_text("Release milestone 1 confirmed")).to_be_visible(timeout=30_000)
        r.shot(a, "05-milestone-released")
        print("✓ evidence -> approve -> release")

        # 5. The credibility moment: project B misses its milestone, funders get money back
        f.goto(f"{WEB}/raise/2")
        print("  waiting for project 2's milestone deadline to pass…")
        expect(f.get_by_role("button", name="Trigger refund")).to_be_visible(timeout=420_000)
        r.shot(f, "06-milestone-missed")
        f.get_by_role("button", name="Trigger refund").click()
        claim = f.get_by_role("button", name="Claim my refund", exact=False)
        expect(claim).to_be_visible(timeout=30_000)
        claim.click()
        expect(f.get_by_text("Your refund has been paid.")).to_be_visible(timeout=30_000)
        r.shot(f, "07-refunded")
        print("✓ missed milestone -> refund triggered -> funder refunded")

        # 6. Researcher opens a new raise from the UI
        pg.goto(f"{WEB}/raise/new")
        pg.get_by_role("button", name="Create on-chain (3 transactions)").click()
        pg.wait_for_url("**/raise/3", timeout=60_000)
        expect(pg.get_by_text("Pilot-scale batch meets lab spec")).to_be_visible(timeout=20_000)
        print("✓ new raise created on-chain (project 3)")

        # 7. Vault: seal, anchor, verify, decrypt
        vault(r, pg)
        browser.close()
    print("ALL GOOD")


def vault(r: Run, pg: Page):
    pg.goto(f"{WEB}/vault")
    r.connect(pg)
    pg.locator("textarea").fill(f"Composition: 62% treated straw fibre, binder B-7 at 3:1. (demo {time.time()})")
    pg.get_by_role("button", name="Encrypt, pin & anchor").click()
    expect(pg.get_by_text("Existence proof")).to_be_visible(timeout=40_000)
    h = pg.locator("dd.font-mono").first.inner_text()
    r.shot(pg, "08-vault-proof")
    pg.get_by_role("button", name="Verify / open").click()
    pg.locator("input").last.fill(h)
    pg.get_by_role("button", name="Verify", exact=True).click()
    pg.get_by_role("button", name="Decrypt with my wallet").click()
    expect(pg.get_by_text("binder B-7")).to_be_visible(timeout=20_000)
    r.shot(pg, "09-vault-decrypted")
    print("✓ vault sealed, anchored, verified and decrypted")


if __name__ == "__main__":
    main()
