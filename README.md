# Swing Research Agent

Automated equity research for German (XETRA) stocks, built entirely on free tools:
GitHub Actions, GitHub Pages and yfinance. Suggest-only research. **Not financial advice.**

- **Dashboard:** https://amaccountant.github.io/swing-agent/
- **Event Lab:** https://amaccountant.github.io/swing-agent/events.html

## Status: research mode
Seven independent tests found no measurable edge for 2-hour to 5-day trades in this
universe after retail costs. The agent therefore issues no trade calls. It estimates
probabilities and records them on paper so that its calibration can be audited.

## What runs, and when (German time)
| Workflow | Schedule | What it does |
|---|---|---|
| Morning Scan | Mon-Fri, about 08:00 | Refreshes the watchlist and estimates P(target before stop) for each stock |
| Evening Review | Mon-Fri, about 18:30 | Resolves paper probes after 5 sessions; updates Brier score and paper P&L |
| Event Lab | Saturday | Earnings-drift and overnight/intraday study |
| Backtest | Sunday | Historical replay of the rule set |

## Files
| Area | Files |
|---|---|
| Engines | `refresh_watchlist.py`, `probability_engine.py`, `track_review.py`, `event_layer.py`, `backtest.py` |
| Site builders | `build_dashboard.py`, `build_events_page.py` |
| Records | `probes_open.json`, `calibration_resolved.csv`, `calibration_summary.json`, `strategy_memory.md`, `equity_state.json` |
| Latest outputs | `picks_today.json`, `analysed_all.json`, `event_results.json`, `backtest_results.json` |

## Method
For each stock, the engine estimates the probability of reaching a 5-day target before a
volatility-based stop. It blends historical first-passage counts (about 500 windows) with a
fat-tailed Monte Carlo simulation that models overnight gaps separately. Every estimate is
tracked until it resolves, then scored with the Brier score.

## Disclaimer
Research and education only. Not investment advice or a recommendation. Data is about
15 minutes delayed. Past results do not guarantee future results.

## Licence
MIT. See `LICENSE` and `THIRD_PARTY_NOTICES.md`.
