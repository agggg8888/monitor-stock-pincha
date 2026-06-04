import requests
import json
import os
import re
from bs4 import BeautifulSoup

PAGE_URL = "https://tiendapincha.com/la-utileria/"
TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT  = os.environ["TG_CHAT"]
STATE_FILE = "state.json"

def send_telegram(text):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT, "text": text}
    )

def get_stock():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = requests.get(PAGE_URL, headers=headers, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")

    products = []
    for product in soup.select(".product, .type-product, article.product"):
        name_el = product.select_one(".woocommerce-loop-product__title, h2, .product-title")
        name = name_el.get_text(strip=True) if name_el else "Producto sin nombre"

        talles = []
        for talle in product.select(".swatchly-term-item, .swatch-label, .variation-selector, option"):
            t = talle.get_text(strip=True)
            if t and t.upper() in ["XS","S","M","L","XL","XXL","XXXL","2XL","3XL","UNICO","U"]:
                talles.append(t.upper())

        products.append({"name": name, "talles": list(set(talles))})

    return products

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None

def save_state(products):
    with open(STATE_FILE, "w") as f:
        json.dump(products, f)

def main():
    try:
        current = get_stock()
    except Exception as e:
        send_telegram(f"⚠️ Error al revisar la página: {e}")
        return

    previous = load_state()

    if previous is None:
        save_state(current)
        nombres = "\n".join(f"• {p['name']}" for p in current) if current else "ninguno"
        send_telegram(f"🤖 Monitor iniciado!\n{len(current)} producto(s) encontrado(s):\n{nombres}\n🔗 {PAGE_URL}")
        return

    prev_map = {p["name"]: p["talles"] for p in previous}
    cambios = False

    for p in current:
        if p["name"] not in prev_map:
            send_telegram(f"✦ NUEVO PRODUCTO!\n{p['name']}\nTalles: {', '.join(p['talles']) or 'sin talles'}\n🔗 {PAGE_URL}")
            cambios = True
        else:
            added = [t for t in p["talles"] if t not in prev_map[p["name"]]]
            removed = [t for t in prev_map[p["name"]] if t not in p["talles"]]
            if added:
                send_telegram(f"↑ NUEVO TALLE!\n{p['name']}\nNuevos: {', '.join(added)}\n🔗 {PAGE_URL}")
                cambios = True
            if removed:
                send_telegram(f"↓ Talle agotado\n{p['name']}\nAgotados: {', '.join(removed)}")
                cambios = True

    for p in previous:
        if not any(c["name"] == p["name"] for c in current):
            send_telegram(f"⚠️ Producto removido: {p['name']}")
            cambios = True

    save_state(current)
    if not cambios:
        print("Sin cambios.")

if __name__ == "__main__":
    main()
