"""
Har bir chiqarilgan signalni saqlaydi (vaqt, narx, ovozlar, umumiy ball, qaror).
Ma'lum vaqt/sham o'tgach, narx qanday harakat qilganini tekshirib,
signal "to'g'ri" yoki "noto'g'ri" chiqqanini aniqlaydi.
"""
import json
import os
from datetime import datetime
import config


def _load() -> list:
    if os.path.exists(config.HISTORY_FILE):
        with open(config.HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def _save(history: list):
    with open(config.HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, default=str)


def log_signal(decision: str, score: float, votes: dict, price: float, candle_datetime):
    if decision == "NEUTRAL":
        return
    history = _load()
    history.append({
        "id": len(history) + 1,
        "decision": decision,
        "score": score,
        "votes": votes,
        "price_at_signal": price,
        "candle_datetime": str(candle_datetime),
        "logged_at": datetime.utcnow().isoformat(),
        "resolved": False,
        "outcome": None,
    })
    _save(history)


def resolve_pending(df, lookahead_candles: int, move_threshold_pct: float = 0.05):
    """
    df: eng so'nggi indikatorlar bilan hisoblangan OHLC DataFrame (datetime, close ustunlari bilan).
    Har bir hali "resolved=False" bo'lgan yozuv uchun, agar signal berilgan
    shamdan keyin kamida `lookahead_candles` ta yangi sham o'tgan bo'lsa,
    narx harakatiga qarab outcome ("BUY"/"SELL"/"FLAT") belgilanadi.

    Qaytaradi: shu chaqiruvda yangi hal qilingan yozuvlar ro'yxati.
    """
    history = _load()
    newly_resolved = []

    datetimes = df["datetime"].tolist()
    closes = df["close"].tolist()

    for entry in history:
        if entry["resolved"]:
            continue

        signal_dt = entry["candle_datetime"]
        try:
            idx = next(i for i, dt in enumerate(datetimes) if str(dt) == signal_dt)
        except StopIteration:
            continue

        target_idx = idx + lookahead_candles
        if target_idx >= len(closes):
            continue

        price_then = entry["price_at_signal"]
        price_after = closes[target_idx]
        pct_change = (price_after - price_then) / price_then * 100

        if pct_change > move_threshold_pct:
            outcome = "BUY"
        elif pct_change < -move_threshold_pct:
            outcome = "SELL"
        else:
            outcome = "FLAT"

        entry["resolved"] = True
        entry["outcome"] = outcome
        entry["price_after"] = price_after
        entry["pct_change"] = pct_change
        newly_resolved.append(entry)

    if newly_resolved:
        _save(history)

    return newly_resolved


def get_stats() -> dict:
    history = _load()
    resolved = [e for e in history if e["resolved"]]
    if not resolved:
        return {"total_signals": len(history), "resolved": 0, "accuracy": None}

    correct = sum(1 for e in resolved if e["outcome"] == e["decision"])
    accuracy = correct / len(resolved) * 100
    return {
        "total_signals": len(history),
        "resolved": len(resolved),
        "correct": correct,
        "accuracy": round(accuracy, 1),
    }
