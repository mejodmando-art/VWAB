import psycopg2
from config import DATABASE_URL

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        self.init_tables()

    def init_tables(self):
        with self.conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS settings (id SERIAL PRIMARY KEY, chat_id BIGINT UNIQUE, symbol VARCHAR(20) DEFAULT 'BTC_USDT', timeframe VARCHAR(10) DEFAULT '15m', trade_amount DECIMAL(20,8) DEFAULT 50.0, max_trades_day INT DEFAULT 6, sl_mult DECIMAL(5,2) DEFAULT 2.0, tp_mult DECIMAL(5,2) DEFAULT 2.0, long_only BOOLEAN DEFAULT true, ema_len INT DEFAULT 34, pullback_dist DECIMAL(5,2) DEFAULT 0.15, active BOOLEAN DEFAULT false, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            cur.execute("CREATE TABLE IF NOT EXISTS trades (id SERIAL PRIMARY KEY, chat_id BIGINT, symbol VARCHAR(20), side VARCHAR(10), entry_price DECIMAL(20,8), stop_loss DECIMAL(20,8), take_profit DECIMAL(20,8), amount DECIMAL(20,8), status VARCHAR(20) DEFAULT 'OPEN', pnl DECIMAL(20,8) DEFAULT 0, opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, closed_at TIMESTAMP, close_price DECIMAL(20,8))")
            cur.execute("CREATE TABLE IF NOT EXISTS daily_trades (id SERIAL PRIMARY KEY, chat_id BIGINT, trade_date DATE DEFAULT CURRENT_DATE, count INT DEFAULT 0, UNIQUE(chat_id, trade_date))")
            cur.execute("CREATE TABLE IF NOT EXISTS signals (id SERIAL PRIMARY KEY, chat_id BIGINT, symbol VARCHAR(20), signal_type VARCHAR(10), price DECIMAL(20,8), vwap DECIMAL(20,8), ema_slope DECIMAL(20,8), atr DECIMAL(20,8), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            self.conn.commit()

    def get_settings(self, chat_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM settings WHERE chat_id=%s", (chat_id,))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO settings (chat_id) VALUES (%s) RETURNING *", (chat_id,))
                self.conn.commit()
                row = cur.fetchone()
            return {
                'symbol': row[2], 'timeframe': row[3], 'trade_amount': float(row[4]),
                'max_trades_day': row[5], 'sl_mult': float(row[6]), 'tp_mult': float(row[7]),
                'long_only': row[8], 'ema_len': row[9], 'pullback_dist': float(row[10]),
                'active': row[11]
            }

    def update_settings(self, chat_id, **kwargs):
        with self.conn.cursor() as cur:
            for key, val in kwargs.items():
                cur.execute("UPDATE settings SET " + key + "=%s WHERE chat_id=%s", (val, chat_id))
            self.conn.commit()

    def get_daily_count(self, chat_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT count FROM daily_trades WHERE chat_id=%s AND trade_date=CURRENT_DATE", (chat_id,))
            row = cur.fetchone()
            return row[0] if row else 0

    def increment_daily_count(self, chat_id):
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO daily_trades (chat_id, count) VALUES (%s, 1) ON CONFLICT (chat_id, trade_date) DO UPDATE SET count = daily_trades.count + 1", (chat_id,))
            self.conn.commit()

    def add_trade(self, chat_id, symbol, side, entry, sl, tp, amount):
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO trades (chat_id, symbol, side, entry_price, stop_loss, take_profit, amount) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", (chat_id, symbol, side, entry, sl, tp, amount))
            self.conn.commit()
            return cur.fetchone()[0]

    def get_open_trades(self, chat_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM trades WHERE chat_id=%s AND status='OPEN'", (chat_id,))
            return cur.fetchall()

    def close_trade(self, trade_id, close_price, pnl):
        with self.conn.cursor() as cur:
            cur.execute("UPDATE trades SET status='CLOSED', close_price=%s, pnl=%s, closed_at=CURRENT_TIMESTAMP WHERE id=%s", (close_price, pnl, trade_id))
            self.conn.commit()

    def get_trade_history(self, chat_id, limit=10):
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM trades WHERE chat_id=%s ORDER BY opened_at DESC LIMIT %s", (chat_id, limit))
            return cur.fetchall()

    def add_signal(self, chat_id, symbol, signal_type, price, vwap, ema_slope, atr):
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO signals (chat_id, symbol, signal_type, price, vwap, ema_slope, atr) VALUES (%s,%s,%s,%s,%s,%s,%s)", (chat_id, symbol, signal_type, price, vwap, ema_slope, atr))
            self.conn.commit()
