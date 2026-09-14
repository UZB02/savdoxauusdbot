"""
Bot uchun barcha sozlamalarni .env fayldan o'qiydi.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")

SYMBOL = os.getenv("SYMBOL", "XAU/USD")
INTERVAL = os.getenv("INTERVAL", "15min")

CHECK_EVERY_SECONDS = int(os.getenv("CHECK_EVERY_SECONDS", "900"))
SIGNAL_THRESHOLD = float(os.getenv("SIGNAL_THRESHOLD", "2.5"))
OUTCOME_LOOKAHEAD_CANDLES = int(os.getenv("OUTCOME_LOOKAHEAD_CANDLES", "4"))
WEIGHT_UPDATE_EVERY_SECONDS = int(os.getenv("WEIGHT_UPDATE_EVERY_SECONDS", "21600"))

# Stop Loss uzoqligi = ATR * shu koeffitsient
SL_ATR_MULTIPLIER = float(os.getenv("SL_ATR_MULTIPLIER", "1.5"))
# Take Profit uzoqligi = ATR * shu koeffitsient (odatda SL dan kattaroq, yaxshi risk/reward uchun)
TP_ATR_MULTIPLIER = float(os.getenv("TP_ATR_MULTIPLIER", "3.0"))
# Kirish zonasi kengligi = ATR * shu ulush (masalan 0.1 = ATR ning 10%)
ENTRY_ZONE_ATR_FRACTION = float(os.getenv("ENTRY_ZONE_ATR_FRACTION", "0.1"))

# Sessiya filtri: London/Nyu-York savdo soatlaridan tashqarida (odatda past
# likvidlik, ko'proq "shovqin" bo'ladigan sof Osiyo sessiyasida) signal
# chiqarishni to'xtatib turadi. Soatlar UTC bo'yicha (data_fetcher.py
# ma'lumotni har doim UTC formatida so'raydi).
SESSION_FILTER_ENABLED = int(os.getenv("SESSION_FILTER_ENABLED", "1"))
SESSION_START_HOUR_UTC = int(os.getenv("SESSION_START_HOUR_UTC", "7"))
SESSION_END_HOUR_UTC = int(os.getenv("SESSION_END_HOUR_UTC", "21"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

CHAT_IDS_FILE = os.path.join(DATA_DIR, "chat_ids.json")
WEIGHTS_FILE = os.path.join(DATA_DIR, "weights.json")
HISTORY_FILE = os.path.join(DATA_DIR, "signal_history.json")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN topilmadi. .env faylini yarating (.env.example asosida) "
        "va token qiymatini kiriting."
    )
if not TWELVEDATA_API_KEY:
    raise RuntimeError(
        "TWELVEDATA_API_KEY topilmadi. https://twelvedata.com saytidan bepul key oling "
        "va .env fayliga qo'shing."
    )
