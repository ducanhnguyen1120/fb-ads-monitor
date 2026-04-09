import os
import json
import requests

# ── Load config ───────────────────────────────────────────────────────────────

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"accounts": []}

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt(n):
    return f"{int(n):,}"

def send_discord(webhook_url, embeds):
    r = requests.post(webhook_url, json={"embeds": embeds}, timeout=10)
    print(f"Discord → {r.status_code}")

# ── Check one account ─────────────────────────────────────────────────────────

def check_account(access_token, account_cfg, discord_webhook):
    account_id            = str(account_cfg["id"]).lstrip("act_")
    spend_warn            = float(account_cfg.get("spend_limit_warning", 150000))
    billing_warn          = float(account_cfg.get("billing_threshold_warning", 200000))

    url = f"https://graph.facebook.com/v19.0/act_{account_id}"
    params = {
        "fields": "name,currency,spend_cap,amount_spent,balance,billing_threshold_amount",
        "access_token": access_token,
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

    name       = data.get("name", f"act_{account_id}")
    currency   = data.get("currency", "VND")
    spend_cap  = float(data.get("spend_cap") or 0)
    spent      = float(data.get("amount_spent") or 0)
    balance    = float(data.get("balance") or 0)        # unbilled spend in current cycle
    billing_threshold = float(data.get("billing_threshold_amount") or 0)

    alerts = []

    # ── 1. Spend cap warning ──────────────────────────────────────────────────
    if spend_cap > 0:
        remaining_cap = spend_cap - spent
        pct = (spent / spend_cap) * 100
        print(f"[{name}] Spend cap: {fmt(spent)}/{fmt(spend_cap)} {currency} ({pct:.1f}%) — còn {fmt(remaining_cap)}")

        if remaining_cap <= spend_warn:
            color = 0xFF0000 if remaining_cap <= spend_warn * 0.5 else 0xFF8C00
            alerts.append({
                "title": "⚠️ Sắp đạt giới hạn chi tiêu (Spend Cap)!",
                "color": color,
                "fields": [
                    {"name": "Tài khoản",       "value": name,                           "inline": False},
                    {"name": "Đã tiêu",          "value": f"{fmt(spent)} {currency}",     "inline": True},
                    {"name": "Giới hạn",         "value": f"{fmt(spend_cap)} {currency}", "inline": True},
                    {"name": "Còn lại",          "value": f"**{fmt(remaining_cap)} {currency}**", "inline": True},
                    {"name": "% đã dùng",        "value": f"{pct:.1f}%",                 "inline": True},
                    {"name": "Ngưỡng cảnh báo",  "value": f"{fmt(spend_warn)} {currency}","inline": True},
                ],
                "footer": {"text": "FB Ads Monitor • Spend Cap Alert"},
            })
    else:
        print(f"[{name}] Không có spend cap")

    # ── 2. Billing threshold warning ──────────────────────────────────────────
    if billing_threshold > 0:
        remaining_billing = billing_threshold - balance
        pct_billing = (balance / billing_threshold) * 100
        print(f"[{name}] Billing threshold: {fmt(balance)}/{fmt(billing_threshold)} {currency} ({pct_billing:.1f}%) — còn {fmt(remaining_billing)}")

        if remaining_billing <= billing_warn:
            color = 0xFF0000 if remaining_billing <= billing_warn * 0.5 else 0x9B59B6
            alerts.append({
                "title": "💳 Sắp đến ngưỡng thanh toán (Billing Threshold)!",
                "color": color,
                "fields": [
                    {"name": "Tài khoản",           "value": name,                                   "inline": False},
                    {"name": "Chi tiêu chưa TT",    "value": f"{fmt(balance)} {currency}",           "inline": True},
                    {"name": "Ngưỡng thanh toán",   "value": f"{fmt(billing_threshold)} {currency}", "inline": True},
                    {"name": "Còn đến ngưỡng",      "value": f"**{fmt(remaining_billing)} {currency}**", "inline": True},
                    {"name": "% đã dùng",           "value": f"{pct_billing:.1f}%",                  "inline": True},
                    {"name": "Ngưỡng cảnh báo",     "value": f"{fmt(billing_warn)} {currency}",      "inline": True},
                ],
                "footer": {"text": "FB Ads Monitor • Billing Threshold Alert"},
            })
    else:
        # Billing threshold không lấy được từ API → bỏ qua, user tự cấu hình nếu cần
        print(f"[{name}] Không lấy được billing threshold từ API")

    if alerts:
        send_discord(discord_webhook, alerts)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    access_token    = os.environ["FB_ACCESS_TOKEN"]
    discord_webhook = os.environ["DISCORD_WEBHOOK_URL"]

    config   = load_config()
    accounts = config.get("accounts", [])

    # Fallback: nếu config chưa có accounts, dùng env var
    if not accounts:
        env_ids = os.environ.get("FB_AD_ACCOUNT_ID", "")
        for aid in [a.strip() for a in env_ids.split(",") if a.strip()]:
            accounts.append({"id": aid})

    if not accounts:
        print("Không có tài khoản nào được cấu hình.")
        return

    for acc in accounts:
        check_account(access_token, acc, discord_webhook)

if __name__ == "__main__":
    main()
