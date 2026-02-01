# OpenSearch Dashboards

Bu klasör Sentry hataları için hazır OpenSearch Dashboard JSON dosyalarını içerir.

## Dashboard Listesi

### 1. Error Overview Dashboard (`error-overview.ndjson`)
Genel hata görünümü için ana dashboard.

**İçerik:**
- Toplam hata sayısı (metric)
- Hata seviyesi dağılımı (pie chart)
- Platform bazında hatalar (pie chart)
- Ortam bazında hatalar (horizontal bar)
- Zaman içinde hata trendi (line chart)
- Top 10 hata mesajı (table)
- Son hatalar listesi (table)

### 2. Project Metrics Dashboard (`project-metrics.ndjson`)
Proje ve release bazlı detaylı metrikler.

**İçerik:**
- Proje bazında hata dağılımı (histogram)
- SDK dağılımı (pie chart)
- Release bazında hata trendi (line chart)
- Exception türleri (tag cloud)
- Top tag'ler (table)
- Saatlik hata yoğunluğu (heatmap)

### 3. User Impact Dashboard (`user-impact.ndjson`)
Kullanıcı etkisi ve coğrafi analiz.

**İçerik:**
- Etkilenen benzersiz kullanıcı sayısı (metric)
- Tarayıcı dağılımı (pie chart)
- İşletim sistemi dağılımı (pie chart)
- Zaman içinde etkilenen kullanıcılar (line chart)
- Coğrafi dağılım haritası (region map)
- Ülke bazında hatalar (horizontal bar)
- Cihaz türü dağılımı (pie chart)
- En çok hata alan URL'ler (table)

## Dashboard'ları İmport Etme

### Adım 1: Index Pattern Oluşturma

Dashboard'ları kullanmadan önce index pattern oluşturmanız gerekir:

1. OpenSearch Dashboards'a gidin (http://localhost:5601)
2. **Stack Management** > **Index Patterns** bölümüne gidin
3. **Create index pattern** butonuna tıklayın
4. Index pattern: `sentry-events-*`
5. Time field: `@timestamp`
6. **Create index pattern** ile tamamlayın

### Adım 2: Dashboard'ları Import Etme

1. **Stack Management** > **Saved Objects** bölümüne gidin
2. **Import** butonuna tıklayın
3. İstediğiniz `.ndjson` dosyasını seçin:
   - `error-overview.ndjson` - Genel hata görünümü
   - `project-metrics.ndjson` - Proje metrikleri
   - `user-impact.ndjson` - Kullanıcı etkisi
4. **Import** butonuna tıklayın
5. Çakışma varsa "Overwrite" seçin

### Adım 3: Dashboard'a Erişim

1. Sol menüden **Dashboard** bölümüne gidin
2. İmport edilen dashboard'ları göreceksiniz:
   - Error Overview Dashboard
   - Project Metrics Dashboard
   - User Impact Dashboard

## Visualizasyon Türleri

| Tür | Açıklama | Kullanım |
|-----|----------|----------|
| Line Chart | Zaman serisi grafikleri | Trend analizi |
| Pie/Donut | Dağılım grafikleri | Kategori analizi |
| Horizontal Bar | Yatay çubuk grafik | Top-N listeler |
| Table | Veri tablosu | Detaylı listeler |
| Metric | Tek değer gösterimi | KPI'lar |
| Heatmap | Isı haritası | Yoğunluk analizi |
| Tag Cloud | Kelime bulutu | Exception türleri |
| Region Map | Coğrafi harita | Lokasyon analizi |

## Özelleştirme

Dashboard'ları kendi ihtiyaçlarınıza göre özelleştirebilirsiniz:

1. Dashboard'u açın
2. **Edit** butonuna tıklayın
3. Panel'leri sürükleyerek yerini değiştirin
4. Yeni visualizasyonlar ekleyin
5. **Save** ile kaydedin

## Yeni Visualizasyon Ekleme

1. **Visualize** > **Create visualization**
2. Visualizasyon türünü seçin
3. Index pattern olarak `sentry-events-*` seçin
4. Aggregation'ları yapılandırın
5. **Save** ile kaydedin
6. Dashboard'a ekleyin

## Mevcut Alanlar

Dashboard'larda kullanılabilecek önemli alanlar:

| Alan | Tür | Açıklama |
|------|-----|----------|
| `@timestamp` | date | Event zamanı |
| `event_id` | keyword | Benzersiz event ID |
| `project_id` | integer | Proje ID |
| `level` | keyword | error, warning, info, fatal |
| `platform` | keyword | python, javascript, node, vb. |
| `environment` | keyword | production, staging, dev |
| `release` | keyword | Versiyon bilgisi |
| `message` | text | Hata mesajı |
| `exception_type` | keyword | Exception türü |
| `exception_value` | text | Exception değeri |
| `user.id` | keyword | Kullanıcı ID |
| `user.ip` | ip | IP adresi |
| `browser.name` | keyword | Tarayıcı adı |
| `os.name` | keyword | İşletim sistemi |
| `geo.country_code` | keyword | Ülke kodu (ISO) |
| `geo.country_name` | keyword | Ülke adı |
| `geo.city` | keyword | Şehir |
| `request.url` | keyword | İstek URL'i |
| `request.method` | keyword | HTTP method |
| `sdk.name` | keyword | SDK adı |
| `sdk.version` | keyword | SDK versiyonu |
| `tags.*` | dynamic | Özel tag'ler |

## Sorun Giderme

### Dashboard boş görünüyor
- Index pattern'in doğru oluşturulduğundan emin olun
- Zaman aralığını kontrol edin (sağ üst köşe)
- Event verisi olduğundan emin olun

### Visualizasyon hata veriyor
- Field mapping'lerin doğru olduğunu kontrol edin
- OpenSearch'te index'in var olduğunu doğrulayın

### GeoIP haritası çalışmıyor
- GeoIP enrichment'ın aktif olduğundan emin olun
- `geo.country_code` alanının dolu olduğunu kontrol edin
