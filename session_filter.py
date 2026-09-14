"""
Savdo faolligi past bo'lgan soatlarda signal chiqarishni to'xtatib
turadigan oddiy vaqt-asosli filtr.

Nega kerak: London (taxminan 07:00-16:00 UTC) va Nyu-York (taxminan
12:00-21:00 UTC) sessiyalari davomida oltin bozorida eng katta likvidlik
va eng ishonchli texnik harakatlar kuzatiladi. Ikkalasi ham yopiq bo'lgan
soatlarda (taxminan 21:00-07:00 UTC, sof Osiyo sessiyasi) narx harakati
ko'pincha tasodifiy "shovqin" bo'lib, texnik indikatorlar (RSI, MACD,
Bollinger) yolg'on signal berish ehtimoli oshadi.

MUHIM: bu yerdagi soatlar UTC bo'yicha. data_fetcher.py Twelve Data'dan
ma'lumotni har doim UTC formatida so'raydi (timezone=UTC), shuning uchun
DataFrame'dagi "datetime" ustuni ham UTC hisoblanadi — boshqa vaqt
mintaqasidagi ma'lumot bilan aralashtirmang.

Bu filtr ovoz (vote) qo'shmaydi — u faqat allaqachon chiqqan BUY/SELL
qarorini "hozir yubormaymiz" deb to'sib qo'yadigan darvoza (gate). Shu
sababli mavjud indikatorlar bilan bir xil narsani ikki marta hisoblash
xavfi yo'q.
"""
import settings_manager


def is_active_session(dt, enabled: bool = None, start_hour: int = None, end_hour: int = None) -> bool:
    """
    dt: pandas Timestamp yoki datetime (UTC bo'yicha bo'lishi kerak).

    enabled/start_hour/end_hour berilmasa (None), joriy /settings
    qiymatlari (settings_manager orqali) ishlatiladi — bot shu tarzda
    ishlaydi. Bu parametrlar backtest.py kabi skriptlarga aniq bir
    holatni (masalan "filtr o'chiq") majburlash imkonini beradi.
    """
    if enabled is None:
        enabled = bool(settings_manager.get("SESSION_FILTER_ENABLED"))
    if not enabled:
        return True

    if start_hour is None:
        start_hour = settings_manager.get("SESSION_START_HOUR_UTC")
    if end_hour is None:
        end_hour = settings_manager.get("SESSION_END_HOUR_UTC")

    hour = dt.hour
    if start_hour <= end_hour:
        return start_hour <= hour < end_hour
    # Masalan 22:00 dan ertalab 06:00 gacha kabi, kecha kesib o'tuvchi
    # oraliq uchun (hozirgi standart qiymatlarda bu holat yuzaga kelmaydi,
    # lekin kimdir /settings'ni shunday sozlasa ham to'g'ri ishlaydi).
    return hour >= start_hour or hour < end_hour
