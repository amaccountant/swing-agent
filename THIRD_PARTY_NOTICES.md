# Third-Party Notices

This project ("Swing Agent") uses the third-party components listed below.
Each remains the property of its respective copyright holders and is used
under the license stated. No component's license text has been altered.

Maintainer: Malviyaarjun · Project license: MIT (see `LICENSE`)
Last reviewed: 2026-09

---

## 1. Chart.js
- **Use:** Charts on the dashboard (accuracy line, hit-rate donuts, deviation bars)
- **Loaded via:** jsDelivr CDN, pinned version `chart.js@4.4.3`
- **Source:** https://github.com/chartjs/Chart.js
- **License:** MIT
- **Copyright:** Copyright (c) 2014-present Chart.js Contributors
- **Note:** Loaded at runtime as an external dependency; source is not copied
  into or redistributed by this repository.

## 2. yfinance
- **Use:** Retrieving delayed market price history in `scan.py`, `scan_in.py`,
  `review.py`, `review_in.py`, `refresh_watchlist*.py`
- **Installed via:** pip (GitHub Actions runtime)
- **Source:** https://github.com/ranaroussi/yfinance
- **License:** Apache License 2.0
- **Copyright:** Copyright Ran Aroussi and contributors
- **Apache-2.0 obligations acknowledged:** attribution retained here; no
  yfinance source files have been modified or redistributed by this project.

## 3. Google Website Translator (translate.google.com element)
- **Use:** Optional on-page language switching
- **Loaded via:** Google-hosted script at runtime
- **Terms:** Governed by Google's Terms of Service; not open-source and not
  redistributed here. https://policies.google.com/terms
- **Note:** Machine translation may be imprecise. Risk disclaimers on the
  dashboard are marked `translate="no"` so they remain in original English.

## 4. Twemoji (PWA icon in `manifest.json`)
- **Use:** App icon referenced from jsDelivr
- **Source:** https://github.com/twitter/twemoji
- **License:** Graphics under CC-BY 4.0; code under MIT
- **Copyright / attribution:** Copyright Twitter, Inc and other contributors.
  Graphics licensed under CC-BY 4.0: https://creativecommons.org/licenses/by/4.0/
- **Note:** Attribution provided here to satisfy CC-BY 4.0.

## 5. Emoji glyphs used in the interface
- Rendered by the end user's own operating system font. Not bundled or
  redistributed by this project.

---

## Market data — important
Price data is obtained through the `yfinance` library from Yahoo Finance and is
**approximately 15 minutes delayed**, based on the prior close. It is used for
**personal, non-commercial research and education only**, is **not redistributed**,
and is **not** presented as live or authoritative. Users must verify live prices
with their own broker. Data providers' terms remain applicable.

## Disclaimer
This project is research and education software. It is **not financial advice**,
not an offer or solicitation, and provides no guarantee of accuracy or outcome.
Users are solely responsible for their own trading decisions and for compliance
with applicable regulations (e.g. BaFin/MiFID II in the EU; SEBI/STT in India).
