# VWAP Trend Momentum Bot - Final Version

Auto trading bot for Gate.io Spot using VWAP + EMA + ATR strategy.
Scans top 100 coins and auto-enters trades.

## Railway Variables (5 only)

| Variable | Source | Description |
|----------|--------|-------------|
| TELEGRAM_TOKEN | @BotFather | Bot token |
| CHAT_ID | @userinfobot | Your chat ID |
| GATEIO_API_KEY | Gate.io API | API Key |
| GATEIO_API_SECRET | Gate.io API | API Secret |
| DATABASE_URL | Supabase/Neon | Database URL |

## Features

- Scans top 100 coins by volume
- Auto-enters trades on signals
- Auto SL/TP based on ATR
- Daily report
- Max 5 open trades
- Filters: volume > 1M, price > 0.01

## Bot Commands

- /start - Show menu
- Status - Bot status
- Settings - Configure strategy
- Balance - USDT balance
- Scan Market - Manual scan
- Opportunities - View signals
- Start/Stop - Auto trading
- History - Trade log
- Report - Daily P&L

## Settings

- Trade Amount (USDT)
- Timeframe (15m, 30m, 1h, 4h, 1d)
- SL Multiplier (x ATR)
- TP Multiplier (x ATR)
- Pullback %
- EMA Length
- Max Open Trades
- Long Only mode
