\
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import html
import json

from astro_core import calculate

app = FastAPI(title="Astro Assistant", version="1.0")

PAGE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Astro Assistant</title>
<style>
body{font-family:Arial,sans-serif;background:#0f1115;color:#f5f5f5;margin:0}
.wrap{max-width:760px;margin:auto;padding:18px}
.card{background:#191d24;border:1px solid #2b313b;border-radius:16px;padding:16px;margin:12px 0}
h1{font-size:26px;margin:6px 0 16px}
h2{font-size:19px;margin-top:4px}
label{display:block;margin:10px 0 5px;color:#cfd5df}
input{width:100%;box-sizing:border-box;padding:12px;border-radius:10px;border:1px solid #3a4350;background:#10141a;color:#fff}
button{width:100%;padding:14px;border:0;border-radius:12px;background:#7c5cff;color:white;font-size:17px;font-weight:bold;margin-top:16px}
pre{white-space:pre-wrap;word-break:break-word;background:#0b0e12;padding:12px;border-radius:12px;direction:ltr;text-align:left}
.note{color:#aeb7c4;font-size:13px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media(max-width:600px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body><div class="wrap">
<h1>Astro Assistant</h1>
<p class="note">Natal • Transits • Solar Return • Secondary Progressions • Primary Directions التجريبية</p>
<form method="post" action="/analyze-form">
<div class="card"><h2>بيانات الميلاد</h2>
<label>الاسم</label><input name="name" value="Abdulhaq">
<label>تاريخ ووقت الميلاد</label><input name="birth_datetime" value="1994-05-23T03:30:00">
<div class="grid">
<div><label>فرق UTC</label><input name="birth_utc_offset" value="3"></div>
<div><label>خط العرض</label><input name="birth_lat" value="13.58"></div>
<div><label>خط الطول</label><input name="birth_lon" value="44.02"></div>
</div></div>

<div class="card"><h2>بيانات الحدث</h2>
<label>تاريخ ووقت الحدث</label><input name="event_datetime" value="2026-07-23T12:00:00">
<div class="grid">
<div><label>فرق UTC</label><input name="event_utc_offset" value="3"></div>
<div><label>خط العرض</label><input name="event_lat" value="13.58"></div>
<div><label>خط الطول</label><input name="event_lon" value="44.02"></div>
</div></div>

<div class="card"><h2>مكان العودة الشمسية</h2>
<div class="grid">
<div><label>خط العرض</label><input name="solar_return_lat" value="13.58"></div>
<div><label>خط الطول</label><input name="solar_return_lon" value="44.02"></div>
</div>
<label>الأورب الأقصى</label><input name="max_orb" value="2.0">
<button type="submit">احسب كل شيء</button>
</div>
</form>
%s
__RESULT_BLOCK__
<p class="note">تنبيه: الأداة تعليمية. التوجيهات الأولية هنا محدودة إلى ASC/MC بمفتاح Naibod، وليست تطبيقًا كاملًا لكل منهج Estadella.</p>
</div></body></html>
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
        result = calculate(locals())
        output = "<div class='card'><h2>النتائج</h2><pre>" + html.escape(
            json.dumps(result, ensure_ascii=False, indent=2)
        ) + "</pre></div>"
    except Exception as exc:
        output = "<div class='card'><h2>خطأ</h2><pre>" + html.escape(str(exc)) + "</pre></div>"
    return PAGE.replace("__RESULT_BLOCK__", output)
