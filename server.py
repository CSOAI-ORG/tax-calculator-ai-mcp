#!/usr/bin/env python3
"""Tax Calculator AI MCP Server - UK/US income tax, VAT, corporation tax, and CGT calculations."""

import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

import json, time
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

# Rate limiting
_rate_limits: dict = defaultdict(list)
RATE_WINDOW = 60
MAX_REQUESTS = 30

def _check_rate(key: str) -> bool:
    now = time.time()
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < RATE_WINDOW]
    if len(_rate_limits[key]) >= MAX_REQUESTS:
        return False
    _rate_limits[key].append(now)
    return True

# UK Income Tax Bands 2025/26
UK_TAX_BANDS = [
    {"name": "Personal Allowance", "lower": 0, "upper": 12570, "rate": 0.0},
    {"name": "Basic Rate", "lower": 12571, "upper": 50270, "rate": 0.20},
    {"name": "Higher Rate", "lower": 50271, "upper": 125140, "rate": 0.40},
    {"name": "Additional Rate", "lower": 125141, "upper": float("inf"), "rate": 0.45},
]

UK_NI_BANDS = [
    {"name": "Below threshold", "lower": 0, "upper": 12570, "rate": 0.0},
    {"name": "Main rate", "lower": 12571, "upper": 50270, "rate": 0.08},
    {"name": "Upper rate", "lower": 50271, "upper": float("inf"), "rate": 0.02},
]

# US Federal Tax Brackets 2025 (Single)
US_TAX_SINGLE = [
    {"lower": 0, "upper": 11600, "rate": 0.10},
    {"lower": 11601, "upper": 47150, "rate": 0.12},
    {"lower": 47151, "upper": 100525, "rate": 0.22},
    {"lower": 100526, "upper": 191950, "rate": 0.24},
    {"lower": 191951, "upper": 243725, "rate": 0.32},
    {"lower": 243726, "upper": 609350, "rate": 0.35},
    {"lower": 609351, "upper": float("inf"), "rate": 0.37},
]

US_TAX_MARRIED = [
    {"lower": 0, "upper": 23200, "rate": 0.10},
    {"lower": 23201, "upper": 94300, "rate": 0.12},
    {"lower": 94301, "upper": 201050, "rate": 0.22},
    {"lower": 201051, "upper": 383900, "rate": 0.24},
    {"lower": 383901, "upper": 487450, "rate": 0.32},
    {"lower": 487451, "upper": 731200, "rate": 0.35},
    {"lower": 731201, "upper": float("inf"), "rate": 0.37},
]

US_STANDARD_DEDUCTION = {"single": 14600, "married": 29200}

# EU VAT Rates
EU_VAT_RATES = {
    "uk": {"standard": 20.0, "reduced": 5.0, "zero": 0.0, "currency": "GBP"},
    "germany": {"standard": 19.0, "reduced": 7.0, "zero": 0.0, "currency": "EUR"},
    "france": {"standard": 20.0, "reduced": 5.5, "zero": 0.0, "currency": "EUR"},
    "italy": {"standard": 22.0, "reduced": 10.0, "zero": 0.0, "currency": "EUR"},
    "spain": {"standard": 21.0, "reduced": 10.0, "zero": 0.0, "currency": "EUR"},
    "netherlands": {"standard": 21.0, "reduced": 9.0, "zero": 0.0, "currency": "EUR"},
    "belgium": {"standard": 21.0, "reduced": 6.0, "zero": 0.0, "currency": "EUR"},
    "ireland": {"standard": 23.0, "reduced": 13.5, "zero": 0.0, "currency": "EUR"},
    "sweden": {"standard": 25.0, "reduced": 12.0, "zero": 0.0, "currency": "SEK"},
    "denmark": {"standard": 25.0, "reduced": 0.0, "zero": 0.0, "currency": "DKK"},
    "poland": {"standard": 23.0, "reduced": 8.0, "zero": 0.0, "currency": "PLN"},
    "austria": {"standard": 20.0, "reduced": 10.0, "zero": 0.0, "currency": "EUR"},
    "portugal": {"standard": 23.0, "reduced": 6.0, "zero": 0.0, "currency": "EUR"},
}

# UK CGT rates 2025/26
UK_CGT = {
    "annual_exempt": 3000,
    "basic_rate_residential": 0.18,
    "higher_rate_residential": 0.24,
    "basic_rate_other": 0.10,
    "higher_rate_other": 0.20,
}

# Tax deadlines
TAX_DEADLINES = {
    "uk": [
        {"deadline": "2026-01-31", "description": "Self Assessment tax return filing and payment deadline (2024/25)"},
        {"deadline": "2026-04-05", "description": "End of 2025/26 tax year"},
        {"deadline": "2026-04-06", "description": "Start of 2026/27 tax year"},
        {"deadline": "2026-07-31", "description": "Second payment on account due (2025/26)"},
        {"deadline": "2026-10-31", "description": "Paper tax return deadline (2025/26)"},
    ],
    "us": [
        {"deadline": "2026-04-15", "description": "Federal income tax filing deadline (2025)"},
        {"deadline": "2026-06-15", "description": "Estimated tax payment Q2 due"},
        {"deadline": "2026-09-15", "description": "Estimated tax payment Q3 due"},
        {"deadline": "2026-10-15", "description": "Extended filing deadline (if extension filed)"},
        {"deadline": "2027-01-15", "description": "Estimated tax payment Q4 due"},
    ],
}

mcp = FastMCP("tax-calculator-ai", instructions="Calculate income tax (UK/US brackets), EU VAT, UK corporation tax, and capital gains tax. Provides estimates only - not professional tax advice.")


def _calculate_banded_tax(income: float, bands: list) -> list:
    """Calculate tax across progressive bands."""
    breakdown = []
    remaining = income
    total_tax = 0.0
    for band in bands:
        if remaining <= 0:
            break
        band_width = band["upper"] - band["lower"] + 1 if band["upper"] != float("inf") else remaining
        taxable_in_band = min(remaining, band_width)
        tax_in_band = taxable_in_band * band["rate"]
        total_tax += tax_in_band
        if taxable_in_band > 0:
            breakdown.append({
                "band": band.get("name", f"{band['rate']*100:.0f}%"),
                "taxable_amount": round(taxable_in_band, 2),
                "rate": band["rate"],
                "tax": round(tax_in_band, 2),
            })
        remaining -= taxable_in_band
    return breakdown


@mcp.tool()
def calculate_income_tax(income: float, country: str = "uk", filing_status: str = "single", include_ni: bool = True, api_key: str = "") -> str:
    """Calculate income tax using UK or US progressive tax brackets."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if not _check_rate(api_key or "anon"):
        return json.dumps({"error": "Rate limit exceeded. Try again in 60 seconds."})

    if income < 0:
        return json.dumps({"error": "Income cannot be negative"})

    country_lower = country.lower()

    if country_lower == "uk":
        # UK personal allowance taper (loses 1 for every 2 over 100k)
        personal_allowance = 12570
        if income > 100000:
            reduction = min(personal_allowance, (income - 100000) / 2)
            personal_allowance = max(0, personal_allowance - reduction)

        adjusted_bands = list(UK_TAX_BANDS)
        adjusted_bands[0] = dict(adjusted_bands[0])
        adjusted_bands[0]["upper"] = personal_allowance

        breakdown = _calculate_banded_tax(income, adjusted_bands)
        total_tax = sum(b["tax"] for b in breakdown)

        result = {
            "country": "UK",
            "tax_year": "2025/26",
            "gross_income": income,
            "personal_allowance": personal_allowance,
            "income_tax": round(total_tax, 2),
            "tax_breakdown": breakdown,
            "effective_rate": round((total_tax / income * 100), 2) if income > 0 else 0,
            "currency": "GBP",
        }

        if include_ni:
            ni_breakdown = _calculate_banded_tax(income, UK_NI_BANDS)
            ni_total = sum(b["tax"] for b in ni_breakdown)
            result["national_insurance"] = round(ni_total, 2)
            result["ni_breakdown"] = ni_breakdown
            result["total_deductions"] = round(total_tax + ni_total, 2)
            result["net_income"] = round(income - total_tax - ni_total, 2)
            result["total_effective_rate"] = round(((total_tax + ni_total) / income * 100), 2) if income > 0 else 0
        else:
            result["net_income"] = round(income - total_tax, 2)

    elif country_lower == "us":
        brackets = US_TAX_MARRIED if filing_status.lower() == "married" else US_TAX_SINGLE
        deduction = US_STANDARD_DEDUCTION.get(filing_status.lower(), US_STANDARD_DEDUCTION["single"])
        taxable_income = max(0, income - deduction)

        breakdown = _calculate_banded_tax(taxable_income, brackets)
        total_tax = sum(b["tax"] for b in breakdown)

        result = {
            "country": "US",
            "tax_year": "2025",
            "gross_income": income,
            "filing_status": filing_status,
            "standard_deduction": deduction,
            "taxable_income": round(taxable_income, 2),
            "federal_tax": round(total_tax, 2),
            "tax_breakdown": breakdown,
            "effective_rate": round((total_tax / income * 100), 2) if income > 0 else 0,
            "net_income": round(income - total_tax, 2),
            "currency": "USD",
            "note": "Federal tax only. State taxes not included.",
        }
    else:
        return json.dumps({"error": f"Unsupported country '{country}'. Supported: uk, us"})

    result["calculated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    result["disclaimer"] = "Estimate only. Consult a qualified tax advisor for accurate calculations."
    return json.dumps(result)


@mcp.tool()
def calculate_vat(amount: float, country: str = "uk", rate_type: str = "standard", is_inclusive: bool = False, api_key: str = "") -> str:
    """Calculate EU/UK VAT by country. Rate types: standard, reduced, zero."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if not _check_rate(api_key or "anon"):
        return json.dumps({"error": "Rate limit exceeded. Try again in 60 seconds."})

    if amount < 0:
        return json.dumps({"error": "Amount cannot be negative"})

    country_lower = country.lower()
    vat_data = EU_VAT_RATES.get(country_lower)
    if not vat_data:
        return json.dumps({"error": f"Country '{country}' not found. Available: {', '.join(sorted(EU_VAT_RATES.keys()))}"})

    rate_pct = vat_data.get(rate_type.lower())
    if rate_pct is None:
        return json.dumps({"error": f"Rate type '{rate_type}' not found for {country}. Available: standard, reduced, zero"})

    rate_decimal = rate_pct / 100.0

    if is_inclusive:
        net = round(amount / (1 + rate_decimal), 2)
        vat_amount = round(amount - net, 2)
        gross = amount
    else:
        net = amount
        vat_amount = round(amount * rate_decimal, 2)
        gross = round(amount + vat_amount, 2)

    return json.dumps({
        "country": country,
        "currency": vat_data["currency"],
        "rate_type": rate_type,
        "vat_rate_pct": rate_pct,
        "input_amount": amount,
        "is_inclusive": is_inclusive,
        "net_amount": net,
        "vat_amount": vat_amount,
        "gross_amount": gross,
        "all_rates": {k: v for k, v in vat_data.items() if k != "currency"},
        "calculated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })


@mcp.tool()
def estimate_corporation_tax(profit: float, financial_year: str = "2025", is_associated: bool = False, api_key: str = "") -> str:
    """Estimate UK corporation tax including marginal relief calculations."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if not _check_rate(api_key or "anon"):
        return json.dumps({"error": "Rate limit exceeded. Try again in 60 seconds."})

    if profit < 0:
        return json.dumps({
            "profit": profit,
            "tax_due": 0,
            "note": "Loss-making. Losses may be carried forward or back. Consult an accountant.",
            "calculated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    # UK Corp tax from April 2023: 19% small profits (<50k), 25% main rate (>250k), marginal between
    small_profits_limit = 50000
    main_rate_limit = 250000
    small_rate = 0.19
    main_rate = 0.25
    marginal_fraction = 3 / 200  # 3/200 for marginal relief

    # Associated companies reduce thresholds
    if is_associated:
        small_profits_limit = 25000
        main_rate_limit = 125000

    if profit <= small_profits_limit:
        tax = profit * small_rate
        effective_rate = small_rate
        band = "Small Profits Rate"
        marginal_relief = 0
    elif profit >= main_rate_limit:
        tax = profit * main_rate
        effective_rate = main_rate
        band = "Main Rate"
        marginal_relief = 0
    else:
        # Marginal relief applies
        tax_at_main = profit * main_rate
        marginal_relief = (main_rate_limit - profit) * marginal_fraction
        tax = tax_at_main - marginal_relief
        effective_rate = tax / profit if profit > 0 else 0
        band = "Marginal Rate"

    return json.dumps({
        "financial_year": financial_year,
        "taxable_profit": profit,
        "tax_band": band,
        "small_profits_limit": small_profits_limit,
        "main_rate_limit": main_rate_limit,
        "small_rate": small_rate,
        "main_rate": main_rate,
        "corporation_tax": round(tax, 2),
        "marginal_relief": round(marginal_relief, 2),
        "effective_rate": round(effective_rate * 100, 2),
        "profit_after_tax": round(profit - tax, 2),
        "is_associated": is_associated,
        "currency": "GBP",
        "calculated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "disclaimer": "Estimate only. Does not account for allowances, reliefs, or R&D credits.",
    })


@mcp.tool()
def calculate_capital_gains(gain: float, asset_type: str = "other", annual_income: float = 0, api_key: str = "") -> str:
    """Calculate UK Capital Gains Tax. Asset types: residential, other."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if not _check_rate(api_key or "anon"):
        return json.dumps({"error": "Rate limit exceeded. Try again in 60 seconds."})

    if gain <= 0:
        return json.dumps({"gain": gain, "tax_due": 0, "note": "No capital gain to tax."})

    exempt = UK_CGT["annual_exempt"]
    taxable_gain = max(0, gain - exempt)

    if taxable_gain == 0:
        return json.dumps({
            "total_gain": gain,
            "annual_exempt_amount": exempt,
            "taxable_gain": 0,
            "tax_due": 0,
            "note": "Gain within annual exempt amount.",
        })

    # Determine rate band based on income
    basic_rate_remaining = max(0, 50270 - 12570 - annual_income)  # remaining basic rate band

    asset = asset_type.lower()
    if asset == "residential":
        basic_rate = UK_CGT["basic_rate_residential"]
        higher_rate = UK_CGT["higher_rate_residential"]
    else:
        basic_rate = UK_CGT["basic_rate_other"]
        higher_rate = UK_CGT["higher_rate_other"]

    if basic_rate_remaining > 0:
        gain_at_basic = min(taxable_gain, basic_rate_remaining)
        gain_at_higher = max(0, taxable_gain - basic_rate_remaining)
    else:
        gain_at_basic = 0
        gain_at_higher = taxable_gain

    tax_at_basic = gain_at_basic * basic_rate
    tax_at_higher = gain_at_higher * higher_rate
    total_tax = tax_at_basic + tax_at_higher

    return json.dumps({
        "total_gain": gain,
        "annual_exempt_amount": exempt,
        "taxable_gain": round(taxable_gain, 2),
        "asset_type": asset_type,
        "tax_breakdown": [
            {"band": "basic_rate", "amount": round(gain_at_basic, 2), "rate": basic_rate, "tax": round(tax_at_basic, 2)},
            {"band": "higher_rate", "amount": round(gain_at_higher, 2), "rate": higher_rate, "tax": round(tax_at_higher, 2)},
        ],
        "total_cgt": round(total_tax, 2),
        "effective_rate": round((total_tax / gain * 100), 2) if gain > 0 else 0,
        "net_gain": round(gain - total_tax, 2),
        "currency": "GBP",
        "calculated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "disclaimer": "Estimate only. Does not account for reliefs (e.g., BADR, PPR).",
    })


@mcp.tool()
def get_tax_deadlines(country: str = "uk", api_key: str = "") -> str:
    """Get upcoming tax filing and payment deadlines for UK or US."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if not _check_rate(api_key or "anon"):
        return json.dumps({"error": "Rate limit exceeded. Try again in 60 seconds."})

    country_lower = country.lower()
    deadlines = TAX_DEADLINES.get(country_lower)
    if not deadlines:
        return json.dumps({"error": f"Country '{country}' not supported. Available: {', '.join(TAX_DEADLINES.keys())}"})

    today = time.strftime("%Y-%m-%d")
    upcoming = [d for d in deadlines if d["deadline"] >= today]
    past = [d for d in deadlines if d["deadline"] < today]

    # Days until next deadline
    next_deadline = upcoming[0] if upcoming else None
    if next_deadline:
        from datetime import datetime
        deadline_date = datetime.strptime(next_deadline["deadline"], "%Y-%m-%d")
        today_date = datetime.strptime(today, "%Y-%m-%d")
        days_until = (deadline_date - today_date).days
    else:
        days_until = None

    return json.dumps({
        "country": country.upper(),
        "as_of": today,
        "next_deadline": next_deadline,
        "days_until_next": days_until,
        "upcoming_deadlines": upcoming,
        "past_deadlines": past,
        "total_deadlines": len(deadlines),
    })


if __name__ == "__main__":
    mcp.run()
