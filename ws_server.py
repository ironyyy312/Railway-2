import asyncio
import websockets
import json
import os
import re
import datetime
from aiohttp import web

bagislar = []
donation_hash_set = set()
json_dosya = "bagislar.json"
log_dosya = "bagis_log.txt"

def bagis_ekle(mesaj):
    print(f"Yeni Bağış Geldi: {mesaj}")
    try:
        parcalar = mesaj.strip().split(" - ")
        if len(parcalar) < 5:
            raise ValueError("Mesaj beklenen formatta değil")
        kanal_isim = parcalar[0].strip("[] ")
        isim = parcalar[1].strip()
        miktar_raw = parcalar[2].strip()
        bagis_turu = parcalar[3].strip()
        mesaj_yazi = " - ".join(parcalar[4:]).strip()
        match = re.search(r"([\d\.,]+)", miktar_raw)
        if not match:
            raise ValueError("Miktar bulunamadı")
        miktar = float(match.group(1).replace(",", "."))
        if bagislar:
            son = bagislar[-1]
            zaman_farki = datetime.datetime.now() - datetime.datetime.strptime(son["tarih"], "%Y-%m-%d %H:%M:%S")
            if (son["isim"] == isim and son["miktar"] == miktar and zaman_farki.total_seconds() < 60):
                print("⚠️ Sistemsel tekrar tespit edildi, atlandı.")
                return
        veri = {
            "kanal": kanal_isim,
            "isim": isim,
            "miktar": miktar,
            "turu": bagis_turu,
            "mesaj": mesaj_yazi,
            "tarih": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        bagislar.append(veri)
        with open(json_dosya, "w", encoding="utf-8") as f:
            json.dump(bagislar, f, ensure_ascii=False, indent=2)
        with open(log_dosya, "a", encoding="utf-8") as log:
            log.write(f'{veri["tarih"]} - {isim} - {miktar} TL - {bagis_turu} - {mesaj_yazi}\n')
    except Exception as e:
        print(f"HATA: Bağış ayrıştırılamadı: {e}")

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print("✅ Yeni bağlantı kuruldu.")
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            bagis_ekle(msg.data)
        elif msg.type == web.WSMsgType.ERROR:
            print(f"❌ WS bağlantı hatası: {ws.exception()}")
    print("🔌 Bağlantı kapatıldı.")
    return ws

async def reset_handler(request):
    global bagislar, donation_hash_set
    bagislar.clear()
    donation_hash_set.clear()
    with open(json_dosya, "w", encoding="utf-8") as f:
        json.dump([], f)
    print("♻️ Manuel reset yapıldı.")
    return web.Response(text="Donations reset.")

async def start():
    app = web.Application()
    app.add_routes([
        web.get("/ws", websocket_handler),
        web.get("/reset", reset_handler)
    ])
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Sunucu başlatılıyor (port {port})...")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(start())
