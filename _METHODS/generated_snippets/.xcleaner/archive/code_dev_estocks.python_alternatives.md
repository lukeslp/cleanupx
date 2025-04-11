# Alternatives for code_dev_estocks.python

<alternative snippet(s)>
def _format_date(date: datetime) -> str:
    """Helper function to format date for Finnhub API"""
    return date.strftime("%Y-%m-%d")

@lru_cache  # Note: This appears to be a typo in the original code; it should likely be @lru_cache from functools for caching expensive operations.
</alternative snippet(s)>