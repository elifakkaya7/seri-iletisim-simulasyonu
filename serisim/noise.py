import random


class NoiseModel:
    def __init__(self, loss_prob=0.0, bit_flip_prob=0.0, seed=None):
        self.loss_prob = loss_prob
        self.bit_flip_prob = bit_flip_prob
        self.rng = random.Random(seed)

    def apply(self, data: bytes):
        # 1. paket kaybı
        if self.rng.random() < self.loss_prob:
            return None
        # 2. bit bozma: her bit, bit_flip_prob olasılıkla ters çevrilir
        buf = bytearray(data)
        for i in range(len(buf)):
            for bit in range(8):
                if self.rng.random() < self.bit_flip_prob:
                    buf[i] ^= (1 << bit)
        return bytes(buf)


if __name__ == "__main__":
    # Paket kaybı testleri (eskisi gibi)
    n = NoiseModel(loss_prob=0.5, seed=1)
    sonuc = [n.apply(b"abc") for _ in range(1000)]
    print("Kaybolan:", sonuc.count(None), "/ 1000")

    n0 = NoiseModel(loss_prob=0.0)
    print("Olasılık 0 iken kayıp:", [n0.apply(b"abc") for _ in range(1000)].count(None))

    n1 = NoiseModel(loss_prob=1.0)
    print("Olasılık 1 iken kayıp:", [n1.apply(b"abc") for _ in range(1000)].count(None))

    # Bit bozma testleri
    paket = bytes(57)

    nb0 = NoiseModel(bit_flip_prob=0.0)
    print("Bozma 0 iken veri aynı mı:", nb0.apply(paket) == paket)          # True

    nb1 = NoiseModel(bit_flip_prob=1.0)
    print("Bozma 1 iken hepsi 0xFF mi:", nb1.apply(paket) == b"\xff" * 57)  # True

    nb = NoiseModel(bit_flip_prob=0.0002, seed=1)
    bozuk = sum(1 for _ in range(10000) if nb.apply(paket) != paket)
    print("Bozulan paket:", bozuk, "/ 10000")                               # yaklaşık 870