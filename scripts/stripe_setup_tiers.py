#!/usr/bin/env python3
"""Stripe tier provisioning — Free / Pay-per-Use / Professional / Scale.

This script is the single source of truth for the four MolTrust billing tiers
in Stripe. It is **dry-run by default**: it prints what it *would* create or
update, exits without touching Stripe. Pass `--live` to apply.

Idempotency is via Stripe `lookup_key` on each price. The price's
lookup_key is what makes a re-run safe — the script first searches by
lookup_key, and only creates a new resource if no match is found.

Run:
    python3 scripts/stripe_setup_tiers.py            # dry-run
    python3 scripts/stripe_setup_tiers.py --live     # apply

Requires `STRIPE_SECRET_KEY` in env (sourced from ~/.moltrust_secrets).
On success, prints a JSON block of `{ tier: { product, price } }` ids that
can be pasted into ~/.moltrust_secrets / DB config.

Tier 0 (Free) has no Stripe entity — it's enforced in the API layer.
"""
from __future__ import annotations

import argparse
import json
import os
import sys


# --- Tier catalogue ---------------------------------------------------------

TIERS = [
    {
        "key": "pay_per_use",
        "product_name": "MolTrust Pay-per-Use",
        "product_description": "Metered MolTrust usage billed monthly.",
        "prices": [
            {
                "lookup_key": "mt_payperuse_renewal",
                "nickname": "AAE renewal",
                "amount_chf": 0.20,
                "recurring": {"interval": "month", "usage_type": "metered"},
            },
            {
                "lookup_key": "mt_payperuse_issuance",
                "nickname": "AAE issuance",
                "amount_chf": 0.30,
                "recurring": {"interval": "month", "usage_type": "metered"},
            },
            {
                "lookup_key": "mt_payperuse_anchor",
                "nickname": "On-chain anchor",
                "amount_chf": 0.50,
                "recurring": {"interval": "month", "usage_type": "metered"},
            },
            {
                "lookup_key": "mt_payperuse_compliance_export",
                "nickname": "Compliance export",
                "amount_chf": 19.00,
                "recurring": {"interval": "month", "usage_type": "metered"},
            },
        ],
    },
    {
        "key": "professional",
        "product_name": "MolTrust Professional",
        "product_description": "CHF 99/mo. Unlimited renewals + anchoring, quarterly compliance export, 99% SLA, validity up to 90 days.",
        "metadata": {
            "renewals": "unlimited",
            "anchoring": "unlimited",
            "compliance_export": "quarterly",
            "validity_max_days": "90",
            "sla": "99",
        },
        "prices": [
            {
                "lookup_key": "mt_professional_monthly",
                "nickname": "Professional monthly",
                "amount_chf": 99.00,
                "recurring": {"interval": "month"},
            },
        ],
    },
    {
        "key": "scale",
        "product_name": "MolTrust Scale",
        "product_description": "CHF 299/mo. Everything in Professional + monthly export, anomaly alerts, 7-year retention, validity up to 365 days.",
        "metadata": {
            "renewals": "unlimited",
            "anchoring": "unlimited",
            "compliance_export": "monthly",
            "validity_max_days": "365",
            "sla": "99",
            "anomaly_alerts": "true",
            "retention_years": "7",
        },
        "prices": [
            {
                "lookup_key": "mt_scale_monthly",
                "nickname": "Scale monthly",
                "amount_chf": 299.00,
                "recurring": {"interval": "month"},
            },
        ],
    },
]


# --- Provisioning -----------------------------------------------------------

def chf_to_rappen(amount: float) -> int:
    """Stripe wants the smallest currency unit. CHF → centimes (×100)."""
    return int(round(amount * 100))


def find_product(stripe, name: str):
    """Return an existing product with this exact name, or None."""
    for p in stripe.Product.list(active=True, limit=100).auto_paging_iter():
        if p["name"] == name:
            return p
    return None


def find_price_by_lookup_key(stripe, lookup_key: str):
    res = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1)
    return res["data"][0] if res["data"] else None


def ensure_product(stripe, tier: dict, dry_run: bool) -> dict:
    name = tier["product_name"]
    existing = None if dry_run else find_product(stripe, name)
    if existing:
        return {"id": existing["id"], "name": name, "action": "exists"}
    if dry_run:
        return {"id": "<dry-run>", "name": name, "action": "would-create"}
    created = stripe.Product.create(
        name=name,
        description=tier.get("product_description", ""),
        metadata=tier.get("metadata", {}),
    )
    return {"id": created["id"], "name": name, "action": "created"}


def ensure_price(stripe, product_id: str, spec: dict, dry_run: bool) -> dict:
    existing = None if dry_run else find_price_by_lookup_key(stripe, spec["lookup_key"])
    if existing:
        return {
            "id": existing["id"],
            "lookup_key": spec["lookup_key"],
            "amount_chf": spec["amount_chf"],
            "action": "exists",
        }
    if dry_run:
        return {
            "id": "<dry-run>",
            "lookup_key": spec["lookup_key"],
            "amount_chf": spec["amount_chf"],
            "action": "would-create",
        }
    payload = {
        "product": product_id,
        "currency": "chf",
        "lookup_key": spec["lookup_key"],
        "nickname": spec["nickname"],
        "unit_amount": chf_to_rappen(spec["amount_chf"]),
        "recurring": spec["recurring"],
    }
    created = stripe.Price.create(**payload)
    return {
        "id": created["id"],
        "lookup_key": spec["lookup_key"],
        "amount_chf": spec["amount_chf"],
        "action": "created",
    }


def run(live: bool) -> dict:
    if not os.environ.get("STRIPE_SECRET_KEY"):
        print("ERROR: STRIPE_SECRET_KEY not set. Source ~/.moltrust_secrets first.", file=sys.stderr)
        sys.exit(2)
    try:
        import stripe
    except ImportError:
        print("ERROR: stripe SDK missing. Activate the moltrust-api venv (it has it).", file=sys.stderr)
        sys.exit(2)
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    out: dict = {"mode": "live" if live else "dry-run", "tier_free": "no_stripe_entity_enforced_in_api", "tiers": {}}
    for tier in TIERS:
        product = ensure_product(stripe, tier, dry_run=not live)
        prices = [ensure_price(stripe, product["id"], spec, dry_run=not live) for spec in tier["prices"]]
        out["tiers"][tier["key"]] = {"product": product, "prices": prices}
    return out


def main():
    parser = argparse.ArgumentParser(description="Provision MolTrust Stripe tiers")
    parser.add_argument("--live", action="store_true", help="Actually create Stripe resources (default: dry-run)")
    args = parser.parse_args()

    result = run(live=args.live)
    print(json.dumps(result, indent=2))

    if not args.live:
        print("\n(dry-run — pass --live to apply)", file=sys.stderr)


if __name__ == "__main__":
    main()
