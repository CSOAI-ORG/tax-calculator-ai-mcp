from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tax-calculator")

US_BRACKETS_2024 = {
    "single": [
        (11600, 0.10), (47150, 0.12), (100525, 0.22),
        (191950, 0.24), (243725, 0.32), (609350, 0.35), (float("inf"), 0.37),
    ],
    "married_jointly": [
        (23200, 0.10), (94300, 0.12), (201050, 0.22),
        (383900, 0.24), (487450, 0.32), (731200, 0.35), (float("inf"), 0.37),
    ],
}

UK_BRACKETS_2024 = [
    (12570, 0.0), (50270, 0.20), (125140, 0.40), (float("inf"), 0.45),
]

@mcp.tool()
def calculate_us_federal_tax(income: float, filing_status: str = "single", deductions: float = 14600) -> dict:
    """Estimate US federal income tax."""
    taxable = max(0.0, income - deductions)
    brackets = US_BRACKETS_2024.get(filing_status, US_BRACKETS_2024["single"])
    previous_limit = 0.0
    tax = 0.0
    for limit, rate in brackets:
        if taxable > limit:
            tax += (limit - previous_limit) * rate
            previous_limit = limit
        else:
            tax += (taxable - previous_limit) * rate
            break
    effective_rate = round((tax / income) * 100, 2) if income > 0 else 0.0
    return {"taxable_income": round(taxable, 2), "estimated_tax": round(tax, 2), "effective_rate_percent": effective_rate}

@mcp.tool()
def calculate_uk_income_tax(income: float) -> dict:
    """Estimate UK income tax."""
    previous_limit = 0.0
    tax = 0.0
    for limit, rate in UK_BRACKETS_2024:
        if income > limit:
            tax += (limit - previous_limit) * rate
            previous_limit = limit
        else:
            tax += (income - previous_limit) * rate
            break
    effective_rate = round((tax / income) * 100, 2) if income > 0 else 0.0
    return {"estimated_tax": round(tax, 2), "effective_rate_percent": effective_rate}

@mcp.tool()
def calculate_effective_tax_rate(total_tax: float, gross_income: float) -> dict:
    """Compute effective tax rate."""
    if gross_income <= 0:
        return {"effective_rate_percent": 0.0}
    return {"effective_rate_percent": round((total_tax / gross_income) * 100, 2)}

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
