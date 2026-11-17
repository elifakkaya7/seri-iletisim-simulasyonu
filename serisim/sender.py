import math
import random


class Sender:
    def __init__(self, team_id, seed=None):
        self.team_id = team_id
        self.rng = random.Random(seed)

    def generate_telemetry(self, time):
        lock = 1 if self.rng.random() < 0.1 else 0
        return {
            "takim_numarasi": self.team_id,
            "iha_enlem": 41.0 + 0.0001 * time,
            "iha_boylam": 29.0 + 0.0001 * time,
            "iha_irtifa": 100 + 20 * math.sin(time / 10),
            "iha_dikilme": 10 * math.sin(time / 5),
            "iha_yonelme": (time * 3) % 360,
            "iha_yatis": 15 * math.sin(time / 7),
            "iha_hiz": 20 + self.rng.uniform(-2, 2),
            "iha_batarya": max(0, 100 - int(time / 10)),
            "iha_otonom": 1,
            "iha_kilitlenme": lock,
            "hedef_merkez_X": 300 if lock else 0,
            "hedef_merkez_Y": 200 if lock else 0,
            "hedef_genislik": 50 if lock else 0,
            "hedef_yukseklik": 40 if lock else 0,
            "gps_saati": {
                "saat": int(time // 3600) % 24,
                "dakika": int(time // 60) % 60,
                "saniye": int(time) % 60,
                "milisaniye": int((time % 1) * 1000),
            },
        }

    def create_packet(self, time):
        telemetry = self.generate_telemetry(time)
        seq = int(time * 2) % 256   # 2 Hz, 0-255 arası döner
        # Packet'in gerçek çağrısı Elif'in koduna göre yazılacak, örnek:
        # return Packet(seq, telemetry)
        raise NotImplementedError("Packet'in imzasını Elif'ten öğren")


if __name__ == "__main__":
    s = Sender(team_id=1, seed=1)
    for t in (0, 0.5, 1.0):
        print(s.generate_telemetry(t))