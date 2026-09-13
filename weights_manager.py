"""
Har bir indikatorning og'irligini (weight) saqlaydi va o'tmishdagi signal
natijalariga (to'g'ri/noto'g'ri chiqqanligiga) qarab moslashtiradi.

Bu — foydalanuvchi so'ragan "signallar orasidagi matematik algoritmni
o'rganish" qismining oddiy, tushunarli implementatsiyasi: agar biror
indikator ko'pincha to'g'ri bashorat qilsa, uning og'irligi asta-sekin
oshadi; agar ko'p xato qilsa — kamayadi.
"""
import json
import os
import config
from signal_engine import INDICATOR_NAMES

LEARNING_RATE = 0.05
MIN_WEIGHT = 0.2
MAX_WEIGHT = 2.0


def load_weights() -> dict:
    if os.path.exists(config.WEIGHTS_FILE):
        with open(config.WEIGHTS_FILE, "r") as f:
            return json.load(f)
    return {name: 1.0 for name in INDICATOR_NAMES}


def save_weights(weights: dict):
    with open(config.WEIGHTS_FILE, "w") as f:
        json.dump(weights, f, indent=2)


def update_weights_from_outcomes(resolved_entries: list) -> dict:
    """
    resolved_entries: history_tracker dagi hal qilingan (outcome aniqlangan)
    yozuvlar ro'yxati. Har biri {"votes": {...}, "outcome": "BUY"/"SELL"/"FLAT"} shaklida.
    Har bir indikator o'z ovozi yakuniy natija bilan mos kelsa mukofotlanadi,
    mos kelmasa jarima olinadi. Keyin og'irliklar MIN/MAX oralig'ida ushlab turiladi.
    """
    weights = load_weights()

    for entry in resolved_entries:
        outcome = entry["outcome"]
        if outcome == "FLAT":
            continue
        outcome_sign = 1 if outcome == "BUY" else -1

        for name in INDICATOR_NAMES:
            vote = entry["votes"].get(name, 0)
            if vote == 0:
                continue
            if vote == outcome_sign:
                weights[name] = min(MAX_WEIGHT, weights[name] + LEARNING_RATE)
            else:
                weights[name] = max(MIN_WEIGHT, weights[name] - LEARNING_RATE)

    save_weights(weights)
    return weights
