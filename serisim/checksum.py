"""XOR checksum hesaplama."""


def calculate(data: bytes) -> int:
    """Baytların XOR'unu döndürür (0-255)."""
    result = 0
    for byte in data:
        result ^= byte    # her baytı sonuca XOR'la
    return result


if __name__ == "__main__":
    print(calculate(bytes([1, 2, 3])))      # 0 olmalı
    print(calculate(bytes([0xAA, 0x01])))   # 171 olmalı
    print(calculate(bytes([0xFF, 0x0F])))   # 240 olmalı
    print(calculate(b""))                   # 0 olmalı