class VirtualChannel:
    def __init__(self, baud_rate=57600, latency=0.05, noise=None):
        self.baud_rate = baud_rate   # saniyede bit sayısı
        self.latency = latency       # gecikme, saniye cinsinden
        self.noise = noise           # NoiseModel ya da None

    def transmission_time(self, n: int) -> float:
        # her bayt başlangıç ve bitiş bitiyle 10 bit olarak gider
        return n * 10 / self.baud_rate + self.latency

    def transmit(self, data: bytes):
        time = self.transmission_time(len(data))
        if self.noise is not None:
            data = self.noise.apply(data)
        return data, time


if __name__ == "__main__":
    paket = bytes(57)

    k = VirtualChannel(baud_rate=57600, latency=0.05)
    _, sure = k.transmit(paket)
    print("57600 baud:", round(sure * 1000, 1), "ms")    # ≈ 59.9

    k2 = VirtualChannel(baud_rate=9600, latency=0.05)
    _, sure2 = k2.transmit(paket)
    print("9600 baud :", round(sure2 * 1000, 1), "ms")   # ≈ 109.4

    k3 = VirtualChannel(baud_rate=57600, latency=0.0)
    _, sure3 = k3.transmit(paket)
    print("Gecikmesiz:", round(sure3 * 1000, 1), "ms")   # ≈ 9.9