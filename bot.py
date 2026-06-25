import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from config import TELEGRAM_TOKEN, CHAT_ID
from database import Database
from exchange import GateIO
from strategy import VWAPStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()
gateio = GateIO()

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 الحالة", callback_data="status"),
         InlineKeyboardButton("⚙️ الإعدادات", callback_data="setup")],
        [InlineKeyboardButton("💰 الرصيد", callback_data="balance"),
         InlineKeyboardButton("📋 الصفقات", callback_data="open_trades")],
        [InlineKeyboardButton("📜 السجل", callback_data="history"),
         InlineKeyboardButton("▶️ تشغيل", callback_data="start_bot"),
         InlineKeyboardButton("⏹️ إيقاف", callback_data="stop_bot")],
        [InlineKeyboardButton("🔄 فحص", callback_data="manual_check")]
    ]
    return InlineKeyboardMarkup(keyboard)

def setup_menu():
    keyboard = [
        [InlineKeyboardButton("💵 المبلغ", callback_data="set_amount"),
         InlineKeyboardButton("⏱️ التايم", callback_data="set_timeframe")],
        [InlineKeyboardButton("📈 الزوج", callback_data="set_symbol"),
         InlineKeyboardButton("🛑 الستوب", callback_data="set_sl")],
        [InlineKeyboardButton("🎯 التيك", callback_data="set_tp"),
         InlineKeyboardButton("📊 EMA", callback_data="set_ema")],
        [InlineKeyboardButton("↩️ Pullback", callback_data="set_pullback"),
         InlineKeyboardButton("🔒 Long", callback_data="toggle_longonly")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def timeframe_menu():
    keyboard = [
        [InlineKeyboardButton("1د", callback_data="tf_1m"),
         InlineKeyboardButton("5د", callback_data="tf_5m"),
         InlineKeyboardButton("15د", callback_data="tf_15m")],
        [InlineKeyboardButton("30د", callback_data="tf_30m"),
         InlineKeyboardButton("1س", callback_data="tf_1h"),
         InlineKeyboardButton("4س", callback_data="tf_4h")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="setup")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = db.get_settings(chat_id)
    welcome = "🤖 بوت VWAP" + chr(10) + chr(10) + "⚙️ الإعدادات:" + chr(10) + "Symbol: " + settings["symbol"] + chr(10) + "⏱️ التايم فريم: " + settings["timeframe"] + chr(10) + "Amount: $" + str(settings["trade_amount"]) + chr(10) + "SL: " + str(settings["sl_mult"]) + "x ATR" + chr(10) + "TP: " + str(settings["tp_mult"]) + "x ATR" + chr(10) + "Status: " + ("🟢 شغال" if settings["active"] else "🔴 متوقف")
    await update.message.reply_text(welcome, reply_markup=main_menu())

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_status(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data

    if data == "main_menu":
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=main_menu())
    elif data == "status":
        await show_status(update, context)
    elif data == "setup":
        settings = db.get_settings(chat_id)
        text = "⚙️ الإعدادات:" + chr(10) + "Amount: $" + str(settings["trade_amount"]) + chr(10) + "TF: " + settings["timeframe"] + chr(10) + "Symbol: " + settings["symbol"] + chr(10) + "SL: " + str(settings["sl_mult"]) + "x" + chr(10) + "TP: " + str(settings["tp_mult"]) + "x" + chr(10) + "EMA: " + str(settings["ema_len"]) + chr(10) + "Pullback: " + str(settings["pullback_dist"]) + "%" + chr(10) + "Long Only: " + ("Yes" if settings["long_only"] else "No") + chr(10) + chr(10) + "Click to edit:"
        await query.edit_message_text(text, reply_markup=setup_menu())
    elif data == "balance":
        try:
            balance = gateio.get_balance()
            text = "USDT Balance: " + str(round(balance, 2))
        except Exception as e:
            text = "❌ خطأ: " + str(e)
        await query.edit_message_text(text, reply_markup=main_menu())
    elif data == "open_trades":
        trades = db.get_open_trades(chat_id)
        if not trades:
            text = "📋 لا توجد صفقات"
        else:
            text = "📋 الصفقات المفتوحة:" + chr(10) + chr(10)
            for t in trades:
                text += t[3] + " " + t[2] + chr(10) + "Entry: " + str(round(float(t[4]), 4)) + chr(10) + "SL: " + str(round(float(t[5]), 4)) + " | TP: " + str(round(float(t[6]), 4)) + chr(10) + "Qty: " + str(round(float(t[7]), 4)) + chr(10) + chr(10)
        await query.edit_message_text(text, reply_markup=main_menu())
    elif data == "history":
        trades = db.get_trade_history(chat_id, 10)
        if not trades:
            text = "📜 لا يوجد سجل"
        else:
            text = "📜 آخر 10 صفقات:" + chr(10) + chr(10)
            for t in trades:
                pnl = float(t[9]) if t[9] else 0
                text += t[3] + " " + t[2] + " ربح/خسارة: " + str(round(pnl, 2)) + chr(10)
        await query.edit_message_text(text, reply_markup=main_menu())
    elif data == "start_bot":
        db.update_settings(chat_id, active=True)
        await query.edit_message_text("✅ البوت شغال!", reply_markup=main_menu())
        asyncio.create_task(monitor_trades(chat_id, context))
    elif data == "stop_bot":
        db.update_settings(chat_id, active=False)
        await query.edit_message_text("⏹️ البوت متوقف!", reply_markup=main_menu())
    elif data == "manual_check":
        await query.edit_message_text("🔄 جاري الفحص...", reply_markup=main_menu())
        result = await check_signal(chat_id)
        await query.edit_message_text(result, reply_markup=main_menu())
    elif data == "set_amount":
        context.user_data["awaiting"] = "amount"
        await query.edit_message_text("💵 أرسل المبلغ بالـ USDT (مثال: 50):", reply_markup=setup_menu())
    elif data == "set_timeframe":
        await query.edit_message_text("⏱️ اختر التايم فريم:", reply_markup=timeframe_menu())
    elif data == "set_symbol":
        context.user_data["awaiting"] = "symbol"
        await query.edit_message_text("📈 أرسل زوج التداول (مثال: BTC_USDT):", reply_markup=setup_menu())
    elif data == "set_sl":
        context.user_data["awaiting"] = "sl"
        await query.edit_message_text("🛑 أرسل مضاعف الستوب (مثال: 2.0):", reply_markup=setup_menu())
    elif data == "set_tp":
        context.user_data["awaiting"] = "tp"
        await query.edit_message_text("🎯 أرسل مضاعف التيك (مثال: 2.0):", reply_markup=setup_menu())
    elif data == "set_ema":
        context.user_data["awaiting"] = "ema"
        await query.edit_message_text("📊 أرسل طول EMA (مثال: 34):", reply_markup=setup_menu())
    elif data == "set_pullback":
        context.user_data["awaiting"] = "pullback"
        await query.edit_message_text("↩️ أرسل نسبة Pullback (مثال: 0.15):", reply_markup=setup_menu())
    elif data == "toggle_longonly":
        settings = db.get_settings(chat_id)
        new_val = not settings["long_only"]
        db.update_settings(chat_id, long_only=new_val)
        await query.edit_message_text("Long Only: " + ("ON" if new_val else "OFF"), reply_markup=setup_menu())
    elif data.startswith("tf_"):
        tf = data.replace("tf_", "")
        db.update_settings(chat_id, timeframe=tf)
        await query.edit_message_text("⏱️ التايم فريم: " + tf, reply_markup=setup_menu())

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    if "awaiting" not in context.user_data:
        await update.message.reply_text("استخدم القائمة:", reply_markup=main_menu())
        return
    awaiting = context.user_data["awaiting"]
    del context.user_data["awaiting"]
    try:
        if awaiting == "amount":
            val = float(text)
            db.update_settings(chat_id, trade_amount=val)
            await update.message.reply_text("✅ المبلغ: $" + str(val), reply_markup=setup_menu())
        elif awaiting == "symbol":
            db.update_settings(chat_id, symbol=text.upper())
            await update.message.reply_text("✅ الزوج: " + text.upper(), reply_markup=setup_menu())
        elif awaiting == "sl":
            val = float(text)
            db.update_settings(chat_id, sl_mult=val)
            await update.message.reply_text("✅ SL: " + str(val) + "x ATR", reply_markup=setup_menu())
        elif awaiting == "tp":
            val = float(text)
            db.update_settings(chat_id, tp_mult=val)
            await update.message.reply_text("✅ TP: " + str(val) + "x ATR", reply_markup=setup_menu())
        elif awaiting == "ema":
            val = int(text)
            db.update_settings(chat_id, ema_len=val)
            await update.message.reply_text("✅ EMA: " + str(val), reply_markup=setup_menu())
        elif awaiting == "pullback":
            val = float(text)
            db.update_settings(chat_id, pullback_dist=val)
            await update.message.reply_text("✅ Pullback: " + str(val) + "%", reply_markup=setup_menu())
    except ValueError:
        await update.message.reply_text("❌ قيمة غير صحيحة، جرب مرة أخرى:", reply_markup=setup_menu())

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = db.get_settings(chat_id)
    daily_count = db.get_daily_count(chat_id)
    open_trades = db.get_open_trades(chat_id)
    try:
        balance = gateio.get_balance()
        price = gateio.get_ticker(settings["symbol"])
    except:
        balance = "Error"
        price = "Error"
    text = "📊 حالة البوت" + chr(10) + chr(10) + "Status: " + ("🟢 شغال" if settings["active"] else "🔴 متوقف") + chr(10) + "Balance: " + (str(balance) if isinstance(balance, str) else str(round(balance, 2)) + " USDT") + chr(10) + "Price: " + (str(price) if isinstance(price, str) else str(round(price, 4))) + chr(10) + "📋 صفقات مفتوحة: " + str(len(open_trades)) + chr(10) + "📊 صفقات اليوم: " + str(daily_count) + "/" + str(settings["max_trades_day"]) + chr(10) + chr(10) + "⚙️ الإعدادات:" + chr(10) + "Symbol: " + settings["symbol"] + " | TF: " + settings["timeframe"] + chr(10) + "Amount: $" + str(settings["trade_amount"]) + chr(10) + "SL: " + str(settings["sl_mult"]) + "x | TP: " + str(settings["tp_mult"]) + "x"
    if hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())
    else:
        await update.message.reply_text(text, reply_markup=main_menu())

async def check_signal(chat_id: int) -> str:
    settings = db.get_settings(chat_id)
    if not settings["active"]:
        return "🔴 البوت متوقف"
    daily_count = db.get_daily_count(chat_id)
    if daily_count >= settings["max_trades_day"]:
        return "⏳ وصلت للحد الأقصى: " + str(settings["max_trades_day"])
    open_trades = db.get_open_trades(chat_id)
    if open_trades:
        return str(len(open_trades)) + " صفقات مفتوحة - انتظار الإغلاق"
    try:
        candles = gateio.get_klines(settings["symbol"], settings["timeframe"], 200)
        if len(candles) < 100:
            return "❌ بيانات غير كافية"
        strategy = VWAPStrategy(
            ema_len=settings["ema_len"],
            sl_mult=settings["sl_mult"],
            tp_mult=settings["tp_mult"],
            long_only=settings["long_only"],
            pullback_dist=settings["pullback_dist"]
        )
        result = strategy.analyze(candles)
        if result["signal"]:
            side = result["signal"]
            entry = result["price"]
            sl = result["stop_loss"]
            tp = result["take_profit"]
            amount = settings["trade_amount"] / entry
            order = gateio.place_order(settings["symbol"], side, amount)
            trade_id = db.add_trade(chat_id, settings["symbol"], side, entry, sl, tp, amount)
            db.increment_daily_count(chat_id)
            db.add_signal(chat_id, settings["symbol"], side, entry, result["vwap"], result["ema_slope"], result["atr"])
            return side + " صفقة مفتوحة!" + chr(10) + "Symbol: " + settings["symbol"] + chr(10) + "Entry: " + str(round(entry, 4)) + chr(10) + "SL: " + str(round(sl, 4)) + chr(10) + "TP: " + str(round(tp, 4)) + chr(10) + "ATR: " + str(round(result["atr"], 4)) + chr(10) + "Qty: " + str(round(amount, 6)) + chr(10) + "R:R = " + str(settings["tp_mult"]) + ":" + str(settings["sl_mult"])
        else:
            return "⏳ لا يوجد إشارة. " + result["reason"]
    except Exception as e:
        return "❌ خطأ: " + str(e)

async def monitor_trades(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    while True:
        try:
            settings = db.get_settings(chat_id)
            if not settings["active"]:
                await asyncio.sleep(60)
                continue
            open_trades = db.get_open_trades(chat_id)
            if not open_trades:
                result = await check_signal(chat_id)
                if "trade opened" in result:
                    await context.bot.send_message(chat_id=chat_id, text=result)
            else:
                current_price = gateio.get_ticker(settings["symbol"])
                for trade in open_trades:
                    trade_id = trade[0]
                    side = trade[3]
                    entry = float(trade[4])
                    sl = float(trade[5])
                    tp = float(trade[6])
                    amount = float(trade[7])
                    hit_sl = (side == "LONG" and current_price <= sl) or (side == "SHORT" and current_price >= sl)
                    hit_tp = (side == "LONG" and current_price >= tp) or (side == "SHORT" and current_price <= tp)
                    if hit_sl or hit_tp:
                        close_side = "SELL" if side == "LONG" else "BUY"
                        gateio.place_order(settings["symbol"], close_side, amount)
                        pnl = (current_price - entry) * amount if side == "LONG" else (entry - current_price) * amount
                        db.close_trade(trade_id, current_price, pnl)
                        result_text = "✅ تم إغلاق الصفقة! " + ("SL" if hit_sl else "TP") + " تم التفعيل. السعر: " + str(round(current_price, 4)) + " ربح/خسارة: " + str(round(pnl, 2)) + " USDT"
                        await context.bot.send_message(chat_id=chat_id, text=result_text)
            await asyncio.sleep(60)
        except Exception as e:
            logger.error("خطأ في المراقبة: " + str(e))
            await asyncio.sleep(60)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("Bot started!")
    application.run_polling()

if __name__ == "__main__":
    main()
