
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import html
import json

from astro_core import calculate

app = FastAPI(title="Astro Assistant", version="1.2")

AR_SIGNS = [
    "الحمل","الثور","الجوزاء","السرطان","الأسد","العذراء",
    "الميزان","العقرب","القوس","الجدي","الدلو","الحوت"
]

SIGN_SYMBOLS = ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"]

AR_PLANETS = {
    "Sun":"الشمس","Moon":"القمر","Mercury":"عطارد","Venus":"الزهرة","Mars":"المريخ",
    "Jupiter":"المشتري","Saturn":"زحل","Uranus":"أورانوس","Neptune":"نبتون",
    "Pluto":"بلوتو","Mean Node":"العقدة الشمالية"
}

SYMBOLS = {
    "Sun":"☉","Moon":"☽","Mercury":"☿","Venus":"♀","Mars":"♂",
    "Jupiter":"♃","Saturn":"♄","Uranus":"♅","Neptune":"♆","Pluto":"♇",
    "Mean Node":"☊","ASC":"ASC","MC":"MC","Vertex":"Vx"
}

ASPECT_AR = {
    "Conjunction":"اقتران",
    "Sextile":"تسديس",
    "Square":"تربيع",
    "Trine":"تثليث",
    "Opposition":"مقابلة",
}

ASPECT_CLASS = {
    "Conjunction":"asp-conj",
    "Sextile":"asp-good",
    "Trine":"asp-good",
    "Square":"asp-hard",
    "Opposition":"asp-hard",
}

HOUSE_MEANINGS = {
    1:"الهوية والبدايات",
    2:"المال والقيم",
    3:"التواصل والتعلم",
    4:"المنزل والجذور",
    5:"الإبداع والمتعة",
    6:"العمل اليومي والصحة",
    7:"العلاقات والشراكات",
    8:"التحولات والموارد المشتركة",
    9:"السفر والمعرفة العليا",
    10:"المهنة والسمعة",
    11:"الأصدقاء والأهداف",
    12:"العزلة واللاوعي",
}

def zodiac_parts(lon: float):
    lon = lon % 360
    sign_index = int(lon // 30)
    degree = lon % 30
    d = int(degree)
    m = int(round((degree - d) * 60))
    if m == 60:
        d += 1
        m = 0
    return sign_index, d, m

def zodiac_position(lon: float) -> str:
    i, d, m = zodiac_parts(lon)
    return f"{SIGN_SYMBOLS[i]} {d}° {m:02d}′ {AR_SIGNS[i]}"

def planet_table(planets: dict) -> str:
    rows = []
    for name, data in planets.items():
        motion = "متراجع ℞" if data.get("retrograde") else "مباشر"
        rows.append(
            f"<tr><td class='symbol'>{SYMBOLS.get(name,'')}</td>"
            f"<td>{html.escape(AR_PLANETS.get(name,name))}</td>"
            f"<td>{zodiac_position(float(data['longitude']))}</td>"
            f"<td>{motion}</td></tr>"
        )
    return table_wrap(
        "<tr><th>الرمز</th><th>الكوكب</th><th>الموقع</th><th>الحركة</th></tr>",
        "".join(rows)
    )

def angle_table(angles: dict) -> str:
    labels = {"ASC":"الطالع ASC","MC":"وسط السماء MC","ARMC":"ARMC","Vertex":"Vertex"}
    rows = []
    for name, lon in angles.items():
        rows.append(
            f"<tr><td>{html.escape(labels.get(name,name))}</td>"
            f"<td>{zodiac_position(float(lon))}</td></tr>"
        )
    return table_wrap("<tr><th>الزاوية</th><th>الموقع</th></tr>", "".join(rows))

def houses_table(houses: dict) -> str:
    rows = []
    for i in range(1, 13):
        key = f"House {i}"
        lon = float(houses[key])
        rows.append(
            f"<tr><td>البيت {i}</td>"
            f"<td>{zodiac_position(lon)}</td>"
            f"<td>{HOUSE_MEANINGS[i]}</td></tr>"
        )
    return table_wrap(
        "<tr><th>البيت</th><th>رأس البيت</th><th>الدلالة العامة</th></tr>",
        "".join(rows)
    )

def aspect_table(aspects: list, limit: int = 80) -> str:
    if not aspects:
        return "<p class='muted'>لا توجد زوايا ضمن الأورب المحدد.</p>"
    rows = []
    for a in aspects[:limit]:
        asp = str(a["aspect"])
        css = ASPECT_CLASS.get(asp,"")
        rows.append(
            f"<tr class='{css}'><td>{html.escape(AR_PLANETS.get(str(a['moving_factor']),str(a['moving_factor'])))}</td>"
            f"<td><span class='aspect-pill'>{html.escape(ASPECT_AR.get(asp,asp))}</span></td>"
            f"<td>{html.escape(AR_PLANETS.get(str(a['natal_factor']),str(a['natal_factor'])))}</td>"
            f"<td>{float(a['orb']):.2f}°</td></tr>"
        )
    return table_wrap(
        "<tr><th>العامل المتحرك</th><th>الزاوية</th><th>العامل الميلادي</th><th>الأورب</th></tr>",
        "".join(rows)
    )

def primary_table(rows: list) -> str:
    if not rows:
        return "<p class='muted'>لا توجد توجيهات أولية قريبة ضمن النطاق التجريبي.</p>"
    out = []
    for a in rows:
        asp = str(a["aspect"])
        css = ASPECT_CLASS.get(asp,"")
        out.append(
            f"<tr class='{css}'><td>{html.escape(a['direction'])}</td>"
            f"<td>{html.escape(a['significator'])}</td>"
            f"<td>{html.escape(ASPECT_AR.get(asp,asp))}</td>"
            f"<td>{html.escape(AR_PLANETS.get(a['natal_factor'],a['natal_factor']))}</td>"
            f"<td>{float(a['orb_arcmin']):.2f}′</td></tr>"
        )
    return table_wrap(
        "<tr><th>الاتجاه</th><th>الدال</th><th>الزاوية</th><th>العامل</th><th>الأورب</th></tr>",
        "".join(out)
    )

def table_wrap(head: str, body: str) -> str:
    return f"<div class='table-wrap'><table><thead>{head}</thead><tbody>{body}</tbody></table></div>"

def section(title: str, body: str, badge: str = "") -> str:
    b = f"<span class='badge'>{badge}</span>" if badge else ""
    return f"<section class='result-card'><h2>{title}{b}</h2>{body}</section>"

def render_results(result: dict) -> str:
    meta = result["metadata"]
    summary = f"""
    <section class="result-card highlight">
      <h2>ملخص الحساب</h2>
      <div class="summary-grid">
        <div><span>الاسم</span><strong>{html.escape(meta.get("name",""))}</strong></div>
        <div><span>وقت الميلاد UTC</span><strong>{html.escape(meta["birth_utc"])}</strong></div>
        <div><span>وقت الحدث UTC</span><strong>{html.escape(meta["event_utc"])}</strong></div>
        <div><span>العودة الشمسية UTC</span><strong>{html.escape(meta["solar_return_utc"])}</strong></div>
        <div><span>التقدم الثانوي</span><strong>{html.escape(meta["progressed_utc"])}</strong></div>
        <div><span>نظام البيوت</span><strong>{html.escape(meta["house_system"])}</strong></div>
      </div>
    </section>
    """

    blocks = [summary]

    natal = result["natal"]
    blocks.append(section(
        "الخريطة الميلادية",
        "<div class='tabs-note'>الأساس الذي تُقارن به بقية الخرائط</div>"
        "<h3>الكواكب</h3>" + planet_table(natal["planets"]) +
        "<h3>الزوايا الأساسية</h3>" + angle_table(natal["angles"]) +
        "<h3>البيوت الاثنا عشر</h3>" + houses_table(natal["houses"]),
        "Natal"
    ))

    transits = result["transits"]
    blocks.append(section(
        "العبور الحالي",
        "<h3>الكواكب العابرة</h3>" + planet_table(transits["planets"]) +
        "<h3>الجوانب إلى الخريطة الميلادية</h3>" + aspect_table(transits["aspects_to_natal"]),
        "Transits"
    ))

    sr = result["solar_return"]
    blocks.append(section(
        "العودة الشمسية",
        "<h3>كواكب العودة</h3>" + planet_table(sr["planets"]) +
        "<h3>زوايا وبيوت العودة</h3>" + angle_table(sr["angles"]) +
        houses_table(sr["houses"]) +
        "<h3>زوايا العودة إلى الميلاد</h3>" + aspect_table(sr["aspects_to_natal"]),
        "Solar Return"
    ))

    prog = result["secondary_progressions"]
    blocks.append(section(
        "التقدمات الثانوية",
        "<h3>الكواكب المتقدمة</h3>" + planet_table(prog["planets"]) +
        "<h3>الزوايا والبيوت المتقدمة</h3>" + angle_table(prog["angles"]) +
        houses_table(prog["houses"]) +
        "<h3>زوايا التقدمات إلى الميلاد</h3>" + aspect_table(prog["aspects_to_natal"]),
        "Progressions"
    ))

    blocks.append(section(
        "التوجيهات الأولية التجريبية",
        primary_table(result["primary_directions_experimental"]) +
        "<p class='muted'>محدودة حاليًا إلى ASC وMC، مباشر وعكسي، بمفتاح Naibod.</p>",
        "Primary Directions"
    ))

    raw = html.escape(json.dumps(result, ensure_ascii=False, indent=2))
    blocks.append(
        f"<details class='result-card'><summary>عرض البيانات الخام JSON</summary><pre>{raw}</pre></details>"
    )

    return "<div id='results'>" + "".join(blocks) + "</div>"

PAGE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Astro Assistant</title>
<style>
:root{
  --bg:#0e1117;--panel:#171c24;--panel2:#11161d;--border:#2c3440;
  --text:#f4f6f8;--muted:#aeb8c6;--accent:#7c5cff;--accent2:#9b86ff;
  --good:#173f33;--goodText:#8be6bd;--hard:#4a2228;--hardText:#ff9ca7;
  --conj:#3a315f;--conjText:#c5b8ff
}
*{box-sizing:border-box}
body{font-family:Arial,Tahoma,sans-serif;background:var(--bg);color:var(--text);margin:0}
.wrap{max-width:980px;margin:auto;padding:18px}
.hero{text-align:center;padding:14px 0 8px}
.hero h1{font-size:32px;margin:0 0 8px}
.hero p{color:var(--muted);margin:0}
.card,.result-card{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:18px;margin:14px 0}
h2{font-size:22px;margin:0 0 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
h3{font-size:17px;margin:18px 0 10px;color:#d9ddff}
.badge{font-size:12px;padding:5px 9px;border-radius:999px;background:#28213f;color:#c9bdff;font-weight:normal}
.tabs-note{color:var(--muted);font-size:13px;margin-top:-6px}
label{display:block;margin:11px 0 6px;color:#d2d8e2}
input{width:100%;padding:13px;border-radius:11px;border:1px solid #3a4453;background:var(--panel2);color:white;font-size:16px}
button{width:100%;padding:15px;border:0;border-radius:12px;background:var(--accent);color:white;font-size:18px;font-weight:bold;margin-top:16px}
button:hover{background:var(--accent2)}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.summary-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.summary-grid div{background:var(--panel2);padding:12px;border-radius:12px}
.summary-grid span{display:block;color:var(--muted);font-size:13px;margin-bottom:6px}
.summary-grid strong{font-size:14px;word-break:break-word}
.highlight{border-color:#6f59db}
.table-wrap{overflow-x:auto;border-radius:12px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;min-width:640px;background:var(--panel2)}
th,td{padding:11px;border-bottom:1px solid var(--border);text-align:right;font-size:14px}
th{color:#dcd5ff;background:#191f29}
.symbol{font-size:20px}
.aspect-pill{display:inline-block;padding:4px 8px;border-radius:999px;font-size:12px}
.asp-good .aspect-pill{background:var(--good);color:var(--goodText)}
.asp-hard .aspect-pill{background:var(--hard);color:var(--hardText)}
.asp-conj .aspect-pill{background:var(--conj);color:var(--conjText)}
.muted{color:var(--muted);font-size:13px}
pre{white-space:pre-wrap;word-break:break-word;background:#090c10;padding:14px;border-radius:12px;direction:ltr;text-align:left;overflow:auto}
details summary{cursor:pointer;font-weight:bold}
.error{border-color:#a94a4a}
@media(max-width:700px){
  .grid,.summary-grid{grid-template-columns:1fr}
  .hero h1{font-size:27px}
  .wrap{padding:12px}
}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h1>Astro Assistant</h1>
    <p>Natal • Transits • Solar Return • Secondary Progressions • Primary Directions</p>
  </div>

  <form method="post" action="/analyze-form">
    <div class="card">
      <h2>بيانات الميلاد</h2>
      <label>الاسم</label><input name="name" value="Abdulhaq">
      <label>تاريخ ووقت الميلاد</label><input name="birth_datetime" value="1994-05-23T03:30:00">
      <div class="grid">
        <div><label>فرق UTC</label><input name="birth_utc_offset" value="3"></div>
        <div><label>خط العرض</label><input name="birth_lat" value="13.58"></div>
        <div><label>خط الطول</label><input name="birth_lon" value="44.02"></div>
      </div>
    </div>

    <div class="card">
      <h2>بيانات الحدث</h2>
      <label>تاريخ ووقت الحدث</label><input name="event_datetime" value="2026-07-23T12:00:00">
      <div class="grid">
        <div><label>فرق UTC</label><input name="event_utc_offset" value="3"></div>
        <div><label>خط العرض</label><input name="event_lat" value="13.58"></div>
        <div><label>خط الطول</label><input name="event_lon" value="44.02"></div>
      </div>
    </div>

    <div class="card">
      <h2>مكان العودة الشمسية</h2>
      <div class="grid">
        <div><label>خط العرض</label><input name="solar_return_lat" value="13.58"></div>
        <div><label>خط الطول</label><input name="solar_return_lon" value="44.02"></div>
        <div><label>الأورب الأقصى</label><input name="max_orb" value="2.0"></div>
      </div>
      <button type="submit">احسب واعرض النتائج</button>
    </div>
  </form>

  __RESULT_BLOCK__

  <p class="muted">
    تنبيه: الأداة تعليمية، والتوجيهات الأولية هنا محدودة وليست تطبيقًا كاملًا لكل مدارس التنجيم.
  </p>
</div>
</body>
</html>
"""

class AnalysisRequest(BaseModel):
    name: str = ""
    birth_datetime: str
    birth_utc_offset: float
    birth_lat: float
    birth_lon: float
    event_datetime: str
    event_utc_offset: float
    event_lat: float
    event_lon: float
    solar_return_lat: float
    solar_return_lon: float
    max_orb: float = 2.0

@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE.replace("__RESULT_BLOCK__", "")

@app.get("/health")
def health():
    return {"status":"healthy"}

@app.post("/analyze")
def analyze(req: AnalysisRequest):
    return calculate(req.model_dump())

@app.post("/analyze-form", response_class=HTMLResponse)
def analyze_form(
    name: str = Form(""),
    birth_datetime: str = Form(...),
    birth_utc_offset: float = Form(...),
    birth_lat: float = Form(...),
    birth_lon: float = Form(...),
    event_datetime: str = Form(...),
    event_utc_offset: float = Form(...),
    event_lat: float = Form(...),
    event_lon: float = Form(...),
    solar_return_lat: float = Form(...),
    solar_return_lon: float = Form(...),
    max_orb: float = Form(2.0),
):
    try:
        payload = {
            "name": name,
            "birth_datetime": birth_datetime,
            "birth_utc_offset": birth_utc_offset,
            "birth_lat": birth_lat,
            "birth_lon": birth_lon,
            "event_datetime": event_datetime,
            "event_utc_offset": event_utc_offset,
            "event_lat": event_lat,
            "event_lon": event_lon,
            "solar_return_lat": solar_return_lat,
            "solar_return_lon": solar_return_lon,
            "max_orb": max_orb,
        }
        result = calculate(payload)
        output = render_results(result)
    except Exception as exc:
        output = (
            "<section class='result-card error'><h2>حدث خطأ</h2>"
            f"<pre>{html.escape(str(exc))}</pre></section>"
        )
    return PAGE.replace("__RESULT_BLOCK__", output)
