# 🎵 Spotify Şarkı Sözleri

Spotify'da dinlediğin şarkının sözlerini, Spotify'ın **"Sözler"** bölümündeki gibi **hareketli ve şarkıyla senkron** şekilde ekranın istediğin yerinde gösteren küçük bir Windows uygulaması.

O an söylenen satır büyük ve parlak, söylenmiş satırlar üstte soluk, sıradaki satırlar altta daha soluk görünür; satır değiştikçe metin yumuşakça yukarı kayar. Pencere her zaman üstte kalır, **tam ekran video, tarayıcı ve oyunların üstünde de** görünür (Minecraft dahil).

> Spotify hesabı, API anahtarı ya da giriş gerekmez.

---

## ✨ Özellikler

- **Senkron sözler:** Söylenen satır anında vurgulanır, geçmiş ve gelecek satırlar farklı tonlarda görünür.
- **Spotify tarzı animasyon:** Yumuşak kaydırma, aktif satırın hafifçe büyümesi, kenarlarda kaybolan satırlar.
- **Müzik araları:** Şarkının girişinde ve sözsüz bölümlerde Spotify'daki gibi dolan **• • •** noktaları.
- **İstediğin yere taşı, boyutlandır:** Sürükle-bırak, sağ alt köşeden boyutlandırma.
- **Temalar:** Koyu, Spotify Yeşili, Gece Mavisi, Mor, Kırmızı, Şeffaf (sadece yazı).
- **Tam ekranda görünür:** Pencere sürekli en üstte tutulur ve odak çalmaz; oyunun içinde tıklarsan oyun küçülmez.
- **Oyunlar için kenarlıksız tam ekran:** `Ctrl+Alt+F` ile öndeki oyunu (ör. Minecraft) kenarlıksız tam ekrana çevirir, böylece sözler oyunun üstünde kalır.
- **Kilitleme:** Tıklamalar pencereden geçip arkadaki uygulamaya gider.
- **Senkron ayarı:** Sözler önde/geride kalıyorsa 0.3 sn'lik adımlarla düzeltilebilir.
- **Ayarlar hatırlanır:** Konum, boyut, tema, yazı boyutu bir sonraki açılışta aynen gelir.
- **Windows ile başlat** seçeneği.
- **Önbellek:** Bir kez bulunan sözler bilgisayarda saklanır, tekrar indirilmez.

---

## 📋 Gereksinimler

- **Windows 10 veya 11**
- **Python 3.10 veya üstü** ([python.org](https://www.python.org/downloads/) — kurarken *"Add python.exe to PATH"* kutusunu işaretle)
- **Spotify masaüstü uygulaması** (web sürümü değil)
- İnternet bağlantısı (sözleri indirmek için)

---

## 🔧 Kurulum

### 1. Projeyi indir

Git ile:

```powershell
git clone https://github.com/ArdaYesil/spotify-sarki-sozleri.git
cd spotify-sarki-sozleri
```

ya da GitHub sayfasında **Code → Download ZIP** ile indirip bir klasöre çıkart.

### 2. Gerekli paketleri kur

```powershell
python -m pip install -r requirements.txt
```

Kurulan paketler:

| Paket | Ne için |
|---|---|
| `PySide6` | Pencere ve animasyonlar (Qt) |
| `requests` | Sözleri internetten indirmek |
| `winrt-*` | Windows'tan Spotify'ın çalan şarkısını ve süresini okumak |

> Bu adımı atlarsan da sorun değil: `Baslat.bat` ilk açılışta eksik paketleri kendisi kurar.

### 3. Başlat

`Baslat.bat` dosyasına **çift tıkla**. Konsol penceresi açılmadan sözler penceresi gelir ve saatin yanında yeşil bir simge belirir.

Elle başlatmak istersen:

```powershell
pythonw sozler.py
```

Her açılışta otomatik başlaması için: pencereye sağ tıkla → **Windows açılışında başlat**.

---

## 🎮 Kullanım

Spotify'da bir şarkı çal; sözler birkaç saniye içinde gelir.

### Fare ve klavye

| İşlem | Ne yapar |
|---|---|
| Sol tıkla sürükle | Pencereyi taşır |
| Sağ alt köşeden sürükle | Boyutlandırır |
| `Ctrl` + fare tekerleği | Yazı boyutunu değiştirir |
| `Shift` + fare tekerleği | Arka plan saydamlığını değiştirir |
| Sağ tık | Ayarlar menüsü |
| Tepsideki yeşil simgeye tıkla | Pencereyi gizler / gösterir |
| Tepsideki simgeye sağ tık | Ayarlar menüsü (pencere kilitliyken de çalışır) |
| `Ctrl` + `Alt` + `F` | Öndeki oyunu kenarlıksız tam ekran yapar / geri alır |

### Ayarlar menüsü

- **Gizle / Göster**
- **Kilitle (tıklamalar arkaya geçsin):** Pencere tıklanamaz olur, oyun ya da video oynarken yanlışlıkla tıklamazsın. Kilidi açmak için tepsideki yeşil simgeye sağ tıkla.
- **Yazı boyutu**
- **Tema**
- **Arka plan saydamlığı:** `%0` seçilirse sadece yazı görünür.
- **Ortalı yazı:** Varsayılan Spotify gibi sola yaslıdır.
- **Şarkı adını göster:** Üstteki "▶ Şarkı • Sanatçı" satırı.
- **Senkron ayarı:** Sözler şarkının gerisinde ya da önünde kalıyorsa düzeltir.
- **Minecraft'ı kenarlıksız tam ekran yap / geri al**
- **Ekranın ortasına getir:** Pencere ekran dışında kaldıysa kurtarır.
- **Bu şarkının sözlerini yeniden ara**
- **Windows açılışında başlat**
- **Çıkış**

### 🟩 Oyunlarda (Minecraft) tam ekran

Bazı oyunların kendi tam ekran modu (Minecraft'ta **F11**) "özel tam ekran"dır ve Windows bu modda **hiçbir pencerenin oyunun üstünde görünmesine izin vermez**. Çözüm, oyunu kenarlıksız tam ekrana almak — görüntü yine tam ekran olur ama sözler üstte kalır:

1. Oyunu aç.
2. Oyun öndeyken **`Ctrl` + `Alt` + `F`**'ye bas.
   - Oyun F11 tam ekranındaysa uygulama önce F11'e kendisi basıp pencere moduna alır, sonra kenarlıksız tam ekrana çevirir.
3. Eski haline döndürmek için tekrar **`Ctrl` + `Alt` + `F`**.

Oyunda tekrar F11'e basarsan oyun kendi tam ekranına döner ve sözler kaybolur; yeniden `Ctrl` + `Alt` + `F`'ye basman yeterli. Uygulamadan çıkınca kenarlıksız yapılan pencereler otomatik olarak eski haline döner.

Bu kısayol Minecraft'a özel değildir; pencere modunda çalışabilen çoğu oyunda kullanılabilir. Oyunun kendi ayarlarında **"Kenarlıksız / Borderless"** seçeneği varsa onu seçmek de aynı işi görür.

---

## ⚙️ Nasıl çalışıyor?

```
 Spotify ──► Windows medya denetimleri (SMTC) ──► MediaWatcher ──┐
                                                                 ├──► LyricsOverlay (Qt penceresi, 60 fps)
 lrclib.net ◄── LyricsFetcher (şarkı adı + sanatçı + süre) ──────┘
```

### 1. Çalan şarkıyı ve süreyi okuma
Spotify, Windows'un **Global System Media Transport Controls (SMTC)** sistemine — ses düğmesine basınca çıkan medya kutusunun kullandığı sisteme — şarkı adını, sanatçıyı, albümü, şarkı süresini, o anki konumu ve çalma/duraklatma durumunu bildirir. `MediaWatcher` arka planda saniyede 4 kez bu bilgiyi `winrt` paketiyle okur.

Spotify konumu her saniye göndermez; sadece "şu an 1:54'teydi, bu bilgi şu saatte güncellendi" der. Uygulama bu zaman damgasından geçen süreyi ekleyerek gerçek konumu hesaplar ve kendi saatini milisaniye hassasiyetinde ilerletir. Kullanıcı şarkıyı ileri sardığında ya da duraklattığında fark 0.6 saniyeyi aşınca saat yeniden eşitlenir; böylece sözler titremeden akar.

### 2. Sözleri bulma
`LyricsFetcher`, şarkı değişince ücretsiz ve açık bir söz veritabanı olan **[LRCLIB](https://lrclib.net)**'e sorar. Sırasıyla şunları dener:

1. Şarkı adı + sanatçı + albüm + süre ile tam eşleşme
2. Albümsüz tam eşleşme
3. Temizlenmiş adla arama (`(Remastered)`, `(feat. …)`, `- Live` gibi ekler atılır), süresi en yakın sonucu seçer

Zamanlamalı sözler LRC biçimindedir (`[00:29.52] Gözyaşım kurak, bak bu son durak`) ve satır satır ayrıştırılır. Sadece düz sözler bulunursa satırlar şarkı süresine eşit dağıtılır ve başlıkta **"(zamanlama tahmini)"** yazar. Sonuç `%LOCALAPPDATA%\SpotifySozler\cache` klasörüne kaydedilir.

### 3. Çizim ve animasyon
`LyricsOverlay`, çerçevesiz ve saydam bir **PySide6 (Qt)** penceresidir; her şeyi `QPainter` ile kendisi çizer:

- Saniyede ~60 kez o anki konuma göre aktif satır bulunur (ikili arama).
- Kaydırma, hedef satıra **üstel yumuşatma** ile yaklaşır; bu sayede Spotify'daki gibi yumuşak bir kayma olur.
- Her satırın bir "aktiflik" değeri vardır; aktif satır bu değerle beyaza döner ve %90'dan %100 boyuta büyür.
- Pencerenin üst ve alt kenarına yaklaşan satırlar yavaşça saydamlaşır.
- Müzik aralarında üç nokta, aranın ne kadarı geçtiğine göre sırayla dolar.

### 4. Tam ekranda üstte kalma
- Pencere `WindowStaysOnTopHint` ile açılır ve ayrıca her 0.8 saniyede Win32 `SetWindowPos(HWND_TOPMOST)` ile tekrar en üste alınır; tam ekran uygulamalar kendini öne çekse bile sözler üstte kalır.
- `WindowDoesNotAcceptFocus` sayesinde pencere tıklanınca odak çalmaz; tam ekran oyun ya da video küçülmez.
- **Kenarlıksız tam ekran** özelliği, oyun penceresinin başlık çubuğunu ve kenarlarını (`WS_CAPTION`, `WS_THICKFRAME`) kaldırıp pencereyi monitör boyutuna getirir. Eski stil ve konum saklanır, geri alınınca aynen geri yüklenir.
- `Ctrl+Alt+F` kısayolu Win32 `RegisterHotKey` ile kaydedilir, bu yüzden oyun öndeyken de çalışır.

---

## 📁 Dosyalar

| Dosya | Açıklama |
|---|---|
| `sozler.py` | Uygulamanın tamamı |
| `Baslat.bat` | Çift tıklayınca paketleri kontrol edip konsolsuz başlatır |
| `requirements.txt` | Gerekli Python paketleri |
| `LICENSE` | MIT lisansı |

Uygulamanın bilgisayarda oluşturduğu şeyler:

| Konum | İçerik |
|---|---|
| `%LOCALAPPDATA%\SpotifySozler\cache\` | İndirilen sözlerin önbelleği |
| Kayıt Defteri: `HKCU\Software\ClaudeTools\SpotifySozler` | Pencere konumu ve ayarlar |
| Kayıt Defteri: `HKCU\...\CurrentVersion\Run` | Sadece "Windows açılışında başlat" açıksa |

---

## 🔒 Gizlilik

- Spotify hesabına erişmez, giriş ya da anahtar istemez.
- İnternete sadece **şarkı adı, sanatçı, albüm ve süre** gönderilir (lrclib.net'e, sözleri bulmak için).
- Önbellek ve ayarlar yalnızca senin bilgisayarında durur.

---

## ❓ Sorun giderme

| Sorun | Çözüm |
|---|---|
| "Spotify'da bir şarkı çal" yazıyor | Spotify **masaüstü uygulamasının** açık olduğundan ve bir şarkı çaldığından emin ol. Web sürümü desteklenmez. |
| "Bu şarkı için söz bulunamadı" | Şarkı LRCLIB'de yok. Menüden **"Bu şarkının sözlerini yeniden ara"** dene. |
| Sözler şarkının önünde / gerisinde | Menü → **Senkron ayarı** ile düzelt. |
| Oyunda sözler görünmüyor | Oyun özel tam ekranda. Oyun öndeyken `Ctrl+Alt+F`'ye bas ya da oyunun ayarlarından **Kenarlıksız** modu seç. |
| `Ctrl+Alt+F` çalışmıyor | Kısayol başka bir program tarafından kullanılıyor olabilir (başlangıçta bildirim çıkar). Menüdeki **Minecraft'ı kenarlıksız tam ekran yap** seçeneğini kullan. |
| Pencere kilitli, tıklanmıyor | Saatin yanındaki yeşil simgeye sağ tıkla → **Kilitle**'nin işaretini kaldır. |
| Pencere ekranda yok | Tepsideki simgeye sağ tıkla → **Ekranın ortasına getir**. |
| `python` bulunamadı hatası | Python'u yeniden kurup *"Add python.exe to PATH"* kutusunu işaretle. |

---

## 📄 Lisans

[MIT](LICENSE) — dilediğin gibi kullanabilir, değiştirebilir ve paylaşabilirsin.

Şarkı sözleri [LRCLIB](https://lrclib.net) topluluğundan gelir; sözlerin hakları sahiplerine aittir. Bu proje Spotify ile bağlantılı değildir.
