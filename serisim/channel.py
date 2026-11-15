class VirtualChannel:
    def __init__(self, baud_rate=57600, latency=0.05):
        self.baud_rate = baud_rate   # saniyede bit sayısı
        self.latency = latency       # gecikme, SANİYE cinsinden (0.05 = 50 ms)

    def transmit(self, data: bytes):
        """Veriyi taşır. (veri, iletim_süresi_saniye) döndürür."""
        sure = len(data) * 10 / self.baud_rate + self.latency
        return data, sure


if __name__ == "__main__":
    paket = bytes(57)   # 57 baytlık sahte paket

    k = VirtualChannel(baud_rate=57600, latency=0.05)
    _, sure = k.transmit(paket)
    print("57600 baud:", round(sure * 1000, 1), "ms")   # yaklaşık 59.9 ms

    k2 = VirtualChannel(baud_rate=9600, latency=0.05)
    _, sure2 = k2.transmit(paket)
    print("9600 baud :", round(sure2 * 1000, 1), "ms")  # yaklaşık 109.4 ms

    k3 = VirtualChannel(baud_rate=57600, latency=0.0)
    _, sure3 = k3.transmit(paket)
    print("Gecikmesiz:", round(sure3 * 1000, 1), "ms")  # yaklaşık 9.9 ms