# Seri İletişim Bağlantı Simülasyonu

Gerçek donanım olmadan, iki sistem arasındaki **veri paketleme, gönderme, alma ve hata ayıklama** sürecini sanal bir ortamda simüle eden Python projesi. Taşınan veri, TEKNOFEST Savaşan İHA Yarışması'nın telemetri paketidir (konum, irtifa, hız, batarya, kilitlenme).

```
Gönderici  ->  Kanal  ->  Gürültü  ->  Alıcı
 Sender     VirtualChannel  NoiseModel   Receiver
```

| Yönerge | Ne yapıyor | Dosya |
|---|---|---|
| 5.1 Sanal veri hattı | Baud rate ve gecikmeye göre paketin hattan geçme süresini hesaplar | `serisim/channel.py` |
| 5.2 Gürültü ve hata | Paket kaybı ve bit flip uygular | `serisim/noise.py` |
| 5.3 Protokol ve checksum | Paketi Header + Payload + Checksum yapar, alıcı bozuk paketi yakalar | `serisim/packet.py`, `checksum.py`, `receiver.py` |

## Çalıştırma

Python 3.10 veya üstü gerekir, ek kütüphane yok.

```bash
git clone https://github.com/elifakkaya7/seri-iletisim-simulasyonu.git
cd seri-iletisim-simulasyonu
python main.py     # üç bölümlü rapor basar
python gui.py      # ayarları kaydırıcılarla değiştirebileceğin arayüz
```

Türkçe karakterler bozuk çıkarsa: `python -X utf8 main.py`

Her modül tek başına da denenebilir: `python -m serisim.noise`, `python -m serisim.receiver` gibi.

## Proje yapısı

```
main.py           Simülasyonu çalıştırır, raporu basar
gui.py            Arayüz (tkinter)
serisim/
  checksum.py     XOR checksum
  packet.py       Packet: encode() ve decode()
  noise.py        NoiseModel: paket kaybı ve bit flip
  channel.py      VirtualChannel: baud rate ve gecikme
  sender.py       Sender: sahte telemetri üretir
  receiver.py     Receiver: doğrular, sayar, kayıp paketi bulur
```

Kanal ve gürültü yalnızca `bytes` alıp `bytes` verir, paketin içini bilmez.

## Nasıl çalışıyor?

**Paket (57 bayt):**

| START | SEQ | LEN | PAYLOAD | CHECKSUM |
|---|---|---|---|---|
| 1 bayt, `0xAA` | 1 bayt, sıra no (0–255) | 1 bayt, 53 | 53 bayt, telemetri | 1 bayt, XOR |

Checksum, SEQ + LEN + PAYLOAD baytlarının XOR'udur. Payload, yarışmanın telemetri alanlarından oluşur: takım no, enlem, boylam, irtifa, dikilme, yönelme, yatış, hız, batarya, otonom, kilitlenme, hedef konumu ve boyutu, GPS saati.

**Kanal:** Seri hatta her bayt 10 bit gider, süre şöyle hesaplanır:

```
süre = bayt sayısı x 10 / baud rate + gecikme
```

Örnek: 57600 baud'da `570 / 57600 + 50 ms = 59,9 ms`. 1200 baud'da 525 ms sürer; 2 Hz'lik gönderim aralığını (500 ms) aştığı için hat yetişemez. Süreler hesaplanır, gerçekten beklenmez.

**Gürültü:** Paket verilen olasılıkla düşer; düşmezse her bit verilen olasılıkla ters çevrilir.

**Alıcı:** Gelen paketi sırayla kontrol eder ve geçemeyeni atar:
1. START, uzunluk ve checksum
2. Alan aralıkları (örneğin yatış −90…+90 dışındaysa paket atılır)
3. Kayıp tespiti: Kaybolan paketi doğrudan göremez, **SEQ numaralarındaki boşluktan** anlar (5'ten sonra 8 geldiyse 6 ve 7 kayıptır).

## Parametreler

| Parametre | Değer |
|---|---|
| Gönderim hızı | 2 Hz (şartnamede telemetri 1–2 Hz) |
| Baud rate | 57600 |
| Gecikme | 50 ms |
| Paket kaybı | %5 (0,05) |
| Bit flip | 0,0002 (bit başına) |
| Paket sayısı | 1000 (500 sn) |
| Seed | 42 (aynı sonuç her seferinde) |

Baud rate, gecikme, kayıp ve bit flip için yarışma belgelerinde değer yoktur; bunlar bu projenin seçimleridir. `main.py`'nin başından ya da `gui.py`'den değiştirilebilir.

## Örnek çıktı

```
=== SERİ İLETİŞİM BAĞLANTI SİMÜLASYONU ===
Paket yapısı: START(1) + SEQ(1) + LEN(1) + PAYLOAD(53) + CHECKSUM(1) = 57 bayt
Gönderim: 1000 paket, 2 Hz, seed=42

--- 5.1 Sanal veri hattı: baud rate ve gecikmenin etkisi ---
   Baud   Gecikme  Paket süresi  Durum
   1200     50 ms      525.0 ms  UYARI: 500 ms gönderim aralığına sığmıyor
   9600     50 ms      109.4 ms  OK
  57600     50 ms       59.9 ms  OK
 115200     50 ms       54.9 ms  OK
  57600    200 ms      209.9 ms  OK
Süre = 57 bayt x 10 bit / baud + gecikme

--- 5.2 Gürültü ve hata: paket kaybı ve bit flip'in etkisi ---
 Kayıp  Bit flip  Kaybolan   Bozuk          Sağlam
     0         0         0       0   1000 (%100.0)   <- gürültüsüz kontrol
  0.05         0        44       0    956 ( %95.6)
     0    0.0002         0      77    923 ( %92.3)
  0.05    0.0002        44      73    883 ( %88.3)
   0.2     0.001       204     276    520 ( %52.0)

--- 5.3 Protokol ve checksum (kayıp 0.05, bit flip 0.0002) ---
Gönderilen paket               : 1000
Kanalda kaybolan (gerçek)      : 44
Alıcının SEQ ile bulduğu kayıp : 44
Kanalda bozulan paket          : 75
  Checksum'ın yakaladığı       : 73
  Aralık kontrolünün yakaladığı: 0
  Fark edilmeden geçen         : 2
Sağlam ulaşan                  : 883 (%88.3)
Ortalama paket süresi          : 59.9 ms
```

- **5.1:** Baud düştükçe paket süresi artar. 1200 baud'da uyarı çıkar.
- **5.2:** Gürültü kapalıyken 1000 paketin 1000'i sağlam gelir. Gürültü arttıkça kayıp ve bozuk paket sayısı da artar.
- **5.3:** Alıcı kaybolan 44 paketin hepsini SEQ ile bulur. Bozulan 75 paketin 73'ünü checksum yakalar, 2'si geçer (XOR checksum aynı bit konumundaki iki bozulmayı yakalayamaz).

## Kim neyi yaptı?

| Kişi | Dosyalar |
|---|---|
| **Elif Akkaya** | `checksum.py`, `packet.py`, `receiver.py`, `main.py`, `gui.py` |
| **Yasir Yusuf Sevgili** | `channel.py`, `noise.py`, `sender.py` |

Elif protokol tarafını ve bütünleştirmeyi (5.3), Yasir kanal tarafını ve veri üretimini (5.1 ve 5.2) üstlendi. Her görev ayrı bir `feature/` dalında geliştirildi.
