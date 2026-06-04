import requests
import json
import os

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
    client = __import__('anthropic').Anthropic()
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": f"""Buscá los productos y talles disponibles en: {PAGE_URL}
Devolvé SOLO JSON sin markdown:
{{\"products\":[{{\"name\":\"nombre\",\"talles\":[\"S\",\"M\",\"L\"]}}]}}"""
        }]
    )
    text = "".join(b.text for b in msg.content if hasattr(b, "text"))
    text = text.replace("```json","").replace("```","").strip()
    match = __import__('re').search(r'\{[\s\S]*\}', text)
    return json.loads(match.group())["products"] if match else []

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None

def save_state(products):
    with open(STATE_FILE, "w") as f:
        json.dump(products, f)

def main():
    current = get_stock()
    previous = load_state()

    if previous is None:
        save_state(current)
        send_telegram(f"🤖 Monitor iniciado!\n{len(current)} producto(s) encontrado(s) en Tienda Pincha.")
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
                send_telegram(f"↑ NUEVO TALLE disponible!\n{p['name']}\nNuevos: {', '.join(added)}\n🔗 {PAGE_URL}")
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
