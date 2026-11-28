"""Basket index and personal-inflation maths.

Implementation lives in :mod:`modules.analytics.analytics` because every figure
is derived from the same tidy history frame; this package is the public
interface for the inflation layer.
"""
from modules.analytics.analytics import (
    basket_change,
    basket_index,
    category_breakdown,
    personal_inflation,
    shrinkflation,
    spend_by_month,
)

__all__ = [
    "basket_change",
    "basket_index",
    "category_breakdown",
    "personal_inflation",
    "shrinkflation",
    "spend_by_month",
]
