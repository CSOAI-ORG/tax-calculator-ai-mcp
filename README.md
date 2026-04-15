# Tax Calculator Ai

> By [MEOK AI Labs](https://meok.ai) — Calculate income tax (UK/US brackets), EU VAT, UK corporation tax, and capital gains tax. Provides estimates only - not professional tax advice.

Tax Calculator AI MCP Server - UK/US income tax, VAT, corporation tax, and CGT calculations.

## Installation

```bash
pip install tax-calculator-ai-mcp
```

## Usage

```bash
# Run standalone
python server.py

# Or via MCP
mcp install tax-calculator-ai-mcp
```

## Tools

### `calculate_income_tax`
Calculate income tax using UK or US progressive tax brackets.

**Parameters:**
- `income` (float)
- `country` (str)
- `filing_status` (str)
- `include_ni` (bool)

### `calculate_vat`
Calculate EU/UK VAT by country. Rate types: standard, reduced, zero.

**Parameters:**
- `amount` (float)
- `country` (str)
- `rate_type` (str)
- `is_inclusive` (bool)

### `estimate_corporation_tax`
Estimate UK corporation tax including marginal relief calculations.

**Parameters:**
- `profit` (float)
- `financial_year` (str)
- `is_associated` (bool)

### `calculate_capital_gains`
Calculate UK Capital Gains Tax. Asset types: residential, other.

**Parameters:**
- `gain` (float)
- `asset_type` (str)
- `annual_income` (float)

### `get_tax_deadlines`
Get upcoming tax filing and payment deadlines for UK or US.

**Parameters:**
- `country` (str)


## Authentication

Free tier: 15 calls/day. Upgrade at [meok.ai/pricing](https://meok.ai/pricing) for unlimited access.

## Links

- **Website**: [meok.ai](https://meok.ai)
- **GitHub**: [CSOAI-ORG/tax-calculator-ai-mcp](https://github.com/CSOAI-ORG/tax-calculator-ai-mcp)
- **PyPI**: [pypi.org/project/tax-calculator-ai-mcp](https://pypi.org/project/tax-calculator-ai-mcp/)

## License

MIT — MEOK AI Labs
