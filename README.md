# EMA 9/21 Crossover Bot

Auto trading bot for Gate.io Spot using EMA 9/21 crossover strategy.
Scans top 500 coins and auto-enters trades on 1H timeframe with 4H confirmation.

## Railway Variables (5 only)

| Variable | Source | Description |
|----------|--------|-------------|
| TELEGRAM_TOKEN | @BotFather | Bot token |
| CHAT_ID | @userinfobot | Your chat ID |
| GATEIO_API_KEY | Gate.io API | API Key |
| GATEIO_API_SECRET | Gate.io API | API Secret |
| DATABASE_URL | Supabase/Neon | Database URL |

## Strategy

- EMA 9 crosses EMA 21 on 1H timeframe
- Confirmed by 4H timeframe trend
- Auto SL/TP based on ATR
- Spot trading only

## Features

- Scans top 500 coins by volume
- Filters: volume > 500K, price > 0.001
- Auto-enters trades on signals
- Max 5 open trades
- Daily report
- Manual scan button

## Bot Commands

- /start - Show menu
- Status - Bot status
- Settings - Configure strategy
- Balance - USDT balance
- Scan 500 Coins - Manual scan
- Opportunities - View signals
- Start/Stop - Auto trading
- History - Trade log
- Report - Daily P&L

## Settings

- Trade Amount (USDT)
- SL Multiplier (x ATR)
- TP Multiplier (x ATR)
- Max Open Trades
- Long Only mode
