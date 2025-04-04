import asyncio
import websockets
import json
import os
import re
import datetime
from aiohttp import web  # HTTP endpoint için

bagislar = []
donation_hash_set = set()  # İsteğe bağlı, tekrar kontrolü için kullanılabilir.
json_dosya = "bagislar.json"
log_dosya = "bagis_log.txt"

def bagis_ekle(mesaj):
    print(f"Yeni Bağış Geldi: {mesaj}")
    try:
        parcalar = mesaj.strip().split(" - ")
        if len(parcalar) < 5:
            raise ValueError("Mesaj beklenen formatta değil")
        kanal_isim = parcalar[0].strip()
        isim = parcalar[1].strip()
        miktar_raw = parcalar[2].strip()
        bagis_turu = parcalar[3].strip()
        mesaj_yazi = " - ".join(parcalar[4:]).strip()
        match = re.search(r"([\d\.,]+)", miktar_raw)
        if not match:
            raise ValueError("Miktar bulunamadı")
        miktar = float(match.group(1).replace(",", "."))
        # SAHTE TESPİT KONTROLÜ: aynı isim + aynı miktar + son 60 saniye
        if bagislar:
            son = bagislar[-1]
            zaman_farki = datetime.datetime.now() - datetime.datetime.strptime(son["tarih"], "%Y-%m-%d %H:%M:%S")
            if (son["isim"] == isim and son["miktar"] == miktar and zaman_farki.total_seconds() < 60):
                print("⚠️ Sistemsel tekrar tespit edildi, atlandı.")
                return
        veri = {
            "kanal": kanal_isim.strip("[] "),
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

async def handler(websocket):
    async for message in websocket:
        bagis_ekle(message)

async def temizle():
    global bagislar, donation_hash_set
    while True:
        await asyncio.sleep(50000)  # İstenilen süreye göre ayarlayın
        bagislar.clear()
        donation_hash_set.clear()
        with open(json_dosya, "w", encoding="utf-8") as f:
            json.dump([], f)
        print("⏳ Veriler sıfırlandı, sistem sıfırdan devam ediyor...")

# Manuel reset için HTTP endpoint
async def reset_handler(request):
    global bagislar, donation_hash_set
    bagislar.clear()
    donation_hash_set.clear()
    with open(json_dosya, "w", encoding="utf-8") as f:
        json.dump([], f)
    print("⏳ Manuel reset yapıldı.")
    return web.Response(text="Donations reset.")

async def start_http_server():
    app = web.Application()
    app.add_routes([web.get('/reset', reset_handler)])
    runner = web.AppRunner(app)
    await runner.setup()
    # 0.0.0.0, tüm arayüzlerden bağlantıyı kabul eder.
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("HTTP server started at http://192.168.1.15:8080 (accessible from your LAN)")

async def main():
    if not os.path.exists(json_dosya):
        with open(json_dosya, "w", encoding="utf-8") as f:
            json.dump([], f)
    # WebSocket sunucusunu 0.0.0.0 IP'si üzerinde 5679 portunda başlatıyoruz.
    ws_server = websockets.serve(handler, "0.0.0.0", 5679)
    await start_http_server()
    print("Sunucu başlatıldı, bekleniyor...")
    await asyncio.gather(
        ws_server,
        temizle(),
        asyncio.Future()
    )

if __name__ == "__main__":
    asyncio.run(main())
