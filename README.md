# VWAP Trend Momentum Bot

Auto trading bot for Gate.io using VWAP + EMA + ATR strategy.

## Railway Variables (5 only)

| Variable | Source | Description |
|----------|--------|-------------|
| TELEGRAM_TOKEN | @BotFather | Bot token |
| CHAT_ID | @userinfobot | Your chat ID |
| GATEIO_API_KEY | Gate.io API | API Key |
| GATEIO_API_SECRET | Gate.io API | API Secret |
| DATABASE_URL | Supabase/Neon | Database URL |

## Setup

1. Create bot with @BotFather, get token
2. Get chat ID from @userinfobot
3. Create API keys on Gate.io (Spot Trade + Read Only)
4. Create database on Supabase or Neon
5. Deploy to Railway with the 5 variables

## Bot Commands (Buttons)

- Status - Show bot status
- Settings - Configure strategy
- Balance - USDT balance
- Open Trades - Active trades
- History - Trade history
- Start - Start bot
- Stop - Stop bot
- Manual Check - Check signal now

## Settings (from bot)

- Trade Amount (USDT)
- Timeframe (1m, 5m, 15m, 30m, 1h, 4h)
- Symbol (BTC_USDT, etc.)
- SL Multiplier (x ATR)
- TP Multiplier (x ATR)
- EMA Length
- Pullback %
- Long Only (Yes/No)

## Files

- bot.py - Main bot
- strategy.py - VWAP strategy
- exchange.py - Gate.io API
- database.py - PostgreSQL
- config.py - Settings
