from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3, uuid, datetime

app = FastAPI()
ADMIN_PASSWORD = "DARKVIPP1"

def init_db():
    conn = sqlite3.connect("licenses.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys (key TEXT PRIMARY KEY, hwid TEXT, expiry TEXT, active INTEGER DEFAULT 1)''')
    conn.commit()
    conn.close()
init_db()

class AppRequest(BaseModel):
    key: str
    hwid: str

@app.get("/", response_class=HTMLResponse)
def login_page():
    return """
    <html dir="rtl"><head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="background:#0a0a0a; color:#FFD700; text-align:center; padding-top:50px; font-family:Arial;">
        <h1 style="text-shadow: 0 0 10px #FFD700;">DARK VIP GZNZRATEUR CODE</h1>
        <form action="/dashboard" method="get" style="background:#1a1a1a; display:inline-block; padding:30px; border-radius:15px; border: 2px solid #FFD700;">
            <input type="password" name="password" placeholder="كلمة السر" style="padding:10px; font-size:16px; border-radius:5px; border:none; text-align:center;"><br><br>
            <button type="submit" style="padding:10px 30px; background:#FFD700; color:black; font-weight:bold; border:none; border-radius:5px; cursor:pointer;">دخول</button>
        </form>
    </body></html>
    """

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(password: str = ""):
    if password != ADMIN_PASSWORD: return "<h2 style='color:red; text-align:center;'>❌ كلمة السر خاطئة!</h2>"
    
    options = ""
    durations = [("1h", "ساعة واحدة ⏱️"), ("3h", "3 ساعات ⏱️"), ("7h", "7 ساعات ⏱️"), ("12h", "12 ساعة ⏱️"), 
                 ("24h", "24 ساعة 📅"), ("2d", "يومين 📅"), ("3d", "3 أيام 📅"), ("7d", "أسبوع 📆")]
    for val, label in durations:
        options += f'<option value="{val}">{label}</option>'

    return f"""
    <html dir="rtl"><head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="background:#0a0a0a; color:#FFD700; text-align:center; padding-top:20px; font-family:Arial;">
        <h1 style="text-shadow: 0 0 10px #FFD700;">DARK VIP GZNZRATEUR CODE</h1>
        <form action="/generate" method="post" style="background:#1a1a1a; display:inline-block; padding:30px; border-radius:15px; border: 2px solid #FFD700;">
            <input type="hidden" name="password" value="{password}">
            <label>اختر المدة:</label><br><br>
            <select name="duration" style="padding:10px; font-size:16px; width:200px; border-radius:5px;">
                {options}
            </select><br><br>
            <label>عدد الأكواد المطلوبة:</label><br><br>
            <input type="number" name="amount" value="1" min="1" max="100" style="padding:10px; font-size:16px; width:180px; text-align:center; border-radius:5px;"><br><br>
            <button type="submit" style="padding:10px 30px; background:#FFD700; color:black; font-weight:bold; border:none; border-radius:5px; cursor:pointer;">توليد الأكواد ✨</button>
        </form>
    </body></html>
    """

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
    
    conn = sqlite3.connect("licenses.db")
    c = conn.cursor()
    
    generated_keys = []
    for _ in range(amount):
        new_key = f"DARK-{str(uuid.uuid4())[:8].upper()}"
        c.execute("INSERT INTO keys (key, expiry) VALUES (?, ?)", (new_key, expiry_str))
        generated_keys.append(new_key)
        
    conn.commit()
    conn.close()
    
    keys_html = "".join([f"<h3 style='background:#333; padding:10px; border-radius:5px; display:inline-block; margin:5px;'>{k}</h3><br>" for k in generated_keys])
    
    return f"""
    <html dir="rtl"><head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="background:#0a0a0a; color:#FFD700; text-align:center; padding-top:20px; font-family:Arial;">
        <h1 style="color:#00E676; text-shadow: 0 0 10px #00E676;">✅ تم توليد الأكواد!</h1>
        <p>صالح حتى: {expiry_str}</p>
        <div style="background:#1a1a1a; padding:20px; border-radius:10px; border: 2px solid #FFD700;">
            {keys_html}
        </div>
        <br>
        <a href="/dashboard?password={password}" style="color:#FFD700; text-decoration:none; font-size:20px;">🔙 العودة للوحة التحكم</a>
    </body></html>
    """

@app.post("/api/validate")
def validate(req: AppRequest):
    conn = sqlite3.connect("licenses.db")
    c = conn.cursor()
    c.execute("SELECT hwid, expiry, active FROM keys WHERE key=?", (req.key,))
    row = c.fetchone()
    if not row:
        conn.close(); raise HTTPException(status_code=400, detail="❌ الكود غير موجود")
    db_hwid, expiry_str, active = row
    if active == 0:
        conn.close(); raise HTTPException(status_code=403, detail="🚫 الكود ملغى")
    expiry = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
    if datetime.datetime.now() > expiry:
        conn.close(); raise HTTPException(status_code=403, detail="⏰ الكود منتهي")
    if not db_hwid:
        c.execute("UPDATE keys SET hwid=? WHERE key=?", (req.hwid, req.key)); conn.commit()
    elif db_hwid != req.hwid:
        conn.close(); raise HTTPException(status_code=403, detail="⚠️ الكود مستخدم في هاتف آخر")
    conn.close()
    return {"status": "success", "expires_in": expiry_str}
