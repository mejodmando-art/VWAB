import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import TELEGRAM_TOKEN, CHAT_ID
from database import Database
from exchange import GateIO
from strategy import VWAPStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()
gateio = GateIO()

# ========== KEYBOARDS ==========

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 الحالة", callback_data="status"),
         InlineKeyboardButton("⚙️ الإعدادات", callback_data="setup")],
        [InlineKeyboardButton("💰 الرصيد", callback_data="balance"),
         InlineKeyboardButton("📋 الصفقات المفتوحة", callback_data="open_trades")],
        [InlineKeyboardButton("📜 السجل", callback_data="history"),
         InlineKeyboardButton("▶️ تشغيل", callback_data="start_bot"),
         InlineKeyboardButton("⏹️ إيقاف", callback_data="stop_bot")],
        [InlineKeyboardButton("🔄 فحص يدوي", callback_data="manual_check")]
    ]
    return InlineKeyboardMarkup(keyboard)

def setup_menu():
    keyboard = [
        [InlineKeyboardButton("💵 مبلغ الصفقة", callback_data="set_amount"),
         InlineKeyboardButton("⏱️ التايم فريم", callback_data="set_timeframe")],
        [InlineKeyboardButton("📈 زوج التداول", callback_data="set_symbol"),
         InlineKeyboardButton("🛑 SL مضاعف", callback_data="set_sl")],
        [InlineKeyboardButton("🎯 TP مضاعف", callback_data="set_tp"),
         InlineKeyboardButton("📊 EMA طول", callback_data="set_ema")],
        [InlineKeyboardButton("↩️ Pullback %", callback_data="set_pullback"),
         InlineKeyboardButton("🔒 Long Only", callback_data="toggle_longonly")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def timeframe_menu():
    keyboard = [
        [InlineKeyboardButton("1m", callback_data="tf_1m"),
         InlineKeyboardButton("5m", callback_data="tf_5m"),
         InlineKeyboardButton("15m", callback_data="tf_15m")],
        [InlineKeyboardButton("30m", callback_data="tf_30m"),
         InlineKeyboardButton("1h", callback_data="tf_1h"),
         InlineKeyboardButton("4h", callback_data="tf_4h")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="setup")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== COMMANDS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = db.get_settings(chat_id)

    welcome = (
        "🤖 <b>بوت VWAP Trend Momentum</b>

"
        "مرحباً! البوت جاهز للتداول التلقائي.

"
        "📊 <b>الإعدادات الحالية:</b>
"
        f"• الزوج: <code>{settings['symbol']}</code>
"
        f"• التايم فريم: <code>{settings['timeframe']}</code>
"
        f"• مبلغ الصفقة: <code>${settings['trade_amount']}</code>
"
        f"• SL: <code>{settings['sl_mult']}x ATR</code>
"
        f"• TP: <code>{settings['tp_mult']}x ATR</code>
"
        f"• الحالة: <code>{'🟢 شغال' if settings['active'] else '🔴 متوقف'}</code>

"
        "اختر من القائمة:"
    )
    await update.message.reply_text(welcome, parse_mode="HTML", reply_markup=main_menu())

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_status(update, context)

# ========== CALLBACKS ==========

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
        text = (
            "⚙️ <b>الإعدادات الحالية:</b>

"
            f"💵 مبلغ الصفقة: ${settings['trade_amount']}
"
            f"⏱️ التايم فريم: {settings['timeframe']}
"
            f"📈 الزوج: {settings['symbol']}
"
            f"🛑 SL: {settings['sl_mult']}x ATR
"
            f"🎯 TP: {settings['tp_mult']}x ATR
"
            f"📊 EMA: {settings['ema_len']}
"
            f"↩️ Pullback: {settings['pullback_dist']}%
"
            f"🔒 Long Only: {'نعم' if settings['long_only'] else 'لا'}

"
            "اضغط لتعديل:"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=setup_menu())

    elif data == "balance":
        try:
            balance = gateio.get_balance()
            text = f"💰 <b>رصيد USDT:</b> <code>{balance:.2f}</code>"
        except Exception as e:
            text = f"❌ خطأ في جلب الرصيد: {str(e)}"
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu())

    elif data == "open_trades":
        trades = db.get_open_trades(chat_id)
        if not trades:
            text = "📋 لا توجد صفقات مفتوحة"
        else:
            text = "📋 <b>الصفقات المفتوحة:</b>\n\n"
            for t in trades:
                side_emoji = "🟢" if t[3] == 'LONG' else "🔴"
                text += f"{side_emoji} <b>{t[3]}</b> {t[2]}\n"
                text += f"الدخول: {float(t[4]):.4f}\n"
                text += f"SL: {float(t[5]):.4f} | TP: {float(t[6]):.4f}\n"
                text += f"الكمية: {float(t[7]):.4f}\n\n"
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu())

    elif data == "history":
        trades = db.get_trade_history(chat_id, 10)
        if not trades:
            text = "📜 لا توجد صفقات سابقة"
        else:
            text = "📜 <b>آخر 10 صفقات:</b>\n\n"
            for t in trades:
                side_emoji = "🟢" if t[3] == 'LONG' else "🔴"
                status_emoji = "✅" if t[8] == 'CLOSED' else "⏳"
                pnl = float(t[9]) if t[9] else 0
                pnl_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                text += f"{status_emoji} {side_emoji} <b>{t[3]}</b> {t[2]} {pnl_emoji} {pnl:.2f}\n"
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu())

    elif data == "start_bot":
        db.update_settings(chat_id, active=True)
        await query.edit_message_text("✅ <b>البوت شغال!</b>\nسيبدأ فحص الإشارات تلقائياً.", parse_mode="HTML", reply_markup=main_menu())
        asyncio.create_task(monitor_trades(chat_id, context))

    elif data == "stop_bot":
        db.update_settings(chat_id, active=False)
        await query.edit_message_text("⏹️ <b>البوت متوقف.</b>\nلن يتم فتح صفقات جديدة.", parse_mode="HTML", reply_markup=main_menu())

    elif data == "manual_check":
        await query.edit_message_text("🔄 جاري الفحص...", reply_markup=main_menu())
        result = await check_signal(chat_id)
        await query.edit_message_text(result, parse_mode="HTML", reply_markup=main_menu())

    # Setup callbacks
    elif data == "set_amount":
        context.user_data['awaiting'] = 'amount'
        await query.edit_message_text("💵 أرسل مبلغ الصفقة بالـ USDT:\n(مثال: 50)", reply_markup=setup_menu())

    elif data == "set_timeframe":
        await query.edit_message_text("⏱️ اختر التايم فريم:", reply_markup=timeframe_menu())

    elif data == "set_symbol":
        context.user_data['awaiting'] = 'symbol'
        await query.edit_message_text("📈 أرسل زوج التداول:\n(مثال: BTC_USDT)", reply_markup=setup_menu())

    elif data == "set_sl":
        context.user_data['awaiting'] = 'sl'
        await query.edit_message_text("🛑 أرسل مضاعف الستوب (x ATR):\n(مثال: 2.0)", reply_markup=setup_menu())

    elif data == "set_tp":
        context.user_data['awaiting'] = 'tp'
        await query.edit_message_text("🎯 أرسل مضاعف التيك بروفيت (x ATR):\n(مثال: 2.0)", reply_markup=setup_menu())

    elif data == "set_ema":
        context.user_data['awaiting'] = 'ema'
        await query.edit_message_text("📊 أرسل طول EMA:\n(مثال: 34)", reply_markup=setup_menu())

    elif data == "set_pullback":
        context.user_data['awaiting'] = 'pullback'
        await query.edit_message_text("↩️ أرسل نسبة الPullback %:\n(مثال: 0.15)", reply_markup=setup_menu())

    elif data == "toggle_longonly":
        settings = db.get_settings(chat_id)
        new_val = not settings['long_only']
        db.update_settings(chat_id, long_only=new_val)
        await query.edit_message_text(f"🔒 Long Only: {'مفعل ✅' if new_val else 'معطل ❌'}", reply_markup=setup_menu())

    # Timeframe selection
    elif data.startswith("tf_"):
        tf = data.replace("tf_", "")
        db.update_settings(chat_id, timeframe=tf)
        await query.edit_message_text(f"⏱️ التايم فريم: <code>{tf}</code>", parse_mode="HTML", reply_markup=setup_menu())

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if 'awaiting' not in context.user_data:
        await update.message.reply_text("استخدم القائمة:", reply_markup=main_menu())
        return

    awaiting = context.user_data['awaiting']
    del context.user_data['awaiting']

    try:
        if awaiting == 'amount':
            val = float(text)
            db.update_settings(chat_id, trade_amount=val)
            await update.message.reply_text(f"✅ مبلغ الصفقة: ${val}", reply_markup=setup_menu())

        elif awaiting == 'symbol':
            db.update_settings(chat_id, symbol=text.upper())
            await update.message.reply_text(f"✅ الزوج: {text.upper()}", reply_markup=setup_menu())

        elif awaiting == 'sl':
            val = float(text)
            db.update_settings(chat_id, sl_mult=val)
            await update.message.reply_text(f"✅ SL: {val}x ATR", reply_markup=setup_menu())

        elif awaiting == 'tp':
            val = float(text)
            db.update_settings(chat_id, tp_mult=val)
            await update.message.reply_text(f"✅ TP: {val}x ATR", reply_markup=setup_menu())

        elif awaiting == 'ema':
            val = int(text)
            db.update_settings(chat_id, ema_len=val)
            await update.message.reply_text(f"✅ EMA: {val}", reply_markup=setup_menu())

        elif awaiting == 'pullback':
            val = float(text)
            db.update_settings(chat_id, pullback_dist=val)
            await update.message.reply_text(f"✅ Pullback: {val}%", reply_markup=setup_menu())

    except ValueError:
        await update.message.reply_text("❌ قيمة غير صحيحة، جرب مرة أخرى:", reply_markup=setup_menu())

# ========== STATUS & SIGNALS ==========

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = db.get_settings(chat_id)
    daily_count = db.get_daily_count(chat_id)
    open_trades = db.get_open_trades(chat_id)

    try:
        balance = gateio.get_balance()
        price = gateio.get_ticker(settings['symbol'])
    except:
        balance = "❌"
        price = "❌"

    text = (
        "📊 <b>حالة البوت</b>\n\n"
        f"🟢 الحالة: {'شغال' if settings['active'] else 'متوقف'}\n"
        f"💰 الرصيد: <code>{balance if isinstance(balance, str) else f'{balance:.2f} USDT'}</code>\n"
        f"📈 السعر الحالي: <code>{price if isinstance(price, str) else f'{price:.4f}'}</code>\n"
        f"📋 صفقات مفتوحة: {len(open_trades)}\n"
        f"📊 صفقات اليوم: {daily_count}/{settings['max_trades_day']}\n\n"
        "⚙️ الإعدادات:\n"
        f"• الزوج: {settings['symbol']} | TF: {settings['timeframe']}\n"
        f"• المبلغ: ${settings['trade_amount']}\n"
        f"• SL: {settings['sl_mult']}x | TP: {settings['tp_mult']}x"
    )

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu())
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu())

async def check_signal(chat_id: int) -> str:
    settings = db.get_settings(chat_id)

    if not settings['active']:
        return "🔴 البوت متوقف"

    daily_count = db.get_daily_count(chat_id)
    if daily_count >= settings['max_trades_day']:
        return f"⏳ وصلت للحد الأقصى ({settings['max_trades_day']} صفقات/يوم)"

    open_trades = db.get_open_trades(chat_id)
    if open_trades:
        return f"⏳ يوجد {len(open_trades)} صفقة مفتوحة - انتظار الإغلاق"

    try:
        candles = gateio.get_klines(settings['symbol'], settings['timeframe'], 200)
        if len(candles) < 100:
            return "❌ بيانات غير كافية"

        strategy = VWAPStrategy(
            ema_len=settings['ema_len'],
            sl_mult=settings['sl_mult'],
            tp_mult=settings['tp_mult'],
            long_only=settings['long_only'],
            pullback_dist=settings['pullback_dist']
        )

        result = strategy.analyze(candles)

        if result['signal']:
            side = result['signal']
            entry = result['price']
            sl = result['stop_loss']
            tp = result['take_profit']
            amount = settings['trade_amount'] / entry

            # Execute order
            order = gateio.place_order(settings['symbol'], side, amount)

            # Save to DB
            trade_id = db.add_trade(chat_id, settings['symbol'], side, entry, sl, tp, amount)
            db.increment_daily_count(chat_id)
            db.add_signal(chat_id, settings['symbol'], side, entry, result['vwap'], result['ema_slope'], result['atr'])

            emoji = "🟢" if side == 'LONG' else "🔴"
            text = (
                f"{emoji} <b>تم فتح صفقة {side}!</b>\n\n"
                f"📈 الزوج: {settings['symbol']}\n"
                f"💵 السعر: {entry:.4f}\n"
                f"🛑 SL: {sl:.4f}\n"
                f"🎯 TP: {tp:.4f}\n"
                f"📊 ATR: {result['atr']:.4f}\n"
                f"💰 الكمية: {amount:.6f}\n\n"
                f"R:R = {settings['tp_mult']}/{settings['sl_mult']}:1"
            )
            return text
        else:
            return f"⏳ لا يوجد إشارة حالياً\n\n{result['reason']}"

    except Exception as e:
        return f"❌ خطأ: {str(e)}"

async def monitor_trades(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Monitor open trades and check for SL/TP hits"""
    while True:
        try:
            settings = db.get_settings(chat_id)
            if not settings['active']:
                await asyncio.sleep(60)
                continue

            open_trades = db.get_open_trades(chat_id)
            if not open_trades:
                # No open trades, check for new signal
                result = await check_signal(chat_id)
                if "تم فتح صفقة" in result:
                    await context.bot.send_message(chat_id=chat_id, text=result, parse_mode="HTML")
            else:
                # Check SL/TP for open trades
                current_price = gateio.get_ticker(settings['symbol'])
                for trade in open_trades:
                    trade_id = trade[0]
                    side = trade[3]
                    entry = float(trade[4])
                    sl = float(trade[5])
                    tp = float(trade[6])
                    amount = float(trade[7])

                    hit_sl = (side == 'LONG' and current_price <= sl) or (side == 'SHORT' and current_price >= sl)
                    hit_tp = (side == 'LONG' and current_price >= tp) or (side == 'SHORT' and current_price <= tp)

                    if hit_sl or hit_tp:
                        # Close position
                        close_side = 'SELL' if side == 'LONG' else 'BUY'
                        gateio.place_order(settings['symbol'], close_side, amount)

                        pnl = (current_price - entry) * amount if side == 'LONG' else (entry - current_price) * amount
                        db.close_trade(trade_id, current_price, pnl)

                        emoji = "🔴" if hit_sl else "🟢"
                        result_text = (
                            f"{emoji} <b>تم إغلاق الصفقة!</b>\n\n"
                            f"{'SL' if hit_sl else 'TP'} تم التفعيل\n"
                            f"السعر: {current_price:.4f}\n"
                            f"PNL: {pnl:.2f} USDT"
                        )

                        await context.bot.send_message(chat_id=chat_id, text=result_text, parse_mode="HTML")

            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            await asyncio.sleep(60)

# ========== MAIN ==========

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("text", message_handler))

    # Handle text messages for settings input
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Bot started!")
    application.run_polling()

if __name__ == "__main__":
    main()
