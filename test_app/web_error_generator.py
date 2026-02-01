#!/usr/bin/env python3
"""
Sentrel Test Uygulaması - Web Tabanlı Hata Üreteci

Bu uygulama web arayüzü üzerinden hata üretmenizi sağlar.
FastAPI tabanlı basit bir UI sunar.

Kullanım:
    python web_error_generator.py --dsn "https://n7826qvl6ho21rzwk8no9c9yjbc2t8sz@localhost:8000/1"
"""

import argparse
import random
import sys
from datetime import datetime
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Gerekli paketler yüklü değil.")
    print("Yüklemek için: pip install fastapi uvicorn")
    sys.exit(1)

try:
    import sentry_sdk
    from sentry_sdk import capture_exception, capture_message, set_user, set_tag
except ImportError:
    print("Sentry SDK yüklü değil. Yüklemek için: pip install sentry-sdk")
    sys.exit(1)


app = FastAPI(title="Sentrel Test - Hata Üreteci", version="1.0.0")

# Global DSN
SENTRY_DSN: Optional[str] = None


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


# =============================================================================
# Kullanıcı Verileri
# =============================================================================

SAMPLE_USERS = [
    {"id": "user-1001", "email": "ahmet@example.com", "username": "ahmet_yilmaz"},
    {"id": "user-1002", "email": "ayse@example.com", "username": "ayse_demir"},
    {"id": "user-1003", "email": "mehmet@example.com", "username": "mehmet_kaya"},
    {"id": "user-1004", "email": "fatma@example.com", "username": "fatma_celik"},
]


# =============================================================================
# Modeller
# =============================================================================

class ErrorRequest(BaseModel):
    error_type: str
    user_email: Optional[str] = None
    custom_message: Optional[str] = None


class BurstRequest(BaseModel):
    count: int = 10


# =============================================================================
# Hata Fonksiyonları
# =============================================================================

def generate_error(error_type: str, user_email: Optional[str] = None, custom_message: Optional[str] = None):
    """Belirtilen tipte hata üret."""
    
    # Kullanıcı ayarla
    if user_email:
        user = {"email": user_email, "username": user_email.split("@")[0]}
    else:
        user = random.choice(SAMPLE_USERS)
    
    set_user(user)
    set_tag("error_type", error_type)
    set_tag("generated_at", datetime.now().isoformat())
    set_tag("source", "web_ui")
    
    error_map = {
        "database": (DatabaseConnectionError, "PostgreSQL bağlantısı başarısız"),
        "rate_limit": (APIRateLimitError, "Rate limit aşıldı: 429"),
        "payment": (PaymentProcessingError, "Ödeme işlenemedi: Yetersiz bakiye"),
        "auth": (AuthenticationFailedError, "JWT token geçersiz"),
        "validation": (DataValidationError, "Veri doğrulama hatası"),
        "division": (ZeroDivisionError, "Sıfıra bölme"),
        "key": (KeyError, "Anahtar bulunamadı"),
        "index": (IndexError, "Geçersiz indeks"),
        "type": (TypeError, "Tip uyuşmazlığı"),
        "value": (ValueError, "Geçersiz değer"),
        "timeout": (TimeoutError, "İstek zaman aşımı"),
    }
    
    if error_type not in error_map:
        raise HTTPException(status_code=400, detail=f"Bilinmeyen hata tipi: {error_type}")
    
    error_class, default_message = error_map[error_type]
    message = custom_message or default_message
    
    try:
        raise error_class(message)
    except Exception as e:
        capture_exception(e)
        return {
            "status": "sent",
            "error_type": error_type,
            "message": message,
            "user": user.get("email"),
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# HTML Template
# =============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentrel Test - Hata Üreteci</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 2rem;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            margin-bottom: 2rem;
            font-size: 2.5rem;
            background: linear-gradient(90deg, #e94560, #f39c12);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .card h2 {
            margin-bottom: 1rem;
            color: #e94560;
            font-size: 1.3rem;
        }
        
        .error-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 0.75rem;
        }
        
        .error-btn {
            padding: 1rem;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
        }
        
        .error-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
        }
        
        .error-btn.red { background: linear-gradient(135deg, #e94560, #c73e54); }
        .error-btn.orange { background: linear-gradient(135deg, #f39c12, #d68910); }
        .error-btn.blue { background: linear-gradient(135deg, #3498db, #2980b9); }
        .error-btn.purple { background: linear-gradient(135deg, #9b59b6, #8e44ad); }
        
        .error-btn span.icon { font-size: 1.5rem; }
        
        .form-group {
            margin-bottom: 1rem;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: #aaa;
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            font-size: 1rem;
        }
        
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #e94560;
        }
        
        .btn-primary {
            width: 100%;
            padding: 1rem;
            border: none;
            border-radius: 10px;
            background: linear-gradient(135deg, #e94560, #f39c12);
            color: white;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(233, 69, 96, 0.4);
        }
        
        .log-container {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 1rem;
            max-height: 300px;
            overflow-y: auto;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.85rem;
        }
        
        .log-entry {
            padding: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .log-entry:last-child {
            border-bottom: none;
        }
        
        .log-entry.success { color: #2ecc71; }
        .log-entry.error { color: #e74c3c; }
        .log-entry.info { color: #3498db; }
        
        .stats {
            display: flex;
            justify-content: space-around;
            text-align: center;
            margin-top: 1rem;
        }
        
        .stat-item h3 {
            font-size: 2rem;
            color: #e94560;
        }
        
        .stat-item p {
            color: #aaa;
            font-size: 0.9rem;
        }
        
        .dsn-info {
            background: rgba(233, 69, 96, 0.1);
            border: 1px solid rgba(233, 69, 96, 0.3);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            font-family: monospace;
            font-size: 0.85rem;
            word-break: break-all;
        }
        
        .burst-controls {
            display: flex;
            gap: 1rem;
            align-items: flex-end;
        }
        
        .burst-controls .form-group {
            flex: 1;
            margin-bottom: 0;
        }
        
        .burst-controls button {
            padding: 0.75rem 2rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 Sentrel Test - Hata Üreteci</h1>
        
        <div class="card">
            <h2>📡 Bağlantı Bilgisi</h2>
            <div class="dsn-info" id="dsn-display">DSN: Yükleniyor...</div>
        </div>
        
        <div class="card">
            <h2>⚡ Hızlı Hata Gönder</h2>
            <div class="error-grid">
                <button class="error-btn red" onclick="sendError('database')">
                    <span class="icon">🗄️</span>
                    <span>Database</span>
                </button>
                <button class="error-btn orange" onclick="sendError('auth')">
                    <span class="icon">🔐</span>
                    <span>Auth</span>
                </button>
                <button class="error-btn blue" onclick="sendError('payment')">
                    <span class="icon">💳</span>
                    <span>Payment</span>
                </button>
                <button class="error-btn purple" onclick="sendError('validation')">
                    <span class="icon">✅</span>
                    <span>Validation</span>
                </button>
                <button class="error-btn red" onclick="sendError('division')">
                    <span class="icon">➗</span>
                    <span>Division</span>
                </button>
                <button class="error-btn orange" onclick="sendError('key')">
                    <span class="icon">🔑</span>
                    <span>KeyError</span>
                </button>
                <button class="error-btn blue" onclick="sendError('type')">
                    <span class="icon">🔤</span>
                    <span>TypeError</span>
                </button>
                <button class="error-btn purple" onclick="sendError('timeout')">
                    <span class="icon">⏱️</span>
                    <span>Timeout</span>
                </button>
            </div>
        </div>
        
        <div class="card">
            <h2>🎯 Özel Hata Gönder</h2>
            <div class="form-group">
                <label>Hata Tipi</label>
                <select id="error-type">
                    <option value="database">Database Connection Error</option>
                    <option value="rate_limit">API Rate Limit Error</option>
                    <option value="payment">Payment Processing Error</option>
                    <option value="auth">Authentication Failed Error</option>
                    <option value="validation">Data Validation Error</option>
                    <option value="division">ZeroDivisionError</option>
                    <option value="key">KeyError</option>
                    <option value="index">IndexError</option>
                    <option value="type">TypeError</option>
                    <option value="value">ValueError</option>
                    <option value="timeout">TimeoutError</option>
                </select>
            </div>
            <div class="form-group">
                <label>Kullanıcı Email (opsiyonel)</label>
                <input type="email" id="user-email" placeholder="test@example.com">
            </div>
            <div class="form-group">
                <label>Özel Mesaj (opsiyonel)</label>
                <input type="text" id="custom-message" placeholder="Hata detayı...">
            </div>
            <button class="btn-primary" onclick="sendCustomError()">🚀 Hata Gönder</button>
        </div>
        
        <div class="card">
            <h2>💥 Hata Patlaması</h2>
            <p style="color: #aaa; margin-bottom: 1rem;">Çok sayıda hatayı hızlıca gönderin (stress test için)</p>
            <div class="burst-controls">
                <div class="form-group">
                    <label>Hata Sayısı</label>
                    <input type="number" id="burst-count" value="10" min="1" max="100">
                </div>
                <button class="btn-primary" onclick="sendBurst()">💥 Burst Gönder</button>
            </div>
        </div>
        
        <div class="card">
            <h2>📋 İşlem Geçmişi</h2>
            <div class="log-container" id="log-container">
                <div class="log-entry info">Uygulama başlatıldı. Hata göndermeye hazır.</div>
            </div>
            <div class="stats">
                <div class="stat-item">
                    <h3 id="total-count">0</h3>
                    <p>Toplam Gönderilen</p>
                </div>
                <div class="stat-item">
                    <h3 id="success-count">0</h3>
                    <p>Başarılı</p>
                </div>
                <div class="stat-item">
                    <h3 id="fail-count">0</h3>
                    <p>Başarısız</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let totalCount = 0;
        let successCount = 0;
        let failCount = 0;
        
        // DSN'i göster
        fetch('/api/info')
            .then(r => r.json())
            .then(data => {
                document.getElementById('dsn-display').textContent = 'DSN: ' + data.dsn;
            });
        
        function addLog(message, type = 'info') {
            const container = document.getElementById('log-container');
            const entry = document.createElement('div');
            entry.className = 'log-entry ' + type;
            entry.textContent = new Date().toLocaleTimeString() + ' - ' + message;
            container.insertBefore(entry, container.firstChild);
        }
        
        function updateStats() {
            document.getElementById('total-count').textContent = totalCount;
            document.getElementById('success-count').textContent = successCount;
            document.getElementById('fail-count').textContent = failCount;
        }
        
        async function sendError(errorType) {
            try {
                totalCount++;
                updateStats();
                addLog('Gönderiliyor: ' + errorType + '...', 'info');
                
                const response = await fetch('/api/error', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({error_type: errorType})
                });
                
                if (response.ok) {
                    const data = await response.json();
                    successCount++;
                    addLog('✅ ' + errorType + ' hatası gönderildi', 'success');
                } else {
                    failCount++;
                    addLog('❌ Hata gönderilemedi: ' + errorType, 'error');
                }
            } catch (e) {
                failCount++;
                addLog('❌ Bağlantı hatası: ' + e.message, 'error');
            }
            updateStats();
        }
        
        async function sendCustomError() {
            const errorType = document.getElementById('error-type').value;
            const userEmail = document.getElementById('user-email').value;
            const customMessage = document.getElementById('custom-message').value;
            
            try {
                totalCount++;
                updateStats();
                addLog('Özel hata gönderiliyor: ' + errorType + '...', 'info');
                
                const response = await fetch('/api/error', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        error_type: errorType,
                        user_email: userEmail || null,
                        custom_message: customMessage || null
                    })
                });
                
                if (response.ok) {
                    successCount++;
                    addLog('✅ Özel hata gönderildi: ' + errorType, 'success');
                } else {
                    failCount++;
                    addLog('❌ Özel hata gönderilemedi', 'error');
                }
            } catch (e) {
                failCount++;
                addLog('❌ Bağlantı hatası: ' + e.message, 'error');
            }
            updateStats();
        }
        
        async function sendBurst() {
            const count = parseInt(document.getElementById('burst-count').value);
            addLog('💥 Burst başlatılıyor: ' + count + ' hata...', 'info');
            
            const errorTypes = ['database', 'auth', 'payment', 'validation', 'division', 'key', 'type', 'timeout'];
            
            for (let i = 0; i < count; i++) {
                const errorType = errorTypes[Math.floor(Math.random() * errorTypes.length)];
                await sendError(errorType);
                await new Promise(r => setTimeout(r, 100));
            }
            
            addLog('💥 Burst tamamlandı: ' + count + ' hata', 'success');
        }
    </script>
</body>
</html>
"""


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def home():
    """Ana sayfa - Web UI."""
    return HTML_TEMPLATE


@app.get("/api/info")
async def get_info():
    """DSN ve uygulama bilgilerini döndür."""
    return {
        "dsn": SENTRY_DSN[:60] + "..." if SENTRY_DSN and len(SENTRY_DSN) > 60 else SENTRY_DSN,
        "status": "connected" if SENTRY_DSN else "not_configured"
    }


@app.post("/api/error")
async def create_error(request: ErrorRequest):
    """Hata üret ve Sentry'ye gönder."""
    if not SENTRY_DSN:
        raise HTTPException(status_code=500, detail="Sentry DSN yapılandırılmamış")
    
    return generate_error(
        request.error_type,
        request.user_email,
        request.custom_message
    )


@app.post("/api/burst")
async def create_burst(request: BurstRequest):
    """Çoklu hata üret."""
    if not SENTRY_DSN:
        raise HTTPException(status_code=500, detail="Sentry DSN yapılandırılmamış")
    
    error_types = ["database", "auth", "payment", "validation", "division", "key", "type", "timeout"]
    results = []
    
    for _ in range(request.count):
        error_type = random.choice(error_types)
        result = generate_error(error_type)
        results.append(result)
    
    return {
        "status": "completed",
        "total": request.count,
        "results": results
    }


@app.post("/api/message")
async def send_message():
    """Test mesajı gönder."""
    capture_message("Web UI'dan test mesajı - Sentrel bağlantısı aktif", level="info")
    return {"status": "sent", "message": "Test mesajı gönderildi"}


# =============================================================================
# Main
# =============================================================================

def main():
    global SENTRY_DSN
    
    parser = argparse.ArgumentParser(description="Sentrel Test - Web Hata Üreteci")
    parser.add_argument(
        "--dsn",
        required=True,
        help="Sentry/Sentrel DSN URL'i"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Sunucu host (varsayılan: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Sunucu port (varsayılan: 8080)"
    )
    parser.add_argument(
        "--env",
        default="test",
        help="Environment (varsayılan: test)"
    )
    
    args = parser.parse_args()
    
    SENTRY_DSN = args.dsn
    
    # Sentry'yi başlat
    sentry_sdk.init(
        dsn=args.dsn,
        environment=args.env,
        release="web-generator-1.0.0",
        traces_sample_rate=1.0,
        send_default_pii=True,
        debug=True,
    )
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║          Sentrel Test - Web Hata Üreteci                  ║
╠═══════════════════════════════════════════════════════════╣
║  🌐 Web UI: http://{args.host}:{args.port}                        
║  📡 DSN: {args.dsn[:40]}...
║  🏠 Environment: {args.env}
╚═══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
