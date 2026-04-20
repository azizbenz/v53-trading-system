"""Adapter-facing runtime error contracts."""

from __future__ import annotations


class VenueRateLimitExceededError(RuntimeError):
    """Raised when a venue-specific quota tracker blocks a request."""


class BinanceApiRateLimitExceededError(VenueRateLimitExceededError):
    """Raised when the bounded Binance quota tracker blocks a request."""


__all__ = [
    "BinanceApiRateLimitExceededError",
    "VenueRateLimitExceededError",
]
