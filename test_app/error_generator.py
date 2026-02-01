#!/usr/bin/env python3
"""
Sentrel Test Uygulaması - Hata Üreteci

Bu uygulama Sentrel'i test etmek için çeşitli hatalar üretir ve Sentry SDK
aracılığıyla gönderir. Farklı hata senaryolarını simüle edebilirsiniz.

Kullanım:
    python error_generator.py --dsn "http://PUBLIC_KEY@localhost:8000/PROJECT_ID"
"""

import argparse
import random
import sys
import time
from datetime import datetime
from typing import Optional

try:
    import sentry_sdk
    from sentry_sdk import capture_exception, capture_message, set_user, set_tag
except ImportError:
    print("Sentry SDK yüklü değil. Yüklemek için: pip install sentry-sdk")
    sys.exit(1)


# =============================================================================
# Hata Sınıfları
# =============================================================================

class DatabaseConnectionError(Exception):
    """Veritabanı bağlantı hatası."""
    pass


class APIRateLimitError(Exception):
    """API rate limit hatası."""
    pass


class PaymentProcessingError(Exception):
    """Ödeme işleme hatası."""
    pass


class AuthenticationFailedError(Exception):
    """Kimlik doğrulama hatası."""
    pass


class DataValidationError(Exception):
    """Veri doğrulama hatası."""
    pass


class FileUploadError(Exception):
    """Dosya yükleme hatası."""
    pass


class CacheExpiredError(Exception):
    """Önbellek zaman aşımı hatası."""
    pass


class ExternalServiceError(Exception):
    """Harici servis hatası."""
    pass


# =============================================================================
# Kullanıcı Simülasyonu
# =============================================================================

SAMPLE_USERS = [
    {"id": "user-1001", "email": "ahmet@example.com", "username": "ahmet_yilmaz"},
    {"id": "user-1002", "email": "ayse@example.com", "username": "ayse_demir"},
    {"id": "user-1003", "email": "mehmet@example.com", "username": "mehmet_kaya"},
    {"id": "user-1004", "email": "fatma@example.com", "username": "fatma_celik"},
    {"id": "user-1005", "email": "ali@example.com", "username": "ali_ozturk"},
    {"id": "user-1006", "email": "zeynep@example.com", "username": "zeynep_sahin"},
    {"id": "user-1007", "email": "mustafa@example.com", "username": "mustafa_arslan"},
    {"id": "user-1008", "email": "elif@example.com", "username": "elif_yildiz"},
]

SAMPLE_TRANSACTIONS = [
    "txn-abc123", "txn-def456", "txn-ghi789", "txn-jkl012", "txn-mno345"
]

SAMPLE_ENDPOINTS = [
    "/api/users", "/api/orders", "/api/products", "/api/payments",
    "/api/auth/login", "/api/auth/register", "/api/reports", "/api/settings"
]


# =============================================================================
# Hata Senaryoları
# =============================================================================

def simulate_database_error():
    """Veritabanı bağlantı hatası simülasyonu."""
    set_tag("service", "database")
    set_tag("db_type", "postgresql")
    raise DatabaseConnectionError(
        "PostgreSQL bağlantısı başarısız: connection refused (localhost:5432)"
    )


def simulate_api_rate_limit():
    """API rate limit hatası simülasyonu."""
    set_tag("service", "external_api")
    set_tag("api_provider", "stripe")
    raise APIRateLimitError(
        "Rate limit aşıldı: 429 Too Many Requests - Stripe API"
    )


def simulate_payment_error():
    """Ödeme işleme hatası simülasyonu."""
    transaction_id = random.choice(SAMPLE_TRANSACTIONS)
    set_tag("transaction_id", transaction_id)
    set_tag("payment_provider", "iyzico")
    raise PaymentProcessingError(
        f"Ödeme işlenemedi (Transaction: {transaction_id}): Yetersiz bakiye"
    )


def simulate_auth_error():
    """Kimlik doğrulama hatası simülasyonu."""
    set_tag("auth_method", "jwt")
    set_tag("endpoint", "/api/protected")
    raise AuthenticationFailedError(
        "JWT token geçersiz veya süresi dolmuş"
    )


def simulate_validation_error():
    """Veri doğrulama hatası simülasyonu."""
    endpoint = random.choice(SAMPLE_ENDPOINTS)
    set_tag("endpoint", endpoint)
    set_tag("validation_type", "schema")
    raise DataValidationError(
        f"Veri doğrulama hatası ({endpoint}): 'email' alanı geçerli bir e-posta adresi olmalı"
    )


def simulate_file_upload_error():
    """Dosya yükleme hatası simülasyonu."""
    set_tag("service", "storage")
    set_tag("storage_provider", "s3")
    raise FileUploadError(
        "Dosya yüklenemedi: Maximum file size exceeded (25MB limit)"
    )


def simulate_cache_error():
    """Önbellek hatası simülasyonu."""
    set_tag("service", "cache")
    set_tag("cache_provider", "redis")
    raise CacheExpiredError(
        "Redis önbellek anahtarı bulunamadı veya süresi dolmuş: session:user-1001"
    )


def simulate_external_service_error():
    """Harici servis hatası simülasyonu."""
    set_tag("service", "notification")
    set_tag("provider", "twilio")
    raise ExternalServiceError(
        "SMS gönderimi başarısız: Twilio servisine bağlanılamadı (timeout)"
    )


def simulate_division_by_zero():
    """Sıfıra bölme hatası simülasyonu."""
    set_tag("calculation", "percentage")
    result = 100 / 0
    return result


def simulate_key_error():
    """KeyError simülasyonu."""
    set_tag("operation", "dict_access")
    data = {"name": "test", "value": 123}
    return data["missing_key"]


def simulate_index_error():
    """IndexError simülasyonu."""
    set_tag("operation", "list_access")
    items = [1, 2, 3]
    return items[10]


def simulate_type_error():
    """TypeError simülasyonu."""
    set_tag("operation", "string_concat")
    result = "Toplam: " + 42
    return result


def simulate_attribute_error():
    """AttributeError simülasyonu."""
    set_tag("operation", "method_call")
    data = None
    return data.process()


def simulate_value_error():
    """ValueError simülasyonu."""
    set_tag("operation", "type_conversion")
    return int("not_a_number")


def simulate_recursion_error():
    """RecursionError simülasyonu."""
    set_tag("operation", "recursive_call")
    
    def infinite_recursion(n):
        return infinite_recursion(n + 1)
    
    return infinite_recursion(0)


def simulate_memory_error():
    """MemoryError simülasyonu (dikkatli kullanın)."""
    set_tag("operation", "memory_allocation")
    # Küçük bir simülasyon - gerçek memory error tehlikeli olabilir
    raise MemoryError("Bellek yetersiz: büyük veri seti işlenemedi")


def simulate_timeout_error():
    """Timeout hatası simülasyonu."""
    set_tag("operation", "http_request")
    set_tag("timeout", "30s")
    raise TimeoutError("İstek zaman aşımına uğradı: 30 saniye beklendi")


# =============================================================================
# Hata Haritası
# =============================================================================

ERROR_SCENARIOS = {
    "database": {
        "func": simulate_database_error,
        "description": "Veritabanı bağlantı hatası",
        "level": "error",
    },
    "rate_limit": {
        "func": simulate_api_rate_limit,
        "description": "API rate limit hatası",
        "level": "warning",
    },
    "payment": {
        "func": simulate_payment_error,
        "description": "Ödeme işleme hatası",
        "level": "error",
    },
    "auth": {
        "func": simulate_auth_error,
        "description": "Kimlik doğrulama hatası",
        "level": "warning",
    },
    "validation": {
        "func": simulate_validation_error,
        "description": "Veri doğrulama hatası",
        "level": "warning",
    },
    "file_upload": {
        "func": simulate_file_upload_error,
        "description": "Dosya yükleme hatası",
        "level": "error",
    },
    "cache": {
        "func": simulate_cache_error,
        "description": "Önbellek hatası",
        "level": "warning",
    },
    "external": {
        "func": simulate_external_service_error,
        "description": "Harici servis hatası",
        "level": "error",
    },
    "division": {
        "func": simulate_division_by_zero,
        "description": "Sıfıra bölme hatası",
        "level": "error",
    },
    "key": {
        "func": simulate_key_error,
        "description": "KeyError - eksik anahtar",
        "level": "error",
    },
    "index": {
        "func": simulate_index_error,
        "description": "IndexError - geçersiz indeks",
        "level": "error",
    },
    "type": {
        "func": simulate_type_error,
        "description": "TypeError - tip uyuşmazlığı",
        "level": "error",
    },
    "attribute": {
        "func": simulate_attribute_error,
        "description": "AttributeError - None objesi",
        "level": "error",
    },
    "value": {
        "func": simulate_value_error,
        "description": "ValueError - geçersiz değer",
        "level": "error",
    },
    "timeout": {
        "func": simulate_timeout_error,
        "description": "Timeout hatası",
        "level": "error",
    },
    "memory": {
        "func": simulate_memory_error,
        "description": "Bellek hatası",
        "level": "fatal",
    },
    "recursion": {
        "func": simulate_recursion_error,
        "description": "Sonsuz döngü hatası",
        "level": "fatal",
    },
}


# =============================================================================
# Ana Fonksiyonlar
# =============================================================================

def init_sentry(dsn: str, environment: str = "test", release: str = "1.0.0"):
    """Sentry SDK'yı başlat."""
    from sentry_sdk.transport import HttpTransport
    from urllib.parse import urlparse
    
    # DSN'den host ve protokol bilgisini al
    parsed = urlparse(dsn)
    
    # HTTP için özel transport class
    class InsecureHttpTransport(HttpTransport):
        """HTTP (non-SSL) destekleyen transport."""
        def __init__(self, options):
            super().__init__(options)
    
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=0.0,  # Trace'leri devre dışı bırak (sadece error gönder)
        profiles_sample_rate=0.0,
        send_default_pii=True,
        attach_stacktrace=True,
        debug=True,
        transport=InsecureHttpTransport,
        # HTTP için SSL doğrulamasını atla
        http_proxy=None,
        https_proxy=None,
    )
    print(f"✅ Sentry SDK başlatıldı")
    print(f"   DSN: {dsn[:50]}...")
    print(f"   Environment: {environment}")
    print(f"   Release: {release}")


def generate_single_error(error_type: str):
    """Tek bir hata üret ve Sentry'ye gönder."""
    if error_type not in ERROR_SCENARIOS:
        print(f"❌ Bilinmeyen hata tipi: {error_type}")
        print(f"   Geçerli tipler: {', '.join(ERROR_SCENARIOS.keys())}")
        return False
    
    scenario = ERROR_SCENARIOS[error_type]
    
    # Rastgele kullanıcı ata
    user = random.choice(SAMPLE_USERS)
    set_user(user)
    
    # Ortak tag'ler
    set_tag("error_type", error_type)
    set_tag("generated_at", datetime.now().isoformat())
    set_tag("test_run", "true")
    
    print(f"\n🔴 Hata üretiliyor: {scenario['description']}")
    print(f"   Kullanıcı: {user['username']} ({user['email']})")
    
    try:
        scenario["func"]()
    except Exception as e:
        capture_exception(e)
        print(f"   ✅ Hata Sentry'ye gönderildi: {type(e).__name__}")
        return True
    
    return False


def generate_random_errors(count: int, delay: float = 0.5):
    """Belirtilen sayıda rastgele hata üret."""
    print(f"\n🎲 {count} adet rastgele hata üretiliyor (aralık: {delay}s)...")
    
    error_types = list(ERROR_SCENARIOS.keys())
    generated = 0
    
    for i in range(count):
        error_type = random.choice(error_types)
        print(f"\n[{i+1}/{count}]", end="")
        
        if generate_single_error(error_type):
            generated += 1
        
        if i < count - 1:
            time.sleep(delay)
    
    print(f"\n\n📊 Sonuç: {generated}/{count} hata başarıyla gönderildi")
    return generated


def generate_burst_errors(count: int = 10):
    """Hızlı hata patlaması üret (rate limit testi için)."""
    print(f"\n💥 Hata patlaması: {count} hata hızlıca gönderiliyor...")
    
    for i in range(count):
        error_type = random.choice(list(ERROR_SCENARIOS.keys()))
        generate_single_error(error_type)
    
    print(f"\n✅ {count} hata gönderildi")


def send_test_message():
    """Sentry'ye test mesajı gönder."""
    capture_message("Test mesajı - Sentrel bağlantısı başarılı!", level="info")
    print("✅ Test mesajı gönderildi")


def list_error_types():
    """Mevcut hata tiplerini listele."""
    print("\n📋 Mevcut Hata Tipleri:")
    print("=" * 60)
    
    for key, scenario in ERROR_SCENARIOS.items():
        level_icon = {"warning": "⚠️", "error": "🔴", "fatal": "💀"}.get(
            scenario["level"], "❓"
        )
        print(f"  {level_icon} {key:15} - {scenario['description']}")
    
    print("=" * 60)
    print(f"  Toplam: {len(ERROR_SCENARIOS)} hata tipi")


def interactive_mode(dsn: str):
    """Etkileşimli mod - kullanıcı komutlarını dinle."""
    print("\n🎮 Etkileşimli Mod")
    print("   Komutlar: list, send <tip>, random <sayı>, burst, message, quit")
    print("-" * 60)
    
    init_sentry(dsn)
    
    while True:
        try:
            cmd = input("\n> ").strip().lower()
            
            if cmd == "quit" or cmd == "q":
                print("👋 Çıkılıyor...")
                break
            elif cmd == "list":
                list_error_types()
            elif cmd.startswith("send "):
                error_type = cmd[5:].strip()
                generate_single_error(error_type)
            elif cmd.startswith("random "):
                try:
                    count = int(cmd[7:].strip())
                    generate_random_errors(count)
                except ValueError:
                    print("❌ Geçersiz sayı")
            elif cmd == "burst":
                generate_burst_errors()
            elif cmd == "message":
                send_test_message()
            elif cmd == "help":
                print("""
Komutlar:
  list              - Hata tiplerini listele
  send <tip>        - Belirtilen tipte hata gönder
  random <sayı>     - Rastgele hatalar gönder
  burst             - Hızlı hata patlaması (10 hata)
  message           - Test mesajı gönder
  quit/q            - Çık
                """)
            else:
                print("❌ Bilinmeyen komut. 'help' yazın yardım için.")
                
        except KeyboardInterrupt:
            print("\n👋 Çıkılıyor...")
            break


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sentrel Test Uygulaması - Hata Üreteci",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  # Tek hata gönder
  python error_generator.py --dsn "http://KEY@localhost:8000/1" --type database

  # Rastgele 10 hata gönder
  python error_generator.py --dsn "http://KEY@localhost:8000/1" --random 10

  # Hata patlaması
  python error_generator.py --dsn "http://KEY@localhost:8000/1" --burst

  # Etkileşimli mod
  python error_generator.py --dsn "http://KEY@localhost:8000/1" --interactive

  # Hata tiplerini listele
  python error_generator.py --list
        """
    )
    
    parser.add_argument(
        "--dsn",
        help="Sentry/Sentrel DSN URL'i (ör: http://PUBLIC_KEY@localhost:8000/PROJECT_ID)",
    )
    parser.add_argument(
        "--type", "-t",
        choices=list(ERROR_SCENARIOS.keys()),
        help="Üretilecek hata tipi",
    )
    parser.add_argument(
        "--random", "-r",
        type=int,
        metavar="N",
        help="N adet rastgele hata üret",
    )
    parser.add_argument(
        "--burst", "-b",
        action="store_true",
        help="Hızlı hata patlaması (10 hata)",
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=0.5,
        help="Hatalar arası bekleme süresi (saniye, varsayılan: 0.5)",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Etkileşimli mod",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Mevcut hata tiplerini listele",
    )
    parser.add_argument(
        "--message", "-m",
        action="store_true",
        help="Basit test mesajı gönder",
    )
    parser.add_argument(
        "--env",
        default="test",
        help="Environment (varsayılan: test)",
    )
    parser.add_argument(
        "--release",
        default="1.0.0",
        help="Release versiyon (varsayılan: 1.0.0)",
    )
    
    args = parser.parse_args()
    
    # Hata tiplerini listele
    if args.list:
        list_error_types()
        return
    
    # DSN kontrolü
    if not args.dsn and not args.list:
        print("❌ DSN gerekli! --dsn parametresini belirtin.")
        print("   Örnek: --dsn \"http://PUBLIC_KEY@localhost:8000/1\"")
        parser.print_help()
        return
    
    # Etkileşimli mod
    if args.interactive:
        interactive_mode(args.dsn)
        return
    
    # Sentry'yi başlat
    init_sentry(args.dsn, args.env, args.release)
    
    # Komutları işle
    if args.message:
        send_test_message()
    elif args.type:
        generate_single_error(args.type)
    elif args.random:
        generate_random_errors(args.random, args.delay)
    elif args.burst:
        generate_burst_errors()
    else:
        print("ℹ️  Bir işlem belirtin: --type, --random, --burst, --message veya --interactive")
        parser.print_help()


if __name__ == "__main__":
    main()
