"""
gold_signal_bot loyihasi uchun backtesting skripti.

MUHIM: bu skript botning HAQIQIY strategiya kodini ishlatadi
(indicators.py, signal_engine.py, trade_planner.py, weights_manager.py) —
ya'ni bot jonli ishlab signal chiqarayotganda ishlatadigan aynan shu
funksiyalar shu yerda ham chaqiriladi. Shuning uchun natijalar botning
haqiqiy xatti-harakatini aks ettiradi, alohida yozilgan "taxminiy" mantiq
emas.

Nima qiladi:
  1. Tarixiy sham (candle) ma'lumotini oladi — Twelve Data API orqali
     yoki --csv bilan bergan faylingizdan.
  2. Har bir sham uchun xuddi bot ishlatadigan ovoz+ball+qaror mantig'ini
     ketma-ket (faqat o'sha vaqtgacha bo'lgan ma'lumot bilan, kelajakni
     "ko'rmasdan") qo'llaydi.
  3. Har signal chiqqanda ATR asosidagi Stop Loss / Take Profit
     darajalarini hisoblaydi va keyingi shamlarda narx qaysi biriga
     birinchi tegishini simulyatsiya qiladi.
  4. Umumiy statistika (win rate, R-multiple, profit factor va h.k.) va
     har bir savdo bo'yicha batafsil CSV/JSON fayl chiqaradi.

Ishlatish misollari:
    python backtest.py
    python backtest.py --symbol XAU/USD --interval 15min --outputsize 5000
    python backtest.py --csv mening_narxlarim.csv
    python backtest.py --sweep-threshold 1.5,2.0,2.5,3.0,3.5
    python backtest.py --plot
    python backtest.py --compare-session-filter   # sessiya filtri yordam beryaptimi, yo'qmi — yonma-yon solishtiradi
    python backtest.py --session-filter off        # filtrni majburiy o'chirib sinash

CSV format (--csv bilan ishlatilganda), ustunlar (katta-kichik harf farqi
yo'q): datetime, open, high, low, close

Cheklov: agar bitta sham ichida ham Stop Loss, ham Take Profit narxi
tegilgan bo'lsa, shu sham ichida qaysi biri OLDIN sodir bo'lganini oddiy
OHLC ma'lumotidan bilib bo'lmaydi (buning uchun tick-darajasidagi
ma'lumot kerak). Bu skript bunday holatlarda ehtiyotkorlik bilan har
doim Stop Loss avval urilgan deb hisoblaydi (worst-case taxmin) — demak
haqiqiy natija bu yerda ko'rsatilganidan biroz yaxshiroq bo'lishi mumkin,
yomonroq emas.
"""
import argparse
import json
import os
import sys
from datetime import datetime

import pandas as pd

import config
import data_fetcher
import indicators
import signal_engine
import trade_planner
import weights_manager
import settings_manager
import session_filter

INDICATOR_NAMES = signal_engine.INDICATOR_NAMES


def parse_args():
    p = argparse.ArgumentParser(description="gold_signal_bot uchun backtesting skripti")
    p.add_argument("--symbol", default=None, help="Masalan XAU/USD (standart: botning hozirgi /settings qiymati)")
    p.add_argument("--interval", default=None, help="Masalan 15min, 1h (standart: botning hozirgi /settings qiymati)")
    p.add_argument("--outputsize", type=int, default=5000, help="Nechta tarixiy sham olish (Twelve Data limitiga bog'liq, standart 5000)")
    p.add_argument("--csv", default=None, help="Twelve Data o'rniga shu CSV fayldan (datetime,open,high,low,close ustunlari) o'qiydi")

    p.add_argument("--threshold", type=float, default=None, help="Signal chegarasi (standart: botning hozirgi /settings qiymati)")
    p.add_argument("--sweep-threshold", default=None, help="Vergul bilan ajratilgan bir nechta chegarani solishtirib chiqadi, masalan 1.5,2.0,2.5,3.0")

    p.add_argument("--sl-mult", type=float, default=None, help="Stop Loss = ATR * shu son (standart: botning hozirgi /settings qiymati)")
    p.add_argument("--tp-mult", type=float, default=None, help="Take Profit = ATR * shu son (standart: botning hozirgi /settings qiymati)")

    p.add_argument("--max-hold", type=int, default=200, help="Bitta savdo eng ko'p necha sham davomida ochiq turishi mumkin (0 = cheksiz, ma'lumot oxirigacha)")

    p.add_argument("--session-filter", choices=["auto", "on", "off"], default="auto",
                    help="Past likvidlik soatlarida signalni to'xtatuvchi filtr: "
                         "auto = botning hozirgi /settings qiymati, on/off = majburiy yoqish/o'chirish")
    p.add_argument("--compare-session-filter", action="store_true",
                    help="Bir xil ma'lumot/sozlamalarda sessiya filtri YOQILGAN va O'CHIRILGAN holatlarini yonma-yon solishtiradi")
    p.add_argument("--equal-weights", action="store_true", help="weights.json dagi o'rgangan og'irliklar o'rniga barcha indikatorlarga teng (1.0) og'irlik beradi")
    p.add_argument("--weights-file", default=None, help="Boshqa weights.json fayl yo'li (standart: loyihadagi data/weights.json)")

    p.add_argument("--out-dir", default="backtest_results", help="Natijalar shu papkaga saqlanadi")
    p.add_argument("--plot", action="store_true", help="Equity curve grafigini PNG sifatida chizadi (matplotlib kerak)")
    return p.parse_args()


def load_price_data(args) -> pd.DataFrame:
    if args.csv:
        df = pd.read_csv(args.csv)
        df.columns = [c.strip().lower() for c in df.columns]
        required = {"datetime", "open", "high", "low", "close"}
        missing = required - set(df.columns)
        if missing:
            raise SystemExit(f"CSV faylda quyidagi ustunlar yetishmayapti: {missing}")
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime").reset_index(drop=True)
        return df

    symbol = args.symbol or settings_manager.get("SYMBOL")
    interval = args.interval or settings_manager.get("INTERVAL")
    print(f"Twelve Data'dan yuklanmoqda: {symbol} / {interval} / outputsize={args.outputsize} ...")
    return data_fetcher.fetch_ohlc(symbol=symbol, interval=interval, outputsize=args.outputsize)


def load_weights(args) -> dict:
    if args.equal_weights:
        return {name: 1.0 for name in INDICATOR_NAMES}
    if args.weights_file:
        with open(args.weights_file) as f:
            return json.load(f)
    return weights_manager.load_weights()


def _votes_at(df: pd.DataFrame, i: int) -> signal_engine.Votes:
    """signal_engine.compute_votes bilan bir xil natija beradi, lekin faqat
    i-1 va i qatorlaridan foydalanadi (kelajak ma'lumotidan foydalanmaydi)."""
    window = df.iloc[i - 1:i + 1].reset_index(drop=True)
    return signal_engine.compute_votes(window)


def _simulate_trade(df: pd.DataFrame, signal_idx: int, decision: str,
                     levels: trade_planner.TradeLevels, max_hold: int) -> dict:
    n = len(df)
    end = n if not max_hold else min(signal_idx + 1 + max_hold, n)
    risk = levels.risk_amount

    for j in range(signal_idx + 1, end):
        bar = df.iloc[j]
        hi, lo = bar["high"], bar["low"]

        if decision == "BUY":
            hit_sl = lo <= levels.stop_loss
            hit_tp = hi >= levels.take_profit
        else:
            hit_sl = hi >= levels.stop_loss
            hit_tp = lo <= levels.take_profit

        # Ikkalasi ham bir shamda tegilgan bo'lsa, SL avval bo'lgan deb
        # hisoblaymiz (worst-case, yuqoridagi cheklovga qarang).
        if hit_sl:
            return {"exit_reason": "SL", "exit_datetime": str(bar["datetime"]),
                     "exit_price": levels.stop_loss, "bars_held": j - signal_idx,
                     "r_multiple": -1.0}
        if hit_tp:
            return {"exit_reason": "TP", "exit_datetime": str(bar["datetime"]),
                     "exit_price": levels.take_profit, "bars_held": j - signal_idx,
                     "r_multiple": round(levels.risk_reward_ratio, 4)}

    # Belgilangan muddatda na SL, na TP urilmadi -> oxirgi mavjud narxda
    # "vaqt tugadi" (timeout) sifatida yopamiz.
    if end - 1 <= signal_idx:
        return {"exit_reason": "NO_DATA", "exit_datetime": None,
                 "exit_price": None, "bars_held": 0, "r_multiple": 0.0}

    last_bar = df.iloc[end - 1]
    entry_price = df.iloc[signal_idx]["close"]
    if decision == "BUY":
        pnl = last_bar["close"] - entry_price
    else:
        pnl = entry_price - last_bar["close"]
    r_multiple = pnl / risk if risk > 0 else 0.0
    return {"exit_reason": "TIMEOUT", "exit_datetime": str(last_bar["datetime"]),
             "exit_price": last_bar["close"], "bars_held": end - 1 - signal_idx,
             "r_multiple": round(r_multiple, 4)}


def simulate(df: pd.DataFrame, weights: dict, threshold: float, max_hold: int,
             sl_mult: float = None, tp_mult: float = None, entry_fraction: float = None,
             session_enabled: bool = None, session_start: int = None, session_end: int = None) -> list:
    trades = []
    last_decision = None
    n = len(df)
    skipped_by_session = 0

    for i in range(1, n - 1):
        row = df.iloc[i]
        atr = row.get("atr")
        if pd.isna(atr) or atr is None or atr <= 0:
            continue

        votes = _votes_at(df, i)
        score = signal_engine.weighted_score(votes, weights)
        decision = signal_engine.classify(score, threshold)

        if decision == "NEUTRAL":
            # main.py dagi kabi: NEUTRAL kelsa, keyingi kuchli signal
            # (hatto avvalgisi bilan bir xil bo'lsa ham) qayta yuboriladi.
            last_decision = None
            continue
        if decision == last_decision:
            continue

        if not session_filter.is_active_session(
            row["datetime"], enabled=session_enabled, start_hour=session_start, end_hour=session_end
        ):
            # main.py dagi kabi: last_decision ATAYLAB o'zgartirilmaydi,
            # shunda faol sessiya boshlanganda hamon shu qaror turgan
            # bo'lsa, u holda darhol hisobga olinadi.
            skipped_by_session += 1
            continue
        last_decision = decision

        levels = trade_planner.compute_trade_levels(
            decision=decision, price=row["close"], atr=atr,
            sl_mult=sl_mult, tp_mult=tp_mult, entry_fraction=entry_fraction,
        )
        outcome = _simulate_trade(df, i, decision, levels, max_hold)

        trades.append({
            "signal_datetime": str(row["datetime"]),
            "decision": decision,
            "score": round(float(score), 3),
            **{f"vote_{k}": v for k, v in votes.as_dict().items()},
            "entry_price": round(float(row["close"]), 4),
            "stop_loss": round(levels.stop_loss, 4),
            "take_profit": round(levels.take_profit, 4),
            "risk_reward_planned": round(levels.risk_reward_ratio, 2),
            **outcome,
        })

    return trades, skipped_by_session


def summarize(trades: list, skipped_by_session: int = 0) -> dict:
    if not trades:
        return {"total_trades": 0, "skipped_by_session": skipped_by_session}

    df = pd.DataFrame(trades)
    resolved = df[df["exit_reason"].isin(["SL", "TP", "TIMEOUT"])]
    wins = resolved[resolved["r_multiple"] > 0]
    losses = resolved[resolved["r_multiple"] <= 0]

    total_r = resolved["r_multiple"].sum()
    gross_win = wins["r_multiple"].sum()
    gross_loss = abs(losses["r_multiple"].sum())

    # Maksimal drawdown (R birligida), kumulyativ ketma-ketlik bo'yicha.
    cum = resolved["r_multiple"].cumsum()
    running_max = cum.cummax()
    drawdown = cum - running_max
    max_dd = drawdown.min() if len(drawdown) else 0.0

    by_decision = {}
    for dec in ["BUY", "SELL"]:
        sub = resolved[resolved["decision"] == dec]
        if len(sub):
            w = sub[sub["r_multiple"] > 0]
            by_decision[dec] = {
                "count": int(len(sub)),
                "win_rate_pct": round(len(w) / len(sub) * 100, 1),
                "total_r": round(float(sub["r_multiple"].sum()), 2),
            }

    indicator_breakdown = {}
    for name in INDICATOR_NAMES:
        col = f"vote_{name}"
        agreeing = resolved[resolved[col] != 0]
        if len(agreeing):
            w = agreeing[agreeing["r_multiple"] > 0]
            indicator_breakdown[name] = {
                "signals_voted_nonzero": int(len(agreeing)),
                "win_rate_when_voted_pct": round(len(w) / len(agreeing) * 100, 1),
            }

    return {
        "total_trades": int(len(df)),
        "resolved_trades": int(len(resolved)),
        "sl_hits": int((resolved["exit_reason"] == "SL").sum()),
        "tp_hits": int((resolved["exit_reason"] == "TP").sum()),
        "timeouts": int((resolved["exit_reason"] == "TIMEOUT").sum()),
        "win_rate_pct": round(len(wins) / len(resolved) * 100, 1) if len(resolved) else None,
        "total_r_multiple": round(float(total_r), 2),
        "avg_r_multiple": round(float(resolved["r_multiple"].mean()), 3) if len(resolved) else None,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
        "max_drawdown_r": round(float(max_dd), 2),
        "skipped_by_session": skipped_by_session,
        "by_decision": by_decision,
        "indicator_breakdown": indicator_breakdown,
    }


def print_summary(label: str, summary: dict):
    print(f"\n=== {label} ===")
    if summary.get("total_trades", 0) == 0:
        print("  Signal chiqmadi (berilgan ma'lumot/sozlamalar bilan).")
        return
    print(f"  Jami signallar     : {summary['total_trades']} (hal bo'lgan: {summary['resolved_trades']})")
    print(f"  TP / SL / Timeout  : {summary['tp_hits']} / {summary['sl_hits']} / {summary['timeouts']}")
    print(f"  Win rate           : {summary['win_rate_pct']}%")
    print(f"  Jami R             : {summary['total_r_multiple']}")
    print(f"  O'rtacha R / savdo : {summary['avg_r_multiple']}")
    print(f"  Profit factor      : {summary['profit_factor']}")
    print(f"  Max drawdown (R)   : {summary['max_drawdown_r']}")
    if summary.get("skipped_by_session"):
        print(f"  Sessiya filtri tufayli o'tkazib yuborilgan signallar: {summary['skipped_by_session']}")
    if summary.get("by_decision"):
        for dec, s in summary["by_decision"].items():
            print(f"    {dec}: {s['count']} ta, win rate {s['win_rate_pct']}%, jami R {s['total_r']}")
    if summary.get("indicator_breakdown"):
        print("  Indikatorlar (ovoz bergan hollarda win rate):")
        for name, s in summary["indicator_breakdown"].items():
            print(f"    {name}: {s['signals_voted_nonzero']} marta ovoz berdi, win rate {s['win_rate_when_voted_pct']}%")


def maybe_plot(trades: list, out_path: str):
    if not trades:
        return
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib o'rnatilmagan, --plot o'tkazib yuborildi: pip install matplotlib)")
        return

    df = pd.DataFrame(trades)
    resolved = df[df["exit_reason"].isin(["SL", "TP", "TIMEOUT"])].reset_index(drop=True)
    if resolved.empty:
        return
    cum_r = resolved["r_multiple"].cumsum()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range(1, len(cum_r) + 1), cum_r, marker="o", markersize=3)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_xlabel("Savdo tartib raqami")
    ax.set_ylabel("Kumulyativ R-multiple")
    ax.set_title("Equity curve (R birligida)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"Equity curve grafigi saqlandi: {out_path}")


def run_once(df: pd.DataFrame, weights: dict, threshold: float, max_hold: int, label: str,
             sl_mult: float = None, tp_mult: float = None, entry_fraction: float = None,
             session_enabled: bool = None, session_start: int = None, session_end: int = None):
    trades, skipped = simulate(df, weights, threshold, max_hold, sl_mult, tp_mult, entry_fraction,
                                session_enabled, session_start, session_end)
    summary = summarize(trades, skipped)
    print_summary(label, summary)
    return trades, summary


def main():
    args = parse_args()

    # sl_mult/tp_mult berilmasa, botning HOZIRGI /settings qiymati ishlatiladi
    # (settings_manager orqali) — bir marta shu yerda "muzlatib" olamiz, shunda
    # butun backtest davomida (agar kimdir shu paytda /settings orqali
    # o'zgartirsa ham) bir xil qiymat bilan ishlaydi.
    sl_mult = args.sl_mult if args.sl_mult is not None else settings_manager.get("SL_ATR_MULTIPLIER")
    tp_mult = args.tp_mult if args.tp_mult is not None else settings_manager.get("TP_ATR_MULTIPLIER")
    entry_fraction = settings_manager.get("ENTRY_ZONE_ATR_FRACTION")

    if args.session_filter == "on":
        session_enabled = True
    elif args.session_filter == "off":
        session_enabled = False
    else:
        session_enabled = bool(settings_manager.get("SESSION_FILTER_ENABLED"))
    session_start = settings_manager.get("SESSION_START_HOUR_UTC")
    session_end = settings_manager.get("SESSION_END_HOUR_UTC")

    raw_df = load_price_data(args)
    print(f"{len(raw_df)} ta sham yuklandi ({raw_df['datetime'].min()} — {raw_df['datetime'].max()})")

    df = indicators.compute_indicators(raw_df)
    df = df.dropna().reset_index(drop=True)
    print(f"Indikatorlar hisoblangach: {len(df)} ta sham qoldi (dastlabki NaN qatorlar olib tashlandi)")

    if len(df) < 10:
        raise SystemExit("Yetarli ma'lumot yo'q. --outputsize ni oshiring yoki boshqa interval tanlang.")

    weights = load_weights(args)
    print(f"Ishlatilayotgan og'irliklar: {weights}")

    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    threshold = args.threshold if args.threshold is not None else settings_manager.get("SIGNAL_THRESHOLD")

    if args.compare_session_filter:
        rows = []
        for label, enabled in [("sessiya filtri O'CHIQ", False), ("sessiya filtri YOQIQ", True)]:
            trades, summary = run_once(df, weights, threshold, args.max_hold, label,
                                        sl_mult, tp_mult, entry_fraction,
                                        enabled, session_start, session_end)
            rows.append({"session_filter": enabled, **{k: v for k, v in summary.items()
                                                         if k not in ("by_decision", "indicator_breakdown")}})
        compare_path = os.path.join(args.out_dir, f"{ts}_session_filter_compare.csv")
        pd.DataFrame(rows).to_csv(compare_path, index=False)
        print(f"\nSolishtirish jadvali saqlandi: {compare_path}")
        print("Diqqat: win rate/R farqi shu ma'lumot to'plamiga xos — xulosa chiqarishdan oldin "
              "yetarlicha uzun (kamida bir necha oylik) HAQIQIY tarixiy ma'lumotda tekshiring.")
        return

    if args.sweep_threshold:
        thresholds = [float(x) for x in args.sweep_threshold.split(",")]
        sweep_rows = []
        for th in thresholds:
            trades, summary = run_once(df, weights, th, args.max_hold, f"threshold={th}",
                                        sl_mult, tp_mult, entry_fraction,
                                        session_enabled, session_start, session_end)
            sweep_rows.append({"threshold": th, **{k: v for k, v in summary.items()
                                                     if k not in ("by_decision", "indicator_breakdown")}})
        sweep_path = os.path.join(args.out_dir, f"{ts}_threshold_sweep.csv")
        pd.DataFrame(sweep_rows).to_csv(sweep_path, index=False)
        print(f"\nChegaralarni solishtirish jadvali saqlandi: {sweep_path}")
        return

    trades, summary = run_once(df, weights, threshold, args.max_hold, f"threshold={threshold}",
                                sl_mult, tp_mult, entry_fraction,
                                session_enabled, session_start, session_end)

    trades_path = os.path.join(args.out_dir, f"{ts}_trades.csv")
    summary_path = os.path.join(args.out_dir, f"{ts}_summary.json")

    pd.DataFrame(trades).to_csv(trades_path, index=False)
    with open(summary_path, "w") as f:
        json.dump({
            "run_at": ts,
            "symbol": args.symbol or settings_manager.get("SYMBOL"),
            "interval": args.interval or settings_manager.get("INTERVAL"),
            "threshold": threshold,
            "sl_mult": sl_mult,
            "tp_mult": tp_mult,
            "entry_zone_fraction": entry_fraction,
            "session_filter_enabled": session_enabled,
            "session_hours_utc": [session_start, session_end],
            "max_hold": args.max_hold,
            "weights": weights,
            "summary": summary,
        }, f, indent=2, default=str)

    print(f"\nBatafsil savdolar: {trades_path}")
    print(f"Xulosa (JSON)     : {summary_path}")

    if args.plot:
        plot_path = os.path.join(args.out_dir, f"{ts}_equity.png")
        maybe_plot(trades, plot_path)


if __name__ == "__main__":
    main()
