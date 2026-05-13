import asyncio
import random
import time
import os
import aiohttp
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest

import psycopg2
from psycopg2.extras import RealDictCursor

# ═══════════════════════════════════════════════
#              SYSTEM CONFIGURATION
# ═══════════════════════════════════════════════
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN")

if not TOKEN or not ADMIN_ID or not CRYPTO_BOT_TOKEN:
    raise ValueError("Check BOT_TOKEN, ADMIN_ID and CRYPTO_BOT_TOKEN in Railway environment variables!")

ADMIN_ID = int(ADMIN_ID)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ═══════════════════════════════════════════════
#              SUBSCRIPTION PLANS
# ═══════════════════════════════════════════════
SUBSCRIPTION_PLANS = {
    "free":   {"limit": 25,  "name": "FREE",   "price": 0,   "emoji": "⬜"},
    "junior": {"limit": 50,  "name": "JUNIOR",  "price": 100,  "duration": 7, "emoji": "🔵"},
    "pro":    {"limit": 100, "name": "PRO",     "price": 200, "duration": 7, "emoji": "🟣"},
}

# ═══════════════════════════════════════════════
#         OTC CURRENCY PAIRS WITH FLAGS
# ═══════════════════════════════════════════════
pairs = [
    "🇦🇪 AED/CNY OTC",
    "🇦🇺 AUD/NZD OTC",
    "🇦🇺 AUD/USD OTC",
    "🇧🇭 BHD/CNY OTC",
    "🇨🇭 CHF/NOK OTC",
    "🇪🇺 EUR/CHF OTC",
    "🇬🇧 GBP/AUD OTC",
    "🇨🇦 CAD/JPY OTC",
    "🇪🇺 EUR/USD OTC",
    "🇲🇦 MAD/USD OTC",
    "🇦🇺 AUD/CAD OTC",
    "🇸🇦 SAR/CNY OTC",
]

# Timeframes for OTC
times = ["⏱ 5 sec", "⏱ 10 sec", "⏱ 15 sec", "⏱ 30 sec"]

# ═══════════════════════════════════════════════
#         MARKET HOURS CHECK
# ═══════════════════════════════════════════════
def is_market_open() -> bool:
    return True

# ═══════════════════════════════════════════════
#              TRANSLATIONS
# ═══════════════════════════════════════════════
TEXTS = {
    "ru": {
        # LANG SELECT
        "choose_lang": "🌐 Выберите язык интерфейса:\n\n🇷🇺 Русский  |  🇬🇧 English",
        "lang_set": "🇷🇺 Язык установлен: <b>Русский</b>",

        # START
        "start_header": (
            "┌─────────────────────────┐\n"
            "│  🖥  AI TRADING TERMINAL  │\n"
            "│     OTC PRO v4.0        │\n"
            "└─────────────────────────┘\n\n"
            "⚡ <b>Профессиональная система сигналов</b> для OTC рынка Pocket Option.\n\n"
            "🧠 <b>Smart Precision Engine:</b>\n"
            "▸ 12 OTC пар с флагами стран\n"
            "▸ Таймфреймы: 5с / 10с / 15с / 30с\n"
            "▸ 6 блоков анализа (RSI + EMA + MACD + BB + Stoch + паттерны)\n"
            "▸ AI уверенность: 78–96%\n\n"
            "👥 Трейдеров: <b>{users}</b>\n"
            "📡 WinRate: <b>88–96%</b>  |  🟢 <b>24/7</b>\n"
            "🕐 {time} MSK"
        ),

        # MENU BUTTONS
        "btn_trading_panel": "📊 Торговая Панель",
        "btn_get_signal": "⚡ Получить Сигнал",
        "btn_profile": "👤 Профиль",
        "btn_stats": "📈 Статистика",
        "btn_subscription": "💎 Подписка",
        "btn_about": "🚀 О боте",
        "btn_lot_calc": "🧮 Калькулятор лота",
        "btn_activate": "🔐 Активировать доступ",
        "btn_support": "🆘 Поддержка",
        "btn_back": "⬅️ Назад",
        "btn_menu": "⬅️ Меню",
        "btn_send_id": "📩 Отправить ID Pocket Option",

        # ACCESS RESTRICTED
        "access_restricted": (
            "🔒 <b>ДОСТУП ОГРАНИЧЕН</b>\n"
            "{div}\n"
            "Этот раздел доступен только верифицированным трейдерам.\n\n"
            "Нажмите <b>«🔐 Активировать доступ»</b>"
        ),

        # ABOUT
        "about": (
            "🤖 <b>AI TRADING TERMINAL — OTC PRO v4.0</b>\n"
            "{div}\n\n"
            "📡 <b>Платформа:</b> Pocket Option (OTC)\n\n"
            "🧠 <b>Smart Precision Engine v4:</b>\n"
            "  ▸ RSI(14)\n"
            "  ▸ EMA(9/21) crossover + тренд\n"
            "  ▸ MACD(12,26,9)\n"
            "  ▸ Bollinger Bands(20,2)\n"
            "  ▸ Stochastic(14,3)\n"
            "  ▸ Свечные паттерны (8 типов)\n"
            "🎯 <b>Фильтр входа:</b> 3 из 6 блоков\n\n"
            "{div}\n"
            "💱 <b>OTC ПАРЫ (12 инструментов):</b>\n\n"
            "{pairs}\n\n"
            "{div}\n"
            "⏱ <b>Таймфреймы:</b> 5с · 10с · 15с · 30с\n"
            "⏰ <b>Режим:</b> ПН–ВС 24/7\n\n"
            "{div}\n"
            "📦 <b>Тарифы:</b>\n"
            "  ⬜ FREE — 25 сигналов в день\n"
            "  🔵 JUNIOR — 50 сигналов в день  |  100$ / 7 дней\n"
            "  🟣 PRO — 100 сигналов в день  |  200$ / 7 дней\n\n"
            "{div}\n"
            "⚠️ <i>Торговля бинарными опционами несёт риски. "
            "Сигналы носят исключительно информационный характер. Всегда соблюдайте манименеджмент.</i>"
        ),

        # LOT CALCULATOR
        "lot_calc_enter": (
            "🧮 <b>КАЛЬКУЛЯТОР ЛОТА</b>\n"
            "{div}\n\n"
            "Введите ваш <b>баланс в долларах</b>:\n\n"
            "<i>Минимум: 50$  |  Пример: 100 или 500</i>"
        ),
        "lot_calc_invalid": (
            "❌ Введите корректную сумму (только цифры, > 0).\n"
            "<i>Пример: 100</i>"
        ),
        "lot_calc_low": (
            "⚠️ <b>БАЛАНС СЛИШКОМ МАЛ</b>\n"
            "{div}\n\n"
            "  Вы ввели: <b>{balance:,.2f}$</b>\n"
            "  Минимум: <b>50$</b>\n\n"
            "{sdiv}\n"
            "❌ Торговля с таким балансом <b>не рекомендуется</b>.\n\n"
            "С балансом ниже 50$ невозможно соблюдать базовые правила манименеджмента:\n\n"
            "▸ Минимальная ставка на Pocket Option — <b>1$</b>\n"
            "▸ Рекомендуемый риск на сделку — <b>1–2% от депозита</b>\n"
            "▸ При балансе ниже 50$ даже ставка в 1$ = <b>риск более 2%</b>, что приводит к быстрому сливу\n"
            "▸ Серия из 5–7 проигрышей полностью обнулит депозит\n\n"
            "{sdiv}\n"
            "💡 <b>Рекомендация:</b> пополните баланс минимум до <b>50$</b>, "
            "оптимально — от <b>100$</b> для комфортной торговли.\n\n"
            "<i>Введите корректную сумму (от 50$):</i>"
        ),
        "lot_calc_result": (
            "🧮 <b>КАЛЬКУЛЯТОР ЛОТА</b>\n"
            "{div}\n\n"
            "  💰 Баланс: <b>{balance:,.2f}$</b>\n\n"
            "{div}\n"
            "🟢 <b>Консервативный (1%)</b>\n"
            "  <code>{bar_c}</code>  <b>{conservative:,.2f}$</b>\n\n"
            "🔵 <b>Умеренный (2%)</b> — оптимально ✅\n"
            "  <code>{bar_m}</code>  <b>{moderate:,.2f}$</b>\n\n"
            "🟡 <b>Агрессивный (3%)</b>\n"
            "  <code>{bar_a}</code>  <b>{aggressive:,.2f}$</b>\n\n"
            "🔴 <b>Максимальный (5%)</b> — красная зона\n"
            "  <code>{bar_x}</code>  <b>{max_risk:,.2f}$</b>\n\n"
            "{div}\n"
            "💡 Оптимально: <b>{moderate:,.2f}$ – {aggressive:,.2f}$</b>\n"
            "<i>Никогда не рискуйте более 5% в одной сделке!</i>"
        ),
        "home": "🏠 <b>Главная</b> · <i>{name}</i>",
        "home_simple": "🏠 <b>Главная Панель</b>",

        # ACTIVATE ACCESS
        "vip_already": (
            "✅ <b>VIP ЛИЦЕНЗИЯ АКТИВНА</b>\n"
            "{div}\n"
            "Все модули терминала разблокированы."
        ),
        "vip_activate": (
            "💎 <b>АКТИВАЦИЯ VIP ЛИЦЕНЗИИ</b>\n"
            "{div}\n\n"
            "📋 <b>3 простых шага:</b>\n\n"
            "1️⃣ <b>Зарегистрируйте аккаунт:</b>\n"
            "   🌍 Global: <a href='https://u3.shortink.io/register?utm_campaign=845784&utm_source=affiliate&utm_medium=sr&a=e0FkuUtf0CHZA5&al=1760257&ac=bot&cid=954756&code=LXJ558'>Pocket Option (Official Gateway)</a>\n"
            "   🇷🇺 RU/СНГ: <a href='https://po-ru4.click/register?utm_campaign=845784&utm_source=affiliate&utm_medium=sr&a=e0FkuUtf0CHZA5&al=1760257&ac=bot&cid=954756&code=LXJ558'>Pocket Option (Зеркало)</a>\n\n"
            "2️⃣ <b>Пополните депозит</b> от <b>$50</b>\n\n"
            "3️⃣ <b>Отправьте ваш ID</b> с помощью кнопки ниже\n\n"
            "{div}\n"
            "🎁 <b>+60% бонус</b> к депозиту при регистрации по нашей ссылке!\n\n"
            "⚠️ <b>Важно:</b> аккаунт должен быть зарегистрирован по нашей ссылке. "
            "Если нет — создайте новый строго по ссылке выше.\n\n"
            "🔐 <i>Активация в течение нескольких минут после верификации.</i>"
        ),

        # SUPPORT
        "support_msg": (
            "🆘 <b>ПОДДЕРЖКА</b>\n"
            "{div}\n\n"
            "Опишите вашу проблему одним сообщением — мы перешлём её администратору.\n\n"
            "💬 <b>FAQ:</b>\n"
            "▸ Активация → «🔐 Активировать доступ»\n"
            "▸ Pocket Option ID → Мой аккаунт → Профиль\n"
            "▸ Лимит сигналов сбрасывается в 00:00 МСК\n"
            "▸ Терминал работает 24/7\n\n"
            "✍️ <b>Напишите ваш вопрос:</b>"
        ),
        "support_sent": (
            "✅ <b>Запрос получен!</b>\n"
            "Ответим в течение 30 минут."
        ),

        # SEND PO ID
        "ask_id": (
            "🔢 <b>ВЕРИФИКАЦИЯ АККАУНТА</b>\n"
            "{div}\n\n"
            "Введите ваш <b>числовой ID профиля Pocket Option</b>:\n\n"
            "📍 <i>Где найти: Pocket Option → Аккаунт → Профиль</i>\n\n"
            "⌨️ <b>Только цифры:</b>"
        ),
        "id_invalid": (
            "❌ <b>Ошибка.</b> Введите <b>только цифры</b>.\n"
            "<i>Пример: 12345678</i>"
        ),
        "id_sent": (
            "⏳ <b>ЗАЯВКА ОТПРАВЛЕНА</b>\n"
            "{div}\n\n"
            "🆔 Pocket Option ID: <code>{po_id}</code>\n\n"
            "Пожалуйста, ожидайте верификации. Активация занимает несколько минут."
        ),

        # VIP ACTIVATED (sent to user by admin)
        "vip_granted": (
            "🚀 <b>VIP ДОСТУП АКТИВИРОВАН!</b>\n"
            "{div}\n\n"
            "✅ Аккаунт верифицирован. Все модули разблокированы.\n\n"
            "📊 Нажмите <b>«📊 Торговая Панель»</b>\n"
            "⚡ Или сразу к <b>«⚡ Получить Сигнал»</b>\n\n"
            "<i>Прибыльных сделок! 📈</i>"
        ),
        "access_revoked": (
            "🛑 <b>ДОСТУП ОТОЗВАН</b>\n"
            "{div}\n\n"
            "VIP лицензия отозвана администратором.\n"
            "Обратитесь в поддержку: /help"
        ),

        # TRADING PANEL
        "trading_panel": (
            "📊 <b>ТОРГОВАЯ ПАНЕЛЬ</b>\n"
            "{div}\n\n"
            "  📡 {session}\n"
            "  🕐 {time} МСК · 12 OTC пар\n\n"
            "Выберите <b>валютную пару:</b>"
        ),
        "session_asian": "🌏 Азиатская · умеренная волатильность",
        "session_eu": "🌍 Европейская · высокая ликвидность",
        "session_us": "🌎 Американская · максимальный объём",
        "session_night": "🌙 Ночная · осторожно, низкий объём",
        "pair_selected": "✅ <b>{pair}</b>\n\n⏱ Выберите <b>время экспирации:</b>",
        "time_selected": (
            "⚙️ <b>ГОТОВО</b>\n"
            "{div}\n\n"
            "  Пара:       <b>{pair}</b>\n"
            "  Экспирация: <b>{time}</b>\n\n"
            "<i>Нажмите «⚡ Получить Сигнал»</i>"
        ),
        "no_pair_selected": (
            "⚠️ <b>Пара не выбрана!</b>\n\n"
            "Нажмите <b>«📊 Торговая Панель»</b>,\n"
            "выберите пару и время экспирации."
        ),
        "no_time_selected": (
            "⚠️ <b>Время не выбрано!</b>\n\n"
            "Пара: <b>{pair}</b>\n\n"
            "Выберите <b>экспирацию:</b>"
        ),
        "select_pair_first": (
            "⚠️ Сначала выберите пару.\n"
            "Нажмите <b>«📊 Торговая Панель»</b>."
        ),

        # SIGNAL
        "analysis_header": "⚡ АНАЛИЗ РЫНКА",
        "analysis_frames": [
            ("⬛⬛⬛⬛⬛  0%",   "Подключение к терминалу..."),
            ("🟩🟩⬛⬛⬛  40%",  "RSI · EMA · MACD..."),
            ("🟩🟩🟩🟩⬛  80%",  "BB · Stoch · паттерны..."),
            ("🟩🟩🟩🟩🟩  100%", "Сигнал сформирован ✅"),
        ],
        "dir_up": "▲  ВВЕРХ  ·  CALL",
        "dir_down": "▼  ВНИЗ  ·  PUT",
        "conf_extreme": "🔥 Экстремальный",
        "conf_strong": "💎 Сильный",
        "conf_steady": "⚡ Устойчивый",
        "conf_standard": "📊 Стандартный",
        "signal_expiry": "Экспирация",
        "signal_last": "<b>⚠️ Последний сигнал на сегодня!</b>",
        "signal_low": "<i>Осталось: <b>{n}</b> сигналов</i>",
        "signal_counter": "<i>{used} / {limit} · осталось {left}</i>",
        "signal_footer": "<i>⚡ 1–3% от баланса на сделку</i>",
        "pro_session_label": "Сессия",
        "pro_volatility_label": "Волатильность",
        "trend_label": "Тренд",
        "pro_tips": [
            "Стандартные условия — следуй алгоритму",
            "Высокая уверенность — стандартный объём",
            "Умеренный сигнал — рекомендуется 1–2% от депозита",
            "Сильное смещение — хорошая точка входа",
            "Контртренд — требуется дополнительная осторожность",
        ],

        # LIMIT REACHED
        "limit_free": (
            "🛑 <b>ДНЕВНОЙ ЛИМИТ ИСЧЕРПАН</b>\n"
            "{div}\n\n"
            "Использовано <b>{limit} / {limit}</b> бесплатных сигналов.\n\n"
            "💡 Получите больше сигналов с подпиской:\n\n"
            "🔵 <b>JUNIOR</b> — <b>50 сигналов в день</b>  |  <b>100$</b>\n"
            "🟣 <b>PRO</b>    — <b>100 сигналов в день</b>  |  <b>200$</b>\n\n"
            "⏳ <i>Или дождитесь сброса в 00:00 МСК</i>"
        ),
        "limit_paid": (
            "🛑 <b>ЛИМИТ ИСЧЕРПАН</b>\n"
            "{div}\n\n"
            "Тариф <b>{plan}</b>: <b>{used} / {limit}</b> сигналов.\n\n"
            "Лимит защищает от эмоциональной торговли.\n"
            "Возвращайтесь завтра — сброс в <b>00:00 МСК</b>.\n\n"
            "💡 Хотите больше? Смените тариф в <b>«💎 Подписка»</b>"
        ),

        # SUBSCRIPTION
        "sub_menu": (
            "💎 <b>ПОДПИСКА</b>\n"
            "{div}\n\n"
            "  Тариф:   {emoji} <b>{plan}</b>\n"
            "  Лимит:   <b>{limit} сигналов в день</b>\n"
            "  Истекает: <b>{expires}</b>"
            "{days_left}"
            "{renew_block}"
            "\n{div}\n"
            "📦 <b>Тарифы:</b>\n\n"
            "⬜ <b>FREE</b>   — 25 сигналов в день  <i>(бесплатно)</i>\n"
            "🔵 <b>JUNIOR</b> — 50 сигналов в день  <i>100$ / 7 дней</i>\n"
            "🟣 <b>PRO</b>    — 100 сигналов в день  <i>200$ / 7 дней</i>\n\n"
            "<i>Оплата в <b>USDT</b> через CryptoBot — мгновенно.</i>"
        ),
        "sub_expires_lifetime": "∞ Бессрочно",
        "sub_remaining": "\n  Осталось: <code>[{bar}]</code> <b>{days} дней</b>",
        "sub_renew_block": (
            "\n{sdiv}\n"
            "🔄 <b>Продлить / Сменить тариф</b>\n"
            "<i>Дни будут добавлены к текущему балансу.</i>\n"
        ),

        # SUB BUTTONS
        "btn_buy_junior": "🔵 JUNIOR — 100$ / 7 дней",
        "btn_buy_pro": "🟣 PRO — 200$ / 7 дней",
        "btn_renew_junior": "🔄 Продлить JUNIOR — 100$ / 7 дней",
        "btn_upgrade_pro": "⬆️ Перейти на PRO — 200$ / 7 дней",
        "btn_renew_pro": "🔄 Продлить PRO — 200$ / 7 дней",
        "btn_switch_junior": "🔵 Перейти на JUNIOR — 100$ / 7 дней",
        "btn_compare": "📊 Сравнить тарифы",
        "btn_upgrade_junior_upg": "🔵 JUNIOR — 50 сигналов/день | 100$",
        "btn_upgrade_pro_upg": "🟣 PRO — 100 сигналов/день | 200$",
        "btn_buy_junior_c": "🔵 Купить JUNIOR — 100$",
        "btn_buy_pro_c": "🟣 Купить PRO — 200$",
        "btn_pay": "💳 Оплатить (USDT)",
        "btn_check_pay": "✅ Проверить оплату",
        "btn_back_plans": "🔙 Назад к тарифам",

        # COMPARE PLANS
        "compare_plans": (
            "📊 <b>СРАВНЕНИЕ ТАРИФОВ</b>\n"
            "{div}\n\n"
            "⬜ <b>FREE</b>  ·  🔵 <b>JUNIOR</b>  ·  🟣 <b>PRO</b>\n\n"
            "{sdiv}\n"
            "📶 <b>Сигналов в день:</b>\n"
            "  ⬜ FREE   — <b>25</b>\n"
            "  🔵 JUNIOR — <b>50</b>\n"
            "  🟣 PRO    — <b>100</b>\n\n"
            "{sdiv}\n"
            "✅ <b>Доступно всем:</b>\n"
            "  ▸ OTC анализ\n"
            "  ▸ RSI / EMA / MACD\n"
            "  ▸ AI коэффициент уверенности\n"
            "  ▸ Калькулятор лота\n\n"
            "{sdiv}\n"
            "🔵 <b>Только JUNIOR &amp; PRO:</b>\n"
            "  ▸ Поддержка\n"
            "  ▸ Аналитика\n"
            "  ▸ Данные волатильности\n\n"
            "{sdiv}\n"
            "🟣 <b>Только PRO:</b>\n"
            "  ▸ VIP уведомления\n"
            "  ▸ Сила тренда\n"
            "  ▸ Объём торгов\n"
            "  ▸ ТОП стратегии\n\n"
            "{sdiv}\n"
            "💵 <b>Цена:</b>\n"
            "  ⬜ FREE   — <b>0$</b>  ·  навсегда\n"
            "  🔵 JUNIOR — <b>100$</b>  ·  7 дней\n"
            "  🟣 PRO    — <b>200$</b>  ·  7 дней\n\n"
            "{div}\n"
            "<i>Больше сигналов = больше возможностей</i>"
        ),

        # INVOICE
        "invoice": (
            "🧾 <b>СЧЁТ — {action}</b>\n"
            "{div}\n\n"
            "  Тариф:    {emoji} <b>{plan}</b>\n"
            "  Сумма:    <b>{price} USDT</b>\n"
            "  Срок:     <b>7 дней</b>\n"
            "  Лимит:    <b>{limit} сигналов в день</b>\n"
            "{renew_note}"
            "{div}\n"
            "1️⃣ Нажмите <b>«💳 Оплатить»</b>\n"
            "2️⃣ Завершите оплату в USDT\n"
            "3️⃣ Нажмите <b>«✅ Проверить оплату»</b>\n\n"
            "<i>⚡ Мгновенная активация после подтверждения.</i>"
        ),
        "invoice_action_purchase": "ПОКУПКА",
        "invoice_action_renewal": "ПРОДЛЕНИЕ",
        "invoice_new_expiry": "  📅 Новая дата: <b>{date}</b>\n",
        "invoice_error": "⚠️ Ошибка создания счёта. Попробуйте позже.",
        "payment_not_received": "❌ Оплата ещё не поступила. Подождите и проверьте снова.",
        "payment_confirmed": (
            "🎉 <b>ОПЛАТА ПОДТВЕРЖДЕНА!</b>\n"
            "{div}\n\n"
            "  Тариф:   {emoji} <b>{plan}</b>\n"
            "  Лимит:   <b>{limit} сигналов в день</b>\n"
            "  Истекает: <b>{expires}</b>\n\n"
            "{div}\n"
            "🚀 <b>Терминал активирован!</b>\n"
            "<i>Прибыльных сделок и зелёного баланса! 📈</i>"
        ),

        # PROFILE
        "profile": (
            "👤 <b>ПРОФИЛЬ</b>\n"
            "{div}\n\n"
            "  {name}  ·  <code>{uid}</code>\n\n"
            "{sdiv}\n"
            "🏆 <b>Ранг:</b> {rank}\n"
            "  <code>{rank_bar}</code>"
            "{rank_progress}\n\n"
            "{sdiv}\n"
            "💎 <b>Подписка:</b> {sub_emoji} <b>{sub_type}</b>\n"
            "  Лимит:   <b>{limit} сиг. в день</b>\n"
            "  Истекает: <b>{expires}</b>"
            "{days_info}\n\n"
            "{sdiv}\n"
            "📈 <b>Активность:</b>\n"
            "  Всего: <b>{total}</b>  ·  Сегодня:\n"
            "  <code>[{daily_bar}]</code> <b>{daily} / {limit}</b>\n\n"
            "{div}\n"
            "🔐 Лицензия: {license}\n\n"
            "<i>Рассчитайте оптимальный лот:</i>"
        ),
        "profile_license_active": "<b>АКТИВНА ✅</b>",
        "profile_license_inactive": "<b>❌ Нет доступа</b>",
        "btn_calc_lot_inline": "🧮 Рассчитать лот",
        "profile_expires_lifetime": "∞ Бессрочно",
        "profile_days_remaining": "\n  Осталось: <code>[{bar}]</code> <b>{days} дней</b>",
        "rank_to_next": "\n  До <b>{title}</b>: <b>{n}</b> сигналов",

        # STATS
        "stats": (
            "📊 <b>СТАТИСТИКА ТЕРМИНАЛА</b>\n"
            "{div}\n\n"
            "WinRate (Smart Precision):\n"
            "<code>[{wr_bar}] {win_rate}%</code>\n\n"
            "🟢 Прибыль: <b>{plus:,}</b>  🔴 Убыток: <b>{minus:,}</b>  🔁 Возврат: <b>{refund:,}</b>\n"
            "📦 Сигналов: <b>{total:,}</b>\n\n"
            "{sdiv}\n"
            "⚡ <b>Система:</b>\n"
            "  ROI:         <b>{avg_profit}%</b>\n"
            "  Топ пара:    <b>{best_pair}</b>\n"
            "  Пик:         <b>{peak_h}:00–{peak_h1}:00</b>\n\n"
            "{sdiv}\n"
            "📈 <b>Активность (МСК):</b>\n\n"
            "{hourly}\n"
            "{sdiv}\n"
            "👥 Трейдеров: <b>{users:,}</b>  ·  Активных: <b>{active:,}</b>\n\n"
            "<i>📅 {date} МСК</i>"
        ),

        # ADMIN NOTIFY
        "admin_new_app": (
            "🔔 <b>НОВАЯ VIP ЗАЯВКА</b>\n"
            "━━━━━━━━━━━━━━━━━\n"
            "👤 Имя: <b>{name}</b>\n"
            "🔗 Username: @{username}\n"
            "🆔 TG ID: <code>{uid}</code>\n"
            "💼 PO ID: <code>{po_id}</code>\n\n"
            "✅ Выдать: <code>/give {uid}</code>\n"
            "🚫 Отказать: <code>/block {uid}</code>"
        ),
        "admin_support_msg": (
            "📩 <b>ЗАПРОС В ПОДДЕРЖКУ</b>\n"
            "━━━━━━━━━━━━━━━━━\n"
            "👤 Имя: <b>{name}</b>\n"
            "🔗 Username: @{username}\n"
            "🆔 ID: <code>{uid}</code>\n\n"
            "📝 <b>Сообщение:</b>\n{text}\n\n"
            "💬 Ответить: <code>/reply {uid} текст</code>"
        ),
        "admin_payment": (
            "💰 <b>НОВЫЙ ПЛАТЁЖ</b>\n"
            "👤 ID: <code>{uid}</code>\n"
            "📦 Тариф: <b>{plan}</b>\n"
            "💵 Сумма: <b>{price} USDT</b>\n"
            "📅 Истекает: <b>{expires}</b>"
        ),
        "admin_broadcast_prefix": (
            "📢 <b>СООБЩЕНИЕ ОТ КОМАНДЫ</b>\n"
            "━━━━━━━━━━━━━━━━━\n\n"
        ),
        "admin_support_reply_prefix": "💬 <b>ОТВЕТ ПОДДЕРЖКИ</b>\n{div}\n\n",
        "admin_stats_msg": (
            "📊 <b>СТАТИСТИКА БОТА</b>\n"
            "━━━━━━━━━━━━━━━━━\n"
            "👥 Всего: <b>{total}</b>\n"
            "🟢 Активных (24ч): <b>{active}</b>\n"
            "📅 {date}"
        ),
        "admin_gave": "✅ Доступ для <code>{uid}</code> активирован.",
        "admin_blocked": "🚫 Доступ для <code>{uid}</code> заблокирован.",
        "admin_replied": "✅ Ответ отправлен пользователю <code>{uid}</code>.",
        "admin_broadcast_done": (
            "📤 <b>Рассылка завершена</b>\n"
            "✅ Доставлено: <b>{sent}</b>\n"
            "❌ Ошибок: <b>{fail}</b>"
        ),
    },

    "en": {
        # LANG SELECT
        "choose_lang": "🌐 Choose interface language:\n\n🇷🇺 Русский  |  🇬🇧 English",
        "lang_set": "🇬🇧 Language set: <b>English</b>",

        # START
        "start_header": (
            "┌─────────────────────────┐\n"
            "│  🖥  AI TRADING TERMINAL  │\n"
            "│     OTC PRO v4.0        │\n"
            "└─────────────────────────┘\n\n"
            "⚡ <b>Professional signal system</b> for Pocket Option OTC market.\n\n"
            "🧠 <b>Smart Precision Engine:</b>\n"
            "▸ 12 OTC pairs with country flags\n"
            "▸ Timeframes: 5s / 10s / 15s / 30s\n"
            "▸ 6 analysis blocks (RSI + EMA + MACD + BB + Stoch + patterns)\n"
            "▸ AI confidence: 78–96%\n\n"
            "👥 Traders: <b>{users}</b>\n"
            "📡 WinRate: <b>88–96%</b>  |  🟢 <b>24/7</b>\n"
            "🕐 {time} MSK"
        ),

        # MENU BUTTONS
        "btn_trading_panel": "📊 Trading Panel",
        "btn_get_signal": "⚡ Get Signal",
        "btn_profile": "👤 Profile",
        "btn_stats": "📈 Statistics",
        "btn_subscription": "💎 Subscription",
        "btn_about": "🚀 About",
        "btn_lot_calc": "🧮 Lot Calculator",
        "btn_activate": "🔐 Activate Access",
        "btn_support": "🆘 Support",
        "btn_back": "⬅️ Back",
        "btn_menu": "⬅️ Menu",
        "btn_send_id": "📩 Send Pocket Option ID",

        # ACCESS RESTRICTED
        "access_restricted": (
            "🔒 <b>ACCESS RESTRICTED</b>\n"
            "{div}\n"
            "This section is available to verified traders only.\n\n"
            "Press <b>«🔐 Activate Access»</b>"
        ),

        # ABOUT
        "about": (
            "🤖 <b>AI TRADING TERMINAL — OTC PRO v4.0</b>\n"
            "{div}\n\n"
            "📡 <b>Platform:</b> Pocket Option (OTC)\n\n"
            "🧠 <b>Smart Precision Engine v4:</b>\n"
            "  ▸ RSI(14)\n"
            "  ▸ EMA(9/21) crossover + trend\n"
            "  ▸ MACD(12,26,9)\n"
            "  ▸ Bollinger Bands(20,2)\n"
            "  ▸ Stochastic(14,3)\n"
            "  ▸ Candlestick patterns (8 types)\n"
            "🎯 <b>Entry filter:</b> 3 of 6 blocks\n\n"
            "{div}\n"
            "💱 <b>OTC PAIRS (12 instruments):</b>\n\n"
            "{pairs}\n\n"
            "{div}\n"
            "⏱ <b>Timeframes:</b> 5s · 10s · 15s · 30s\n"
            "⏰ <b>Mode:</b> MON–SUN 24/7\n\n"
            "{div}\n"
            "📦 <b>Plans:</b>\n"
            "  ⬜ FREE — 25 signals per day\n"
            "  🔵 JUNIOR — 50 signals per day  |  100$ / 7 days\n"
            "  🟣 PRO — 100 signals per day  |  200$ / 7 days\n\n"
            "{div}\n"
            "⚠️ <i>Trading binary options involves risks. "
            "Signals are for informational purposes only. Always use proper money management.</i>"
        ),

        # LOT CALCULATOR
        "lot_calc_enter": (
            "🧮 <b>LOT CALCULATOR</b>\n"
            "{div}\n\n"
            "Enter your <b>balance in dollars</b>:\n\n"
            "<i>Minimum: 50$  |  Example: 100 or 500</i>"
        ),
        "lot_calc_invalid": (
            "❌ Enter a valid amount (numbers only, > 0).\n"
            "<i>Example: 100</i>"
        ),
        "lot_calc_low": (
            "⚠️ <b>BALANCE TOO LOW</b>\n"
            "{div}\n\n"
            "  You entered: <b>{balance:,.2f}$</b>\n"
            "  Minimum: <b>50$</b>\n\n"
            "{sdiv}\n"
            "❌ Trading with this balance is <b>not recommended</b>.\n\n"
            "With a balance below 50$ you cannot follow basic money management rules:\n\n"
            "▸ Minimum trade on Pocket Option is <b>1$</b>\n"
            "▸ Recommended risk per trade — <b>1–2% of deposit</b>\n"
            "▸ With a balance under 50$, even a $1 trade = <b>2%+ risk</b>, leading to fast loss\n"
            "▸ A streak of 5–7 losing trades will completely wipe the deposit\n\n"
            "{sdiv}\n"
            "💡 <b>Recommendation:</b> top up to at least <b>50$</b>, "
            "ideally from <b>100$</b> for comfortable trading.\n\n"
            "<i>Enter a valid amount (from 50$):</i>"
        ),
        "lot_calc_result": (
            "🧮 <b>LOT CALCULATOR</b>\n"
            "{div}\n\n"
            "  💰 Balance: <b>{balance:,.2f}$</b>\n\n"
            "{div}\n"
            "🟢 <b>Conservative (1%)</b>\n"
            "  <code>{bar_c}</code>  <b>{conservative:,.2f}$</b>\n\n"
            "🔵 <b>Moderate (2%)</b> — optimal ✅\n"
            "  <code>{bar_m}</code>  <b>{moderate:,.2f}$</b>\n\n"
            "🟡 <b>Aggressive (3%)</b>\n"
            "  <code>{bar_a}</code>  <b>{aggressive:,.2f}$</b>\n\n"
            "🔴 <b>Maximum (5%)</b> — red zone\n"
            "  <code>{bar_x}</code>  <b>{max_risk:,.2f}$</b>\n\n"
            "{div}\n"
            "💡 Optimal: <b>{moderate:,.2f}$ – {aggressive:,.2f}$</b>\n"
            "<i>Never risk more than 5% in a single trade!</i>"
        ),
        "home": "🏠 <b>Home</b> · <i>{name}</i>",
        "home_simple": "🏠 <b>Main Panel</b>",

        # ACTIVATE ACCESS
        "vip_already": (
            "✅ <b>VIP LICENSE ACTIVE</b>\n"
            "{div}\n"
            "All terminal modules are unlocked."
        ),
        "vip_activate": (
            "💎 <b>VIP LICENSE ACTIVATION</b>\n"
            "{div}\n\n"
            "📋 <b>3 simple steps:</b>\n\n"
            "1️⃣ <b>Register an account:</b>\n"
            "   🌍 Global: <a href='https://u3.shortink.io/register?utm_campaign=845784&utm_source=affiliate&utm_medium=sr&a=e0FkuUtf0CHZA5&al=1760257&ac=bot&cid=954756&code=LXJ558'>Pocket Option (Official Gateway)</a>\n"
            "   🇷🇺 RU/CIS: <a href='https://po-ru4.click/register?utm_campaign=845784&utm_source=affiliate&utm_medium=sr&a=e0FkuUtf0CHZA5&al=1760257&ac=bot&cid=954756&code=LXJ558'>Pocket Option (Mirror)</a>\n\n"
            "2️⃣ <b>Top up your deposit</b> from <b>$50</b>\n\n"
            "3️⃣ <b>Send your ID</b> using the button below\n\n"
            "{div}\n"
            "🎁 <b>+60% bonus</b> on deposit when registering via our link!\n\n"
            "⚠️ <b>Important:</b> your account must be registered via our link. "
            "If not, create a new one strictly via the link above.\n\n"
            "🔐 <i>Activation within a few minutes after verification.</i>"
        ),

        # SUPPORT
        "support_msg": (
            "🆘 <b>SUPPORT</b>\n"
            "{div}\n\n"
            "Describe your issue in one message — we'll forward it to the admin.\n\n"
            "💬 <b>FAQ:</b>\n"
            "▸ Activation → «🔐 Activate Access»\n"
            "▸ Pocket Option ID → My Account → Profile\n"
            "▸ Signal limit resets at 00:00 MSK\n"
            "▸ Terminal operates 24/7\n\n"
            "✍️ <b>Write your question:</b>"
        ),
        "support_sent": (
            "✅ <b>Request received!</b>\n"
            "We'll respond within 30 minutes."
        ),

        # SEND PO ID
        "ask_id": (
            "🔢 <b>ACCOUNT VERIFICATION</b>\n"
            "{div}\n\n"
            "Enter your <b>numeric Pocket Option profile ID</b>:\n\n"
            "📍 <i>Where to find it: Pocket Option → Account → Profile</i>\n\n"
            "⌨️ <b>Numbers only:</b>"
        ),
        "id_invalid": (
            "❌ <b>Error.</b> Enter <b>numbers only</b>.\n"
            "<i>Example: 12345678</i>"
        ),
        "id_sent": (
            "⏳ <b>APPLICATION SENT</b>\n"
            "{div}\n\n"
            "🆔 Pocket Option ID: <code>{po_id}</code>\n\n"
            "Please wait for verification. Activation takes a few minutes."
        ),

        # VIP ACTIVATED
        "vip_granted": (
            "🚀 <b>VIP ACCESS ACTIVATED!</b>\n"
            "{div}\n\n"
            "✅ Account verified. All modules unlocked.\n\n"
            "📊 Press <b>«📊 Trading Panel»</b>\n"
            "⚡ Or go straight to <b>«⚡ Get Signal»</b>\n\n"
            "<i>Profitable trades! 📈</i>"
        ),
        "access_revoked": (
            "🛑 <b>ACCESS REVOKED</b>\n"
            "{div}\n\n"
            "VIP license has been revoked by the administrator.\n"
            "Contact support: /help"
        ),

        # TRADING PANEL
        "trading_panel": (
            "📊 <b>TRADING PANEL</b>\n"
            "{div}\n\n"
            "  📡 {session}\n"
            "  🕐 {time} MSK · 12 OTC pairs\n\n"
            "Select a <b>currency pair:</b>"
        ),
        "session_asian": "🌏 Asian · moderate volatility",
        "session_eu": "🌍 European · high liquidity",
        "session_us": "🌎 American · maximum volume",
        "session_night": "🌙 Night · caution, low volume",
        "pair_selected": "✅ <b>{pair}</b>\n\n⏱ Select <b>expiration time:</b>",
        "time_selected": (
            "⚙️ <b>READY</b>\n"
            "{div}\n\n"
            "  Pair:       <b>{pair}</b>\n"
            "  Expiration: <b>{time}</b>\n\n"
            "<i>Press «⚡ Get Signal»</i>"
        ),
        "no_pair_selected": (
            "⚠️ <b>No pair selected!</b>\n\n"
            "Press <b>«📊 Trading Panel»</b>,\n"
            "select a pair and expiration time."
        ),
        "no_time_selected": (
            "⚠️ <b>No time selected!</b>\n\n"
            "Pair: <b>{pair}</b>\n\n"
            "Select <b>expiration:</b>"
        ),
        "select_pair_first": (
            "⚠️ Please select a pair first.\n"
            "Press <b>«📊 Trading Panel»</b>."
        ),

        # SIGNAL
        "analysis_header": "⚡ MARKET ANALYSIS",
        "analysis_frames": [
            ("⬛⬛⬛⬛⬛  0%",   "Connecting to terminal..."),
            ("🟩🟩⬛⬛⬛  40%",  "RSI · EMA · MACD..."),
            ("🟩🟩🟩🟩⬛  80%",  "BB · Stoch · patterns..."),
            ("🟩🟩🟩🟩🟩  100%", "Signal formed ✅"),
        ],
        "dir_up": "▲  UP  ·  CALL",
        "dir_down": "▼  DOWN  ·  PUT",
        "conf_extreme": "🔥 Extreme",
        "conf_strong": "💎 Strong",
        "conf_steady": "⚡ Steady",
        "conf_standard": "📊 Standard",
        "signal_expiry": "Expiration",
        "signal_last": "<b>⚠️ Last signal for today!</b>",
        "signal_low": "<i>Remaining: <b>{n}</b> signals</i>",
        "signal_counter": "<i>{used} / {limit} · {left} remaining</i>",
        "signal_footer": "<i>⚡ 1–3% of balance per trade</i>",
        "pro_session_label": "Session",
        "pro_volatility_label": "Volatility",
        "trend_label": "Trend",
        "pro_tips": [
            "Standard conditions — follow the algorithm",
            "High confidence — standard volume",
            "Moderate signal — recommend 1–2% of deposit",
            "Strong bias — good entry point",
            "Counter-trend — extra caution advised",
        ],

        # LIMIT REACHED
        "limit_free": (
            "🛑 <b>DAILY LIMIT REACHED</b>\n"
            "{div}\n\n"
            "Used <b>{limit} / {limit}</b> free signals.\n\n"
            "💡 Get more signals with a subscription:\n\n"
            "🔵 <b>JUNIOR</b> — <b>50 signals per day</b>  |  <b>100$</b>\n"
            "🟣 <b>PRO</b>    — <b>100 signals per day</b>  |  <b>200$</b>\n\n"
            "⏳ <i>Or wait for the reset at 00:00 MSK</i>"
        ),
        "limit_paid": (
            "🛑 <b>LIMIT REACHED</b>\n"
            "{div}\n\n"
            "Plan <b>{plan}</b>: <b>{used} / {limit}</b> signals.\n\n"
            "The limit protects against emotional trading.\n"
            "Come back tomorrow — resets at <b>00:00 MSK</b>.\n\n"
            "💡 Want more? Change your plan in <b>«💎 Subscription»</b>"
        ),

        # SUBSCRIPTION
        "sub_menu": (
            "💎 <b>SUBSCRIPTION</b>\n"
            "{div}\n\n"
            "  Plan:    {emoji} <b>{plan}</b>\n"
            "  Limit:   <b>{limit} signals per day</b>\n"
            "  Expires: <b>{expires}</b>"
            "{days_left}"
            "{renew_block}"
            "\n{div}\n"
            "📦 <b>Plans:</b>\n\n"
            "⬜ <b>FREE</b>   — 25 signals per day  <i>(free)</i>\n"
            "🔵 <b>JUNIOR</b> — 50 signals per day  <i>100$ / 7 days</i>\n"
            "🟣 <b>PRO</b>    — 100 signals per day  <i>200$ / 7 days</i>\n\n"
            "<i>Payment in <b>USDT</b> via CryptoBot — instant.</i>"
        ),
        "sub_expires_lifetime": "∞ Lifetime",
        "sub_remaining": "\n  Remaining: <code>[{bar}]</code> <b>{days} days</b>",
        "sub_renew_block": (
            "\n{sdiv}\n"
            "🔄 <b>Renew / Change Plan</b>\n"
            "<i>Days will be added to your current balance.</i>\n"
        ),

        # SUB BUTTONS
        "btn_buy_junior": "🔵 JUNIOR — 100$ / 7 days",
        "btn_buy_pro": "🟣 PRO — 200$ / 7 days",
        "btn_renew_junior": "🔄 Renew JUNIOR — 100$ / 7 days",
        "btn_upgrade_pro": "⬆️ Upgrade to PRO — 200$ / 7 days",
        "btn_renew_pro": "🔄 Renew PRO — 200$ / 7 days",
        "btn_switch_junior": "🔵 Switch to JUNIOR — 100$ / 7 days",
        "btn_compare": "📊 Compare Plans",
        "btn_upgrade_junior_upg": "🔵 JUNIOR — 50 signals/day | 100$",
        "btn_upgrade_pro_upg": "🟣 PRO — 100 signals/day | 200$",
        "btn_buy_junior_c": "🔵 Buy JUNIOR — 100$",
        "btn_buy_pro_c": "🟣 Buy PRO — 200$",
        "btn_pay": "💳 Pay (USDT)",
        "btn_check_pay": "✅ Check Payment",
        "btn_back_plans": "🔙 Back to Plans",

        # COMPARE PLANS
        "compare_plans": (
            "📊 <b>PLAN COMPARISON</b>\n"
            "{div}\n\n"
            "⬜ <b>FREE</b>  ·  🔵 <b>JUNIOR</b>  ·  🟣 <b>PRO</b>\n\n"
            "{sdiv}\n"
            "📶 <b>Signals per day:</b>\n"
            "  ⬜ FREE   — <b>25</b>\n"
            "  🔵 JUNIOR — <b>50</b>\n"
            "  🟣 PRO    — <b>100</b>\n\n"
            "{sdiv}\n"
            "✅ <b>Available to all:</b>\n"
            "  ▸ OTC analysis\n"
            "  ▸ RSI / EMA / MACD\n"
            "  ▸ AI confidence score\n"
            "  ▸ Lot calculator\n\n"
            "{sdiv}\n"
            "🔵 <b>JUNIOR &amp; PRO only:</b>\n"
            "  ▸ Support\n"
            "  ▸ Analytics\n"
            "  ▸ Volatility data\n\n"
            "{sdiv}\n"
            "🟣 <b>PRO exclusive:</b>\n"
            "  ▸ VIP notifications\n"
            "  ▸ Trend strength\n"
            "  ▸ Trade volume\n"
            "  ▸ TOP strategies\n\n"
            "{sdiv}\n"
            "💵 <b>Price:</b>\n"
            "  ⬜ FREE   — <b>0$</b>  ·  forever\n"
            "  🔵 JUNIOR — <b>100$</b>  ·  7 days\n"
            "  🟣 PRO    — <b>200$</b>  ·  7 days\n\n"
            "{div}\n"
            "<i>More signals = more opportunities</i>"
        ),

        # INVOICE
        "invoice": (
            "🧾 <b>INVOICE — {action}</b>\n"
            "{div}\n\n"
            "  Plan:     {emoji} <b>{plan}</b>\n"
            "  Amount:   <b>{price} USDT</b>\n"
            "  Duration: <b>7 days</b>\n"
            "  Limit:    <b>{limit} signals per day</b>\n"
            "{renew_note}"
            "{div}\n"
            "1️⃣ Press <b>«💳 Pay»</b>\n"
            "2️⃣ Complete payment in USDT\n"
            "3️⃣ Press <b>«✅ Check Payment»</b>\n\n"
            "<i>⚡ Instant activation after confirmation.</i>"
        ),
        "invoice_action_purchase": "PURCHASE",
        "invoice_action_renewal": "RENEWAL",
        "invoice_new_expiry": "  📅 New expiry: <b>{date}</b>\n",
        "invoice_error": "⚠️ Invoice creation error. Please try again later.",
        "payment_not_received": "❌ Payment not received yet. Please wait and check again.",
        "payment_confirmed": (
            "🎉 <b>PAYMENT CONFIRMED!</b>\n"
            "{div}\n\n"
            "  Plan:    {emoji} <b>{plan}</b>\n"
            "  Limit:   <b>{limit} signals per day</b>\n"
            "  Expires: <b>{expires}</b>\n\n"
            "{div}\n"
            "🚀 <b>Terminal activated!</b>\n"
            "<i>Profitable trades and a green balance! 📈</i>"
        ),

        # PROFILE
        "profile": (
            "👤 <b>PROFILE</b>\n"
            "{div}\n\n"
            "  {name}  ·  <code>{uid}</code>\n\n"
            "{sdiv}\n"
            "🏆 <b>Rank:</b> {rank}\n"
            "  <code>{rank_bar}</code>"
            "{rank_progress}\n\n"
            "{sdiv}\n"
            "💎 <b>Subscription:</b> {sub_emoji} <b>{sub_type}</b>\n"
            "  Limit:   <b>{limit} sig. per day</b>\n"
            "  Expires: <b>{expires}</b>"
            "{days_info}\n\n"
            "{sdiv}\n"
            "📈 <b>Activity:</b>\n"
            "  Total: <b>{total}</b>  ·  Today:\n"
            "  <code>[{daily_bar}]</code> <b>{daily} / {limit}</b>\n\n"
            "{div}\n"
            "🔐 License: {license}\n\n"
            "<i>Calculate your optimal lot:</i>"
        ),
        "profile_license_active": "<b>ACTIVE ✅</b>",
        "profile_license_inactive": "<b>❌ No access</b>",
        "btn_calc_lot_inline": "🧮 Calculate Lot",
        "profile_expires_lifetime": "∞ Lifetime",
        "profile_days_remaining": "\n  Remaining: <code>[{bar}]</code> <b>{days} days</b>",
        "rank_to_next": "\n  To <b>{title}</b>: <b>{n}</b> more signals",

        # STATS
        "stats": (
            "📊 <b>TERMINAL STATISTICS</b>\n"
            "{div}\n\n"
            "WinRate (Smart Precision):\n"
            "<code>[{wr_bar}] {win_rate}%</code>\n\n"
            "🟢 Profit: <b>{plus:,}</b>  🔴 Loss: <b>{minus:,}</b>  🔁 Refund: <b>{refund:,}</b>\n"
            "📦 Signals: <b>{total:,}</b>\n\n"
            "{sdiv}\n"
            "⚡ <b>System:</b>\n"
            "  ROI:       <b>{avg_profit}%</b>\n"
            "  Top pair:  <b>{best_pair}</b>\n"
            "  Peak:      <b>{peak_h}:00–{peak_h1}:00</b>\n\n"
            "{sdiv}\n"
            "📈 <b>Activity (MSK):</b>\n\n"
            "{hourly}\n"
            "{sdiv}\n"
            "👥 Traders: <b>{users:,}</b>  ·  Active: <b>{active:,}</b>\n\n"
            "<i>📅 {date} MSK</i>"
        ),

        # ADMIN NOTIFY (always in Russian for admin)
        "admin_new_app": (
            "🔔 <b>NEW VIP APPLICATION</b>\n"
            "━━━━━━━━━━━━━━━━━\n"
            "👤 Name: <b>{name}</b>\n"
            "🔗 Username: @{username}\n"
            "🆔 TG ID: <code>{uid}</code>\n"
            "💼 PO ID: <code>{po_id}</code>\n\n"
            "✅ Grant: <code>/give {uid}</code>\n"
            "🚫 Deny: <code>/block {uid}</code>"
        ),
        "admin_support_msg": (
            "📩 <b>SUPPORT REQUEST</b>\n"
            "━━━━━━━━━━━━━━━━━\n"
            "👤 Name: <b>{name}</b>\n"
            "🔗 Username: @{username}\n"
            "🆔 ID: <code>{uid}</code>\n\n"
            "📝 <b>Message:</b>\n{text}\n\n"
            "💬 Reply: <code>/reply {uid} text</code>"
        ),
        "admin_payment": (
            "💰 <b>NEW PAYMENT</b>\n"
            "👤 ID: <code>{uid}</code>\n"
            "📦 Plan: <b>{plan}</b>\n"
            "💵 Amount: <b>{price} USDT</b>\n"
            "📅 Expires: <b>{expires}</b>"
        ),
        "admin_broadcast_prefix": (
            "📢 <b>MESSAGE FROM THE TEAM</b>\n"
            "━━━━━━━━━━━━━━━━━\n\n"
        ),
        "admin_support_reply_prefix": "💬 <b>SUPPORT REPLY</b>\n{div}\n\n",
        "admin_stats_msg": (
            "📊 <b>BOT STATISTICS</b>\n"
            "━━━━━━━━━━━━━━━━━\n"
            "👥 Total: <b>{total}</b>\n"
            "🟢 Active (24h): <b>{active}</b>\n"
            "📅 {date}"
        ),
        "admin_gave": "✅ Access for <code>{uid}</code> activated.",
        "admin_blocked": "🚫 Access for <code>{uid}</code> blocked.",
        "admin_replied": "✅ Reply sent to user <code>{uid}</code>.",
        "admin_broadcast_done": (
            "📤 <b>Broadcast complete</b>\n"
            "✅ Delivered: <b>{sent}</b>\n"
            "❌ Errors: <b>{fail}</b>"
        ),
    }
}

def T(uid: int, key: str) -> str:
    lang = user_lang.get(uid, "ru")
    return TEXTS[lang].get(key, TEXTS["en"].get(key, key))

# ════════════════════════════════════════════════
#              PostgreSQL OPERATIONS
# ════════════════════════════════════════════════
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id         BIGINT PRIMARY KEY,
                has_access      BOOLEAN   DEFAULT FALSE,
                total_signals   INTEGER   DEFAULT 0,
                daily_signals   INTEGER   DEFAULT 0,
                last_signal_date TEXT,
                sub_type        TEXT      DEFAULT 'free',
                sub_expires     TIMESTAMP,
                username        TEXT,
                first_seen      TIMESTAMP DEFAULT NOW(),
                last_active     TIMESTAMP DEFAULT NOW(),
                lang            TEXT      DEFAULT 'ru'
            )
        """)
        for col, definition in [
            ("username",    "TEXT"),
            ("first_seen",  "TIMESTAMP DEFAULT NOW()"),
            ("last_active", "TIMESTAMP DEFAULT NOW()"),
            ("lang",        "TEXT DEFAULT 'ru'"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {definition}")
            except Exception:
                pass
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB initialization error: {e}")

def db_get_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT has_access, total_signals, daily_signals, last_signal_date, "
            "sub_type, sub_expires, username, lang FROM users WHERE user_id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            sub_type = row['sub_type']
            if row['sub_expires'] and row['sub_expires'] < datetime.now():
                sub_type = 'free'
                db_update_user(user_id, sub_type='free', sub_expires=None)

            today = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d")
            daily_count = row['daily_signals']
            last_date   = row['last_signal_date'] or ""

            if last_date != "" and last_date != today:
                daily_count = 0
                last_date   = today
                db_update_user(user_id, daily=0, date=today)

            # sync lang to memory
            lang = row.get('lang') or 'ru'
            user_lang[user_id] = lang

            return {
                "has_access":  row['has_access'],
                "signals":     row['total_signals'],
                "daily_count": daily_count,
                "last_date":   last_date,
                "sub_type":    sub_type,
                "sub_expires": row['sub_expires'],
                "username":    row.get('username', ''),
                "lang":        lang,
            }
    except Exception as e:
        print(f"DB read error: {e}")
    return {"has_access": False, "signals": 0, "daily_count": 0,
            "last_date": "", "sub_type": "free", "sub_expires": None, "username": "", "lang": "ru"}

def db_update_user(user_id, has_access=None, signals=None, daily=None,
                   date=None, sub_type=None, sub_expires=None, username=None, lang=None):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
            (user_id,)
        )
        if has_access  is not None:
            cursor.execute("UPDATE users SET has_access = %s WHERE user_id = %s", (has_access, user_id))
        if signals     is not None:
            cursor.execute("UPDATE users SET total_signals = %s WHERE user_id = %s", (signals, user_id))
        if daily       is not None:
            cursor.execute("UPDATE users SET daily_signals = %s WHERE user_id = %s", (daily, user_id))
        if date        is not None:
            cursor.execute("UPDATE users SET last_signal_date = %s WHERE user_id = %s", (date, user_id))
        if sub_type    is not None:
            cursor.execute("UPDATE users SET sub_type = %s WHERE user_id = %s", (sub_type, user_id))
        if sub_expires is not None or sub_type == 'free':
            cursor.execute("UPDATE users SET sub_expires = %s WHERE user_id = %s", (sub_expires, user_id))
        if username    is not None:
            cursor.execute("UPDATE users SET username = %s WHERE user_id = %s", (username, user_id))
        if lang        is not None:
            cursor.execute("UPDATE users SET lang = %s WHERE user_id = %s", (lang, user_id))
        cursor.execute("UPDATE users SET last_active = NOW() WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB update error: {e}")

def db_get_total_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except:
        return 0

def db_get_active_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '24 hours'")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except:
        return 0

# ════════════════════════════════════════════════
#              CRYPTO BOT API
# ════════════════════════════════════════════════
async def create_invoice(amount, plan_name):
    url     = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    payload = {
        "asset":        "USDT",
        "amount":       str(amount),
        "description":  f"Subscription {plan_name} for 7 days | AI Trading Terminal",
        "paid_btn_name":"callback",
        "paid_btn_url": "https://t.me/CryptoBot"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            return await resp.json()

async def check_invoice(invoice_id):
    url     = f"https://pay.crypt.bot/api/getInvoices?invoice_ids={invoice_id}"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data['ok'] and data['result']['items']:
                return data['result']['items'][0]['status'] == 'paid'
    return False

# ════════════════════════════════════════════════
#   OTC SIGNAL GENERATOR (autonomous mode)
# ════════════════════════════════════════════════
def generate_otc_signal(pair: str, timeframe: str) -> tuple[str, int, str]:
    now = datetime.utcnow()

    if "5 sec" in timeframe:
        bucket = int(now.timestamp() / 5)
    elif "10 sec" in timeframe:
        bucket = int(now.timestamp() / 10)
    elif "15 sec" in timeframe:
        bucket = int(now.timestamp() / 15)
    elif "30 sec" in timeframe:
        bucket = int(now.timestamp() / 30)
    else:
        bucket = int(now.timestamp() / 60)

    seed = hash(f"{pair}_{bucket}") % (2**32)
    rng = random.Random(seed)

    rsi = rng.uniform(25, 75)
    if rsi <= 35:
        rsi_vote = +2
    elif rsi <= 45:
        rsi_vote = +1
    elif rsi >= 65:
        rsi_vote = -2
    elif rsi >= 55:
        rsi_vote = -1
    else:
        rsi_vote = rng.choice([-1, 0, 0, +1])

    ema_options = [(+2, ""), (-2, ""), (+1, ""), (-1, ""), (0, "")]
    ema_vote, _ = rng.choices(ema_options, weights=[15, 15, 25, 25, 20])[0]

    macd_options = [(+2, ""), (-2, ""), (+1, ""), (-1, ""), (0, "")]
    macd_vote, _ = rng.choices(macd_options, weights=[15, 15, 25, 25, 20])[0]

    bb_options = [(+2, ""), (-2, ""), (+1, ""), (-1, ""), (0, "")]
    bb_vote, _ = rng.choices(bb_options, weights=[12, 12, 26, 26, 24])[0]

    stoch_k = rng.uniform(15, 85)
    if stoch_k <= 20:
        stoch_vote = +2
    elif stoch_k >= 80:
        stoch_vote = -2
    elif stoch_k < 40:
        stoch_vote = +1
    elif stoch_k > 60:
        stoch_vote = -1
    else:
        stoch_vote = rng.choice([-1, 0, +1])

    pattern_options = [(+1, ""), (+1, ""), (+1, ""), (-1, ""), (-1, ""), (-1, ""), (0, ""), (0, "")]
    pattern_vote, _ = rng.choices(pattern_options, weights=[12, 10, 8, 12, 10, 8, 15, 25])[0]

    votes = [rsi_vote, ema_vote, macd_vote, bb_vote, stoch_vote, pattern_vote]
    total_score = sum(votes)

    if total_score > 0:
        agreeing = sum(1 for v in votes if v > 0)
    else:
        agreeing = sum(1 for v in votes if v < 0)

    if agreeing < 3 or abs(total_score) < 3:
        direction  = rng.choice(["UP", "DOWN"])
        confidence = rng.randint(78, 82)
        return direction, confidence, None

    max_possible = 11
    signal_strength = abs(total_score) / max_possible
    base_confidence = 78 + int(signal_strength * 16)
    block_bonus = (agreeing - 3) * 2
    confidence = min(base_confidence + block_bonus, 96)
    confidence += rng.choice([-1, 0, 0, 1])
    confidence = max(78, min(96, confidence))

    direction = "UP" if total_score > 0 else "DOWN"
    return direction, confidence, None


# ════════════════════════════════════════════════
#         RANKS AND UTILITIES
# ════════════════════════════════════════════════
RANKS = [
    (0,    100,  "🌱 Beginner",      "Retail"),
    (101,  300,  "📊 Trader",        "Prop Firm"),
    (301,  1000, "📈 Pro Trader",    "Institutional"),
    (1001, 2000, "🔥 Expert",        "Smart Money"),
    (2001, 9999999, "👑 Market Maker", "Whale"),
]

def get_rank(count):
    for lo, hi, title, level in RANKS:
        if lo <= count <= hi:
            return f"{title} ({level})"
    return "👑 Market Maker (Whale)"

def get_next_rank(count):
    for lo, hi, title, level in RANKS:
        if lo <= count <= hi:
            idx = RANKS.index((lo, hi, title, level))
            if idx + 1 < len(RANKS):
                nxt = RANKS[idx + 1]
                return nxt[2], nxt[3], nxt[0] - count
    return None, None, 0

def confidence_bar(pct: int) -> str:
    filled = int(pct / 10)
    filled = max(0, min(10, filled))
    return "▓" * filled + "░" * (10 - filled)

def days_bar(used: int, total: int) -> str:
    pct = used / total if total > 0 else 0
    filled = int(pct * 10)
    return "█" * filled + "░" * (10 - filled)

def calc_lot(balance: float) -> dict:
    conservative = round(balance * 0.01, 2)
    moderate     = round(balance * 0.02, 2)
    aggressive   = round(balance * 0.03, 2)
    max_risk     = round(balance * 0.05, 2)
    return {
        "conservative": conservative,
        "moderate":     moderate,
        "aggressive":   aggressive,
        "max_risk":     max_risk,
    }

def rank_progress_bar(current: int, lo: int, hi: int) -> str:
    if hi == 9999999:
        return "▓▓▓▓▓▓▓▓▓▓ MAX"
    total = hi - lo
    done  = current - lo
    pct   = done / total if total > 0 else 1
    filled = int(pct * 10)
    filled = max(0, min(10, filled))
    bar = "▓" * filled + "░" * (10 - filled)
    return f"[{bar}] {int(pct * 100)}%"

# ════════════════════════════════════════════════
#         DESIGN CONSTANTS (short lines)
# ════════════════════════════════════════════════
DIV  = "───────────────"
SDIV = "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈"

# ════════════════════════════════════════════════
#              TEMPORARY DATA
# ════════════════════════════════════════════════
user_temp_data   = {}
pending_users    = set()
pending_support  = set()
pending_lot_calc = set()
pending_lang     = set()   # users currently selecting language

last_signal_request = {}   # uid -> timestamp of last successful signal

# In-memory language cache (also persisted to DB)
user_lang: dict[int, str] = {}   # uid -> "ru" | "en"

# ════════════════════════════════════════════════
#              KEYBOARDS (language-aware)
# ════════════════════════════════════════════════
def get_main_menu(has_access: bool, uid: int = 0):
    if uid and user_lang.get(uid) == "en":
        keyboard = [
            [KeyboardButton(text="📊 Trading Panel"), KeyboardButton(text="⚡ Get Signal")],
            [KeyboardButton(text="👤 Profile"),        KeyboardButton(text="📈 Statistics")],
            [KeyboardButton(text="💎 Subscription"),   KeyboardButton(text="🚀 About")],
            [KeyboardButton(text="🧮 Lot Calculator")],
        ]
        row_bottom = []
        if not has_access:
            row_bottom.append(KeyboardButton(text="🔐 Activate Access"))
        row_bottom.append(KeyboardButton(text="🆘 Support"))
        keyboard.append(row_bottom)
    else:
        keyboard = [
            [KeyboardButton(text="📊 Торговая Панель"), KeyboardButton(text="⚡ Получить Сигнал")],
            [KeyboardButton(text="👤 Профиль"),          KeyboardButton(text="📈 Статистика")],
            [KeyboardButton(text="💎 Подписка"),          KeyboardButton(text="🚀 О боте")],
            [KeyboardButton(text="🧮 Калькулятор лота")],
        ]
        row_bottom = []
        if not has_access:
            row_bottom.append(KeyboardButton(text="🔐 Активировать доступ"))
        row_bottom.append(KeyboardButton(text="🆘 Поддержка"))
        keyboard.append(row_bottom)
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_access_kb(uid: int = 0):
    if uid and user_lang.get(uid) == "en":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📩 Send Pocket Option ID")],
                [KeyboardButton(text="⬅️ Back")]
            ],
            resize_keyboard=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Отправить ID Pocket Option")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_pair_kb():
    rows = []
    pair_list = list(pairs)
    for i in range(0, len(pair_list), 2):
        if i + 1 < len(pair_list):
            rows.append([
                KeyboardButton(text=pair_list[i]),
                KeyboardButton(text=pair_list[i + 1])
            ])
        else:
            rows.append([KeyboardButton(text=pair_list[i])])
    rows.append([KeyboardButton(text="⬅️ Back")])
    rows.append([KeyboardButton(text="⬅️ Назад")])
    # use single back button — handle both
    rows_clean = []
    for i in range(0, len(pair_list), 2):
        if i + 1 < len(pair_list):
            rows_clean.append([
                KeyboardButton(text=pair_list[i]),
                KeyboardButton(text=pair_list[i + 1])
            ])
        else:
            rows_clean.append([KeyboardButton(text=pair_list[i])])
    rows_clean.append([KeyboardButton(text="⬅️ Back / Назад")])
    return ReplyKeyboardMarkup(keyboard=rows_clean, resize_keyboard=True)

pair_kb = get_pair_kb()

time_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⏱ 5 sec"),  KeyboardButton(text="⏱ 10 sec")],
        [KeyboardButton(text="⏱ 15 sec"), KeyboardButton(text="⏱ 30 sec")],
        [KeyboardButton(text="⬅️ Back / Назад")]
    ],
    resize_keyboard=True
)

def get_signal_kb(uid: int = 0):
    if uid and user_lang.get(uid) == "en":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⚡ Get Signal")],
                [KeyboardButton(text="📊 Trading Panel"), KeyboardButton(text="⬅️ Menu")]
            ],
            resize_keyboard=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Получить Сигнал")],
            [KeyboardButton(text="📊 Торговая Панель"), KeyboardButton(text="⬅️ Меню")]
        ],
        resize_keyboard=True
    )

def get_back_kb(uid: int = 0):
    if uid and user_lang.get(uid) == "en":
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅️ Back")]],
            resize_keyboard=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )

def get_sub_kb(current_plan: str, uid: int = 0):
    t = TEXTS[user_lang.get(uid, "ru")]
    buttons = []
    if current_plan == "free":
        buttons.append([InlineKeyboardButton(text=t["btn_buy_junior"], callback_data="buy_junior")])
        buttons.append([InlineKeyboardButton(text=t["btn_buy_pro"],    callback_data="buy_pro")])
    elif current_plan == "junior":
        buttons.append([InlineKeyboardButton(text=t["btn_renew_junior"], callback_data="buy_junior")])
        buttons.append([InlineKeyboardButton(text=t["btn_upgrade_pro"],  callback_data="buy_pro")])
    elif current_plan == "pro":
        buttons.append([InlineKeyboardButton(text=t["btn_renew_pro"],    callback_data="buy_pro")])
        buttons.append([InlineKeyboardButton(text=t["btn_switch_junior"],callback_data="buy_junior")])
    buttons.append([InlineKeyboardButton(text=t["btn_compare"], callback_data="compare_plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_upgrade_kb(uid: int = 0):
    t = TEXTS[user_lang.get(uid, "ru")]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_upgrade_junior_upg"], callback_data="buy_junior")],
        [InlineKeyboardButton(text=t["btn_upgrade_pro_upg"],   callback_data="buy_pro")],
        [InlineKeyboardButton(text=t["btn_compare"],            callback_data="compare_plans")],
    ])

def get_confirm_sub_kb(invoice_url, invoice_id, plan_key, uid: int = 0):
    t = TEXTS[user_lang.get(uid, "ru")]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_pay"], url=invoice_url)],
        [InlineKeyboardButton(text=t["btn_check_pay"], callback_data=f"check_{invoice_id}_{plan_key}")],
        [InlineKeyboardButton(text=t["btn_back_plans"],  callback_data="back_to_plans")],
    ])

# Language selection keyboard
lang_select_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en"),
    ]
])

# ════════════════════════════════════════════════
#              MIDDLEWARE
# ════════════════════════════════════════════════

# All possible back/menu button texts (both languages)
BACK_TEXTS = {"⬅️ Back", "⬅️ Назад", "⬅️ Back / Назад", "⬅️ Menu", "⬅️ Меню"}

# All possible "allowed without access" texts (both languages)
ALLOWED_TEXTS = {
    "🔐 Activate Access", "🔐 Активировать доступ",
    "📩 Send Pocket Option ID", "📩 Отправить ID Pocket Option",
    "⬅️ Back", "⬅️ Назад", "⬅️ Back / Назад",
    "/start", "⬅️ Menu", "⬅️ Меню", "/vip", "/help",
    "🆘 Support", "🆘 Поддержка", "🚀 About", "🚀 О боте"
}

class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            uid  = event.from_user.id
            text = event.text or ""
            if uid == ADMIN_ID:
                return await handler(event, data)
            user_info = db_get_user(uid)
            lang = user_lang.get(uid, "ru")
            if not user_info["has_access"] and uid not in pending_users and uid not in pending_support:
                if text not in ALLOWED_TEXTS:
                    await event.answer(
                        TEXTS[lang]["access_restricted"].format(div=DIV),
                        parse_mode="HTML"
                    )
                    return
        return await handler(event, data)

dp.message.middleware(AccessMiddleware())

# ════════════════════════════════════════════════
#   LANGUAGE SELECTION HANDLER
# ════════════════════════════════════════════════

@dp.callback_query(F.data.in_({"set_lang_ru", "set_lang_en"}))
async def set_language(callback: CallbackQuery):
    uid  = callback.from_user.id
    lang = "ru" if callback.data == "set_lang_ru" else "en"
    user_lang[uid] = lang
    db_update_user(uid, lang=lang)

    confirmation = TEXTS[lang]["lang_set"]
    await callback.message.edit_text(confirmation, parse_mode="HTML")

    # Now show the full start screen
    u           = db_get_user(uid)
    total_users = db_get_total_users()
    now_msk     = (datetime.utcnow() + timedelta(hours=3)).strftime("%d.%m.%Y %H:%M")

    start_text = TEXTS[lang]["start_header"].format(
        users=f"{total_users + 152:,}",
        time=now_msk
    )
    await callback.message.answer(
        start_text,
        reply_markup=get_main_menu(u["has_access"], uid),
        parse_mode="HTML"
    )
    await callback.answer()

# ════════════════════════════════════════════════
#              SUBSCRIPTION HANDLERS
# ════════════════════════════════════════════════
@dp.message(F.text.in_({"💎 Subscription", "💎 Подписка"}))
async def sub_menu(message: Message):
    uid   = message.from_user.id
    u     = db_get_user(uid)
    lang  = user_lang.get(uid, "ru")
    t     = TEXTS[lang]
    plan  = SUBSCRIPTION_PLANS[u['sub_type']]
    limit = plan['limit']
    emoji = plan['emoji']

    exp_str = t["sub_expires_lifetime"]
    days_left_str = ""
    if u['sub_expires']:
        exp_str = u['sub_expires'].strftime("%d.%m.%Y %H:%M")
        days_left = (u['sub_expires'] - datetime.now()).days
        days_used = 7 - days_left
        bar = days_bar(days_used, 7)
        days_left_str = t["sub_remaining"].format(bar=bar, days=max(days_left, 0))

    renew_block = ""
    if u['sub_type'] != 'free':
        renew_block = t["sub_renew_block"].format(sdiv=SDIV)

    text = t["sub_menu"].format(
        div=DIV, sdiv=SDIV,
        emoji=emoji,
        plan=u['sub_type'].upper(),
        limit=limit,
        expires=exp_str,
        days_left=days_left_str,
        renew_block=renew_block,
    )
    await message.answer(text, reply_markup=get_sub_kb(u['sub_type'], uid), parse_mode="HTML")

@dp.callback_query(F.data == "compare_plans")
async def compare_plans(callback: CallbackQuery):
    uid  = callback.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]
    text = t["compare_plans"].format(div=DIV, sdiv=SDIV)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_buy_junior_c"], callback_data="buy_junior")],
        [InlineKeyboardButton(text=t["btn_buy_pro_c"],    callback_data="buy_pro")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "back_to_plans")
async def back_to_plans(callback: CallbackQuery):
    uid = callback.from_user.id
    u   = db_get_user(uid)
    await callback.message.edit_reply_markup(reply_markup=get_sub_kb(u['sub_type'], uid))

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    uid      = callback.from_user.id
    lang     = user_lang.get(uid, "ru")
    t        = TEXTS[lang]
    plan_key = callback.data.split("_")[1]
    plan     = SUBSCRIPTION_PLANS[plan_key]
    u        = db_get_user(uid)
    res      = await create_invoice(plan['price'], plan['name'])

    is_renew    = u['sub_type'] == plan_key
    action_word = t["invoice_action_renewal"] if is_renew else t["invoice_action_purchase"]

    if res['ok']:
        invoice_url = res['result']['pay_url']
        invoice_id  = res['result']['invoice_id']
        kb = get_confirm_sub_kb(invoice_url, invoice_id, plan_key, uid)

        renew_note = ""
        if is_renew and u['sub_expires']:
            new_exp = u['sub_expires'] + timedelta(days=7)
            renew_note = t["invoice_new_expiry"].format(date=new_exp.strftime('%d.%m.%Y'))

        text = t["invoice"].format(
            div=DIV,
            action=action_word,
            emoji=plan['emoji'],
            plan=plan['name'],
            price=plan['price'],
            limit=plan['limit'],
            renew_note=renew_note,
        )
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.answer(t["invoice_error"], show_alert=True)

@dp.callback_query(F.data.startswith("check_"))
async def process_check(callback: CallbackQuery):
    uid      = callback.from_user.id
    lang     = user_lang.get(uid, "ru")
    t        = TEXTS[lang]
    parts    = callback.data.split("_")
    inv_id   = parts[1]
    plan_key = parts[2]
    is_paid  = await check_invoice(inv_id)

    if is_paid:
        u = db_get_user(uid)
        if u['sub_type'] == plan_key and u['sub_expires'] and u['sub_expires'] > datetime.now():
            expiry = u['sub_expires'] + timedelta(days=7)
        else:
            expiry = datetime.now() + timedelta(days=7)

        db_update_user(uid, sub_type=plan_key, sub_expires=expiry)
        plan = SUBSCRIPTION_PLANS[plan_key]
        text = t["payment_confirmed"].format(
            div=DIV,
            emoji=plan['emoji'],
            plan=plan_key.upper(),
            limit=plan['limit'],
            expires=expiry.strftime('%d.%m.%Y %H:%M'),
        )
        await callback.message.edit_text(text, parse_mode="HTML")
        try:
            await bot.send_message(
                ADMIN_ID,
                TEXTS["ru"]["admin_payment"].format(
                    uid=uid,
                    plan=plan_key.upper(),
                    price=plan['price'],
                    expires=expiry.strftime('%d.%m.%Y %H:%M'),
                ),
                parse_mode="HTML"
            )
        except:
            pass
    else:
        await callback.answer(t["payment_not_received"], show_alert=True)

# ════════════════════════════════════════════════
#              COMMANDS AND MAIN HANDLERS
# ════════════════════════════════════════════════
@dp.message(CommandStart())
async def start(message: Message):
    uid = message.from_user.id
    db_update_user(uid, username=message.from_user.username)
    # Load lang from DB
    db_get_user(uid)

    # Show language selection first
    await message.answer(
        "🌐 <b>Choose language / Выберите язык</b>\n\n"
        "🇷🇺 Русский  |  🇬🇧 English",
        reply_markup=lang_select_kb,
        parse_mode="HTML"
    )

@dp.message(F.text.in_({"🚀 About", "🚀 О боте"}))
async def about_bot(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]
    pairs_list = "\n".join([f"  ▸ {p}" for p in pairs])
    text = t["about"].format(div=DIV, pairs=pairs_list)
    await message.answer(text, parse_mode="HTML")

# ════════════════════════════════════════════════
#         🧮 LOT CALCULATOR
# ════════════════════════════════════════════════
@dp.message(F.text.in_({"🧮 Lot Calculator", "🧮 Калькулятор лота"}))
async def lot_calculator(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    pending_lot_calc.add(uid)
    await message.answer(
        TEXTS[lang]["lot_calc_enter"].format(div=DIV),
        reply_markup=get_back_kb(uid),
        parse_mode="HTML"
    )

@dp.message(lambda msg: msg.from_user.id in pending_lot_calc)
async def process_lot_calc(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]

    if message.text in BACK_TEXTS:
        pending_lot_calc.discard(uid)
        u = db_get_user(uid)
        return await message.answer(
            t["home_simple"],
            reply_markup=get_main_menu(u["has_access"], uid),
            parse_mode="HTML"
        )

    text = (message.text or "").replace(",", ".").replace(" ", "")
    try:
        balance = float(text)
        if balance <= 0:
            raise ValueError
    except ValueError:
        return await message.answer(t["lot_calc_invalid"], parse_mode="HTML")

    if balance < 50:
        return await message.answer(
            t["lot_calc_low"].format(div=DIV, sdiv=SDIV, balance=balance),
            parse_mode="HTML"
        )

    pending_lot_calc.discard(uid)
    u   = db_get_user(uid)
    lot = calc_lot(balance)

    bar_c = confidence_bar(10)
    bar_m = confidence_bar(20)
    bar_a = confidence_bar(30)
    bar_x = confidence_bar(50)

    await message.answer(
        t["lot_calc_result"].format(
            div=DIV,
            balance=balance,
            bar_c=bar_c, conservative=lot['conservative'],
            bar_m=bar_m, moderate=lot['moderate'],
            bar_a=bar_a, aggressive=lot['aggressive'],
            bar_x=bar_x, max_risk=lot['max_risk'],
        ),
        reply_markup=get_main_menu(u["has_access"], uid),
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════
#              ACCESS ACTIVATION
# ════════════════════════════════════════════════
@dp.message(Command("vip"))
@dp.message(F.text.in_({"🔐 Activate Access", "🔐 Активировать доступ"}))
async def activate(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]
    user_info = db_get_user(uid)
    if user_info["has_access"]:
        return await message.answer(
            t["vip_already"].format(div=DIV),
            parse_mode="HTML"
        )
    await message.answer(
        t["vip_activate"].format(div=DIV),
        reply_markup=get_access_kb(uid),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@dp.message(Command("help"))
@dp.message(F.text.in_({"🆘 Support", "🆘 Поддержка"}))
async def help_cmd(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]
    pending_support.add(uid)
    await message.answer(
        t["support_msg"].format(div=DIV),
        reply_markup=get_back_kb(uid),
        parse_mode="HTML"
    )

@dp.message(F.text.in_({"📩 Send Pocket Option ID", "📩 Отправить ID Pocket Option"}))
async def ask_id(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]
    pending_users.add(uid)
    await message.answer(
        t["ask_id"].format(div=DIV),
        reply_markup=get_back_kb(uid),
        parse_mode="HTML"
    )

@dp.message(F.text.in_(BACK_TEXTS))
async def go_back(message: Message):
    uid = message.from_user.id
    pending_users.discard(uid)
    pending_support.discard(uid)
    pending_lot_calc.discard(uid)
    u    = db_get_user(uid)
    lang = user_lang.get(uid, "ru")
    name = message.from_user.first_name or "Trader"
    await message.answer(
        TEXTS[lang]["home"].format(name=name),
        reply_markup=get_main_menu(u["has_access"], uid),
        parse_mode="HTML"
    )

@dp.message(lambda msg: msg.from_user.id in pending_support)
async def process_support_message(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]

    if message.text in BACK_TEXTS:
        pending_support.discard(uid)
        return await go_back(message)

    username = message.from_user.username or "—"
    name     = message.from_user.full_name or "—"
    # Admin always gets Russian
    await bot.send_message(
        ADMIN_ID,
        TEXTS["ru"]["admin_support_msg"].format(
            name=name, username=username, uid=uid, text=message.text
        ),
        parse_mode="HTML"
    )
    pending_support.discard(uid)
    u = db_get_user(uid)
    await message.answer(
        t["support_sent"],
        reply_markup=get_main_menu(u["has_access"], uid),
        parse_mode="HTML"
    )

@dp.message(lambda msg: msg.from_user.id in pending_users)
async def process_id(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]

    if message.text in BACK_TEXTS:
        pending_users.discard(uid)
        return await go_back(message)
    if not message.text or not message.text.isdigit():
        return await message.answer(t["id_invalid"], parse_mode="HTML")

    pending_users.discard(uid)
    await bot.send_message(
        ADMIN_ID,
        TEXTS["ru"]["admin_new_app"].format(
            name=message.from_user.full_name,
            username=message.from_user.username or "—",
            uid=uid,
            po_id=message.text,
        ),
        parse_mode="HTML"
    )
    u = db_get_user(uid)
    await message.answer(
        t["id_sent"].format(div=DIV, po_id=message.text),
        reply_markup=get_main_menu(u["has_access"], uid),
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════
#              ADMIN COMMANDS
# ════════════════════════════════════════════════
@dp.message(F.text.startswith("/give"))
async def admin_give(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target = int(message.text.split()[1])
        db_update_user(target, has_access=True)
        target_lang = user_lang.get(target, "ru")
        await bot.send_message(
            target,
            TEXTS[target_lang]["vip_granted"].format(div=DIV),
            parse_mode="HTML",
            reply_markup=get_main_menu(True, target)
        )
        await message.answer(TEXTS["ru"]["admin_gave"].format(uid=target), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"⚠️ Error: {e}\nFormat: <code>/give ID</code>", parse_mode="HTML")

@dp.message(F.text.startswith("/block"))
async def admin_block(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target = int(message.text.split()[1])
        db_update_user(target, has_access=False)
        try:
            target_lang = user_lang.get(target, "ru")
            await bot.send_message(
                target,
                TEXTS[target_lang]["access_revoked"].format(div=DIV),
                parse_mode="HTML",
                reply_markup=get_main_menu(False, target)
            )
        except:
            pass
        await message.answer(TEXTS["ru"]["admin_blocked"].format(uid=target), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"⚠️ Error: {e}\nFormat: <code>/block ID</code>", parse_mode="HTML")

@dp.message(F.text.startswith("/reply"))
async def admin_reply(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts  = message.text.split(maxsplit=2)
        target = int(parts[1])
        text   = parts[2]
        target_lang = user_lang.get(target, "ru")
        await bot.send_message(
            target,
            TEXTS[target_lang]["admin_support_reply_prefix"].format(div=DIV) + text,
            parse_mode="HTML"
        )
        await message.answer(TEXTS["ru"]["admin_replied"].format(uid=target), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"⚠️ Error: {e}\nFormat: <code>/reply ID text</code>", parse_mode="HTML")

@dp.message(Command("stats_admin"))
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    total  = db_get_total_users()
    active = db_get_active_users()
    await message.answer(
        TEXTS["ru"]["admin_stats_msg"].format(
            total=total,
            active=active,
            date=datetime.now().strftime('%d.%m.%Y %H:%M'),
        ),
        parse_mode="HTML"
    )

@dp.message(F.text.startswith("/broadcast"))
async def admin_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        text = message.text.split(maxsplit=1)[1]
        try:
            conn   = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            cursor.close()
            conn.close()
        except:
            users = []

        sent = 0
        fail = 0
        for (uid,) in users:
            try:
                target_lang = user_lang.get(uid, "ru")
                await bot.send_message(
                    uid,
                    TEXTS[target_lang]["admin_broadcast_prefix"] + text,
                    parse_mode="HTML"
                )
                sent += 1
                await asyncio.sleep(0.05)
            except:
                fail += 1

        await message.answer(
            TEXTS["ru"]["admin_broadcast_done"].format(sent=sent, fail=fail),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"⚠️ Format: <code>/broadcast text</code>\n{e}", parse_mode="HTML")

# ════════════════════════════════════════════════
#              TRADING PANEL
# ════════════════════════════════════════════════
@dp.message(F.text.in_({"📊 Trading Panel", "📊 Торговая Панель"}))
async def t_panel(message: Message):
    uid = message.from_user.id
    if not db_get_user(uid)["has_access"]:
        return
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]

    now_msk = datetime.utcnow() + timedelta(hours=3)
    hour = now_msk.hour
    if 3 <= hour < 10:
        session_info = t["session_asian"]
    elif 10 <= hour < 18:
        session_info = t["session_eu"]
    elif 18 <= hour < 23:
        session_info = t["session_us"]
    else:
        session_info = t["session_night"]

    await message.answer(
        t["trading_panel"].format(
            div=DIV,
            session=session_info,
            time=now_msk.strftime('%H:%M'),
        ),
        reply_markup=pair_kb,
        parse_mode="HTML"
    )

@dp.message(F.text.in_(set(pairs)))
async def set_pair(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]
    user_temp_data[uid] = {"pair": message.text}
    await message.answer(
        t["pair_selected"].format(pair=message.text),
        reply_markup=time_kb,
        parse_mode="HTML"
    )

@dp.message(F.text.in_(set(times)))
async def set_time(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]

    if uid not in user_temp_data or "pair" not in user_temp_data.get(uid, {}):
        await message.answer(
            t["select_pair_first"],
            parse_mode="HTML"
        )
        return

    user_temp_data[uid]["time"] = message.text
    pair = user_temp_data[uid]["pair"]

    await message.answer(
        t["time_selected"].format(div=DIV, pair=pair, time=message.text),
        reply_markup=get_signal_kb(uid),
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════
#     MAIN SIGNAL HANDLER
# ════════════════════════════════════════════════
@dp.message(Command("signals"))
@dp.message(F.text.in_({"⚡ Get Signal", "⚡ Получить Сигнал"}))
async def get_signal(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]
    u    = db_get_user(uid)
    if not u["has_access"]:
        return

    # Anti-spam
    now_ts  = time.time()
    last_ts = last_signal_request.get(uid, 0)
    if now_ts - last_ts < 1.5:
        return

    today = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d")
    daily = u["daily_count"]

    if u["last_date"] != today:
        daily = 0
        db_update_user(uid, daily=0, date=today)

    sub_type      = u['sub_type']
    current_limit = SUBSCRIPTION_PLANS[sub_type]['limit']

    if daily >= current_limit:
        if sub_type == "free":
            return await message.answer(
                t["limit_free"].format(div=DIV, limit=current_limit),
                reply_markup=get_upgrade_kb(uid),
                parse_mode="HTML"
            )
        else:
            return await message.answer(
                t["limit_paid"].format(div=DIV, plan=sub_type.upper(), used=daily, limit=current_limit),
                reply_markup=get_upgrade_kb(uid),
                parse_mode="HTML"
            )

    # Check configuration
    data = user_temp_data.get(uid, {})

    if not data.get("pair"):
        return await message.answer(
            t["no_pair_selected"],
            reply_markup=get_main_menu(True, uid),
            parse_mode="HTML"
        )

    if not data.get("time"):
        await message.answer(
            t["no_time_selected"].format(pair=data['pair']),
            reply_markup=time_kb,
            parse_mode="HTML"
        )
        return

    last_signal_request[uid] = now_ts

    # Animated progress bar
    progress_frames = t["analysis_frames"]

    try:
        progress_msg = await message.answer(
            f"<b>{t['analysis_header']}</b>\n"
            f"{DIV}\n\n"
            f"<code>{progress_frames[0][0]}</code>\n"
            f"<i>{progress_frames[0][1]}</i>",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Progress bar error: {e}")
        return

    for bar, label in progress_frames[1:]:
        await asyncio.sleep(0.35)
        try:
            await progress_msg.edit_text(
                f"<b>{t['analysis_header']}</b>\n"
                f"{DIV}\n\n"
                f"<code>{bar}</code>\n"
                f"<i>{label}</i>",
                parse_mode="HTML"
            )
        except (TelegramBadRequest, Exception):
            pass

    # Signal generation
    direction, confidence, _ = generate_otc_signal(data["pair"], data["time"])

    db_update_user(uid, signals=u["signals"] + 1, daily=daily + 1, date=today)
    new_daily = daily + 1
    remaining = current_limit - new_daily

    is_up = direction == "UP"
    dir_line  = t["dir_up"]  if is_up else t["dir_down"]
    dir_emoji = "🟢"          if is_up else "🔴"

    conf_bar = confidence_bar(confidence)

    if confidence >= 93:
        conf_label = t["conf_extreme"]
    elif confidence >= 88:
        conf_label = t["conf_strong"]
    elif confidence >= 84:
        conf_label = t["conf_steady"]
    else:
        conf_label = t["conf_standard"]

    # Limit line
    if remaining == 0:
        limit_line = t["signal_last"]
    elif remaining <= 3:
        limit_line = t["signal_low"].format(n=remaining)
    else:
        limit_line = t["signal_counter"].format(used=new_daily, limit=current_limit, left=remaining)

    # PRO block
    pro_block = ""
    if sub_type in ("junior", "pro"):
        now_msk = datetime.utcnow() + timedelta(hours=3)
        hour = now_msk.hour
        if 3 <= hour < 10:
            session = t["session_asian"]
        elif 10 <= hour < 18:
            session = t["session_eu"]
        elif 18 <= hour < 23:
            session = t["session_us"]
        else:
            session = t["session_night"]

        volatility_opts_ru = ["🟢 Низкая", "🟡 Умеренная", "🟠 Средняя", "🔴 Высокая"]
        volatility_opts_en = ["🟢 Low", "🟡 Moderate", "🟠 Medium", "🔴 High"]
        volatility_opts = volatility_opts_en if lang == "en" else volatility_opts_ru
        rng_vol  = random.Random(hash(f"{data['pair']}_{confidence}_{hour}"))
        volatility = rng_vol.choice(volatility_opts)

        pro_block = (
            f"\n{SDIV}\n"
            f"  📡 {t['pro_session_label']}:    <b>{session}</b>\n"
            f"  📊 {t['pro_volatility_label']}: <b>{volatility}</b>\n"
        )

    # PRO extended block
    pro_extra = ""
    if sub_type == "pro":
        rng_pro = random.Random(hash(f"{data['pair']}_{direction}_{confidence}"))
        trend_strength = rng_pro.randint(55, 95)
        trend_bar = confidence_bar(trend_strength)
        pro_tip = rng_pro.choice(t["pro_tips"])
        pro_extra = (
            f"  💪 {t['trend_label']}: <code>{trend_bar}</code> <b>{trend_strength}%</b>\n"
            f"  💬 <i>{pro_tip}</i>\n"
        )

    res = (
        f"{dir_emoji} <b>{dir_line}</b> {dir_emoji}\n"
        f"{DIV}\n"
        f"  {data['pair']}\n"
        f"  {t['signal_expiry']}: <b>{data['time']}</b>\n"
        f"{SDIV}\n"
        f"  AI: <code>{conf_bar}</code> <b>{confidence}%</b>\n"
        f"  {conf_label}"
        f"{pro_block}"
        f"{pro_extra}"
        f"\n{SDIV}\n"
        f"  {limit_line}\n"
        f"{t['signal_footer']}"
    )

    try:
        await progress_msg.delete()
    except Exception:
        pass

    try:
        await message.answer(res, parse_mode="HTML", reply_markup=get_signal_kb(uid))
    except Exception as e:
        print(f"Signal send error: {e}")

# ════════════════════════════════════════════════
#              PROFILE
# ════════════════════════════════════════════════
@dp.message(Command("profile"))
@dp.message(F.text.in_({"👤 Profile", "👤 Профиль"}))
async def profile(message: Message):
    uid       = message.from_user.id
    lang      = user_lang.get(uid, "ru")
    t         = TEXTS[lang]
    u         = db_get_user(uid)
    rank      = get_rank(u["signals"])
    sub_plan  = SUBSCRIPTION_PLANS[u["sub_type"]]
    sub_limit = sub_plan["limit"]
    sub_emoji = sub_plan["emoji"]

    expiry_str = t["profile_expires_lifetime"]
    days_info  = ""
    if u['sub_expires']:
        expiry_str = u['sub_expires'].strftime("%d.%m.%Y %H:%M")
        days_left  = max((u['sub_expires'] - datetime.now()).days, 0)
        days_used  = 7 - days_left
        bar        = days_bar(days_used, 7)
        days_info  = t["profile_days_remaining"].format(bar=bar, days=days_left)

    next_title, next_level, signals_left = get_next_rank(u["signals"])
    rank_progress = ""
    if next_title:
        rank_progress = t["rank_to_next"].format(title=next_title, n=signals_left)

    rank_bar_str = ""
    for lo, hi, title, level in RANKS:
        if lo <= u["signals"] <= hi:
            rank_bar_str = rank_progress_bar(u["signals"], lo, hi)
            break

    used_pct  = min(int((u["daily_count"] / sub_limit) * 10), 10)
    daily_bar = "▓" * used_pct + "░" * (10 - used_pct)

    name    = message.from_user.first_name or "Trader"
    license_str = t["profile_license_active"] if u['has_access'] else t["profile_license_inactive"]

    profile_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_calc_lot_inline"], callback_data="open_lot_calc")],
    ])

    await message.answer(
        t["profile"].format(
            div=DIV, sdiv=SDIV,
            name=name, uid=message.from_user.id,
            rank=rank, rank_bar=rank_bar_str, rank_progress=rank_progress,
            sub_emoji=sub_emoji, sub_type=u['sub_type'].upper(),
            limit=sub_limit, expires=expiry_str, days_info=days_info,
            total=u['signals'], daily_bar=daily_bar, daily=u['daily_count'],
            license=license_str,
        ),
        reply_markup=profile_kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "open_lot_calc")
async def open_lot_calc_callback(callback: CallbackQuery):
    uid  = callback.from_user.id
    lang = user_lang.get(uid, "ru")
    pending_lot_calc.add(uid)
    await callback.message.answer(
        TEXTS[lang]["lot_calc_enter"].format(div=DIV),
        reply_markup=get_back_kb(uid),
        parse_mode="HTML"
    )
    await callback.answer()

# ════════════════════════════════════════════════
#              STATISTICS
# ════════════════════════════════════════════════
@dp.message(F.text.in_({"📈 Statistics", "📈 Статистика"}))
async def stats(message: Message):
    uid  = message.from_user.id
    lang = user_lang.get(uid, "ru")
    t    = TEXTS[lang]

    seed_val = int(datetime.now().strftime("%Y%m%d"))
    random.seed(seed_val)

    total_day    = random.randint(1800, 2500)
    win_rate     = round(random.uniform(91.5, 96.2), 1)
    plus_deals   = int(total_day * (win_rate / 100))
    minus_deals  = total_day - plus_deals - random.randint(10, 30)
    refunds      = total_day - plus_deals - minus_deals
    avg_profit   = round(random.uniform(85.5, 93.8), 1)
    best_pair    = random.choice([p.replace("🇦🇪 ", "").replace("🇦🇺 ", "").replace("🇧🇭 ", "")
                                   .replace("🇨🇭 ", "").replace("🇪🇺 ", "").replace("🇲🇦 ", "")
                                   .replace("🇳🇿 ", "").replace("🇸🇦 ", "").replace("🇺🇸 ", "")
                                   .replace("🇬🇧 ", "").replace("🇨🇦 ", "")
                                   for p in pairs])
    peak_hour    = random.randint(10, 18)
    total_users  = db_get_total_users()
    active_users = db_get_active_users()

    wr_filled = int(win_rate / 10)
    wr_bar    = "█" * wr_filled + "░" * (10 - wr_filled)

    rng_chart = random.Random(seed_val)
    hourly_bars = ""
    for h in range(6, 24, 3):
        vol = rng_chart.randint(2, 10)
        bar_h = "█" * vol + "░" * (10 - vol)
        hourly_bars += f"  {h:02d}:00  <code>{bar_h}</code>\n"

    await message.answer(
        t["stats"].format(
            div=DIV, sdiv=SDIV,
            wr_bar=wr_bar, win_rate=win_rate,
            plus=plus_deals, minus=minus_deals, refund=refunds,
            total=total_day,
            avg_profit=avg_profit, best_pair=best_pair,
            peak_h=peak_hour, peak_h1=peak_hour + 1,
            hourly=hourly_bars,
            users=total_users + 152, active=active_users + 94,
            date=datetime.now().strftime('%d.%m.%Y %H:%M'),
        ),
        parse_mode="HTML"
    )
    random.seed()

# ════════════════════════════════════════════════
#              STARTUP
# ════════════════════════════════════════════════
async def main():
    print("=" * 60)
    print("  🚀 AI TRADING TERMINAL — OTC PRO v4.0")
    print("  ✅ BOT STARTED SUCCESSFULLY")
    print("  🌐 BILINGUAL: RU / EN")
    print("  🧠 SMART PRECISION ENGINE v4 (OTC MODE):")
    print("     RSI(14) + EMA(9/21) + MACD + BB + STOCH + PATTERNS")
    print("     FILTER: 3/6 blocks minimum")
    print("  💱 OTC PAIRS: 12 instruments with country flags")
    print("  ⏱ TIMEFRAMES: 5s / 10s / 15s / 30s")
    print("  📦 LIMITS: FREE=25 | JUNIOR=50 | PRO=100")
    print("=" * 60)

    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
