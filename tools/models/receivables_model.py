"""Unit economics of one financed invoice: the ChatGPT draft vs a restructured, tranched design.

    python tools/models/receivables_model.py              # both scenarios + sensitivity tables
    python tools/models/receivables_model.py --json       # machine-readable

Every rate here is an ASSUMPTION to replace with quotes from Thai banks/factors, the tax opinion and the
pilot recycler's real payment history. Sources for the benchmark ranges are in docs/BUSINESS_MODEL.md.
Nothing here is investment, tax or legal advice.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

DAYS = 365


def ann_simple(gain: float, base: float, days: float) -> float:
    return gain / base * DAYS / days if base else 0.0


def ann_comp(gain: float, base: float, days: float) -> float:
    return (1 + gain / base) ** (DAYS / days) - 1 if base else 0.0


@dataclass
class Draft:
    """The plan as written: $100k invoice, $95k advance, funder repaid $98k, platform fee $2k, flat."""
    face: float = 100_000
    advance: float = 95_000
    funder_back: float = 98_000
    platform_fee: float = 2_000
    days: float = 90
    direct_cost: float = 800  # the draft's 'Direct Operating Costs'
    treasury_share: float = 0.20  # of gross contribution


def draft(d: Draft, pd: float = 0.0, lgd: float = 0.0, wht: float = 0.0, paid_on_day: float | None = None) -> dict:
    days = paid_on_day or d.days
    funder_gain = d.funder_back - d.advance
    expected_loss = pd * lgd * d.advance  # all credit risk sits with the funder in the draft
    funder_net = funder_gain * (1 - wht) - expected_loss
    seller_cost = d.face - d.advance
    contribution = d.platform_fee - d.direct_cost
    treasury = contribution * d.treasury_share
    return {
        "funder_return_simple": ann_simple(funder_net, d.advance, days),
        "funder_return_compound": ann_comp(funder_net, d.advance, days),
        "seller_cost_simple": ann_simple(seller_cost, d.advance, d.days),
        "seller_cost_compound": ann_comp(seller_cost, d.advance, d.days),
        "platform_share_of_spread": d.platform_fee / seller_cost,
        "platform_fee_annualised_on_advance": ann_simple(d.platform_fee, d.advance, d.days),
        "platform_bears_credit_risk": False,
        "invoices_to_recover_one_total_default": d.advance / funder_gain,
        "treasury_per_invoice": treasury,
        "treasury_per_year_per_dollar_advanced": treasury / d.advance * DAYS / d.days,
    }


@dataclass
class Tranched:
    """Buyer-confirmed invoice (CCC s.306/308 written consent), collections into a controlled account,
    a reserve held back until the buyer pays, a time-based rate, and a first-loss tranche held by the
    platform/originator. Platform earns a share of interest, not a share of face value."""
    face: float = 100_000
    advance_rate: float = 0.90  # reserve = 10%, released after collection
    days: float = 90
    seller_rate_pa: float = 0.16  # charged on the advanced amount, per day outstanding
    verification_fee: float = 300  # KYB, buyer confirmation, registry checks: cost recovery, not profit
    platform_share_of_interest: float = 0.15  # cf. Goldfinch 10% reserve; Centrifuge 0.4% of loan value
    junior_share: float = 0.20  # first-loss tranche, held by platform/originator (skin in the game)
    senior_target_pa: float = 0.10
    servicing_cost: float = 250  # per invoice: collections, reporting, legal admin
    treasury_share_of_platform_net: float = 0.20


def tranched(t: Tranched, pd: float = 0.0, lgd: float = 0.0, wht_senior: float = 0.0, sbt: float = 0.0,
             paid_on_day: float | None = None) -> dict:
    days = paid_on_day or t.days
    adv = t.face * t.advance_rate
    interest = adv * t.seller_rate_pa * days / DAYS  # time-based: late payment keeps accruing
    interest_after_sbt = interest * (1 - sbt)  # if the SPV is treated as a factoring business (tax opinion needed)
    platform_fee = interest_after_sbt * t.platform_share_of_interest
    senior = adv * (1 - t.junior_share)
    junior = adv * t.junior_share
    senior_due = senior * t.senior_target_pa * days / DAYS
    expected_loss = pd * lgd * adv
    junior_gain = interest_after_sbt - platform_fee - senior_due - expected_loss  # junior absorbs losses first
    senior_loss = max(0.0, -junior_gain - junior) if junior_gain < 0 else 0.0  # only if losses exceed the tranche
    senior_net = senior_due * (1 - wht_senior) - senior_loss
    platform_net = platform_fee + t.verification_fee - t.servicing_cost
    seller_cost = interest + t.verification_fee
    return {
        "advance": adv,
        "reserve_released_to_seller_on_payment": t.face - adv,
        "seller_cost_simple": ann_simple(seller_cost, adv, days),
        "seller_cost_compound": ann_comp(seller_cost, adv, days),
        "senior_return_simple": ann_simple(senior_net, senior, days),
        "junior_return_simple": ann_simple(junior_gain, junior, days),
        "platform_fee": platform_fee,
        "platform_net_after_servicing": platform_net,
        "platform_share_of_interest": t.platform_share_of_interest,
        "platform_bears_credit_risk": True,
        "treasury_per_invoice": max(0.0, platform_net) * t.treasury_share_of_platform_net,
        "treasury_per_year_per_dollar_advanced": max(0.0, platform_net) * t.treasury_share_of_platform_net / adv * DAYS / days,
    }


def book_needed(treasury_per_year_per_dollar: float, research_budget: float) -> float:
    """Average capital that must be continuously advanced for the treasury slice to fund `research_budget`/yr."""
    return research_budget / treasury_per_year_per_dollar if treasury_per_year_per_dollar > 0 else float("inf")


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--research-budget", type=float, default=250_000)
    a = ap.parse_args()
    d, t = Draft(), Tranched()
    out = {
        "assumptions": {"draft": asdict(d), "tranched": asdict(t), "research_budget": a.research_budget},
        "draft_base": draft(d),
        "draft_sensitivity": {
            "pd2_lgd50": draft(d, 0.02, 0.5), "pd3_lgd60": draft(d, 0.03, 0.6), "pd5_lgd60": draft(d, 0.05, 0.6),
            "wht15": draft(d, wht=0.15), "paid_day150": draft(d, paid_on_day=150), "paid_day180": draft(d, paid_on_day=180),
        },
        "tranched_base": tranched(t),
        "tranched_sensitivity": {
            "pd0.5_lgd50": tranched(t, 0.005, 0.5), "pd2_lgd50": tranched(t, 0.02, 0.5),
            "pd5_lgd60": tranched(t, 0.05, 0.6), "wht15_senior": tranched(t, wht_senior=0.15),
            "sbt3": tranched(t, sbt=0.03), "paid_day150": tranched(t, paid_on_day=150),
        },
    }
    capped = Tranched(seller_rate_pa=0.12, senior_target_pa=0.08)  # keeps the seller's all-in cost under the 15% civil cap
    out["tranched_capped15"] = {"assumptions": asdict(capped), "base": tranched(capped),
                                "pd0.5_lgd50": tranched(capped, 0.005, 0.5), "pd2_lgd50": tranched(capped, 0.02, 0.5)}
    out["book_needed_for_research_budget"] = {
        "draft": book_needed(out["draft_base"]["treasury_per_year_per_dollar_advanced"], a.research_budget),
        "tranched": book_needed(out["tranched_base"]["treasury_per_year_per_dollar_advanced"], a.research_budget),
    }
    if a.json:
        print(json.dumps(out, indent=1))
        return
    b = out["draft_base"]
    print("DRAFT (as written): $100k invoice, $95k advance, funder gets $98k, platform $2k, 90 days")
    print(f"  funder {pct(b['funder_return_simple'])} simple / {pct(b['funder_return_compound'])} compounded; "
          f"seller pays {pct(b['seller_cost_simple'])} / {pct(b['seller_cost_compound'])}")
    print(f"  platform takes {pct(b['platform_share_of_spread'])} of the spread "
          f"({pct(b['platform_fee_annualised_on_advance'])}/yr on the advance) and bears no credit risk")
    print(f"  one total default = profit of {b['invoices_to_recover_one_total_default']:.1f} good invoices")
    for k, v in out["draft_sensitivity"].items():
        print(f"    {k:12} funder {pct(v['funder_return_simple'])} simple")
    print(f"  treasury: ${b['treasury_per_invoice']:.0f}/invoice = {pct(b['treasury_per_year_per_dollar_advanced'])} of book per year")
    tb = out["tranched_base"]
    print("\nTRANCHED (buyer-confirmed, 90% advance, 16%/yr time-based, 20% first loss, platform 15% of interest)")
    print(f"  seller {pct(tb['seller_cost_simple'])} simple (all-in incl. verification fee); senior {pct(tb['senior_return_simple'])}; "
          f"junior {pct(tb['junior_return_simple'])} before losses; platform net ${tb['platform_net_after_servicing']:.0f}/invoice")
    for k, v in out["tranched_sensitivity"].items():
        print(f"    {k:13} senior {pct(v['senior_return_simple'])}  junior {pct(v['junior_return_simple'])}  "
              f"seller {pct(v['seller_cost_simple'])}")
    c = out["tranched_capped15"]
    print("\nTRANCHED, CAPPED (seller all-in under 15%/yr in case the deal is recharacterised as a loan: 12%/yr, senior 8%)")
    for k in ("base", "pd0.5_lgd50", "pd2_lgd50"):
        v = c[k]
        print(f"    {k:13} seller {pct(v['seller_cost_simple'])}  senior {pct(v['senior_return_simple'])}  "
              f"junior {pct(v['junior_return_simple'])}  platform net ${v['platform_net_after_servicing']:.0f}/invoice")
    nb = out["book_needed_for_research_budget"]
    print(f"\nCapital continuously advanced to fund ${a.research_budget:,.0f}/yr of research from the treasury slice alone:")
    print(f"  draft ${nb['draft'] / 1e6:.1f}M   tranched ${nb['tranched'] / 1e6:.1f}M   "
          "(before credit losses hit platform revenue) -> research must be funded mainly by corporates and grants")


if __name__ == "__main__":
    main()
