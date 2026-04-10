import sys
import requests

def exchange_token(app_id, app_secret, short_lived_token):
    url = "https://graph.facebook.com/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token,
    }
    res = requests.get(url, params=params, timeout=15)
    data = res.json()

    if "error" in data:
        print(f"Lỗi: {data['error'].get('message', str(data['error']))}")
        sys.exit(1)

    token = data["access_token"]
    expires_in = data.get("expires_in", 0)
    days = expires_in // 86400
    print(f"Long-lived token ({days} ngày):")
    print(token)
    return token

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python gen_token.py <APP_ID> <APP_SECRET> <SHORT_LIVED_TOKEN>")
        sys.exit(1)
    exchange_token(sys.argv[1], sys.argv[2], sys.argv[3])
