import os
import json
import requests

# Currencies that have no decimal places (API returns full units)
ZERO_DECIMAL = {"VND", "JPY", "KRW", "TWD", "IDR", "CLP", "ISK", "GNF", "UGX"}

# ── Load config ───────────────────────────────────────────────────────────────

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"accounts": []}

# ── Helpers ───────────────────────────────────────────────────────────────────

def to_major(amount, currency):
    """Convert API minor unit → major unit (cents → dollars, VND stays VND)."""
    if currency in ZERO_DECIMAL:
        return amount
    return amount / 100

def fmt(n, currency):
    if currency in ZERO_DECIMAL:
        return f"{int(n):,}"
    return f"{n:,.2f}"

def send_discord(webhook_url, embeds):
    r = requests.post(webhook_url, json={"embeds": embeds}, timeout=10)
    print(f"Discord → {r.status_code}")

# ── Check one account ─────────────────────────────────────────────────────────

def check_account(default_token, account_cfg, discord_webhook):
    account_id = str(account_cfg["id"]).lstrip("act_")
    spend_warn = float(account_cfg.get("spend_limit_warning", 150000))

    # Per-account token takes priority over global token
    token = account_cfg.get("access_token") or default_token

    url = f"https://graph.facebook.com/v19.0/act_{account_id}"
    params = {
        "fields": "name,currency,spend_cap,amount_spent,balance",
        "access_token": token,
    }

    res = requests.get(url, params=params, timeout=15)
    data = res.json()

    if "error" in data:
        msg = data["error"].get("message", str(data["error"]))
        print(f"[{account_id}] Lỗi: {msg}")
        send_discord(discord_webhook, [{
            "title": "❌ FB Ads Monitor — Lỗi API",
            "description": f"Tài khoản `{account_id}`: {msg}",
            "color": 0xED4245,
            "footer": {"text": "FB Ads Monitor"},
        }])
        return

    name     = data.get("name", f"act_{account_id}")
    currency = data.get("currency", "VND")

    # Convert from API minor units to major units
    spend_cap = to_major(float(data.get("spend_cap") or 0), currency)
    spent     = to_major(float(data.get("amount_spent") or 0), currency)

    if spend_cap > 0:
        remaining_cap = spend_cap - spent
        pct = (spent / spend_cap) * 100
        print(f"[{name}] Spend cap: {fmt(spent, currency)}/{fmt(spend_cap, currency)} {currency} ({pct:.1f}%) — còn {fmt(remaining_cap, currency)}")

        if remaining_cap <= spend_warn:
            color = 0xFF0000 if remaining_cap <= spend_warn * 0.5 else 0xFF8C00
            send_discord(discord_webhook, [{
                "title": "⚠️ Sắp đạt giới hạn chi tiêu (Spend Cap)!",
                "color": color,
                "fields": [
                    {"name": "Tài khoản",      "value": name,                                        "inline": False},
                    {"name": "Đã tiêu",         "value": f"{fmt(spent, currency)} {currency}",        "inline": True},
                    {"name": "Giới hạn",        "value": f"{fmt(spend_cap, currency)} {currency}",    "inline": True},
                    {"name": "Còn lại",         "value": f"**{fmt(remaining_cap, currency)} {currency}**", "inline": True},
                    {"name": "% đã dùng",       "value": f"{pct:.1f}%",                               "inline": True},
                    {"name": "Ngưỡng cảnh báo", "value": f"{fmt(spend_warn, currency)} {currency}",   "inline": True},
                ],
                "footer": {"text": "FB Ads Monitor • Spend Cap Alert"},
            }])
    else:
        print(f"[{name}] Không có spend cap")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    default_token   = os.environ["FB_ACCESS_TOKEN"]
    discord_webhook = os.environ["DISCORD_WEBHOOK_URL"]

    config   = load_config()
    accounts = config.get("accounts", [])

    if not accounts:
        env_ids = os.environ.get("FB_AD_ACCOUNT_ID", "")
        for aid in [a.strip() for a in env_ids.split(",") if a.strip()]:
            accounts.append({"id": aid})

    if not accounts:
        print("Không có tài khoản nào được cấu hình.")
        return

    for acc in accounts:
        check_account(default_token, acc, discord_webhook)

if __name__ == "__main__":
    main()
