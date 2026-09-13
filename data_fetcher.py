"""
Twelve Data API orqali OHLC (Open/High/Low/Close) narx ma'lumotlarini oladi.
"""
import requests
import pandas as pd
import config

TWELVEDATA_URL = "https://api.twelvedata.com/time_series"


class DataFetchError(Exception):
    """Twelve Data'dan umumiy xatolik qaytganda ko'tariladi."""
    pass


class RateLimitError(DataFetchError):
    """Twelve Data API so'rovlar limiti (kunlik/daqiqalik) tugaganda ko'tariladi."""
    pass


# Twelve Data limit tugaganda xabarida odatda shu so'zlar uchraydi
# (masalan "You have run out of API credits for the current ...").
_RATE_LIMIT_HINTS = ("api credit", "run out of api", "limit")


def fetch_ohlc(symbol: str = None, interval: str = None, outputsize: int = 200) -> pd.DataFrame:
    """
    Berilgan instrument uchun tarixiy sham (candle) ma'lumotlarini qaytaradi.
    DataFrame ustunlari: datetime, open, high, low, close (eskidan yangiga saralangan).
    """
    symbol = symbol or config.SYMBOL
    interval = interval or config.INTERVAL

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": config.TWELVEDATA_API_KEY,
        "format": "JSON",
    }

    resp = requests.get(TWELVEDATA_URL, params=params, timeout=20)
    data = resp.json()

    if data.get("status") == "error" or "values" not in data:
        message = str(data.get("message", data))
        code = data.get("code")
        if code == 429 or any(hint in message.lower() for hint in _RATE_LIMIT_HINTS):
            raise RateLimitError(f"Twelve Data API limiti tugadi: {message}")
        raise DataFetchError(f"Twelve Data xatosi: {message}")

    df = pd.DataFrame(data["values"])
    df = df.rename(columns={"datetime": "datetime"})
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    return df
