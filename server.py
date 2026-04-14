#!/usr/bin/env python3

import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

from mcp.server.fastmcp import FastMCP
import json
mcp = FastMCP("tax-calculator-ai-mcp")
RATES = {"uk": {"basic": 0.20, "higher": 0.40}, "us": {"federal": 0.22}, "de": {"income": 0.42}}
@mcp.tool(name="calculate_income_tax")
async def calculate_income_tax(country: str, income: float, api_key: str = "") -> str:
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    r = RATES.get(country.lower(), {"flat": 0.20})
    rate = list(r.values())[0]
    return {"country": country, "income": income, "estimated_tax": round(income * rate, 2), "rate": rate}
@mcp.tool(name="vat_calculator")
async def vat_calculator(amount: float, vat_rate: float = 0.20, api_key: str = "") -> str:
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    return {"net": amount, "vat": round(amount * vat_rate, 2), "gross": round(amount * (1 + vat_rate), 2)}
    return {"net": amount, "vat": round(amount * vat_rate, 2), "gross": round(amount * (1 + vat_rate), 2)}
if __name__ == "__main__":
    mcp.run()
