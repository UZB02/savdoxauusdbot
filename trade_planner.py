"""
ATR (Average True Range) asosida savdo darajalarini hisoblaydi:
- Kirish zonasi (entry zone)
- Stop Loss (xavfsiz yopish darajasi)
- Take Profit (maqsadli foyda darajasi)

Mantiq: ATR bozorning "o'rtacha kunlik/soatlik tebranish kengligini" ko'rsatadi.
Shuni asos qilib Stop Loss va Take Profit narxdan necha ATR uzoqlikda
qo'yilishini belgilaymiz. Bu bozor notinch bo'lganda darajalarni kengroq,
tinch bo'lganda torroq qilib avtomatik moslashtiradi.
"""
from dataclasses import dataclass
import config


@dataclass
class TradeLevels:
    decision: str
    entry_low: float
    entry_high: float
    stop_loss: float
    take_profit: float
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float


def compute_trade_levels(decision: str, price: float, atr: float) -> TradeLevels:
    """
    decision: "BUY" yoki "SELL"
    price: signal chiqqan paytdagi narx (oxirgi close)
    atr: shu paytdagi ATR (14) qiymati
    """
    entry_buffer = atr * config.ENTRY_ZONE_ATR_FRACTION
    sl_distance = atr * config.SL_ATR_MULTIPLIER
    tp_distance = atr * config.TP_ATR_MULTIPLIER

    entry_low = price - entry_buffer
    entry_high = price + entry_buffer

    if decision == "BUY":
        stop_loss = price - sl_distance
        take_profit = price + tp_distance
    else:  # SELL
        stop_loss = price + sl_distance
        take_profit = price - tp_distance

    risk_amount = sl_distance
    reward_amount = tp_distance
    rr_ratio = reward_amount / risk_amount if risk_amount > 0 else 0.0

    return TradeLevels(
        decision=decision,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_amount=risk_amount,
        reward_amount=reward_amount,
        risk_reward_ratio=rr_ratio,
    )
