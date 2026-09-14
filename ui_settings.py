"""
/settings buyrug'i uchun tugmali (inline keyboard) menyuni yasaydi.
Har bir sozlash guruhi o'z qatoridagi tugmalarga ega; joriy tanlangan
qiymat oldiga ✅ belgisi qo'yiladi.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import settings_manager

SYMBOL_OPTIONS = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
INTERVAL_OPTIONS = ["1min", "5min", "15min", "30min", "1h", "4h"]
CHECK_EVERY_OPTIONS = [
    (60, "1 daq"), (300, "5 daq"), (900, "15 daq"),
    (1800, "30 daq"), (3600, "1 soat"),
]
THRESHOLD_OPTIONS = [1.5, 2.0, 2.5, 3.0, 3.5]
SL_OPTIONS = [1.0, 1.5, 2.0, 2.5]
TP_OPTIONS = [2.0, 3.0, 4.0, 5.0]
SESSION_FILTER_OPTIONS = [(1, "🟢 Yoqilgan"), (0, "🔴 O'chirilgan")]


def _row(key, options_with_labels, current):
    buttons = []
    for value, label in options_with_labels:
        mark = "✅ " if str(value) == str(current) else ""
        buttons.append(
            InlineKeyboardButton(f"{mark}{label}", callback_data=f"set:{key}:{value}")
        )
    return buttons


def _header(text):
    return [InlineKeyboardButton(text, callback_data="noop")]


def build_settings_keyboard() -> InlineKeyboardMarkup:
    s = settings_manager.get_all()
    rows = [
        _header("— Instrument —"),
        _row("SYMBOL", [(v, v) for v in SYMBOL_OPTIONS], s["SYMBOL"]),

        _header("— Sham intervali —"),
        _row("INTERVAL", [(v, v) for v in INTERVAL_OPTIONS], s["INTERVAL"]),

        _header("— Tekshirish chastotasi —"),
        _row("CHECK_EVERY_SECONDS", CHECK_EVERY_OPTIONS, s["CHECK_EVERY_SECONDS"]),

        _header("— Signal chegarasi (kuchlilik) —"),
        _row("SIGNAL_THRESHOLD", [(v, str(v)) for v in THRESHOLD_OPTIONS], s["SIGNAL_THRESHOLD"]),

        _header("— Stop Loss (x ATR) —"),
        _row("SL_ATR_MULTIPLIER", [(v, str(v)) for v in SL_OPTIONS], s["SL_ATR_MULTIPLIER"]),

        _header("— Take Profit (x ATR) —"),
        _row("TP_ATR_MULTIPLIER", [(v, str(v)) for v in TP_OPTIONS], s["TP_ATR_MULTIPLIER"]),

        _header("— Sessiya filtri (07-21 UTC, past likvidlik soatlarida signal to'xtatiladi) —"),
        _row("SESSION_FILTER_ENABLED", SESSION_FILTER_OPTIONS, s["SESSION_FILTER_ENABLED"]),

        [InlineKeyboardButton("✅ Yopish", callback_data="close")],
    ]
    return InlineKeyboardMarkup(rows)


def format_settings_text() -> str:
    s = settings_manager.get_all()
    return (
        "⚙️ Bot sozlamalari\n\n"
        f"📊 Instrument: {s['SYMBOL']}\n"
        f"🕐 Sham intervali: {s['INTERVAL']}\n"
        f"🔄 Tekshirish chastotasi: {s['CHECK_EVERY_SECONDS']} soniya\n"
        f"🎯 Signal chegarasi: {s['SIGNAL_THRESHOLD']}\n"
        f"🛑 Stop Loss: {s['SL_ATR_MULTIPLIER']} x ATR\n"
        f"🏁 Take Profit: {s['TP_ATR_MULTIPLIER']} x ATR\n"
        f"🕰 Sessiya filtri: {'Yoqilgan' if s['SESSION_FILTER_ENABLED'] else 'O`chirilgan'} "
        f"({s['SESSION_START_HOUR_UTC']:02d}:00–{s['SESSION_END_HOUR_UTC']:02d}:00 UTC)\n\n"
        "Quyidagi tugmalar orqali o'zgartiring — darhol kuchga kiradi:"
    )
