import os, secrets, time
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="ROZIXXIT SERVER")
DATABASE_URL = os.getenv("DATABASE_URL", "")
ADMIN_TOKEN = "123"

@contextmanager
def conn():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row, prepare_threshold=None) as c:
        yield c

# إنشاء الجدول مع دعم تعدد الأجهزة
with conn() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS rozi_keys(
        key TEXT PRIMARY KEY,
        duration BIGINT NOT NULL,
        expires_at BIGINT,
        hwid TEXT,
        max_devices INTEGER NOT NULL DEFAULT 1,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at BIGINT NOT NULL)""")

def admin(x_admin_token: str = Header(default="")):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(401, "Unauthorized")

def status_of(r, now):
    if not r["active"]: return "disabled"
    if r["expires_at"] is None: return "unused"
    return "expired" if r["expires_at"] <= now else "active"

# ================= API =================
class Gen(BaseModel):
    duration: int = Field(ge=60)
    quantity: int = Field(ge=1, le=100)
    max_devices: int = Field(ge=1, le=2)

class Ext(BaseModel):
    seconds: int = Field(86400, ge=60)

@app.post("/api/generate", dependencies=[Depends(admin)])
def generate(b: Gen):
    now = int(time.time())
    a = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    keys = [f"ROZIX-{''.join(secrets.choice(a) for _ in range(3))}-{''.join(secrets.choice(a) for _ in range(3))}-{''.join(secrets.choice(a) for _ in range(3))}" for _ in range(b.quantity)]
    
    with conn() as c:
        c.cursor().executemany(
            "INSERT INTO rozi_keys(key,duration,active,created_at,max_devices) VALUES(%s,%s,TRUE,%s,%s)",
            [(k, b.duration, now, b.max_devices) for k in keys],
        )
    return {"keys": keys}

@app.get("/api/keys", dependencies=[Depends(admin)])
def list_keys():
    now = int(time.time())
    with conn() as c:
        rows = c.execute("SELECT * FROM rozi_keys ORDER BY created_at DESC").fetchall()
    return [{"key": r["key"], "status": status_of(r, now), "active": r["active"],
             "expires_at": r["expires_at"], "duration": r["duration"], "hwid": r["hwid"], "max_devices": r["max_devices"]} for r in rows]

@app.post("/api/key/{key}/toggle", dependencies=[Depends(admin)])
def toggle(key: str):
    with conn() as c:
        c.execute("UPDATE rozi_keys SET active = NOT active WHERE key=%s", (key,))
    return {"ok": True}

@app.post("/api/key/{key}/extend", dependencies=[Depends(admin)])
def extend(key: str, b: Ext = Ext()):
    now = int(time.time())
    with conn() as c:
        r = c.execute("SELECT expires_at FROM rozi_keys WHERE key=%s", (key,)).fetchone()
        if not r: raise HTTPException(404)
        if r["expires_at"] is None:
            c.execute("UPDATE rozi_keys SET duration = duration + %s WHERE key=%s", (b.seconds, key))
        else:
            c.execute("UPDATE rozi_keys SET expires_at=%s WHERE key=%s", (max(r["expires_at"], now) + b.seconds, key))
    return {"ok": True}

@app.delete("/api/key/{key}", dependencies=[Depends(admin)])
def delete(key: str):
    with conn() as c:
        c.execute("DELETE FROM rozi_keys WHERE key=%s", (key,))
    return {"ok": True}

class Validate(BaseModel):
    key: str
    hwid: str

@app.post("/api/validate")
def validate(b: Validate):
    now = int(time.time())
    with conn() as c:
        r = c.execute("SELECT * FROM rozi_keys WHERE key=%s", (b.key.strip().upper(),)).fetchone()
        if not r or not r["active"]: return {"valid": False, "reason": "invalid"}
        
        # منطق تعدد الأجهزة
        current_hwids = r["hwid"].split(",") if r["hwid"] else []
        if b.hwid not in current_hwids:
            if len(current_hwids) >= r["max_devices"]:
                return {"valid": False, "reason": "device_limit_reached"}
            current_hwids.append(b.hwid)
            c.execute("UPDATE rozi_keys SET hwid=%s WHERE key=%s", (",".join(current_hwids), r["key"]))
            
        exp = r["expires_at"]
        if exp is None:
            exp = now + r["duration"]
            c.execute("UPDATE rozi_keys SET expires_at=%s WHERE key=%s", (exp, r["key"]))
        elif exp <= now:
            return {"valid": False, "reason": "expired"}
            
    return {"valid": True, "expires_at": exp}

# ================= واجهة الموقع الفخمة =================
HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ROZIXXIT | PANEL</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&family=JetBrains+Mono:wght@700&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<style>
    :root { --main: #a855f7; --sec: #06b6d4; --bg: #09090b; }
    body { background-color: var(--bg); color: #fff; font-family: 'Cairo', sans-serif; overflow-x: hidden; min-height: 100vh; }
    .mono { font-family: 'JetBrains Mono', monospace; direction: ltr; }
    
    /* خلفية متحركة */
    .bg-blobs { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; overflow: hidden; }
    .blob-1 { position: absolute; top: -10%; left: -10%; width: 40vw; height: 40vw; background: var(--main); border-radius: 50%; filter: blur(100px); opacity: 0.2; animation: float 10s infinite alternate; }
    .blob-2 { position: absolute; bottom: -10%; right: -10%; width: 40vw; height: 40vw; background: var(--sec); border-radius: 50%; filter: blur(100px); opacity: 0.2; animation: float 10s infinite alternate-reverse; }
    @keyframes float { 0% { transform: translate(0, 0); } 100% { transform: translate(50px, 50px); } }

    .glass { background: rgba(20, 20, 25, 0.7); backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .btn { background: linear-gradient(135deg, var(--main), var(--sec)); color: #000; font-weight: 900; padding: 10px 20px; border-radius: 8px; border: none; cursor: pointer; transition: 0.3s; }
    .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(168,85,247,0.5); }
    .inp { background: rgba(0,0,0,0.5); border: 1px solid #333; color: #fff; padding: 10px; border-radius: 8px; width: 100%; transition: 0.3s; }
    .inp:focus { outline: none; border-color: var(--main); box-shadow: 0 0 10px rgba(168,85,247,0.3); }
    
    .key-card { background: rgba(0,0,0,0.4); border: 1px solid #222; border-radius: 12px; padding: 15px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 10px; transition: 0.3s; }
    .key-card:hover { border-color: var(--sec); box-shadow: 0 0 15px rgba(6,182,212,0.2); }
    .key-text { font-size: 1.25rem; font-weight: 900; color: var(--sec); text-shadow: 0 0 5px rgba(6,182,212,0.5); letter-spacing: 1px; }
    
    /* إخفاء و إظهار */
    .hidden { display: none !important; }
    
    /* شريط تمرير مخصص */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--main); border-radius: 4px; }
</style>
</head>
<body>
<div class="bg-blobs"><div class="blob-1"></div><div class="blob-2"></div></div>

<!-- Login Screen -->
<div id="loginScreen" class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-80 z-50">
    <div class="glass p-8 w-full max-w-sm text-center">
        <h1 class="text-4xl font-black mb-6 text-transparent bg-clip-text bg-gradient-to-r from-purple-500 to-cyan-500">ROZIXXIT</h1>
        <input type="password" id="tokenInput" class="inp mono text-center mb-4" placeholder="ACCESS TOKEN">
        <button onclick="login()" class="btn w-full">تسجيل الدخول</button>
        <p id="loginError" class="text-red-500 mt-2 text-sm hidden">كلمة المرور خاطئة!</p>
    </div>
</div>

<!-- Dashboard -->
<div id="dashboard" class="hidden max-w-4xl mx-auto p-4 md:p-8">
    <header class="flex justify-between items-center mb-8 border-b border-gray-800 pb-4">
        <h1 class="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-500 to-cyan-500">ROZIXXIT PANEL</h1>
        <button onclick="location.reload()" class="text-red-500 hover:text-white transition">خروج 🚪</button>
    </header>

    <!-- Generator -->
    <div class="glass p-6 mb-8">
        <h2 class="text-xl font-bold mb-4 text-purple-400">✨ توليد الأكواد</h2>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
                <label class="text-xs text-gray-400 mb-1 block">المدة</label>
                <select id="duration" class="inp" onchange="toggleCustom()">
                    <option value="3600">ساعة واحدة</option>
                    <option value="10800">3 ساعات</option>
                    <option value="21600">6 ساعات</option>
                    <option value="43200">12 ساعة</option>
                    <option value="86400">يوم واحد</option>
                    <option value="172800">يومين</option>
                    <option value="259200">3 أيام</option>
                    <option value="604800">أسبوع</option>
                    <option value="1296000">15 يوم</option>
                    <option value="2592000">شهر</option>
                    <option value="custom">مخصص ⚙️</option>
                </select>
            </div>
            <div id="customBox" class="hidden">
                <label class="text-xs text-gray-400 mb-1 block">عدد الساعات</label>
                <input type="number" id="customHours" value="1" min="1" class="inp mono text-center">
            </div>
            <div>
                <label class="text-xs text-gray-400 mb-1 block">عدد الأجهزة</label>
                <select id="max_devices" class="inp">
                    <option value="1">جهاز واحد</option>
                    <option value="2">جهازين</option>
                </select>
            </div>
            <div>
                <label class="text-xs text-gray-400 mb-1 block">الكمية (1-100)</label>
                <input type="number" id="qty" value="1" min="1" max="100" class="inp mono text-center">
            </div>
        </div>
        <button onclick="generate()" id="genBtn" class="btn w-full mt-4 text-lg">توليد الأكواد 🚀</button>
    </div>

    <!-- Keys List -->
    <div class="glass p-6">
        <h2 class="text-xl font-bold mb-4 text-cyan-400">📦 الأكواد المخزنة</h2>
        <div id="keysList" class="space-y-3"></div>
    </div>
</div>

<script>
let TOKEN = localStorage.getItem('rozi_token') || '';
const API = '/api';

async function apiCall(endpoint, method='GET', body=null) {
    const headers = { 'X-Admin-Token': TOKEN };
    if(body) headers['Content-Type'] = 'application/json';
    const res = await fetch(endpoint, { method, headers, body: body ? JSON.stringify(body) : null });
    if(res.status === 401) { localStorage.removeItem('rozi_token'); location.reload(); }
    if(!res.ok) throw new Error('API Error');
    return res.json();
}

function toggleCustom() {
    const val = document.getElementById('duration').value;
    const box = document.getElementById('customBox');
    if(val === 'custom') box.classList.remove('hidden');
    else box.classList.add('hidden');
}

async function login() {
    const token = document.getElementById('tokenInput').value;
    if(!token) return;
    TOKEN = token;
    try {
        await apiCall('/keys');
        localStorage.setItem('rozi_token', token);
        document.getElementById('loginScreen').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');
        loadKeys();
    } catch(e) {
        document.getElementById('loginError').classList.remove('hidden');
    }
}

async function generate() {
    const btn = document.getElementById('genBtn');
    let duration = document.getElementById('duration').value;
    const qty = parseInt(document.getElementById('qty').value);
    const max_dev = parseInt(document.getElementById('max_devices').value);

    if(duration === 'custom') {
        const hours = parseInt(document.getElementById('customHours').value);
        if(!hours || hours < 1) return alert('أدخل عدد ساعات صحيح');
        duration = hours * 3600;
    } else {
        duration = parseInt(duration);
    }

    btn.disabled = true; btn.innerText = 'جاري التوليد... ⏳';
    try {
        const res = await apiCall('/generate', 'POST', { duration, quantity: qty, max_devices: max_dev });
        // نسخ الأكواد فوراً للحافظة
        navigator.clipboard.writeText(res.keys.join('\\n'));
        alert(`✅ تم توليد ${qty} كود ونسخهم للحافظة تلقائياً!`);
        loadKeys();
    } catch(e) { alert('خطأ في التوليد'); }
    btn.disabled = false; btn.innerText = 'توليد الأكواد 🚀';
}

async function loadKeys() {
    const keys = await apiCall('/keys');
    const list = document.getElementById('keysList');
    if(keys.length === 0) { list.innerHTML = '<p class="text-gray-500 text-center">لا توجد أكواد حالياً.</p>'; return; }
    
    list.innerHTML = keys.map(k => {
        let statusColor = k.status === 'active' ? 'text-green-400' : (k.status === 'unused' ? 'text-gray-400' : 'text-red-400');
        let statusText = k.status === 'active' ? 'نشط' : (k.status === 'unused' ? 'غير مفعل' : 'منتهي');
        let deviceText = k.max_devices === 1 ? 'جهاز 1' : 'جهازين';
        
        return `
        <div class="key-card">
            <div class="flex justify-between items-center flex-wrap gap-2">
                <span class="key-text mono">${k.key}</span>
                <span class="${statusColor} font-bold text-sm bg-black px-2 py-1 rounded">${statusText}</span>
            </div>
            <div class="flex justify-between items-center text-sm text-gray-400 flex-wrap gap-2 mt-2">
                <span>⏱️ ينتهي: ${k.expires_at ? new Date(k.expires_at*1000).toLocaleString('ar-EG') : 'عند أول تفعيل'}</span>
                <span>📱 ${deviceText}</span>
            </div>
            <div class="flex gap-2 mt-2">
                <button onclick="copyKey('${k.key}')" class="flex-1 bg-cyan-900 text-cyan-300 hover:bg-cyan-700 py-1 rounded text-xs transition">📋 نسخ</button>
                <button onclick="extendKey('${k.key}')" class="flex-1 bg-blue-900 text-blue-300 hover:bg-blue-700 py-1 rounded text-xs transition">➕ يوم</button>
                <button onclick="toggleKey('${k.key}')" class="flex-1 bg-yellow-900 text-yellow-300 hover:bg-yellow-700 py-1 rounded text-xs transition">🚫 تعطيل</button>
                <button onclick="deleteKey('${k.key}')" class="flex-1 bg-red-900 text-red-300 hover:bg-red-700 py-1 rounded text-xs transition">🗑️ حذف</button>
            </div>
        </div>
        `;
    }).join('');
}

function copyKey(key) {
    navigator.clipboard.writeText(key);
    alert('تم نسخ الكود: ' + key);
}

async function extendKey(key) {
    await apiCall(`/key/${key}/extend`, 'POST', {seconds: 86400});
    loadKeys();
}

async function toggleKey(key) {
    await apiCall(`/key/${key}/toggle`, 'POST');
    loadKeys();
}

async function deleteKey(key) {
    if(!confirm('هل أنت متأكد من حذف الكود نهائياً؟')) return;
    await apiCall(`/key/${key}`, 'DELETE');
    loadKeys();
}

if(TOKEN) {
    document.getElementById('loginScreen').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
    loadKeys().catch(() => location.reload());
}
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML
