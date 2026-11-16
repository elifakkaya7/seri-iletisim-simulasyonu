"""Telemetri paketi: Header + Payload + Checksum."""

import struct

from serisim.checksum import calculate

START_BYTE = 0xAA                                   # paketin başladığını gösteren işaret
TELEMETRY_FORMAT = "<BddfffffBBBHHHHBBBH"           # telemetrinin bayt düzeni
PAYLOAD_SIZE = struct.calcsize(TELEMETRY_FORMAT)    # 53 bayt
PACKET_SIZE = PAYLOAD_SIZE + 4                      # 57 bayt (3 header + 1 checksum)

# Paketleme sırası. Anahtarlar yarışma dokümanındaki resmi isimler.
FIELDS = [
    "takim_numarasi", "iha_enlem", "iha_boylam", "iha_irtifa",
    "iha_dikilme", "iha_yonelme", "iha_yatis", "iha_hiz",
    "iha_batarya", "iha_otonom", "iha_kilitlenme",
    "hedef_merkez_X", "hedef_merkez_Y", "hedef_genislik", "hedef_yukseklik",
]
GPS_FIELDS = ["saat", "dakika", "saniye", "milisaniye"]


class Packet:
    """Düzen: START_BYTE (1) + seq (1) + uzunluk (1) + payload (53) + checksum (1)"""

    def __init__(self, seq: int, telemetry: dict):
        self.seq = seq % 256          # sıra numarası 1 bayta sığmalı (0-255)
        self.telemetry = telemetry

    def encode(self) -> bytes:
        """Paketi baytlara çevirir."""
        values = [self.telemetry[field] for field in FIELDS]
        values += [self.telemetry["gps_saati"][field] for field in GPS_FIELDS]
        payload = struct.pack(TELEMETRY_FORMAT, *values)    # değerleri baytlara çevir

        body = bytes([self.seq, len(payload)]) + payload    # seq + uzunluk + veri
        return bytes([START_BYTE]) + body + bytes([calculate(body)])

    @staticmethod
    def decode(data: bytes) -> "Packet":
        """Baytlardan paketi geri kurar. Bozuksa ValueError fırlatır."""
        if len(data) != PACKET_SIZE:
            raise ValueError("Paket boyutu yanlış")
        if data[0] != START_BYTE:
            raise ValueError("Başlangıç baytı yanlış")
        if data[2] != PAYLOAD_SIZE:
            raise ValueError("Uzunluk alanı yanlış")
        if calculate(data[1:-1]) != data[-1]:               # checksum'ı yeniden hesapla
            raise ValueError("Checksum tutmuyor")

        values = struct.unpack(TELEMETRY_FORMAT, data[3:-1])  # baytları değerlere çevir
        n = len(FIELDS)
        telemetry = dict(zip(FIELDS, values[:n]))
        telemetry["gps_saati"] = dict(zip(GPS_FIELDS, values[n:]))
        return Packet(data[1], telemetry)


if __name__ == "__main__":
    sample = {
        "takim_numarasi": 1, "iha_enlem": 41.508775, "iha_boylam": 36.118335,
        "iha_irtifa": 38, "iha_dikilme": 7, "iha_yonelme": 210, "iha_yatis": -30,
        "iha_hiz": 28, "iha_batarya": 50, "iha_otonom": 1, "iha_kilitlenme": 1,
        "hedef_merkez_X": 300, "hedef_merkez_Y": 230,
        "hedef_genislik": 30, "hedef_yukseklik": 43,
        "gps_saati": {"saat": 11, "dakika": 38, "saniye": 37, "milisaniye": 654},
    }

    data = Packet(5, sample).encode()
    print("Paket boyutu:", len(data))            # 57 olmalı

    back = Packet.decode(data)
    print("Sıra no:", back.seq)                  # 5 olmalı
    print("Telemetri:", back.telemetry)

    corrupted = bytearray(data)
    corrupted[10] ^= 0b00000100                  # bir biti bozuyoruz
    try:
        Packet.decode(bytes(corrupted))
    except ValueError as error:
        print("Bozuk paket yakalandı:", error)   # "Checksum tutmuyor" olmalı