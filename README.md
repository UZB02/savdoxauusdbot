# Oltin (XAU/USD) Signal Tahlil Boti

Telegram orqali XAU/USD (Oltin/Dollar) uchun texnik tahlil qiladigan va
faqat **kuchli** BUY/SELL signal chiqqanda xabar beradigan bot.

## ⚠️ Muhim ogohlantirish

Bu bot faqat texnik indikatorlar asosida yordamchi tahlil beradi.
U moliyaviy maslahat emas va foyda kafolatlamaydi. Yakuniy savdo
qarorini har doim o'zingiz, risk-menejmentingizga amal qilgan holda
qabul qiling.

## Qanday ishlaydi

1. **Narx ma'lumoti**: [Twelve Data](https://twelvedata.com) API orqali
   XAU/USD narxlari olinadi (bepul tarif kuniga 800 so'rovga yetadi).
2. **Indikatorlar**: RSI, MACD (crossover), EMA20/EMA50 trend, Bollinger
   Bands — har biri +1 (BUY tarafda), -1 (SELL tarafda) yoki 0 (neytral)
   ovoz beradi.
3. **Umumiy ball**: ovozlar og'irliklar bilan qo'shiladi. Ball
   `SIGNAL_THRESHOLD` dan oshsa — signal "kuchli" hisoblanadi va sizga
   yuboriladi.
4. **O'rganish**: har bir yuborilgan signal keyinchalik narx qanday
   harakat qilganiga qarab "to'g'ri/noto'g'ri" deb belgilanadi. Shunga
   asosan har bir indikatorning og'irligi asta-sekin o'zgaradi — ko'p
   to'g'ri chiqqan indikator kelajakda ko'proq ta'sir qiladi.

Bu — oddiy, tushunarli, o'zingiz nazorat qila oladigan adaptiv tizim.
To'liq "AI" yoki neyron tarmoq emas, lekin real ishlaydigan va
kengaytirish mumkin bo'lgan matematik asos.

## O'rnatish

1. Python 3.10+ o'rnatilgan bo'lishi kerak.
2. Kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```
3. Telegram bot yarating: [@BotFather](https://t.me/BotFather) ga yozib,
   `/newbot` buyrug'i bilan token oling.
4. [twelvedata.com](https://twelvedata.com) da ro'yxatdan o'ting va
   bepul API key oling.
5. `.env.example` faylini `.env` nomiga nusxalang va o'z
   token/key larni kiriting:
   ```bash
   cp .env.example .env
   nano .env
   ```
6. Botni ishga tushiring:
   ```bash
   python main.py
   ```
7. Telegram'da botingizga `/start` yozing — shundan keyin sizga
   signallar kela boshlaydi.

## Buyruqlar

- `/start` — botni faollashtirish va xabar olishni boshlash
- `/status` — joriy indikator og'irliklari va aniqlik statistikasi
- `/settings` — **barcha asosiy sozlamalarni tugmalar orqali o'zgartirish** (instrument, sham intervali, tekshirish chastotasi, signal chegarasi, Stop Loss/Take Profit koeffitsientlari). O'zgarish darhol kuchga kiradi, .env faylini tahrirlash yoki botni qayta ishga tushirish shart emas.

## Sozlash (.env fayl)

| O'zgaruvchi | Tavsif |
|---|---|
| `SYMBOL` | Kuzatiladigan instrument (masalan `XAU/USD`, `EUR/USD`) |
| `INTERVAL` | Sham intervali: `1min`, `5min`, `15min`, `1h`, `4h`, `1day` |
| `CHECK_EVERY_SECONDS` | Necha soniyada bozor tekshirilsin |
| `SIGNAL_THRESHOLD` | Signal "kuchli" deb hisoblanishi uchun minimal ball |
| `OUTCOME_LOOKAHEAD_CANDLES` | Signal natijasi necha sham keyin tekshirilsin |
| `WEIGHT_UPDATE_EVERY_SECONDS` | Og'irliklar qayta hisoblanish oralig'i |

## Doimiy ishlashi uchun (production)

Bot uzluksiz ishlashi kerak bo'lsa, quyidagilardan birini tanlang:

- **O'z kompyuteringiz**: `tmux`/`screen` yoki `nohup python main.py &`
  bilan fonda ishga tushiring.
- **Server/VPS**: `systemd` service yoki Docker konteyner sifatida
  ishga tushiring.
- **Bulutli xizmat**: Render, Railway, Fly.io kabi xizmatlarga "worker"
  sifatida joylashtiring (bu doimiy ishlaydigan process talab qiladi,
  chunki bot polling orqali ishlaydi).

Xohlasangiz, keyingi qadamda shulardan birini sozlab beraman —
masalan Docker fayl yoki systemd service fayli tayyorlab beraman.

## Oracle Cloud serverga joylashtirish (bosqichma-bosqich)

VM tayyor bo'lgach (Ubuntu 22.04, Public IP qo'lda), quyidagilarni bajaring:

### 1. Serverga ulanish

```bash
chmod 600 /path/to/ssh-key.key
ssh -i /path/to/ssh-key.key ubuntu@SIZNING_PUBLIC_IP
```

### 2. Kerakli dasturlarni o'rnatish

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git
```

### 3. Loyihani serverga yuklash

Loyiha GitHub'da joylashgan (https://github.com/UZB02/savdoxauusdbot), shuning
uchun kompyuteringizdan fayl ko'chirish (`scp`) shart emas — to'g'ridan-to'g'ri
server terminalida yuklab oling:

```bash
git clone https://github.com/UZB02/savdoxauusdbot.git gold_signal_bot
cd gold_signal_bot
```

> Eslatma: `git clone` `.env`, `data/` kabi lokal (gitignore qilingan) fayllarni
> olib kelmaydi — bu aynan kerakli holat, chunki serverda `.env` alohida
> to'ldiriladi (5-qadam) va `data/` bot birinchi marta ishga tushganda
> avtomatik yaratiladi.

### 4. Serverda kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt --break-system-packages
```

### 5. `.env` faylini sozlash

```bash
cp .env.example .env
nano .env
```

Token va API key larni kiriting, `Ctrl+O` (saqlash), `Ctrl+X` (chiqish).

### 6. Botni doimiy xizmat (systemd service) sifatida ishga tushirish

```bash
sudo cp deploy/gold-signal-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gold-signal-bot
sudo systemctl start gold-signal-bot
```

### 7. Holatini tekshirish

```bash
sudo systemctl status gold-signal-bot
journalctl -u gold-signal-bot -f
```

`journalctl -u gold-signal-bot -f` — bu botning jonli loglarini (live logs) ko'rsatadi, `Ctrl+C` bilan chiqasiz (bot to'xtamaydi, faqat log ko'rish rejimidan chiqasiz).

Shu bilan bot serverda 24/7 ishlaydi — kompyuteringizni o'chirsangiz ham, hatto server qayta yuklansa ham (masalan yangilanish tufayli) bot avtomatik qayta ishga tushadi.

### Botni yangilash kerak bo'lsa

Kodga o'zgartirish kiritib, GitHub'ga push qilgach, serverda:

```bash
cd /home/ubuntu/gold_signal_bot
git pull
sudo systemctl restart gold-signal-bot
```

## Zaxira variant: Google Cloud (agar Oracle "joy yo'q" xatosi bersa)

Oracle Cloud'da Ampere/ARM shape'lar ba'zan mavjud bo'lmasligi mumkin. Bunday holda Google Cloud'ning bepul `e2-micro` instansiyasidan foydalaning (faqat ma'lum AQSh regionlarida to'liq bepul: `us-west1`, `us-central1`, `us-east1`).

### 1. Hisob va loyiha yaratish

1. https://console.cloud.google.com ga kiring, Google hisobingiz bilan ro'yxatdan o'ting (karta so'ralishi mumkin, tasdiqlash uchun).
2. Yangi loyiha (project) yarating.

### 2. VM yaratish

1. Chap menyudan **Compute Engine → VM instances → Create Instance**.
2. **Region**: `us-central1` (yoki `us-west1`, `us-east1`) tanlang — bepul limit shu hududlarda ishlaydi.
3. **Machine type**: `e2-micro` tanlang.
4. **Boot disk**: Ubuntu 22.04 LTS, 30GB (standart bepul limit ichida).
5. **Firewall**: hech narsani belgilash shart emas (bot faqat tashqariga so'rov yuboradi, ichkariga emas).
6. **Create** tugmasini bosing.

### 3. Serverga ulanish

VM ro'yxatida yangi instansiya qatorida **SSH** tugmasini bosing — brauzer orqali to'g'ridan-to'g'ri terminal ochiladi (alohida SSH kalit tashish shart emas).

### 4. Botni joylashtirish

Brauzer SSH oynasida:

```bash
sudo apt update
sudo apt install -y python3-pip git
git clone https://github.com/UZB02/savdoxauusdbot.git gold_signal_bot
cd gold_signal_bot
pip install -r requirements.txt --break-system-packages
cp .env.example .env
nano .env    # token va key larni kiriting, Ctrl+O va Ctrl+X bilan saqlang
```

### 5. Doimiy xizmat sifatida ishga tushirish

```bash
sudo cp deploy/gold-signal-bot.service /etc/systemd/system/
sudo sed -i 's/ubuntu/YOUR_GCP_USERNAME/g' /etc/systemd/system/gold-signal-bot.service
sudo systemctl daemon-reload
sudo systemctl enable gold-signal-bot
sudo systemctl start gold-signal-bot
sudo systemctl status gold-signal-bot
```

> **Eslatma**: Google Cloud SSH orqali kirganda foydalanuvchi nomingiz `ubuntu` bo'lmasligi mumkin (odatda Google hisobingiz nomiga o'xshash). `whoami` buyrug'i bilan aniqlab, `gold-signal-bot.service` faylidagi `User=` va papka yo'llarini shunga moslang.

## Kengaytirish g'oyalari

- Ko'proq indikator qo'shish (Stochastic, ADX, Ichimoku)
- Bir nechta timeframe'ni birlashtirib tahlil qilish (masalan 15min + 1h)
- Backtesting skripti yozib, strategiyani tarixiy ma'lumotda sinash
- Signal tarixini Excel/Google Sheets ga eksport qilish
# savdoxauusdbot
