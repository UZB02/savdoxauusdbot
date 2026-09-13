"""
Har bir indikator uchun ovoz (vote) chiqaradi: +1 = BUY tarafda, -1 = SELL tarafda, 0 = neytral.
So'ng bu ovozlarni og'irliklar (weights) bilan qo'shib, umumiy signal kuchini hisoblaydi.

Og'irliklar vaqt o'tishi bilan weights_manager.py orqali o'tmishdagi signal
natijalari asosida moslashtiriladi ("o'rganish" qismi shu yerda amalga oshadi).
"""
from dataclasses import dataclass, asdict
import pandas as pd

INDICATOR_NAMES = ["rsi", "macd", "ema_trend", "bollinger"]


@dataclass
class Votes:
    rsi: int
    macd: int
    ema_trend: int
    bollinger: int

    def as_dict(self):
        return asdict(self)


def compute_votes(df: pd.DataFrame) -> Votes:
    """Oxirgi ikkita sham (candle) asosida ovozlarni hisoblaydi."""
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # 1) RSI: haddan tashqari sotilgan/sotib olingan zonalar
    if last["rsi"] < 30:
        rsi_vote = 1
    elif last["rsi"] > 70:
        rsi_vote = -1
    else:
        rsi_vote = 0

    # 2) MACD: signal chizig'ini kesib o'tishi (crossover)
    macd_now_above = last["macd_line"] > last["macd_signal"]
    macd_prev_above = prev["macd_line"] > prev["macd_signal"]
    if macd_now_above and not macd_prev_above:
        macd_vote = 1
    elif not macd_now_above and macd_prev_above:
        macd_vote = -1
    else:
        macd_vote = 0

    # 3) EMA trend: qisqa muddatli EMA uzoq muddatlidan yuqori/past
    if last["ema20"] > last["ema50"]:
        ema_vote = 1
    elif last["ema20"] < last["ema50"]:
        ema_vote = -1
    else:
        ema_vote = 0

    # 4) Bollinger Bands: narx quyi/yuqori chegaraga yaqinlashgani (qaytish ehtimoli)
    band_width = last["bb_upper"] - last["bb_lower"]
    if band_width > 0:
        position = (last["close"] - last["bb_lower"]) / band_width
    else:
        position = 0.5

    if position <= 0.1:
        bb_vote = 1
    elif position >= 0.9:
        bb_vote = -1
    else:
        bb_vote = 0

    return Votes(rsi=rsi_vote, macd=macd_vote, ema_trend=ema_vote, bollinger=bb_vote)


def weighted_score(votes: Votes, weights: dict) -> float:
    v = votes.as_dict()
    return sum(v[name] * weights.get(name, 1.0) for name in INDICATOR_NAMES)


def classify(score: float, threshold: float) -> str:
    if score >= threshold:
        return "BUY"
    elif score <= -threshold:
        return "SELL"
    return "NEUTRAL"
