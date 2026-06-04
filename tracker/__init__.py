"""tickers_watchlist — twice-daily watchlist tracker (pile on / trim / hold).

The Python layer is *pure data plumbing*: it fetches prices, returns, technicals,
news, earnings dates and analyst actions, computes position math and rule-based
signals, and writes a structured snapshot JSON. All qualitative reasoning
(catalyst summaries, earnings recaps, the final pile/trim/hold call) is done by
the Claude routine that runs this — on the subscription, never the paid API.
"""
