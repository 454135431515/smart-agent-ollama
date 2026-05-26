import json
import os
import threading
import time
from datetime import datetime
from typing import Any, Callable

from app.registry import TOOL_REGISTRY
from tools.finance import get_exchange_rate
from tools.onchain import get_gas_price

# Hard cap for the whole snapshot fetch. Individual tools also have their own
# request timeouts (~5s in requests/web3), but we don't trust any single layer —
# a slow tool must never delay the REPL.
_SNAPSHOT_TIMEOUT_S = 3.0


def _safe_call(fn: Callable[..., str], **kwargs: Any) -> dict:
    """Call a tool function and return its JSON output as a dict.

    Tool functions return JSON strings — either a success payload or
    {"error": "..."}. We never let an exception escape: a broken
    dashboard must not block the agent from starting.
    """
    try:
        raw = fn(**kwargs)
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001 — UI init, never propagate
        return {"error": f"{type(exc).__name__}: {exc}"}


def _fetch_snapshot() -> dict[str, dict]:
    """Fetch all snapshot values in parallel with a hard total deadline.

    Uses daemon threads (not ThreadPoolExecutor) so that a hanging job
    cannot block the main thread past _SNAPSHOT_TIMEOUT_S. ThreadPoolExecutor's
    context manager calls shutdown(wait=True) on exit, which defeats the
    timeout. Daemon threads, by contrast, die with the process.
    """
    jobs: dict[str, tuple[Callable, dict]] = {
        "usd": (get_exchange_rate, {"currency_code": "USD"}),
        "eur": (get_exchange_rate, {"currency_code": "EUR"}),
        "gas": (get_gas_price, {}),
    }

    results: dict[str, dict] = {k: {"error": "timeout"} for k in jobs}

    def worker(key: str, fn: Callable, kwargs: dict) -> None:
        results[key] = _safe_call(fn, **kwargs)

    threads = [
        threading.Thread(target=worker, args=(key, fn, kw), daemon=True)
        for key, (fn, kw) in jobs.items()
    ]
    for t in threads:
        t.start()

    deadline = time.monotonic() + _SNAPSHOT_TIMEOUT_S
    for t in threads:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        t.join(timeout=remaining)

    return results


def _fmt_fx(payload: dict, label: str, emoji: str) -> str:
    if "error" in payload:
        return f"    {emoji} {label:<5}: n/a"
    rate = payload.get("rate_rub")
    return f"    {emoji} {label:<5}: {rate} ₽"


def _fmt_gas(payload: dict) -> str:
    if "error" in payload:
        return "    ⛽ Gas (Base): n/a"
    gwei = payload.get("gas_price_gwei")
    return f"    ⛽ Gas (Base): {gwei} gwei"


def show_dashboard() -> None:
    now = datetime.now()
    months = [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ]
    weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    date_str = f"{now.day} {months[now.month - 1]} {now.year}, {weekdays[now.weekday()]}"

    model_name = os.getenv("MODEL_NAME", "AI-модель")

    friendly_capabilities = {
        "get_weather": "🌤  Узнавать точную погоду в любом городе",
        "get_exchange_rate": "💰 Узнавать курсы валют (USD, EUR, JPY, ...)",
        "calculator": "🧮 Проводить математические расчеты",
        "read_file": "📄 Читать ваши текстовые документы",
        "save_note": "📝 Сохранять и вести ваши заметки",
        "get_current_time": "⏰ Подсказывать время по всему миру",
        "get_eth_balance": "🪙 Проверять ETH-баланс на Base",
        "get_erc20_balance": "🪙 Проверять баланс ERC-20 токенов на Base",
        "get_recent_transactions": "📜 Смотреть недавние транзакции на Base",
        "get_gas_price": "⛽ Узнавать текущую цену газа на Base",
    }

    print("\n" + "=" * 60)
    print("   ✨ Добро пожаловать! Я ваш умный AI-ассистент ✨")
    print("=" * 60)
    print(f" 📅 Сегодня: {date_str}")
    print(f" 🧠 Мозг   : {model_name}")

    print("\n 📊 Сводка рынка:")
    snapshot = _fetch_snapshot()
    print(_fmt_fx(snapshot["usd"], "USD", "💵"))
    print(_fmt_fx(snapshot["eur"], "EUR", "💶"))
    print(_fmt_gas(snapshot["gas"]))

    print("\n 🛠️  Вот что я умею делать:")
    for tool_name in TOOL_REGISTRY.keys():
        if tool_name == "list_notes":
            continue
        description = friendly_capabilities.get(tool_name, f"🔧 {tool_name} (Системный инструмент)")
        print(f"    {description}")

    print("-" * 60)
    print(" 💡 ПОДСКАЗКИ:")
    print("  • Попробуйте спросить: «Сколько будет 200 долларов в рублях?»")
    print("  • Напишите /clear, чтобы я забыл прошлый разговор и мы начали заново.")
    print("=" * 60 + "\n")
