"""
Oltin (XAU/USD) uchun signal tahlil qiluvchi Telegram bot.

Ishlash tartibi:
1. Har CHECK_EVERY_SECONDS da narx ma'lumotlarini oladi (Twelve Data).
2. Texnik indikatorlarni hisoblaydi (RSI, MACD, EMA20/50, Bollinger Bands, ATR).
3. Har bir indikatordan ovoz oladi, joriy og'irliklar bilan umumiy ballni hisoblaydi.
4. Agar ball SIGNAL_THRESHOLD dan oshsa (kuchli signal) va oldingi
   signaldan farqli bo'lsa — foydalanuvchilarga xabar yuboradi (kirish
   zonasi, Stop Loss va Take Profit bilan birga).
5. Har WEIGHT_UPDATE_EVERY_SECONDS da o'tmishdagi signallarning natijasini
   tekshirib, og'irliklarni moslashtiradi (oddiy "o'rganish" mexanizmi).
6. /settings buyrug'i orqali barcha asosiy sozlamalarni tugmalar bilan,
   kodga tegmasdan o'zgartirish mumkin — o'zgarish darhol kuchga kiradi.

Ishga tushirish:
    pip install -r requirements.txt
    cp .env.example .env   # va .env faylini o'zingizning tokenlaringiz bilan to'ldiring
    python main.py
"""
import logging
import time

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import config
import data_fetcher
import indicators
import signal_engine
import trade_planner
import weights_manager
import history_tracker
import chat_registry
import settings_manager
import ui_settings

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("gold_signal_bot")

# Har SCHEDULER_TICK_SECONDS da "hozir tahlil/og'irlik yangilash vaqti
# keldimi?" deb tekshiramiz. Bu sozlamalar (masalan tekshirish chastotasi)
# har safar botni qayta ishga tushirmasdan, /settings orqali o'zgarganda
# ham darhol qo'llanilishini ta'minlaydi.
SCHEDULER_TICK_SECONDS = 30

# Oxirgi yuborilgan qarorni saqlab turamiz, xuddi shu qaror qayta-qayta
# yuborilib, foydalanuvchini bezovta qilmasligi uchun.
_last_decision = {"decision": None}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_registry.add_chat_id(update.effective_chat.id)
    s = settings_manager.get_all()
    await update.message.reply_text(
        "Salom! Men Oltin/valyuta juftliklari uchun texnik tahlil botiman.\n\n"
        f"Kuzatilayotgan instrument: {s['SYMBOL']}\n"
        f"Sham intervali: {s['INTERVAL']}\n"
        f"Tekshirish chastotasi: har {s['CHECK_EVERY_SECONDS'] // 60} daqiqada\n\n"
        "Faqat KUCHLI signal chiqqanda sizga xabar yuboraman.\n\n"
        "/status — joriy holat va aniqlik statistikasini ko'rish\n"
        "/settings — sozlamalarni tugmalar orqali o'zgartirish"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    weights = weights_manager.load_weights()
    stats = history_tracker.get_stats()

    weights_text = "\n".join(f"  • {k}: {v:.2f}" for k, v in weights.items())
    stats_text = (
        f"Jami signallar: {stats['total_signals']}\n"
        f"Natijasi tekshirilgan: {stats['resolved']}\n"
    )
    if stats.get("accuracy") is not None:
        stats_text += f"Aniqlik: {stats['accuracy']}%"
    else:
        stats_text += "Aniqlik: hali yetarli ma'lumot yo'q"

    await update.message.reply_text(
        f"📊 Joriy indikator og'irliklari:\n{weights_text}\n\n"
        f"📈 Statistika:\n{stats_text}\n\n"
        f"Oxirgi qaror: {_last_decision['decision'] or 'hali yo`q'}\n\n"
        "Sozlamalarni o'zgartirish uchun /settings yozing."
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        ui_settings.format_settings_text(),
        reply_markup=ui_settings.build_settings_keyboard(),
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, key, value = query.data.split(":", 2)
    new_value = settings_manager.set(key, value)
    await query.answer(f"{key} -> {new_value} ga o'zgartirildi")
    await query.edit_message_text(
        ui_settings.format_settings_text(),
        reply_markup=ui_settings.build_settings_keyboard(),
    )


async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


async def close_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "⚙️ Sozlamalar yopildi. Qayta ochish uchun /settings yozing."
    )


def format_signal_message(decision: str, score: float, votes, price: float, candle_dt,
                           levels: trade_planner.TradeLevels, symbol: str, threshold: float) -> str:
    emoji = "🟢" if decision == "BUY" else "🔴"
    votes_lines = "\n".join(f"  • {name}: {v:+d}" for name, v in votes.as_dict().items())
    return (
        f"{emoji} KUCHLI SIGNAL: {decision}\n\n"
        f"Instrument: {symbol}\n"
        f"Joriy narx: {price:.2f}\n"
        f"Sham vaqti: {candle_dt}\n"
        f"Umumiy ball: {score:+.2f} (chegara: {threshold})\n\n"
        f"📍 Kirish zonasi: {levels.entry_low:.2f} — {levels.entry_high:.2f}\n"
        f"🛑 Stop Loss: {levels.stop_loss:.2f}\n"
        f"🎯 Take Profit: {levels.take_profit:.2f}\n"
        f"⚖️ Risk/Reward: 1:{levels.risk_reward_ratio:.1f}\n\n"
        f"Indikator ovozlari:\n{votes_lines}\n\n"
        "⚠️ Bu darajalar ATR (bozor volatilligi) asosida avtomatik hisoblangan "
        "texnik taxmin, kafolat emas. Har doim o'z risk-menejmentingizga "
        "va pozitsiya hajmingizga alohida e'tibor bering."
    )


async def analyze_market(context: ContextTypes.DEFAULT_TYPE):
    try:
        symbol = settings_manager.get("SYMBOL")
        interval = settings_manager.get("INTERVAL")
        threshold = settings_manager.get("SIGNAL_THRESHOLD")

        df = data_fetcher.fetch_ohlc(symbol=symbol, interval=interval)
        df = indicators.compute_indicators(df)
        df = df.dropna().reset_index(drop=True)

        if len(df) < 3:
            logger.warning("Yetarli ma'lumot yo'q, tekshiruv o'tkazib yuborildi.")
            return

        weights = weights_manager.load_weights()
        votes = signal_engine.compute_votes(df)
        score = signal_engine.weighted_score(votes, weights)
        decision = signal_engine.classify(score, threshold)

        last_row = df.iloc[-1]
        logger.info(
            "Tekshiruv (%s, %s): narx=%.2f ovozlar=%s ball=%.2f qaror=%s",
            symbol, interval, last_row["close"], votes.as_dict(), score, decision,
        )

        if decision != "NEUTRAL" and decision != _last_decision["decision"]:
            levels = trade_planner.compute_trade_levels(
                decision=decision, price=last_row["close"], atr=last_row["atr"]
            )

            history_tracker.log_signal(
                decision=decision,
                score=score,
                votes=votes.as_dict(),
                price=last_row["close"],
                candle_datetime=last_row["datetime"],
            )

            message = format_signal_message(
                decision, score, votes, last_row["close"], last_row["datetime"],
                levels, symbol, threshold,
            )
            chat_ids = chat_registry.load_chat_ids()
            for chat_id in chat_ids:
                await context.bot.send_message(chat_id=chat_id, text=message)

            _last_decision["decision"] = decision
        elif decision == "NEUTRAL":
            # Bozor "kutish" holatida bo'lsa, keyingi kuchli signal
            # qayta yuborilishi uchun holatni tozalaymiz.
            _last_decision["decision"] = None

    except Exception:
        logger.exception("analyze_market ichida xatolik yuz berdi")


async def update_weights_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        symbol = settings_manager.get("SYMBOL")
        interval = settings_manager.get("INTERVAL")

        df = data_fetcher.fetch_ohlc(symbol=symbol, interval=interval)
        df = indicators.compute_indicators(df).dropna().reset_index(drop=True)
        resolved = history_tracker.resolve_pending(
            df, lookahead_candles=config.OUTCOME_LOOKAHEAD_CANDLES
        )
        if resolved:
            new_weights = weights_manager.update_weights_from_outcomes(resolved)
            logger.info("Og'irliklar yangilandi: %s", new_weights)
    except Exception:
        logger.exception("update_weights_job ichida xatolik yuz berdi")


async def scheduler_tick(context: ContextTypes.DEFAULT_TYPE):
    """
    Har SCHEDULER_TICK_SECONDS da ishga tushadi va joriy sozlamalarga
    qarab, tahlil yoki og'irlik yangilash vaqti kelgan-kelmaganini tekshiradi.
    Shu tarzda /settings orqali chastota o'zgartirilsa, botni qayta ishga
    tushirmasdan darhol qo'llaniladi.
    """
    now = time.time()
    bot_data = context.application.bot_data

    check_every = settings_manager.get("CHECK_EVERY_SECONDS")
    last_analysis = bot_data.get("last_analysis_ts", 0)
    if now - last_analysis >= check_every:
        bot_data["last_analysis_ts"] = now
        await analyze_market(context)

    weight_every = settings_manager.get("WEIGHT_UPDATE_EVERY_SECONDS")
    last_weight_update = bot_data.get("last_weight_update_ts", 0)
    if now - last_weight_update >= weight_every:
        bot_data["last_weight_update_ts"] = now
        await update_weights_job(context)


def main():
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^set:"))
    application.add_handler(CallbackQueryHandler(close_settings_callback, pattern=r"^close$"))
    application.add_handler(CallbackQueryHandler(noop_callback, pattern=r"^noop$"))

    job_queue = application.job_queue
    job_queue.run_repeating(scheduler_tick, interval=SCHEDULER_TICK_SECONDS, first=5)

    logger.info("Bot ishga tushdi. Boshlang'ich sozlamalar: %s", settings_manager.get_all())
    application.run_polling()


if __name__ == "__main__":
    main()
