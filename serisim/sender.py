import math
import random

from serisim.packet import Packet

# GPS saati simülasyon başında 11:38:37 olsun (saniye cinsinden)
GPS_START = 11 * 3600 + 38 * 60 + 37


class Sender:
    def __init__(self, team_id, seed=None):
        self.team_id = team_id
        self.rng = random.Random(seed)

    def generate_telemetry(self, time):
        """Verilen simülasyon saniyesi için sahte telemetri sözlüğü üretir."""
        lock = 1 if self.rng.random() < 0.1 else 0
        gps = GPS_START + time

        return {
            "takim_numarasi": self.team_id,
            "iha_enlem": 41.0 + 0.0001 * time,
            "iha_boylam": 29.0 + 0.0001 * time,
            "iha_irtifa": 100 + 20 * math.sin(time / 10),
            "iha_dikilme": 10 * math.sin(time / 5),         # -90..90 içinde
            "iha_yonelme": (time * 3) % 360,                # 0..360 içinde
            "iha_yatis": 15 * math.sin(time / 7),           # -90..90 içinde
            "iha_hiz": 20 + self.rng.uniform(-2, 2),        # negatif olamaz
            "iha_batarya": max(0, 100 - int(time / 10)),    # int, 0..100
            "iha_otonom": 1,
            "iha_kilitlenme": lock,
            # kilitlenme 1 ise hedef alanları sıfırdan farklı olmalı
            "hedef_merkez_X": 300 + int(20 * math.sin(time)) if lock else 0,
            "hedef_merkez_Y": 200 + int(20 * math.cos(time)) if lock else 0,
            "hedef_genislik": 50 if lock else 0,
            "hedef_yukseklik": 40 if lock else 0,
            "gps_saati": {
                "saat": int(gps // 3600) % 24,
                "dakika": int(gps // 60) % 60,
                "saniye": int(gps) % 60,
                "milisaniye": int((gps % 1) * 1000),
            },
        }

    def create_packet(self, time):
        """Telemetriyi üretir ve Packet nesnesi olarak döndürür."""
        seq = int(time * 2)          # 2 Hz: her 0,5 saniyede bir paket
        return Packet(seq, self.generate_telemetry(time))


if __name__ == "__main__":
    s = Sender(team_id=1, seed=1)

    p = s.create_packet(0)
    data = p.encode()
    print("Paket boyutu:", len(data))                 # 57 olmalı

    back = Packet.decode(data)
    print("Sıra no:", back.seq)                       # 0 olmalı
    print("Telemetri:", back.telemetry)

    # Her pakette değerler değişiyor mu?
    a = s.generate_telemetry(0.5)
    b = s.generate_telemetry(1.0)
    print("Telemetri değişiyor mu:", a != b)          # True olmalı

    # 1000 paketin hepsi 57 bayt ve decode edilebilir mi?
    for i in range(1000):
        Packet.decode(s.create_packet(i / 2).encode())
    print("1000 paket sorunsuz")