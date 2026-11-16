"""Alıcı: gelen paketi açar, kontrol eder ve sayaç tutar."""

from serisim.packet import Packet

INF = float("inf")

# Geçerli aralıklar (Haberleşme Dokümanı)
RANGES = {
    "takim_numarasi": (0, 255),
    "iha_enlem": (-90, 90),
    "iha_boylam": (-180, 180),
    "iha_irtifa": (0, INF),
    "iha_dikilme": (-90, 90),
    "iha_yonelme": (0, 360),
    "iha_yatis": (-90, 90),
    "iha_hiz": (0, INF),
    "iha_batarya": (0, 100),
    "iha_otonom": (0, 1),
    "iha_kilitlenme": (0, 1),
    "hedef_merkez_X": (0, 65535),
    "hedef_merkez_Y": (0, 65535),
    "hedef_genislik": (0, 65535),
    "hedef_yukseklik": (0, 65535),
}
GPS_RANGES = {"saat": (0, 23), "dakika": (0, 59), "saniye": (0, 59), "milisaniye": (0, 999)}
TARGET_FIELDS = ["hedef_merkez_X", "hedef_merkez_Y", "hedef_genislik", "hedef_yukseklik"]


class Receiver:
    def __init__(self):
        self.valid = 0          # sağlam paket sayısı
        self.corrupted = 0      # checksum ya da yapı hatası
        self.out_of_range = 0   # checksum tuttu ama değer aralık dışında

    def receive(self, data: bytes, time: float) -> dict | None:
        """Paket sağlamsa telemetriyi, değilse None döndürür.

        time şimdilik kullanılmıyor, arayüz değişmesin diye duruyor.
        """
        try:
            packet = Packet.decode(data)   # bozuksa ValueError fırlatır
        except ValueError:
            self.corrupted += 1
            return None

        if not self._in_range(packet.telemetry):
            self.out_of_range += 1
            return None

        self.valid += 1
        return packet.telemetry

    def stats(self) -> dict:
        return {
            "valid": self.valid,
            "corrupted": self.corrupted,
            "out_of_range": self.out_of_range,
        }

    @staticmethod
    def _in_range(telemetry: dict) -> bool:
        """Bütün değerler geçerli aralıktaysa True döndürür."""
        # NaN karşılaştırmaları False verir, bozuk float'lar da burada elenir
        for field, (low, high) in RANGES.items():
            if not low <= telemetry[field] <= high:
                return False

        for field, (low, high) in GPS_RANGES.items():
            if not low <= telemetry["gps_saati"][field] <= high:
                return False

        # kilitlenme varsa hedef bilgileri 0 olamaz
        if telemetry["iha_kilitlenme"] == 1:
            if any(telemetry[field] == 0 for field in TARGET_FIELDS):
                return False

        return True


if __name__ == "__main__":
    sample = {
        "takim_numarasi": 1, "iha_enlem": 41.5, "iha_boylam": 36.1,
        "iha_irtifa": 38, "iha_dikilme": 7, "iha_yonelme": 210, "iha_yatis": -30,
        "iha_hiz": 28, "iha_batarya": 50, "iha_otonom": 1, "iha_kilitlenme": 0,
        "hedef_merkez_X": 0, "hedef_merkez_Y": 0, "hedef_genislik": 0, "hedef_yukseklik": 0,
        "gps_saati": {"saat": 11, "dakika": 38, "saniye": 37, "milisaniye": 654},
    }
    receiver = Receiver()

    receiver.receive(Packet(1, sample).encode(), 0.0)          # sağlam

    wrong = dict(sample, iha_yatis=400)                        # yatış aralık dışı
    receiver.receive(Packet(2, wrong).encode(), 0.5)

    corrupted = bytearray(Packet(3, sample).encode())
    corrupted[20] ^= 1                                         # bir bit bozuldu
    receiver.receive(bytes(corrupted), 1.0)

    print(receiver.stats())   # {'valid': 1, 'corrupted': 1, 'out_of_range': 1} olmalı