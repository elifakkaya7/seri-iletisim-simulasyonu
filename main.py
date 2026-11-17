"""Seri iletişim bağlantı simülasyonu.

Rapor, proje yönergesinin üç maddesine göre bölümlere ayrılmıştır:
5.1 sanal veri hattı, 5.2 gürültü ve hata, 5.3 protokol ve checksum.
"""

from serisim.channel import VirtualChannel
from serisim.noise import NoiseModel
from serisim.packet import PACKET_SIZE, PAYLOAD_SIZE
from serisim.receiver import Receiver
from serisim.sender import Sender

TEAM_ID = 1
PACKET_COUNT = 1000
SEND_INTERVAL = 0.5         # saniye (2 Hz)
BAUD_RATE = 57600
LATENCY = 0.05              # saniye
LOSS_PROB = 0.05            # paket kaybı olasılığı
BIT_FLIP_PROB = 0.0002      # bit başına bozulma olasılığı
SEED = 42                   # aynı seed ile her çalıştırmada aynı sonuç çıkar

# 5.1 tablosunda denenecek (baud rate, gecikme) çiftleri
CHANNEL_CASES = [(1200, 0.05), (9600, 0.05), (57600, 0.05), (115200, 0.05), (57600, 0.2)]

# 5.2 tablosunda denenecek (paket kaybı, bit flip) çiftleri
NOISE_CASES = [(0, 0), (LOSS_PROB, 0), (0, BIT_FLIP_PROB), (LOSS_PROB, BIT_FLIP_PROB),
               (0.2, 0.001)]


def simulate(baud_rate, latency, loss_prob, bit_flip_prob,
             packet_count=PACKET_COUNT, seed=SEED) -> dict:
    """Paketleri gönderir, kanaldan geçirir, alıcıya verir; sonuçları döndürür."""
    noise = NoiseModel(loss_prob, bit_flip_prob, seed=seed)
    channel = VirtualChannel(baud_rate, latency, noise)
    sender = Sender(TEAM_ID, seed=seed)
    receiver = Receiver()

    lost = 0          # kanalda gerçekten kaybolan
    flipped = 0       # kanalda en az bir biti bozulan
    missed = 0        # bozulduğu halde alıcının sağlam saydığı
    total_time = 0.0

    for i in range(packet_count):
        time = i * SEND_INTERVAL
        packet = sender.create_packet(time)          # paket oluştur
        data, duration = channel.transmit(packet)    # kanaldan geçir
        total_time += duration

        if data is None:                             # paket kayboldu
            lost += 1
            continue

        telemetry = receiver.receive(data, time + duration)   # alıcı kontrol eder
        if data != packet:                           # main orijinali bildiği için
            flipped += 1                             # bozulmayı kesin olarak görür
            if telemetry is not None:
                missed += 1

    stats = receiver.stats()
    result = {
        "sent": packet_count,
        "lost": lost,
        "seq_lost": stats.pop("lost"),               # alıcının SEQ ile bulduğu
        "flipped": flipped,
        "missed": missed,
        "avg_time": total_time / packet_count,
    }
    result.update(stats)
    return result


def percent(part, whole) -> str:
    return f"%{100 * part / whole:.1f}" if whole else "-"


def report_channel() -> None:
    """5.1: baud rate ve gecikmenin paket süresine etkisi."""
    print("--- 5.1 Sanal veri hattı: baud rate ve gecikmenin etkisi ---")
    print(f"{'Baud':>7}  {'Gecikme':>8}  {'Paket süresi':>12}  Durum")
    for baud, latency in CHANNEL_CASES:
        duration = VirtualChannel(baud, latency).transmission_time(PACKET_SIZE)
        if duration > SEND_INTERVAL:
            status = f"UYARI: {SEND_INTERVAL * 1000:.0f} ms gönderim aralığına sığmıyor"
        else:
            status = "OK"
        print(f"{baud:>7}  {latency * 1000:>5.0f} ms  {duration * 1000:>9.1f} ms  {status}")
    print(f"Süre = {PACKET_SIZE} bayt x 10 bit / baud + gecikme\n")


def report_noise() -> None:
    """5.2: paket kaybı ve bit flip olasılıklarının etkisi."""
    print("--- 5.2 Gürültü ve hata: paket kaybı ve bit flip'in etkisi ---")
    print(f"{'Kayıp':>6}  {'Bit flip':>8}  {'Kaybolan':>8}  {'Bozuk':>6}  {'Sağlam':>14}")
    for loss, flip in NOISE_CASES:
        r = simulate(BAUD_RATE, LATENCY, loss, flip)
        note = "   <- gürültüsüz kontrol" if loss == 0 and flip == 0 else ""
        print(f"{loss:>6}  {flip:>8}  {r['lost']:>8}  {r['corrupted']:>6}  "
              f"{r['valid']:>5} ({percent(r['valid'], r['sent']):>6}){note}")
    print()


def report_protocol() -> None:
    """5.3: paket yapısı, checksum ve alıcının hata tespiti."""
    r = simulate(BAUD_RATE, LATENCY, LOSS_PROB, BIT_FLIP_PROB)
    print(f"--- 5.3 Protokol ve checksum (kayıp {LOSS_PROB}, bit flip {BIT_FLIP_PROB}) ---")
    print(f"Gönderilen paket               : {r['sent']}")
    print(f"Kanalda kaybolan (gerçek)      : {r['lost']}")
    print(f"Alıcının SEQ ile bulduğu kayıp : {r['seq_lost']}")
    print(f"Kanalda bozulan paket          : {r['flipped']}")
    print(f"  Checksum'ın yakaladığı       : {r['corrupted']}")
    print(f"  Aralık kontrolünün yakaladığı: {r['out_of_range']}")
    print(f"  Fark edilmeden geçen         : {r['missed']}")
    print(f"Sağlam ulaşan                  : {r['valid']} ({percent(r['valid'], r['sent'])})")
    print(f"Ortalama paket süresi          : {r['avg_time'] * 1000:.1f} ms")


if __name__ == "__main__":
    print("=== SERİ İLETİŞİM BAĞLANTI SİMÜLASYONU ===")
    print(f"Paket yapısı: START(1) + SEQ(1) + LEN(1) + PAYLOAD({PAYLOAD_SIZE}) "
          f"+ CHECKSUM(1) = {PACKET_SIZE} bayt")
    print(f"Gönderim: {PACKET_COUNT} paket, {1 / SEND_INTERVAL:.0f} Hz, seed={SEED}\n")

    report_channel()
    report_noise()
    report_protocol()
