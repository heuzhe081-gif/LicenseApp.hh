from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
import sqlite3, uuid, datetime

app = FastAPI()
ADMIN_PASSWORD = "DARKVIPP1"
DB_PATH = "/tmp/licenses.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys (key TEXT PRIMARY KEY, hwid TEXT, expiry TEXT, active INTEGER DEFAULT 1)''')
    conn.commit()
    conn.close()
init_db()

class AppRequest(BaseModel):
    key: str
    hwid: str

# --- التصميم الفخم المشترك (CSS) ---
# هذا الجزء مسؤول عن الألوان، الخطوط، والزجاج الشفاف
CSS_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
    * { font-family: 'Cairo', sans-serif; box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #09090b; color: #fff; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 20px; }
    
    /* خلفية متحركة فخمة */
    .bg-glow { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; overflow: hidden; }
    .glow-circle { position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.4; }
    .circle-1 { width: 400px; height: 400px; background: #00f2fe; top: -100px; left: -100px; }
    .circle-2 { width: 300px; height: 300px; background: #4facfe; bottom: -50px; right: -50px; }

    /* التصميم الزجاجي */
    .glass-panel { background: rgba(20, 20, 25, 0.7); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 30px; width: 100%; max-width: 900px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-bottom: 20px; }
    .title { font-size: 28px; font-weight: 900; text-align: center; background: linear-gradient(90deg, #00f2fe, #4facfe); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 20px; letter-spacing: 2px; }
    
    /* الحقول والأزرار */
    input, select { background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 12px; border-radius: 10px; outline: none; transition: 0.3s; font-size: 14px; margin-bottom: 10px; width: 100%; }
    input:focus, select:focus { border-color: #00f2fe; box-shadow: 0 0 10px rgba(0, 242, 254, 0.3); }
    button { background: linear-gradient(90deg, #00f2fe, #4facfe); color: #000; font-weight: 900; border: none; padding: 12px 25px; border-radius: 10px; cursor: pointer; transition: 0.3s; width: 100%; font-size: 16px; }
    button:hover { transform: scale(1.02); box-shadow: 0 0 20px rgba(0, 242, 254, 0.6); }
    
    /* الجدول */
    .table-container { overflow-x: auto; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); }
    table { width: 100%; border-collapse: collapse; text-align: center; font-size: 13px; }
    th { background: rgba(0,0,0,0.6); padding: 15px; color: #00f2fe; font-weight: 700; }
    td { padding: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); }
    tr:hover td { background: rgba(255,255,255,0.03); }
    
    /* أزرار التحكم */
    .action-btn { padding: 6px 10px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; margin: 0 2px; display: inline-block; }
    .btn-extend { background: rgba(0, 242, 254, 0.2); color: #00f2fe; border: 1px solid #00f2fe; }
    .btn-toggle { background: rgba(255, 165, 0, 0.2); color: orange; border: 1px solid orange; }
    .btn-delete { background: rgba(255, 0, 0, 0.2); color: red; border: 1px solid red; }
    
    /* شارات الحالة */
    .status-active { color: #00e676; text-shadow: 0 0 5px #00e676; font-weight: bold; }
    .status-expired { color: orange; font-weight: bold; }
    .status-disabled { color: red; font-weight: bold; }
</style>
<div class="bg-glow">
    <div class="glow-circle circle-1"></div>
    <div class="glow-circle circle-2"></div>
</div>
"""

# --- صفحة تسجيل الدخول ---
@app.get("/", response_class=HTMLResponse)
def login_page():
    return f"""
    <html dir="rtl"><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>ADHEMXAYOUB</title>{CSS_STYLE}</head>
    <body style="justify-content: center; height: 100vh;">
        <div class="glass-panel" style="max-width: 400px;">
            <div class="title">ADHEMXAYOUB</div>
            <p style="text-align:center; color:#aaa; margin-bottom: 20px;">لوحة التحكم الفخمة</p>
            <form action="/dashboard" method="get">
                <input type="password" name="password" placeholder="أدخل كلمة السر 🔐" required>
                <button type="submit">دخول النظام ⚡</button>
            </form>
        </div>
    </body></html>
    """

# --- لوحة التحكم ---
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(password: str = ""):
    if password != ADMIN_PASSWORD: return f"<html>{CSS_STYLE}<body><h2 style='color:red; text-align:center;'>❌ كلمة السر خاطئة!</h2></body></html>"
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT key, hwid, expiry, active FROM keys ORDER BY expiry DESC")
    rows = c.fetchall()
    
    # إحصائيات سريعة
    total_keys = len(rows)
    active_keys = sum(1 for r in rows if r[3] == 1 and datetime.datetime.now() <= datetime.datetime.strptime(r[2], "%Y-%m-%d %H:%M:%S"))
    conn.close()

    table_rows = ""
    now = datetime.datetime.now()
    for row in rows:
        key, hwid, expiry, active = row
        exp_date = datetime.datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
        
        if active == 0: status = "<span class='status-disabled'>🚫 معطل</span>"
        elif now > exp_date: status = "<span class='status-expired'>⏰ منتهي</span>"
        else: status = "<span class='status-active'>🟢 نشط</span>"
            
        device = hwid[:6] + "..." if hwid else "غير مربوط 📱"
        
        table_rows += f"""
        <tr>
            <td style="color:#00f2fe; font-weight:bold;">{key}</td>
            <td>{status}</td>
            <td style="color:#aaa; font-size:11px;">{expiry}</td>
            <td style="color:#aaa; font-size:11px;">{device}</td>
            <td>
                <a href="/extend/{key}?password={password}" class="action-btn btn-extend">➕ يوم</a>
                <a href="/toggle/{key}?password={password}" class="action-btn btn-toggle">🚫 تبديل</a>
                <a href="/delete/{key}?password={password}" class="action-btn btn-delete" onclick="return confirm('هل أنت متأكد من الحذف؟')">🗑️ حذف</a>
            </td>
        </tr>
        """

    options = ""
    durations = [("1h", "ساعة ⏱️"), ("3h", "3 ساعات ⏱️"), ("7h", "7 ساعات ⏱️"), ("12h", "12 ساعة ⏱️"), 
                 ("24h", "24 ساعة 📅"), ("2d", "يومين 📅"), ("3d", "3 أيام 📅"), ("7d", "أسبوع 📆")]
    for val, label in durations:
        options += f'<option value="{val}">{label}</option>'

    return f"""
    <html dir="rtl"><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>ADHEMXAYOUB</title>{CSS_STYLE}</head>
    <body>
        <!-- الشريط العلوي -->
        <div style="width:100%; max-width:900px; display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h1 class="title" style="margin:0;">ADHEMXAYOUB VIP</h1>
            <a href="/" style="color:red; text-decoration:none; font-weight:bold;">تسجيل خروج 🚪</a>
        </div>

        <!-- لوحة الإحصائيات -->
        <div style="display:flex; gap:15px; width:100%; max-width:900px; margin-bottom:20px;">
            <div class="glass-panel" style="flex:1; text-align:center; padding:15px; margin-bottom:0;">
                <h3 style="color:#aaa; font-size:14px;">إجمالي الأكواد</h3>
                <p style="font-size:24px; font-weight:bold; color:#fff;">{total_keys}</p>
            </div>
            <div class="glass-panel" style="flex:1; text-align:center; padding:15px; margin-bottom:0;">
                <h3 style="color:#aaa; font-size:14px;">الأكواد النشطة</h3>
                <p style="font-size:24px; font-weight:bold; color:#00e676;">{active_keys}</p>
            </div>
        </div>
        
        <!-- موليد الأكواد -->
        <div class="glass-panel">
            <h3 style="color:#fff; margin-bottom:15px; font-size:16px;">✨ توليد أكواد جديدة</h3>
            <form action="/generate" method="post" style="display:flex; gap:10px; flex-wrap:wrap;">
                <input type="hidden" name="password" value="{password}">
                <select name="duration" style="flex:2; min-width:150px; margin-bottom:0;">
                    {options}
                </select>
                <input type="number" name="amount" value="1" min="1" max="100" style="flex:1; min-width:80px; text-align:center; margin-bottom:0;" placeholder="الكمية">
                <button type="submit" style="flex:1; min-width:120px;">توليد الأكواد 🚀</button>
            </form>
        </div>

        <!-- جدول الأكواد -->
        <div class="glass-panel" style="padding:15px;">
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>الكود</th>
                            <th>الحالة</th>
                            <th>تاريخ الانتهاء</th>
                            <th>الجهاز</th>
                            <th>التحكم</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows if table_rows else "<tr><td colspan='5' style='padding:30px; color:#aaa;'>لا توجد أكواد في النظام حالياً</td></tr>"}
                    </tbody>
                </table>
            </div>
        </div>
    </body></html>
    """

# --- مسارات التحكم (توليد، حذف، تعطيل، زيادة) ---
@app.post("/generate", response_class=HTMLResponse)
def generate_web(password: str = Form(...), duration: str = Form(...), amount: int = Form(...)):
    if password != ADMIN_PASSWORD: return "<h2>❌ غير مصرح لك</h2>"
    now = datetime.datetime.now()
    if duration == "1h": expiry = now + datetime.timedelta(hours=1)
    elif duration == "3h": expiry = now + datetime.timedelta(hours=3)
    elif duration == "7h": expiry = now + datetime.timedelta(hours=7)
    elif duration == "12h": expiry = now + datetime.timedelta(hours=12)
    elif duration == "24h": expiry = now + datetime.timedelta(days=1)
    elif duration == "2d": expiry = now + datetime.timedelta(days=2)
    elif duration == "3d": expiry = now + datetime.timedelta(days=3)
    else: expiry = now + datetime.timedelta(days=7)
    expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for _ in range(amount):
        new_key = f"DARK-{str(uuid.uuid4())[:8].upper()}"
        c.execute("INSERT INTO keys (key, expiry) VALUES (?, ?)", (new_key, expiry_str))
    conn.commit(); conn.close()
    return RedirectResponse(url=f"/dashboard?password={password}", status_code=303)

@app.get("/delete/{key}")
def delete_key(key: str, password: str):
    if password != ADMIN_PASSWORD: return "غير مصرح"
    conn = sqlite3.connect(DB_PATH); conn.execute("DELETE FROM keys WHERE key=?", (key,)); conn.commit(); conn.close()
    return RedirectResponse(url=f"/dashboard?password={password}", status_code=303)

@app.get("/toggle/{key}")
def toggle_key(key: str, password: str):
    if password != ADMIN_PASSWORD: return "غير مصرح"
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT active FROM keys WHERE key=?", (key,))
    row = c.fetchone()
    if row:
        new_status = 0 if row[0] == 1 else 1
        c.execute("UPDATE keys SET active=? WHERE key=?", (new_status, key)); conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?password={password}", status_code=303)

@app.get("/extend/{key}")
def extend_key(key: str, password: str):
    if password != ADMIN_PASSWORD: return "غير مصرح"
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT expiry FROM keys WHERE key=?", (key,))
    row = c.fetchone()
    if row:
        current_expiry = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        new_expiry = current_expiry + datetime.timedelta(days=1)
        c.execute("UPDATE keys SET expiry=? WHERE key=?", (new_expiry.strftime("%Y-%m-%d %H:%M:%S"), key)); conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?password={password}", status_code=303)

# --- API للتطبيق ---
@app.post("/api/validate")
def validate(req: AppRequest):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT hwid, expiry, active FROM keys WHERE key=?", (req.key,))
    row = c.fetchone()
    if not row:
        conn.close(); raise HTTPException(status_code=400, detail="❌ الكود غير موجود")
    db_hwid, expiry_str, active = row
    if active == 0:
        conn.close(); raise HTTPException(status_code=403, detail="🚫 الكود معطل")
    expiry = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
    if datetime.datetime.now() > expiry:
        conn.close(); raise HTTPException(status_code=403, detail="⏰ الكود منتهي")
    if not db_hwid:
        c.execute("UPDATE keys SET hwid=? WHERE key=?", (req.hwid, req.key)); conn.commit()
    elif db_hwid != req.hwid:
        conn.close(); raise HTTPException(status_code=403, detail="⚠️ الكود مستخدم في هاتف آخر")
    conn.close()
    return {"status": "success", "expires_in": expiry_str}
