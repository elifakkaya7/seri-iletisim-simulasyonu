"""Seri iletişim bağlantı simülasyonu."""

from serisim.channel import VirtualChannel
from serisim.noise import NoiseModel
from serisim.receiver import Receiver
from serisim.sender import Sender

TEAM_ID = 1
PACKET_COUNT = 1000
SEND_INTERVAL = 0.5         # saniye (2 Hz)
BAUD_RATE = 57600
LATENCY = 0.05              # saniye
LOSS_PROB = 0.05            # paket kaybı olasılığı
BIT_FLIP_PROB = 0.0002      # bit başına bozulma olasılığı


def simulate(baud_rate, latency, loss_prob, bit_flip_prob, packet_count=PACKET_COUNT) -> dict:
    """Paketleri gönderir, kanaldan geçirir, alıcıya verir; sonuçları döndürür."""
    noise = NoiseModel(loss_prob, bit_flip_prob)
    channel = VirtualChannel(baud_rate, latency, noise)
    sender = Sender(TEAM_ID)
    receiver = Receiver()

    lost = 0
    total_time = 0.0

    for i in range(packet_count):
        time = i * SEND_INTERVAL
        packet = sender.create_packet(time)          # paket oluştur
        data, duration = channel.transmit(packet)    # kanaldan geçir
        total_time += duration

        if data is None:                             # paket kayboldu
            lost += 1
        else:
            receiver.receive(data, time + duration)  # alıcı kontrol eder

    result = {"sent": packet_count, "lost": lost, "total_time": total_time}
    result.update(receiver.stats())
    return result


def print_report(result: dict) -> None:
    """Sonuçları ekrana yazar."""
    sent = result["sent"]
    print(f"Gönderilen paket     : {sent}")
    print(f"Kaybolan             : {result['lost']}")
    print(f"Bozuk (checksum)     : {result['corrupted']}")
    print(f"Aralık dışı          : {result['out_of_range']}")
    print(f"Sağlam ulaşan        : {result['valid']} (%{100 * result['valid'] / sent:.1f})")
    print(f"Toplam iletim süresi : {result['total_time']:.2f} s")


if __name__ == "__main__":
    print(f"Ayarlar: {BAUD_RATE} baud, {LATENCY} s gecikme, "
          f"kayıp {LOSS_PROB}, bit flip {BIT_FLIP_PROB}\n")
    result = simulate(BAUD_RATE, LATENCY, LOSS_PROB, BIT_FLIP_PROB)
    print_report(result)