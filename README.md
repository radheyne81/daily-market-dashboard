# Daily Market Dashboard — free web portal

This starter project turns the Colab workflow into a responsive browser dashboard. It is designed to work on mobile browsers and can be added to the phone's home screen. It is a web app, not a native Android APK.

## Included
- Market overview: Nifty 50, Bank Nifty, India VIX, Dow Jones, Nasdaq
- Market breadth: Nifty 50/100/200 and Nifty Bank
- Nifty 200 Heikin Ashi + RSI screener (capped by default to control runtime)
- Index technicals: MACD, EMA, RSI
- Cross-asset return correlation matrix
- Expert interpretation notes and CSV downloads
- Optional access-code gate

## Deploy free on Streamlit Community Cloud

1. Download and unzip this project.
2. Create a GitHub account if you do not have one.
3. Create a new **private or public repository** named `daily-market-dashboard` and upload `app.py` and `requirements.txt`.
4. Open Streamlit Community Cloud at https://share.streamlit.io/ and sign in with GitHub.
5. Choose **Create app**, select the repository, branch, and `app.py`, then deploy.
6. For an open portal, leave the access-code secret unset. For a simple shared access code, open the app's **Settings → Secrets** and add:
   `PORTAL_ACCESS_CODE = "choose-a-long-random-code"`
   This is a basic gate, not individual-user authentication. Anyone with the code can enter.
7. Your app will have a public URL that works from any phone or computer.

## Use it like a mobile app

- Android/Chrome: open the deployed URL → browser menu (⋮) → **Add to Home screen** or **Install app**.
- iPhone/Safari: open the URL → Share → **Add to Home Screen**.

The exact wording varies by browser. A home-screen shortcut opens the portal like an app, but it still needs an internet connection.

## Google Sheets integration

This starter version calculates from Yahoo Finance data directly; it does not require a Google Sheets credential, which keeps deployment simpler. Your original Colab script writes to `Daily_Market_Dashboard`. If you want the portal to read those exact tabs, a follow-up version can connect Google Sheets using Streamlit Secrets and a Google service account. Never commit credentials or private keys to GitHub.

## Important limitations

- Yahoo Finance is unofficial and may be delayed, incomplete, rate-limited, or unavailable. Do not treat it as an exchange-authorized live feed.
- Streamlit Community Cloud and data providers have free-tier limits; long Nifty 200 scans may take time. The screener defaults to 50 stocks and can be increased in the app.
- The portal runs when accessed, and cached data is refreshed periodically. This does **not** guarantee a scheduled background update while nobody is using the app.
- The access-code option is a simple shared gate, not robust account-level authentication.
- This is an analytics tool, not financial advice or a trade-execution system.
