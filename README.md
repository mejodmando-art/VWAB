# 🤖 VWAP Trend Momentum Bot

بوت تداول تلقائي على Gate.io باستخدام استراتيجية VWAP + EMA + ATR

## 📋 المتغيرات المطلوبة في Railway (5 فقط)

| المتغير | الحصول عليه | وصف |
|---------|-------------|-----|
| `TELEGRAM_TOKEN` | @BotFather في Telegram | توكن البوت |
| `CHAT_ID` | @userinfobot في Telegram | شات آي دي |
| `GATEIO_API_KEY` | Gate.io → API Management | API Key |
| `GATEIO_API_SECRET` | Gate.io → API Management | API Secret |
| `DATABASE_URL` | Supabase/Neon/Railway | URL قاعدة البيانات |

## 🚀 خطوات التشغيل

### 1. إنشاء بوت Telegram
- افتح @BotFather
- أرسل `/newbot`
- احفظ التوكن

### 2. الحصول على Chat ID
- افتح @userinfobot
- أرسل `/start`
- احفظ الرقم

### 3. Gate.io API Keys
- سجل في [Gate.io](https://www.gate.io)
- Wallet → API Management
- أنشئ API Key بصلاحيات:
  - ✅ Spot Trade
  - ✅ Read Only
  - ❌ Withdraw (ما تفعلهاش!)

### 4. قاعدة البيانات
- استخدم Supabase أو Neon أو Railway Postgres
- احفظ الـ DATABASE_URL

### 5. رفع على GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_REPO_URL
git push -u origin main
```

### 6. Railway Deployment
- New Project → Deploy from GitHub repo
- اختار الـ repo
- Variables → أضف الـ 5 متغيرات
- Deploy!

## 🎮 أوامر البوت (أزرار)

| الزر | الوظيفة |
|------|---------|
| 📊 الحالة | عرض حالة البوت والرصيد |
| ⚙️ الإعدادات | تعديل إعدادات الاستراتيجية |
| 💰 الرصيد | رصيد USDT في Gate.io |
| 📋 الصفقات المفتوحة | الصفقات النشطة حالياً |
| 📜 السجل | سجل الصفقات السابقة |
| ▶️ تشغيل | تشغيل البوت |
| ⏹️ إيقاف | إيقاف فتح صفقات جديدة |
| 🔄 فحص يدوي | فحص إشارة يدوياً |

## ⚙️ الإعدادات (تعديل من البوت)

- 💵 مبلغ الصفقة (USDT)
- ⏱️ التايم فريم (1m, 5m, 15m, 30m, 1h, 4h)
- 📈 زوج التداول (BTC_USDT, ETH_USDT, إلخ)
- 🛑 SL مضاعف (x ATR)
- 🎯 TP مضاعف (x ATR)
- 📊 EMA طول
- ↩️ Pullback %
- 🔒 Long Only (نعم/لا)

## ⚠️ تحذيرات

- ابدأ بمبالغ صغيرة
- جرب على Testnet أولاً
- لا تشارك API Keys مع أحد
- البوت يتداول Spot فقط (لا Futures)
- الماضي لا يضمن المستقبل

## 📁 هيكل المشروع

```
trading-bot/
├── bot.py           # البوت الرئيسي
├── strategy.py      # منطق VWAP Strategy
├── exchange.py      # Gate.io API
├── database.py      # PostgreSQL
├── config.py        # الإعدادات
├── requirements.txt # المكتبات
├── Procfile         # Railway config
├── runtime.txt      # Python version
└── .env.example     # نموذج المتغيرات
```
