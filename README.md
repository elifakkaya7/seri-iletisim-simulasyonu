# Seri İletişim Bağlantı Simülasyonu

İHA telemetri paketlerinin sanal bir seri hattan gönderilmesini simüle eden Python projesi.
Gönderici telemetri paketleri üretir. Paketler, baud rate ve gecikmesi ayarlanabilen sanal bir hattan
geçerken kaybolabilir ya da bitleri bozulabilir. Alıcı her paketi checksum ile kontrol eder ve sağlam olanları kabul eder.

Telemetri alanları TEKNOFEST Savaşan İHA Haberleşme Dokümanı'na göre seçildi.

## Yönerge maddeleri

| Madde | Karşılığı |
|---|---|
| 5.1 Sanal veri hattı (baud rate, gecikme) | `channel.py` |
| 5.2 Gürültü (paket kaybı, bit flip) | `noise.py` |
| 5.3 Header + Payload + Checksum, alıcıda doğrulama | `packet.py`, `checksum.py`, `receiver.py` |

## Proje yapısı

```
main.py              # simülasyonu çalıştırır, raporu yazdırır
gui.py               # ayarları değiştirip sonucu görmek için arayüz
serisim/
├── checksum.py      # XOR checksum
├── packet.py        # paket oluşturma (encode) ve çözme (decode)
├── channel.py       # sanal hat: iletim süresi = bayt × 10 / baud + gecikme
├── noise.py         # paket kaybı ve bit flip
├── sender.py        # telemetri üretir, paketler
└── receiver.py      # paketi doğrular, sayar
```

## Nasıl çalışıyor

1. **Gönderici (`sender.py`)** saniyede 2 kez telemetri verisi üretir. Bu veri konum, irtifa, hız, batarya, kilitlenme bilgisi ve GPS saati gibi alanlardan oluşur. Değerler gerçek bir uçuşa benzesin diye zamanla değişecek şekilde hesaplanır.
2. **Paketleme (`packet.py`)** bu veriyi `struct` ile 53 baytlık payload'a çevirir. Başına header (START, SEQ, LEN), sonuna checksum ekleyerek 57 baytlık paketi oluşturur.
3. **Sanal hat (`channel.py`)** paketin iletim süresini hesaplar. Seri haberleşmede her bayt başlangıç ve bitiş bitleriyle birlikte 10 bit olarak gider, bu yüzden süre `bayt × 10 / baud + gecikme` ile bulunur.
4. **Gürültü (`noise.py`)** hat üzerinde iki tür hata oluşturur:
   - **Paket kaybı:** paket belirli bir olasılıkla hiç ulaşmaz.
   - **Bit flip:** paketin her biti belirli bir olasılıkla ters çevrilir (0 → 1, 1 → 0).
5. **Alıcı (`receiver.py`)** gelen paketi açar ve kontrol eder:
   - Checksum'ı yeniden hesaplar. Pakettekiyle tutmazsa paketi bozuk sayıp atar.
   - SEQ numarasındaki atlamalara bakarak kaybolan paketleri bulur.
   - Değerlerin geçerli aralıkta olup olmadığına bakar.
   - Bu kontrollerin hepsinden geçen paketi sağlam sayar.
6. **`main.py`** bu adımları 1000 paket için çalıştırır. Farklı baud rate ve gürültü ayarlarını deneyip sonuçları yönergedeki 5.1, 5.2 ve 5.3 başlıklarına göre yazdırır.
7. **`gui.py`** aynı simülasyonu bir pencerede çalıştırır. Ayarlar kaydırıcılarla değiştirilir ve sonuç anında görülür. Her paketin başına ne geldiği (sağlam, kayboldu, checksum attı) listelenir. Seçilen paketin baytları da bozulan yerler işaretli olarak gösterilir.

## Paket yapısı (57 bayt)

| START | SEQ | LEN | PAYLOAD | CHECKSUM |
|---|---|---|---|---|
| 1 bayt (`0xAA`) | 1 bayt | 1 bayt | 53 bayt telemetri | 1 bayt |

- **SEQ:** paketin sıra numarası. Alıcı aradaki boşluklara bakarak kaybolan paketleri bulur.
- **CHECKSUM:** SEQ, LEN ve PAYLOAD baytlarının XOR'u. Alıcı aynı hesabı tekrar yapar; sonuç tutmazsa paketi atar.
- Checksum tutan paketlerde değerlerin geçerli aralıkta olup olmadığı da kontrol edilir (örneğin enlem −90..90).

## Çalıştırma

Python 3.10 veya üstü gerekir, ek kütüphane gerekmez.

```bash
python main.py      # konsol raporu
python gui.py       # arayüz
```

Modüller tek tek de test edilebilir:

```bash
python -m serisim.packet
python -m serisim.receiver
```

## Sonuçlar

Varsayılan ayarlar: 57600 baud, 0.05 s gecikme, 0.05 paket kaybı olasılığı, bit başına 0.0002 bit flip olasılığı, 1000 paket, 2 Hz.

| Kayıp | Bit flip | Kaybolan | Bozuk | Sağlam |
|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 1000 (%100) |
| 0.05 | 0 | 44 | 0 | 956 (%95.6) |
| 0 | 0.0002 | 0 | 77 | 923 (%92.3) |
| 0.05 | 0.0002 | 44 | 73 | 883 (%88.3) |

- Gürültü yokken bütün paketler sağlam ulaşıyor. Gürültü arttıkça sağlam ulaşan paket oranı düşüyor.
- Bir paketin iletimi 57600 baud'da 59.9 ms sürüyor. 1200 baud'da ise 525 ms sürüyor ve 500 ms'lik gönderim aralığına sığmıyor.
- Alıcı kaybolan 44 paketin hepsini SEQ ile buldu. Bozulan 75 paketin 73'ünü checksum yakaladı. Kalan 2 paket fark edilmeden geçti, çünkü XOR checksum aynı bit konumunda iki bozulma olunca hatayı göremiyor.

## Git akışı

Her parça ayrı bir feature branch'inde yazıldı ve pull request ile `main`'e alındı.
Her PR'ı diğer ekip üyesi inceleyip merge etti.

## Ekip

- **Elif Akkaya:** [@elifakkaya7](https://github.com/elifakkaya7)
- **Yasir Yusuf Sevgili:** [@YasirYusufSevgili](https://github.com/YasirYusufSevgili)

| Görev | Dosya | Yapan |
|---|---|---|
| Proje iskeleti | `serisim/`, `.gitignore` | Elif |
| XOR checksum | `checksum.py` | Elif |
| Paket yapısı (encode / decode) | `packet.py` | Elif |
| Sanal hat (baud rate, gecikme) | `channel.py` | Yasir |
| Paket kaybı ve bit flip | `noise.py` | Yasir |
| Telemetri üretimi (gönderici) | `sender.py` | Yasir |
| Paket doğrulama, SEQ ile kayıp bulma (alıcı) | `receiver.py` | Elif |
| Simülasyon ve rapor | `main.py` | Elif |
| Arayüz | `gui.py` | Elif |
| README | `README.md` | Elif ve Yasir |