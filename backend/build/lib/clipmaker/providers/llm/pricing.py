"""List prices used for cost tracking (USD per million tokens).

Source: Anthropic's published model prices (cached 2026-11). Cache writes bill at 1.25x input
and cache reads at 0.1x input for the default 5-minute cache. Unknown models are priced at the
most expensive known rate so cost is never under-reported.
TECH DEBT: move to a DB-managed price table when more providers are added.
"""

from __future__ import annotations

from decimal import Decimal

from clipmaker.providers.llm.base import LLMUsage

# model id -> (input $/MTok, output $/MTok)
PRICES: dict[str, tuple[Decimal, Decimal]] = {
    "claude-opus-5-5": (Decimal("4"), Decimal("20")),
    "claude-sonnet-5-5": (Decimal("2"), Decimal("10")),
    "claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50")),
    "claude-opus-5": (Decimal("5"), Decimal("25")),
    "claude-opus-4-8": (Decimal("5"), Decimal("25")),
    "claude-sonnet-5": (Decimal("2"), Decimal("10")),
}
_FALLBACK = (Decimal("10"), Decimal("50"))
_CACHE_WRITE = Decimal("1.25")
_CACHE_READ = Decimal("0.1")
_MILLION = Decimal(1_000_000)


def cost_for(model: str, usage: LLMUsage) -> Decimal:
    """Dollar cost of one call."""
    price_in, price_out = PRICES.get(model, _FALLBACK)
    cost = (
        Decimal(usage.input_tokens) * price_in
        + Decimal(usage.cache_write_tokens) * price_in * _CACHE_WRITE
        + Decimal(usage.cache_read_tokens) * price_in * _CACHE_READ
        + Decimal(usage.output_tokens) * price_out
    ) / _MILLION
    return cost.quantize(Decimal("0.000001"))
