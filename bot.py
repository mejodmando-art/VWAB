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
scanning = False

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 الحالة", callback_data="status"),
         InlineKeyboardButton("⚙️ الإعدادات", callback_data="setup")],
        [InlineKeyboardButton("💰 الرصيد", callback_data="balance"),
         InlineKeyboardButton("📋 صفقاتي", callback_data="open_trades")],
        [InlineKeyboardButton("🔍 فحص السوق", callback_data="scan_market"),
         InlineKeyboardButton("📈 الفرص", callback_data="opportunities")],
        [InlineKeyboardButton("▶️ تشغيل", callback_data="start_bot"),
         InlineKeyboardButton("⏹️ إيقاف", callback_data="stop_bot")],
        [InlineKeyboardButton("📜 السجل", callback_data="history"),
         InlineKeyboardButton("📊 التقرير", callback_data="report")]
    ]
    return InlineKeyboardMarkup(keyboard)

def setup_menu():
    keyboard = [
        [InlineKeyboardButton("💵 المبلغ", callback_data="set_amount"),
         InlineKeyboardButton("⏱️ التايم", callback_data="set_timeframe")],
        [InlineKeyboardButton("🛑 الستوب", callback_data="set_sl"),
         InlineKeyboardButton("🎯 التيك", callback_data="set_tp")],
        [InlineKeyboardButton("↩️ Pullback", callback_data="set_pullback"),
         InlineKeyboardButton("📊 EMA", callback_data="set_ema")],
        [InlineKeyboardButton("🔒 Long Only", callback_data="toggle_longonly"),
         InlineKeyboardButton("📈 Max صفقات", callback_data="set_max_trades")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def timeframe_menu():
    keyboard = [
        [InlineKeyboardButton("15د", callback_data="tf_15m"),
         InlineKeyboardButton("30د", callback_data="tf_30m"),
         InlineKeyboardButton("1س", callback_data="tf_1h")],
        [InlineKeyboardButton("4س", callback_data="tf_4h"),
         InlineKeyboardButton("1ي", callback_data="tf_1d")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="setup")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = db.get_settings(chat_id)
    welcome = "🤖 بوت VWAP Trend Momentum" + chr(10) + chr(10) + "📊 الإعدادات:" + chr(10) + "• الزوج: " + settings["symbol"] + chr(10) + "• التايم: " + settings["timeframe"] + chr(10) + "• المبلغ: $" + str(settings["trade_amount"]) + chr(10) + "• SL: " + str(settings["sl_mult"]) + "x ATR" + chr(10) + "• TP: " + str(settings["tp_mult"]) + "x ATR" + chr(10) + "• Max صفقات: " + str(settings["max_open_trades"]) + chr(10) + "• الحالة: " + ("🟢 شغال" if settings["active"] else "🔴 متوقف")
    await update.message.reply_text(welcome, reply_markup=main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global scanning
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
        text = "⚙️ الإعدادات:" + chr(10) + chr(10) + "💵 المبلغ: $" + str(settings["trade_amount"]) + chr(10) + "⏱️ التايم: " + settings["timeframe"] + chr(10) + "🛑 SL: " + str(settings["sl_mult"]) + "x" + chr(10) + "🎯 TP: " + str(settings["tp_mult"]) + "x" + chr(10) + "📊 EMA: " + str(settings["ema_len"]) + chr(10) + "↩️ Pullback: " + str(settings["pullback_dist"]) + "%" + chr(10) + "🔒 Long Only: " + ("نعم" if settings["long_only"] else "لا") + chr(10) + "📈 Max صفقات: " + str(settings["max_open_trades"]) + chr(10) + chr(10) + "اضغط لتعديل:"
        await query.edit_message_text(text, reply_markup=setup_menu())
    elif data == "balance":
        try:
            balance = gateio.get_balance()
            text = "💰 رصيد USDT: " + str(round(balance, 2))
        except Exception as e:
            text = "❌ خطأ: " + str(e)
        await query.edit_message_text(text, reply_markup=main_menu())
    elif data == "open_trades":
        trades = db.get_open_trades(chat_id)
        if not trades:
            text = "📋 لا توجد صفقات مفتوحة"
        else:
            text = "📋 الصفقات المفتوحة (" + str(len(trades)) + "):" + chr(10) + chr(10)
            for t in trades:
                text += ("🟢" if t[3] == "LONG" else "🔴") + " " + t[3] + " " + t[2] + chr(10) + "الدخول: " + str(round(float(t[4]), 4)) + " | الحالي: ???" + chr(10) + "SL: " + str(round(float(t[5]), 4)) + " | TP: " + str(round(float(t[6]), 4)) + chr(10) + "الكمية: " + str(round(float(t[7]), 4)) + chr(10) + chr(10)
        await query.edit_message_text(text, reply_markup=main_menu())
    elif data == "history":
        trades = db.get_trade_history(chat_id, 20)
        if not trades:
            text = "📜 لا يوجد سجل"
        else:
            text = "📜 آخر 20 صفقة:" + chr(10) + chr(10)
            for t in trades:
                pnl = float(t[9]) if t[9] else 0
                emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                text += ("✅" if t[8] == "CLOSED" else "⏳") + " " + t[3] + " " + t[2] + " " + emoji + " " + str(round(pnl, 2)) + " USDT" + chr(10)
        await query.edit_message_text(text, reply_markup=main_menu())
    elif data == "report":
        await show_report(update, context)
    elif data == "start_bot":
        db.update_settings(chat_id, active=True)
        await query.edit_message_text("✅ البوت شغال! سيبدأ الفحص التلقائي كل ساعة.", reply_markup=main_menu())
        asyncio.create_task(auto_scan_and_trade(chat_id, context))
    elif data == "stop_bot":
        db.update_settings(chat_id, active=False)
        await query.edit_message_text("⏹️ البوت متوقف.", reply_markup=main_menu())
    elif data == "scan_market":
        if scanning:
            await query.edit_message_text("⏳ جاري الفحص بالفعل...", reply_markup=main_menu())
        else:
            scanning = True
            await query.edit_message_text("🔍 جاري فحص 100 عملة...", reply_markup=main_menu())
            asyncio.create_task(scan_market_task(chat_id, context))
    elif data == "opportunities":
        await show_opportunities(update, context)
    elif data == "set_amount":
        context.user_data["awaiting"] = "amount"
        await query.edit_message_text("💵 أرسل المبلغ بالـ USDT (مثال: 50):", reply_markup=setup_menu())
    elif data == "set_timeframe":
        await query.edit_message_text("⏱️ اختر التايم فريم:", reply_markup=timeframe_menu())
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
        await query.edit_message_text("↩️ أرسل نسبة Pullback % (مثال: 0.5):", reply_markup=setup_menu())
    elif data == "set_max_trades":
        context.user_data["awaiting"] = "max_trades"
        await query.edit_message_text("📈 أرسل الحد الأقصى للصفقات المفتوحة (مثال: 5):", reply_markup=setup_menu())
    elif data == "toggle_longonly":
        settings = db.get_settings(chat_id)
        new_val = not settings["long_only"]
        db.update_settings(chat_id, long_only=new_val)
        await query.edit_message_text("🔒 Long Only: " + ("مفعل ✅" if new_val else "معطل ❌"), reply_markup=setup_menu())
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
        elif awaiting == "max_trades":
            val = int(text)
            db.update_settings(chat_id, max_open_trades=val)
            await update.message.reply_text("✅ Max صفقات: " + str(val), reply_markup=setup_menu())
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
        balance = "❌"
        price = "❌"
    text = "📊 حالة البوت" + chr(10) + chr(10) + "🟢 الحالة: " + ("شغال" if settings["active"] else "متوقف") + chr(10) + "💰 الرصيد: " + (str(balance) if isinstance(balance, str) else str(round(balance, 2)) + " USDT") + chr(10) + "📋 صفقات مفتوحة: " + str(len(open_trades)) + "/" + str(settings["max_open_trades"]) + chr(10) + "📊 صفقات اليوم: " + str(daily_count) + "/" + str(settings["max_trades_day"]) + chr(10) + chr(10) + "⚙️ الإعدادات:" + chr(10) + "• المبلغ: $" + str(settings["trade_amount"]) + chr(10) + "• التايم: " + settings["timeframe"] + chr(10) + "• SL: " + str(settings["sl_mult"]) + "x | TP: " + str(settings["tp_mult"]) + "x"
    if hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())
    else:
        await update.message.reply_text(text, reply_markup=main_menu())

async def show_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    today_pnl = db.get_today_pnl(chat_id)
    trades = db.get_trade_history(chat_id, 100)
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t[9] and float(t[9]) > 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_pnl = sum(float(t[9]) for t in trades if t[9])

    text = "📊 التقرير اليومي" + chr(10) + chr(10) + "💰 ربح/خسارة اليوم: " + str(round(today_pnl, 2)) + " USDT" + chr(10) + "📈 إجمالي الربح: " + str(round(total_pnl, 2)) + " USDT" + chr(10) + "📊 إجمالي الصفقات: " + str(total_trades) + chr(10) + "🟢 الصفقات الرابحة: " + str(winning_trades) + chr(10) + "🔴 نسبة النجاح: " + str(round(win_rate, 1)) + "%"

    if hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())
    else:
        await update.message.reply_text(text, reply_markup=main_menu())

async def show_opportunities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Get recent signals
    text = "📈 الفرص الأخيرة:" + chr(10) + chr(10) + "اضغط 🔍 فحص السوق للحصول على فرص جديدة"
    if hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())
    else:
        await update.message.reply_text(text, reply_markup=main_menu())

async def scan_market_task(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    global scanning
    try:
        settings = db.get_settings(chat_id)
        await context.bot.send_message(chat_id=chat_id, text="🔍 جاري تحميل قائمة العملات...")

        # Get top coins
        coins = gateio.get_top_coins(100)
        if not coins:
            await context.bot.send_message(chat_id=chat_id, text="❌ لم يتم العثور على عملات")
            scanning = False
            return

        await context.bot.send_message(chat_id=chat_id, text="✅ تم العثور على " + str(len(coins)) + " عملة. جاري الفحص...")

        strategy = VWAPStrategy(
            ema_len=settings["ema_len"],
            sl_mult=settings["sl_mult"],
            tp_mult=settings["tp_mult"],
            long_only=settings["long_only"],
            pullback_dist=settings["pullback_dist"]
        )

        opportunities = []
        scanned = 0

        for coin in coins:
            try:
                candles = gateio.get_klines(coin["symbol"], settings["timeframe"], 200)
                if len(candles) < 100:
                    continue

                result = strategy.analyze(candles)
                if result["signal"] and result["strength"] > 30:
                    opportunities.append({
                        "symbol": coin["symbol"],
                        "signal": result["signal"],
                        "price": result["price"],
                        "sl": result["stop_loss"],
                        "tp": result["take_profit"],
                        "atr": result["atr"],
                        "strength": result["strength"],
                        "vwap_dist": result["vwap_dist"]
                    })

                scanned += 1
                if scanned % 20 == 0:
                    await context.bot.send_message(chat_id=chat_id, text="⏳ تم فحص " + str(scanned) + "/" + str(len(coins)) + " عملة...")

                await asyncio.sleep(0.5)  # Rate limit
            except Exception as e:
                continue

        # Sort by strength
        opportunities.sort(key=lambda x: x["strength"], reverse=True)

        if not opportunities:
            await context.bot.send_message(chat_id=chat_id, text="⏳ لا توجد فرص حالياً من " + str(scanned) + " عملة.")
        else:
            text = "🎯 أفضل " + str(min(10, len(opportunities))) + " فرص:" + chr(10) + chr(10)
            for i, opp in enumerate(opportunities[:10]):
                emoji = "🟢" if opp["signal"] == "LONG" else "🔴"
                text += str(i+1) + ". " + emoji + " " + opp["signal"] + " " + opp["symbol"] + chr(10)
                text += "   السعر: " + str(round(opp["price"], 4)) + " | القوة: " + str(round(opp["strength"], 1)) + "%" + chr(10)
                text += "   SL: " + str(round(opp["sl"], 4)) + " | TP: " + str(round(opp["tp"], 4)) + chr(10) + chr(10)

            await context.bot.send_message(chat_id=chat_id, text=text)

            # Auto trade top 3 if bot is active
            if settings["active"]:
                await auto_trade_opportunities(chat_id, context, opportunities[:3], settings)

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text="❌ خطأ في الفحص: " + str(e))
    finally:
        scanning = False

async def auto_trade_opportunities(chat_id: int, context: ContextTypes.DEFAULT_TYPE, opportunities: list, settings: dict):
    """Auto trade top opportunities"""
    open_trades = db.get_open_trades(chat_id)
    daily_count = db.get_daily_count(chat_id)

    if len(open_trades) >= settings["max_open_trades"]:
        await context.bot.send_message(chat_id=chat_id, text="⏳ وصلت للحد الأقصى للصفقات المفتوحة (" + str(settings["max_open_trades"]) + ")")
        return

    if daily_count >= settings["max_trades_day"]:
        await context.bot.send_message(chat_id=chat_id, text="⏳ وصلت للحد الأقصى اليومي")
        return

    trades_made = 0
    for opp in opportunities:
        if len(open_trades) + trades_made >= settings["max_open_trades"]:
            break
        if daily_count + trades_made >= settings["max_trades_day"]:
            break

        try:
            amount = settings["trade_amount"] / opp["price"]
            order = gateio.place_order(opp["symbol"], opp["signal"], amount)

            trade_id = db.add_trade(chat_id, opp["symbol"], opp["signal"], opp["price"], opp["sl"], opp["tp"], amount, opp["atr"])
            db.increment_daily_count(chat_id)
            db.add_signal(chat_id, opp["symbol"], opp["signal"], opp["price"], opp["price"], 0, opp["atr"], opp["strength"])

            emoji = "🟢" if opp["signal"] == "LONG" else "🔴"
            text = emoji + " تم فتح صفقة " + opp["signal"] + "!" + chr(10) + chr(10)
            text += "📈 الزوج: " + opp["symbol"] + chr(10)
            text += "💵 السعر: " + str(round(opp["price"], 4)) + chr(10)
            text += "🛑 SL: " + str(round(opp["sl"], 4)) + chr(10)
            text += "🎯 TP: " + str(round(opp["tp"], 4)) + chr(10)
            text += "📊 ATR: " + str(round(opp["atr"], 4)) + chr(10)
            text += "💰 الكمية: " + str(round(amount, 6)) + chr(10)
            text += "⚡ القوة: " + str(round(opp["strength"], 1)) + "%"

            await context.bot.send_message(chat_id=chat_id, text=text)
            trades_made += 1
            await asyncio.sleep(1)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text="❌ خطأ في فتح صفقة " + opp["symbol"] + ": " + str(e))

    if trades_made > 0:
        await context.bot.send_message(chat_id=chat_id, text="✅ تم فتح " + str(trades_made) + " صفقة بنجاح!")

async def auto_scan_and_trade(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Auto scan every hour"""
    while True:
        try:
            settings = db.get_settings(chat_id)
            if not settings["active"]:
                await asyncio.sleep(60)
                continue

            # Check open trades SL/TP
            await check_open_trades(chat_id, context)

            # Scan market every hour
            current_hour = int(asyncio.get_event_loop().time()) // 3600
            if current_hour % 1 == 0:  # Every hour
                await scan_market_task(chat_id, context)

            await asyncio.sleep(300)  # Check every 5 minutes
        except Exception as e:
            logger.error("Auto scan error: " + str(e))
            await asyncio.sleep(300)

async def check_open_trades(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check SL/TP for open trades"""
    try:
        open_trades = db.get_open_trades(chat_id)
        for trade in open_trades:
            try:
                trade_id = trade[0]
                symbol = trade[2]
                side = trade[3]
                entry = float(trade[4])
                sl = float(trade[5])
                tp = float(trade[6])
                amount = float(trade[7])

                current_price = gateio.get_ticker(symbol)
                if current_price == 0:
                    continue

                hit_sl = (side == "LONG" and current_price <= sl) or (side == "SHORT" and current_price >= sl)
                hit_tp = (side == "LONG" and current_price >= tp) or (side == "SHORT" and current_price <= tp)

                if hit_sl or hit_tp:
                    close_side = "SELL" if side == "LONG" else "BUY"
                    gateio.place_order(symbol, close_side, amount)

                    pnl = (current_price - entry) * amount if side == "LONG" else (entry - current_price) * amount
                    db.close_trade(trade_id, current_price, pnl)

                    emoji = "🔴" if hit_sl else "🟢"
                    text = emoji + " تم إغلاق صفقة!" + chr(10) + chr(10)
                    text += ("🛑 SL" if hit_sl else "🎯 TP") + " تم التفعيل" + chr(10)
                    text += "الزوج: " + symbol + chr(10)
                    text += "السعر: " + str(round(current_price, 4)) + chr(10)
                    text += "ربح/خسارة: " + str(round(pnl, 2)) + " USDT"

                    await context.bot.send_message(chat_id=chat_id, text=text)
            except Exception as e:
                continue
    except Exception as e:
        logger.error("Check trades error: " + str(e))

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("Bot started!")
    application.run_polling()

if __name__ == "__main__":
    main()
