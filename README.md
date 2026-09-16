# 📈 Swing Agent

A personal, **suggest-only** short-swing stock research dashboard for
🇩🇪 German (XETRA) and 🇮🇳 Indian (NSE) equities. Runs free on GitHub Actions +
GitHub Pages. Built by **Malviyaarjun**.

**Live dashboard:** https://amaccountant.github.io/swing-agent/

## What it does
- Rebuilds an intelligent watchlist of liquid, affordable movers each morning
- Scores candidates on trend, momentum (RSI), volatility (ATR) and liquidity
- Sets a history-based realistic target, a stop-loss, and a cost-aware
  "worthwhile" test (Germany ≥3%, India ≥1.5%)
- Grades itself after the close and writes lessons into a strategy memory

## ⚠️ Disclaimer
Research and education only — **not financial advice**. Market data is
**~15 minutes delayed** and based on the prior close. All targets are estimates,
never guarantees. You place, own, and are responsible for every trade, including
tax and regulatory compliance.

## Licensing
- This project: **MIT** — see [`LICENSE`](LICENSE)
- Third-party components and data terms: see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
