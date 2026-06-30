import psycopg2
from config import DATABASE_URL

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        self.init_tables()

    def init_tables(self):
        with self.conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS settings CASCADE")
            cur.execute("DROP TABLE IF EXISTS trades CASCADE")
            cur.execute("DROP TABLE IF EXISTS daily_trades CASCADE")
            cur.execute("DROP TABLE IF EXISTS signals CASCADE")
            cur.execute("DROP TABLE IF EXISTS top_coins CASCADE")

            cur.execute("CREATE TABLE IF NOT EXISTS settings (id SERIAL PRIMARY KEY, chat_id BIGINT UNIQUE, trade_amount DECIMAL(20,8) DEFAULT 50.0, max_trades_day INT DEFAULT 20, sl_mult DECIMAL(5,2) DEFAULT 2.0, tp_mult DECIMAL(5,2) DEFAULT 2.0, long_only BOOLEAN DEFAULT true, ema_fast INT DEFAULT 9, ema_slow INT DEFAULT 21, max_open_trades INT DEFAULT 5, active BOOLEAN DEFAULT false, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            cur.execute("CREATE TABLE IF NOT EXISTS trades (id SERIAL PRIMARY KEY, chat_id BIGINT, symbol VARCHAR(20), side VARCHAR(10), entry_price DECIMAL(20,8), stop_loss DECIMAL(20,8), take_profit DECIMAL(20,8), amount DECIMAL(20,8), status VARCHAR(20) DEFAULT 'OPEN', pnl DECIMAL(20,8) DEFAULT 0, opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, closed_at TIMESTAMP, close_price DECIMAL(20,8), atr DECIMAL(20,8), ema9 DECIMAL(20,8), ema21 DECIMAL(20,8))")
            cur.execute("CREATE TABLE IF NOT EXISTS daily_trades (id SERIAL PRIMARY KEY, chat_id BIGINT, trade_date DATE DEFAULT CURRENT_DATE, count INT DEFAULT 0, UNIQUE(chat_id, trade_date))")
            cur.execute("CREATE TABLE IF NOT EXISTS signals (id SERIAL PRIMARY KEY, chat_id BIGINT, symbol VARCHAR(20), signal_type VARCHAR(10), price DECIMAL(20,8), ema9 DECIMAL(20,8), ema21 DECIMAL(20,8), atr DECIMAL(20,8), strength DECIMAL(5,2), timeframe VARCHAR(10), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            cur.execute("CREATE TABLE IF NOT EXISTS top_coins (symbol VARCHAR(20) PRIMARY KEY, volume_24h DECIMAL(20,2), price DECIMAL(20,8), updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            self.conn.commit()

    def get_settings(self, chat_id):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM settings WHERE chat_id=%s", (chat_id,))
                row = cur.fetchone()
                if not row:
                    cur.execute("INSERT INTO settings (chat_id) VALUES (%s) RETURNING *", (chat_id,))
                    self.conn.commit()
                    row = cur.fetchone()
                # id=0, chat_id=1, trade_amount=2, max_trades_day=3, sl_mult=4, tp_mult=5, long_only=6, ema_fast=7, ema_slow=8, max_open_trades=9, active=10, created_at=11
                return {
                    'trade_amount': float(row[2]),
                    'max_trades_day': row[3],
                    'sl_mult': float(row[4]),
                    'tp_mult': float(row[5]),
                    'long_only': row[6],
                    'ema_fast': row[7],
                    'ema_slow': row[8],
                    'max_open_trades': row[9],
                    'active': row[10]
                }
        except Exception as e:
            self.conn.rollback()
            raise e

    def update_settings(self, chat_id, **kwargs):
        try:
            with self.conn.cursor() as cur:
                for key, val in kwargs.items():
                    cur.execute("UPDATE settings SET " + key + "=%s WHERE chat_id=%s", (val, chat_id))
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def get_daily_count(self, chat_id):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT count FROM daily_trades WHERE chat_id=%s AND trade_date=CURRENT_DATE", (chat_id,))
                row = cur.fetchone()
                return row[0] if row else 0
        except Exception as e:
            self.conn.rollback()
            return 0

    def increment_daily_count(self, chat_id):
        try:
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO daily_trades (chat_id, count) VALUES (%s, 1) ON CONFLICT (chat_id, trade_date) DO UPDATE SET count = daily_trades.count + 1", (chat_id,))
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()

    def add_trade(self, chat_id, symbol, side, entry, sl, tp, amount, atr, ema9, ema21):
        try:
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO trades (chat_id, symbol, side, entry_price, stop_loss, take_profit, amount, atr, ema9, ema21) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (chat_id, symbol, side, entry, sl, tp, amount, atr, ema9, ema21))
                self.conn.commit()
                return cur.fetchone()[0]
        except Exception as e:
            self.conn.rollback()
            raise e

    def get_open_trades(self, chat_id):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM trades WHERE chat_id=%s AND status='OPEN'", (chat_id,))
                return cur.fetchall()
        except Exception as e:
            self.conn.rollback()
            return []

    def get_all_open_trades(self):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM trades WHERE status='OPEN'")
                return cur.fetchall()
        except Exception as e:
            self.conn.rollback()
            return []

    def close_trade(self, trade_id, close_price, pnl):
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE trades SET status='CLOSED', close_price=%s, pnl=%s, closed_at=CURRENT_TIMESTAMP WHERE id=%s", (close_price, pnl, trade_id))
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()

    def get_trade_history(self, chat_id, limit=20):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM trades WHERE chat_id=%s ORDER BY opened_at DESC LIMIT %s", (chat_id, limit))
                return cur.fetchall()
        except Exception as e:
            self.conn.rollback()
            return []

    def get_today_pnl(self, chat_id):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT SUM(pnl) FROM trades WHERE chat_id=%s AND DATE(closed_at)=CURRENT_DATE", (chat_id,))
                row = cur.fetchone()
                return float(row[0]) if row[0] else 0
        except Exception as e:
            self.conn.rollback()
            return 0

    def add_signal(self, chat_id, symbol, signal_type, price, ema9, ema21, atr, strength, timeframe):
        try:
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO signals (chat_id, symbol, signal_type, price, ema9, ema21, atr, strength, timeframe) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (chat_id, symbol, signal_type, price, ema9, ema21, atr, strength, timeframe))
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()

    def save_top_coins(self, coins):
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM top_coins")
                for coin in coins:
                    cur.execute("INSERT INTO top_coins (symbol, volume_24h, price) VALUES (%s,%s,%s)", (coin['symbol'], coin['volume'], coin['price']))
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()

    def get_top_coins(self, limit=500):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT symbol FROM top_coins ORDER BY volume_24h DESC LIMIT %s", (limit,))
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            self.conn.rollback()
            return []
