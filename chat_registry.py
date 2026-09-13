"""
/start bosgan foydalanuvchilarning chat_id larini saqlaydi, shunda
signal chiqqanda hammaga xabar yuborish mumkin bo'ladi.
"""
import json
import os
import config


def load_chat_ids() -> set:
    if os.path.exists(config.CHAT_IDS_FILE):
        with open(config.CHAT_IDS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def add_chat_id(chat_id: int):
    ids = load_chat_ids()
    ids.add(chat_id)
    with open(config.CHAT_IDS_FILE, "w") as f:
        json.dump(list(ids), f)
