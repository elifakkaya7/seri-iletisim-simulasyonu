import random


class NoiseModel:
    def __init__(self, loss_prob=0.0, bit_flip_prob=0.0, seed=None):
        self.loss_prob = loss_prob
        self.bit_flip_prob = bit_flip_prob
        self.rng = random.Random(seed)

    def drop(self, data: bytes):
        if self.rng.random() < self.loss_prob:
            return None
        return data


if __name__ == "__main__":
    n = NoiseModel(loss_prob=0.5, seed=1)
    sonuc = [n.drop(b"abc") for _ in range(1000)]
    print("Kaybolan:", sonuc.count(None), "/ 1000")

    n0 = NoiseModel(loss_prob=0.0)
    print("Olasılık 0 iken kayıp:", [n0.drop(b"abc") for _ in range(1000)].count(None))

    n1 = NoiseModel(loss_prob=1.0)
    print("Olasılık 1 iken kayıp:", [n1.drop(b"abc") for _ in range(1000)].count(None))