"""
Botning ba'zi sozlamalarini (.env dagi standart qiymatlar ustidan)
alohida faylda saqlaydi, shunda ularni Telegram tugmalari orqali
o'zgartirish mumkin bo'ladi — .env faylini qayta tahrirlash yoki
botni qayta ishga tushirish shart bo'lmaydi.
"""
import json
import os
import config

SETTINGS_FILE = os.path.join(config.DATA_DIR, "settings.json")

# Har bir sozlamaning boshlang'ich (.env dagi) qiymati.
DEFAULTS = {
    "SYMBOL": config.SYMBOL,
    "INTERVAL": config.INTERVAL,
    "CHECK_EVERY_SECONDS": config.CHECK_EVERY_SECONDS,
    "SIGNAL_THRESHOLD": config.SIGNAL_THRESHOLD,
    "SL_ATR_MULTIPLIER": config.SL_ATR_MULTIPLIER,
    "TP_ATR_MULTIPLIER": config.TP_ATR_MULTIPLIER,
    "ENTRY_ZONE_ATR_FRACTION": config.ENTRY_ZONE_ATR_FRACTION,
    "WEIGHT_UPDATE_EVERY_SECONDS": config.WEIGHT_UPDATE_EVERY_SECONDS,
}

# Har bir sozlama qanday turga (int, float, str) o'girilishi kerakligini
# DEFAULTS dagi qiymat turidan avtomatik aniqlaymiz.
_TYPES = {k: type(v) for k, v in DEFAULTS.items()}


def _load_all() -> dict:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            saved = json.load(f)
    else:
        saved = {}
    merged = dict(DEFAULTS)
    merged.update(saved)
    return merged


def get(key: str):
    return _load_all().get(key, DEFAULTS.get(key))


def get_all() -> dict:
    return _load_all()


def set(key: str, value):
    if key not in DEFAULTS:
        raise KeyError(f"Noma'lum sozlama: {key}")
    value = _TYPES[key](value)
    all_settings = _load_all()
    all_settings[key] = value
    with open(SETTINGS_FILE, "w") as f:
        json.dump(all_settings, f, indent=2)
    return value
