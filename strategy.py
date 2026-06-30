from typing import Dict, List, Optional

class EMA9Cross21Strategy:
    def __init__(self, ema_fast=9, ema_slow=21, sl_mult=2.0, tp_mult=2.0, long_only=True):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.sl_mult = sl_mult
        self.tp_mult = tp_mult
        self.long_only = long_only

    def _ema(self, data, period):
        if len(data) < period:
            return data
        k = 2.0 / (period + 1)
        ema = [sum(data[:period]) / period]
        for price in data[period:]:
            ema.append(price * k + ema[-1] * (1 - k))
        result = [None] * (period - 1) + ema
        return result

    def _atr(self, highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return [0] * len(closes)
        trs = []
        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            trs.append(max(tr1, tr2, tr3))

        atr = [sum(trs[:period]) / period]
        for tr in trs[period:]:
            atr.append((atr[-1] * (period - 1) + tr) / period)

        result = [0] * (period) + atr
        return result

    def analyze_1h(self, candles_1h, candles_4h):
        """Analyze 1H candles with 4H confirmation"""
        if len(candles_1h) < self.ema_slow + 10 or len(candles_4h) < self.ema_slow + 5:
            return {"signal": None, "reason": "Insufficient data", "strength": 0}

        closes_1h = [c["close"] for c in candles_1h]
        highs_1h = [c["high"] for c in candles_1h]
        lows_1h = [c["low"] for c in candles_1h]

        closes_4h = [c["close"] for c in candles_4h]

        # Calculate EMAs for 1H
        ema9_1h = self._ema(closes_1h, self.ema_fast)
        ema21_1h = self._ema(closes_1h, self.ema_slow)
        atr_1h = self._atr(highs_1h, lows_1h, closes_1h)

        # Calculate EMAs for 4H (confirmation)
        ema9_4h = self._ema(closes_4h, self.ema_fast)
        ema21_4h = self._ema(closes_4h, self.ema_slow)

        i = len(candles_1h) - 1
        curr_close = closes_1h[i]
        curr_ema9 = ema9_1h[i]
        curr_ema21 = ema21_1h[i]
        curr_atr = atr_1h[i]

        if curr_ema9 is None or curr_ema21 is None or curr_atr == 0:
            return {"signal": None, "reason": "Indicators not ready", "strength": 0}

        # Previous values for crossover detection
        prev_ema9 = ema9_1h[i-1]
        prev_ema21 = ema21_1h[i-1]

        if prev_ema9 is None or prev_ema21 is None:
            return {"signal": None, "reason": "Need more history", "strength": 0}

        # Crossover detection
        cross_up = prev_ema9 <= prev_ema21 and curr_ema9 > curr_ema21
        cross_down = prev_ema9 >= prev_ema21 and curr_ema9 < curr_ema21

        # 4H confirmation
        j = len(candles_4h) - 1
        confirm_bull = False
        confirm_bear = False

        if ema9_4h[j] is not None and ema21_4h[j] is not None:
            confirm_bull = ema9_4h[j] > ema21_4h[j]
            confirm_bear = ema9_4h[j] < ema21_4h[j]

        # Signal generation
        signal = None
        stop_loss = None
        take_profit = None
        strength = 0

        if cross_up and confirm_bull:
            signal = "LONG"
            stop_loss = curr_close - curr_atr * self.sl_mult
            take_profit = curr_close + curr_atr * self.tp_mult
            strength = 50 + ((curr_ema9 - curr_ema21) / curr_ema21 * 100) * 5
        elif cross_down and confirm_bear and not self.long_only:
            signal = "SHORT"
            stop_loss = curr_close + curr_atr * self.sl_mult
            take_profit = curr_close - curr_atr * self.tp_mult
            strength = 50 + ((curr_ema21 - curr_ema9) / curr_ema21 * 100) * 5

        strength = min(100, max(0, strength))

        return {
            "signal": signal,
            "price": curr_close,
            "ema9": curr_ema9,
            "ema21": curr_ema21,
            "atr": curr_atr,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "strength": strength,
            "cross_up": cross_up,
            "cross_down": cross_down,
            "confirm_4h": confirm_bull if cross_up else confirm_bear,
            "reason": "1H EMA9/21 " + ("Cross Up" if cross_up else "Cross Down" if cross_down else "No Cross") + " | 4H: " + ("Bull" if confirm_bull else "Bear" if confirm_bear else "Neutral")
        }
