
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import html
import json
import math
from collections import Counter
from datetime import datetime, timedelta

from astro_core import calculate

app = FastAPI(title="Astro Assistant", version="2.1")

AR_SIGNS = [
    "الحمل","الثور","الجوزاء","السرطان","الأسد","العذراء",
    "الميزان","العقرب","القوس","الجدي","الدلو","الحوت"
]

SIGN_SYMBOLS = ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"]

AR_PLANETS = {
    "Sun":"الشمس","Moon":"القمر","Mercury":"عطارد","Venus":"الزهرة","Mars":"المريخ",
    "Jupiter":"المشتري","Saturn":"زحل","Uranus":"أورانوس","Neptune":"نبتون",
    "Pluto":"بلوتو","Mean Node":"العقدة الشمالية","ASC":"الطالع",
    "MC":"وسط السماء","ARMC":"ARMC","Vertex":"Vertex"
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

FACTOR_THEMES = {
    "Sun":"الهوية والثقة والظهور",
    "Moon":"المزاج والراحة والأسرة",
    "Mercury":"التفكير والتواصل والقرارات",
    "Venus":"العلاقات والمال والذوق",
    "Mars":"الدافع والمنافسة والطاقة",
    "Jupiter":"التوسع والفرص والتعلم",
    "Saturn":"المسؤولية والضغط والانضباط",
    "Uranus":"التغيير المفاجئ والاستقلال",
    "Neptune":"الخيال والضبابية والإلهام",
    "Pluto":"التحول العميق والقوة",
    "Mean Node":"الاتجاه العام والتجارب الجديدة",
    "ASC":"الصورة الشخصية والبدايات",
    "MC":"المهنة والسمعة والهدف العام",
    "ARMC":"التوقيت والزوايا المحورية",
    "Vertex":"اللقاءات والانعطافات",
}

ASPECT_TONE = {
    "Conjunction": ("مركز", 82),
    "Trine": ("منساب", 78),
    "Sextile": ("مساند", 70),
    "Square": ("ضاغط", 76),
    "Opposition": ("استقطابي", 80),
}

ANALYSIS_FACTORS = {
    "Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
    "Uranus","Neptune","Pluto","Mean Node","ASC","MC","Vertex"
}

PAIR_MEANINGS = {
    "Sun": "الإرادة والهوية والظهور",
    "Moon": "الاحتياجات العاطفية والمزاج والأسرة",
    "Mercury": "التفكير والتواصل والقرارات",
    "Venus": "العلاقات والمال والانسجام",
    "Mars": "الدافع والمنافسة ورد الفعل",
    "Jupiter": "الفرص والتوسع والثقة",
    "Saturn": "المسؤولية والحدود والانضباط",
    "Uranus": "التغيير والاستقلال والمفاجآت",
    "Neptune": "الخيال والإلهام والضبابية",
    "Pluto": "القوة والتحول والسيطرة",
    "Mean Node": "الاتجاه الجديد والتجارب المتطورة",
    "ASC": "الصورة الشخصية والبدايات",
    "MC": "المهنة والسمعة والهدف العام",
    "Vertex": "اللقاءات والانعطافات",
}

def clean_analysis_aspects(aspects: list, source_label: str) -> list:
    """يزيل الإشارات الحسابية البنيوية والضوضاء من قسم التفسير فقط."""
    cleaned = []
    for a in aspects:
        moving = str(a.get("moving_factor", ""))
        natal = str(a.get("natal_factor", ""))
        aspect = str(a.get("aspect", ""))

        # لا نستخدم رؤوس البيوت أو ARMC كتفسير حدث مستقل.
        if moving.startswith("House ") or natal.startswith("House "):
            continue
        if moving == "ARMC" or natal == "ARMC":
            continue
        if moving not in ANALYSIS_FACTORS or natal not in ANALYSIS_FACTORS:
            continue

        # الشمس في العودة الشمسية تعود حتمًا إلى موضع الشمس الميلادية؛
        # هذه خاصية تعريفية وليست أقوى حدث في السنة.
        if (
            source_label == "العودة الشمسية"
            and moving == "Sun"
            and natal == "Sun"
            and aspect == "Conjunction"
        ):
            continue

        cleaned.append(a)
    return cleaned

def specific_interpretation(moving: str, natal: str, aspect: str) -> str:
    moving_theme = PAIR_MEANINGS.get(moving, factor_theme(moving))
    natal_theme = PAIR_MEANINGS.get(natal, factor_theme(natal))

    if aspect in ("Trine", "Sextile"):
        bridge = (
            f"توجد قابلية للتعاون بين {moving_theme} وبين {natal_theme}. "
            "الاستفادة تكون أفضل مع مبادرة عملية بدل انتظار النتيجة تلقائيًا."
        )
    elif aspect in ("Square", "Opposition"):
        bridge = (
            f"يظهر احتكاك بين {moving_theme} وبين {natal_theme}. "
            "المطلوب تنظيم الأولويات وتجنب ردود الفعل المتسرعة أو القرارات القصوى."
        )
    else:
        bridge = (
            f"يتركز الانتباه بقوة على العلاقة بين {moving_theme} وبين {natal_theme}. "
            "قد يصبح هذا الموضوع أكثر وضوحًا ويحتاج إلى قرار أو توجيه واعٍ."
        )

    special = {
        frozenset(("Sun","Jupiter")): "ترتفع الرغبة في التوسع والظهور، مع ضرورة عدم المبالغة في الوعود.",
        frozenset(("Sun","Saturn")): "تزداد الجدية واختبارات المسؤولية، وقد يكون النجاح أبطأ لكنه أكثر ثباتًا.",
        frozenset(("Sun","Uranus")): "يميل المسار إلى التغيير والتحرر من نمط قديم أو مفاجأة تخص الاتجاه الشخصي.",
        frozenset(("Sun","Neptune")): "يزداد الإلهام، لكن يلزم التحقق من الحقائق قبل بناء توقعات كبيرة.",
        frozenset(("Sun","Pluto")): "تظهر رغبة قوية في استعادة السيطرة أو إعادة تعريف الدور والهدف.",
        frozenset(("Moon","Saturn")): "قد يظهر تحفظ عاطفي أو شعور بالواجب؛ الروتين والحدود الواضحة يساعدان.",
        frozenset(("Moon","Uranus")): "المزاج أو الظروف المنزلية قد تتبدل بسرعة؛ المرونة أهم من المقاومة.",
        frozenset(("Moon","Neptune")): "الحساسية والخيال مرتفعان، ولذلك يجب الفصل بين الحدس والانطباع المؤقت.",
        frozenset(("Mercury","Mars")): "سرعة التفكير والرد عالية؛ ممتاز للحسم، لكن النقاش قد يتحول إلى صدام.",
        frozenset(("Mercury","Saturn")): "التفكير يصبح أكثر تدقيقًا وجدية، وقد تتأخر القرارات حتى تكتمل المعلومات.",
        frozenset(("Mercury","Uranus")): "أفكار غير معتادة وأخبار مفاجئة؛ مناسب للابتكار مع مراجعة التفاصيل.",
        frozenset(("Venus","Jupiter")): "مناخ اجتماعي ومالي أكثر انفتاحًا، مع ضرورة ضبط الإسراف أو التوقعات.",
        frozenset(("Venus","Saturn")): "العلاقات والقيم تخضع لاختبار الجدية والاستمرار والحدود.",
        frozenset(("Venus","Uranus")): "تغيير مفاجئ في الذوق أو العلاقة أو المصروف، والحاجة إلى مساحة أكبر.",
        frozenset(("Venus","Pluto")): "تزداد شدة الانجذاب أو قضايا المال والقوة؛ الوضوح يمنع التلاعب.",
        frozenset(("Mars","Jupiter")): "طاقة كبيرة للمبادرة والمنافسة، لكن الاندفاع قد يرفع المخاطرة.",
        frozenset(("Mars","Saturn")): "شد بين الرغبة في الحركة والقيود؛ الخطة المرحلية أفضل من القوة المباشرة.",
        frozenset(("Mars","Uranus")): "اندفاع وتغيير مفاجئ؛ تجنب القرارات الحادة والعمل بلا خطة.",
        frozenset(("Jupiter","Saturn")): "توازن مطلوب بين التوسع والحذر؛ النجاح يأتي من نمو محسوب.",
        frozenset(("Saturn","Uranus")): "صراع بين الاستقرار والتغيير؛ الحل في تحديث البنية دون هدمها بالكامل.",
        frozenset(("Saturn","Neptune")): "اختبار للواقعية: تحويل الرؤية إلى خطوات قابلة للقياس أو كشف الوهم.",
        frozenset(("Uranus","Pluto")): "إعادة هيكلة عميقة ومفاجئة، وغالبًا لا تنجح الحلول السطحية.",
    }
    return bridge + " " + special.get(frozenset((moving, natal)), "")

INTERPRETATION_TEMPLATES = {
    "Conjunction":"تركيز قوي يدمج موضوعَي العاملين ويجعل الأثر واضحًا ومباشرًا.",
    "Trine":"تدفق سهل يساعد على الاستفادة من الإمكانات دون مقاومة كبيرة.",
    "Sextile":"فرصة قابلة للاستثمار، لكنها تحتاج مبادرة واعية حتى تظهر فائدتها.",
    "Square":"احتكاك يفرض تعديلًا أو قرارًا ويكشف نقطة تحتاج إلى إدارة أفضل.",
    "Opposition":"شدّ بين طرفين أو حاجتين مختلفتين، والحل في التوازن لا في التطرف.",
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


def polar(cx: float, cy: float, radius: float, longitude: float):
    """تحويل الطول الفلكي إلى إحداثيات SVG مع وضع الحمل عند اليسار."""
    angle = math.radians(180 - (longitude % 360))
    return cx + radius * math.cos(angle), cy - radius * math.sin(angle)


def distribute_positions(items: list, base_ring: float, close_deg: float = 6.0):
    """يوزع الأجسام المتقاربة على حلقات مختلفة لتقليل التداخل."""
    result = []
    rings = [base_ring, base_ring - 22, base_ring + 22, base_ring - 42, base_ring + 42]
    for name, data in items:
        lon = float(data["longitude"])
        used = set()
        for prev in result:
            diff = abs((lon - prev["lon"] + 180) % 360 - 180)
            if diff < close_deg:
                used.add(prev["ring"])
        ring = next((r for r in rings if r not in used), rings[-1])
        result.append({"name": name, "data": data, "lon": lon, "ring": ring})
    return result

def aspect_css(aspect_name: str) -> str:
    return {
        "Trine": "aspect-line good",
        "Sextile": "aspect-line good",
        "Square": "aspect-line hard",
        "Opposition": "aspect-line hard",
        "Conjunction": "aspect-line conj",
    }.get(aspect_name, "aspect-line")

def chart_wheel(
    planets: dict,
    houses: dict,
    angles: dict,
    title: str,
    overlay: dict = None,
    aspects: list = None,
    center_lines: list = None,
) -> str:
    size = 640
    cx = cy = size / 2
    outer = 292
    zodiac_r = 256
    house_r = 214
    planet_r = 176
    aspect_r = 84
    inner = 92

    svg = [
        f"<div class='wheel-card'><h3>{html.escape(title)}</h3>",
        f"<svg class='astro-wheel' viewBox='0 0 {size} {size}' width='1280' height='1280' role='img' aria-label='{html.escape(title)}'>",
        f"<circle cx='{cx}' cy='{cy}' r='{outer}' class='wheel-bg'/>",
        f"<circle cx='{cx}' cy='{cy}' r='{zodiac_r}' class='wheel-ring'/>",
        f"<circle cx='{cx}' cy='{cy}' r='{house_r}' class='wheel-ring'/>",
        f"<circle cx='{cx}' cy='{cy}' r='{inner}' class='wheel-ring inner'/>",
    ]

    # Zodiac sectors and labels
    for i in range(12):
        lon = i * 30
        x1, y1 = polar(cx, cy, outer, lon)
        x2, y2 = polar(cx, cy, zodiac_r, lon)
        svg.append(
            f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' class='zodiac-line'/>"
        )
        lx, ly = polar(cx, cy, 274, lon + 15)
        svg.append(
            f"<text x='{lx:.2f}' y='{ly:.2f}' class='zodiac-label'>{SIGN_SYMBOLS[i]}</text>"
        )

    # House cusps
    for i in range(1, 13):
        lon = float(houses[f"House {i}"])
        x1, y1 = polar(cx, cy, zodiac_r, lon)
        x2, y2 = polar(cx, cy, inner, lon)
        css = "house-line major" if i in (1, 4, 7, 10) else "house-line"
        svg.append(
            f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' class='{css}'/>"
        )
        lx, ly = polar(cx, cy, 198, lon + 7)
        svg.append(
            f"<text x='{lx:.2f}' y='{ly:.2f}' class='house-number'>{i}</text>"
        )

    # ASC / MC labels
    for key in ("ASC", "MC"):
        if key in angles:
            lon = float(angles[key])
            lx, ly = polar(cx, cy, 228, lon)
            svg.append(
                f"<text x='{lx:.2f}' y='{ly:.2f}' class='angle-label'>{key}</text>"
            )

    # Aspect lines between known factors
    positions = {name: float(data["longitude"]) for name, data in planets.items()}
    if overlay:
        positions.update(
            {f"overlay:{name}": float(data["longitude"]) for name, data in overlay.items()}
        )

    if aspects:
        for index, a in enumerate(aspects[:70]):
            moving = str(a.get("moving_factor", ""))
            natal = str(a.get("natal_factor", ""))
            aspect_name = str(a.get("aspect", ""))
            orb = float(a.get("orb", 0.0))

            moving_key = f"overlay:{moving}" if overlay and f"overlay:{moving}" in positions else moving
            natal_key = natal
            if moving_key not in positions or natal_key not in positions:
                continue

            x1, y1 = polar(cx, cy, aspect_r, positions[moving_key])
            x2, y2 = polar(cx, cy, aspect_r, positions[natal_key])
            css = aspect_css(aspect_name)

            svg.append(
                f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' class='{css}'/>"
            )

            # Show orb only for the tightest lines to avoid clutter.
            if index < 12 and orb <= 1.25:
                mx = (x1 + x2) / 2
                my = (y1 + y2) / 2
                svg.append(
                    f"<rect x='{mx-15:.2f}' y='{my-8:.2f}' width='30' height='16' rx='7' class='orb-bg'/>"
                )
                svg.append(
                    f"<text x='{mx:.2f}' y='{my+1:.2f}' class='orb-label'>{orb:.1f}°</text>"
                )

    # Strong ASC and MC arrows
    for key, css in (("ASC", "axis-arrow asc-arrow"), ("MC", "axis-arrow mc-arrow")):
        if key in angles:
            lon = float(angles[key])
            ax1, ay1 = polar(cx, cy, outer + 1, lon)
            ax2, ay2 = polar(cx, cy, inner - 5, lon)
            svg.append(
                f"<line x1='{ax1:.2f}' y1='{ay1:.2f}' x2='{ax2:.2f}' y2='{ay2:.2f}' class='{css}'/>"
            )

    # Natal or single-wheel planets
    for item in distribute_positions(list(planets.items()), planet_r):
        name = item["name"]
        data = item["data"]
        lon = item["lon"]
        ring = item["ring"]
        px, py = polar(cx, cy, ring, lon)
        label = SYMBOLS.get(name, name[:2])
        retro = " ℞" if data.get("retrograde") else ""
        tooltip = (
            f"{AR_PLANETS.get(name, name)} — "
            f"{zodiac_position(lon)} — "
            f"{'متراجع' if data.get('retrograde') else 'مباشر'}"
        )
        svg.append(
            f"<g class='planet-group'><title>{html.escape(tooltip)}</title>"
            f"<circle cx='{px:.2f}' cy='{py:.2f}' r='15' class='planet-dot'/>"
            f"<text x='{px:.2f}' y='{py:.2f}' class='planet-label'>{html.escape(label + retro)}</text></g>"
        )

    # Optional overlay ring
    if overlay:
        for item in distribute_positions(list(overlay.items()), 112, close_deg=5.0):
            name = item["name"]
            data = item["data"]
            lon = item["lon"]
            ring = item["ring"]
            px, py = polar(cx, cy, ring, lon)
            label = SYMBOLS.get(name, name[:2])
            retro = " ℞" if data.get("retrograde") else ""
            tooltip = (
                f"{AR_PLANETS.get(name, name)} — "
                f"{zodiac_position(lon)} — "
                f"{'متراجع' if data.get('retrograde') else 'مباشر'}"
            )
            svg.append(
                f"<g class='planet-group'><title>{html.escape(tooltip)}</title>"
                f"<circle cx='{px:.2f}' cy='{py:.2f}' r='13' class='overlay-dot'/>"
                f"<text x='{px:.2f}' y='{py:.2f}' class='overlay-label'>{html.escape(label + retro)}</text></g>"
            )

    # Center details
    center_lines = center_lines or []
    start_y = cy - ((len(center_lines) - 1) * 10)
    for idx, line in enumerate(center_lines[:4]):
        y = start_y + idx * 20
        css = "center-title" if idx == 0 else "center-text"
        svg.append(
            f"<text x='{cx}' y='{y}' class='{css}'>{html.escape(str(line))}</text>"
        )

    svg.append("</svg>")
    if overlay:
        svg.append(
            "<div class='wheel-legend'>"
            "<span><i class='legend-natal'></i> الميلاد</span>"
            "<span><i class='legend-overlay'></i> الخريطة المقارنة</span>"
            "<span><i class='legend-good'></i> زاوية منسجمة</span>"
            "<span><i class='legend-hard'></i> زاوية ضاغطة</span>"
            "</div>"
        )
    else:
        svg.append(
            "<div class='wheel-legend'>"
            "<span><i class='legend-good'></i> تثليث/تسديس</span>"
            "<span><i class='legend-hard'></i> تربيع/مقابلة</span>"
            "<span><i class='legend-conj'></i> اقتران</span>"
            "</div>"
        )
    svg.append("</div>")
    return "".join(svg)

def table_wrap(head: str, body: str) -> str:
    return f"<div class='table-wrap'><table><thead>{head}</thead><tbody>{body}</tbody></table></div>"

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

def strength_score(aspect: dict) -> int:
    asp = str(aspect["aspect"])
    base = ASPECT_TONE.get(asp, ("", 65))[1]
    orb = float(aspect.get("orb", 2.0))
    score = round(base + max(0.0, 2.0 - orb) * 9)
    return max(45, min(99, score))

def factor_theme(name: str) -> str:
    if name.startswith("House "):
        try:
            number = int(name.split()[-1])
            return HOUSE_MEANINGS.get(number, "موضوع حياتي")
        except Exception:
            return "موضوع حياتي"
    return FACTOR_THEMES.get(name, AR_PLANETS.get(name, name))

def interpret_aspect(aspect: dict, source_label: str) -> dict:
    moving = str(aspect["moving_factor"])
    natal = str(aspect["natal_factor"])
    asp = str(aspect["aspect"])
    score = strength_score(aspect)
    title = (
        f"{AR_PLANETS.get(moving,moving)} "
        f"{ASPECT_AR.get(asp,asp)} "
        f"{AR_PLANETS.get(natal,natal)}"
    )
    text = (
        f"{specific_interpretation(moving, natal, asp)} "
        f"هذه قراءة رمزية من {source_label} وليست وعدًا بحدث محدد."
    )
    return {
        "title": title,
        "text": text,
        "score": score,
        "class": ASPECT_CLASS.get(asp,""),
        "orb": float(aspect.get("orb",0)),
    }

def analysis_cards(aspects: list, source_label: str, limit: int = 8) -> str:
    aspects = clean_analysis_aspects(aspects, source_label)
    if not aspects:
        return "<p class='muted'>لا توجد إشارات تفسيرية قوية ضمن الأورب المحدد.</p>"

    ranked = sorted(aspects, key=lambda a: (-strength_score(a), float(a.get("orb",9))))[:limit]
    cards = []
    for a in ranked:
        item = interpret_aspect(a, source_label)
        cards.append(
            f"<article class='analysis-card {item['class']}'>"
            f"<div class='analysis-head'><h4>{html.escape(item['title'])}</h4>"
            f"<span class='score'>{item['score']}/100</span></div>"
            f"<p>{html.escape(item['text'])}</p>"
            f"<small>الأورب: {item['orb']:.2f}°</small>"
            f"</article>"
        )
    return "<div class='analysis-grid'>" + "".join(cards) + "</div>"

def overview_panel(result: dict) -> str:
    buckets = {
        "العبور": clean_analysis_aspects(result["transits"]["aspects_to_natal"], "العبور"),
        "العودة الشمسية": clean_analysis_aspects(result["solar_return"]["aspects_to_natal"], "العودة الشمسية"),
        "التقدمات": clean_analysis_aspects(result["secondary_progressions"]["aspects_to_natal"], "التقدمات الثانوية"),
    }

    all_aspects = []
    source_counts = Counter()
    hard = 0
    supportive = 0

    for source, aspects in buckets.items():
        source_counts[source] = len(aspects)
        for a in aspects:
            all_aspects.append((source, a))
            if a["aspect"] in ("Square","Opposition"):
                hard += 1
            elif a["aspect"] in ("Trine","Sextile"):
                supportive += 1

    top = sorted(all_aspects, key=lambda x: (-strength_score(x[1]), float(x[1].get("orb",9))))[:5]

    if supportive > hard:
        climate = "المناخ العام يميل إلى وجود فرص مساندة أكثر من نقاط الاحتكاك."
        climate_class = "climate-good"
    elif hard > supportive:
        climate = "المناخ العام يميل إلى الضغط وإعادة الترتيب، مع حاجة للهدوء والمرونة."
        climate_class = "climate-hard"
    else:
        climate = "المناخ العام متوازن بين فرص الدعم ونقاط التحدي."
        climate_class = "climate-neutral"

    rows = []
    for source, a in top:
        title = f"{AR_PLANETS.get(a['moving_factor'],a['moving_factor'])} {ASPECT_AR.get(a['aspect'],a['aspect'])} {AR_PLANETS.get(a['natal_factor'],a['natal_factor'])}"
        rows.append(
            f"<tr><td>{html.escape(source)}</td><td>{html.escape(title)}</td>"
            f"<td>{strength_score(a)}/100</td><td>{float(a['orb']):.2f}°</td></tr>"
        )

    return f"""
    <section class="result-card overview">
      <h2>القراءة المركزة</h2>
      <div class="climate {climate_class}">{html.escape(climate)}</div>
      <div class="stats">
        <div><span>إشارات مساندة</span><strong>{supportive}</strong></div>
        <div><span>إشارات ضاغطة</span><strong>{hard}</strong></div>
        <div><span>إجمالي الزوايا</span><strong>{len(all_aspects)}</strong></div>
      </div>
      <h3>أقوى خمس إشارات</h3>
      {table_wrap("<tr><th>المصدر</th><th>الإشارة</th><th>القوة</th><th>الأورب</th></tr>", "".join(rows))}
      <p class="muted">درجة القوة ترتيب داخلي يعتمد على نوع الزاوية وضيق الأورب، وليست نسبة تحقق لحدث.</p>
    </section>
    """

def section(title: str, body: str, badge: str = "") -> str:
    b = f"<span class='badge'>{badge}</span>" if badge else ""
    return f"<section class='result-card'><h2>{title}{b}</h2>{body}</section>"


def wheel_aspects(planets_a: dict, planets_b: dict = None, max_orb: float = 2.0) -> list:
    planets_b = planets_b or planets_a
    definitions = [
        ("Conjunction", 0),
        ("Sextile", 60),
        ("Square", 90),
        ("Trine", 120),
        ("Opposition", 180),
    ]
    rows = []
    same = planets_a is planets_b

    items_a = list(planets_a.items())
    items_b = list(planets_b.items())

    for i, (name_a, data_a) in enumerate(items_a):
        for j, (name_b, data_b) in enumerate(items_b):
            if same and j <= i:
                continue
            diff = abs((float(data_a["longitude"]) - float(data_b["longitude"]) + 180) % 360 - 180)
            for aspect_name, exact in definitions:
                orb = abs(diff - exact)
                if orb <= max_orb:
                    rows.append({
                        "moving_factor": name_a,
                        "natal_factor": name_b,
                        "aspect": aspect_name,
                        "orb": orb,
                    })
                    break
    return sorted(rows, key=lambda x: x["orb"])

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

    blocks = [summary, overview_panel(result)]

    natal = result["natal"]
    transits = result["transits"]
    sr = result["solar_return"]
    prog = result["secondary_progressions"]

    natal_wheel_aspects = wheel_aspects(natal["planets"], max_orb=2.0)
    sr_wheel_aspects = wheel_aspects(sr["planets"], max_orb=2.0)
    prog_wheel_aspects = wheel_aspects(prog["planets"], max_orb=2.0)

    center_natal = [
        meta.get("name", ""),
        meta["birth_utc"][:10],
        meta["birth_utc"][11:19],
        meta["house_system"].split(" ")[0],
    ]
    center_event = [
        meta.get("name", ""),
        meta["event_utc"][:10],
        meta["event_utc"][11:19],
        "Transit × Natal",
    ]
    center_sr = [
        meta.get("name", ""),
        meta["solar_return_utc"][:10],
        meta["solar_return_utc"][11:19],
        "Solar Return",
    ]
    center_prog = [
        meta.get("name", ""),
        meta["progressed_utc"][:10],
        meta["progressed_utc"][11:19],
        "Progressions",
    ]

    blocks.append(section(
        "عجلات الخرائط",
        "<div class='wheel-grid'>" +
        chart_wheel(
            natal["planets"], natal["houses"], natal["angles"],
            "الخريطة الميلادية",
            aspects=natal_wheel_aspects,
            center_lines=center_natal,
        ) +
        chart_wheel(
            natal["planets"], natal["houses"], natal["angles"],
            "العبور فوق الميلاد",
            overlay=transits["planets"],
            aspects=transits["aspects_to_natal"],
            center_lines=center_event,
        ) +
        chart_wheel(
            sr["planets"], sr["houses"], sr["angles"],
            "العودة الشمسية",
            aspects=sr_wheel_aspects,
            center_lines=center_sr,
        ) +
        chart_wheel(
            prog["planets"], prog["houses"], prog["angles"],
            "التقدمات الثانوية",
            aspects=prog_wheel_aspects,
            center_lines=center_prog,
        ) +
        "</div>",
        "Chart Wheels"
    ))
    blocks.append(section(
        "الخريطة الميلادية",
        "<div class='tabs-note'>الأساس الذي تُقارن به بقية الخرائط</div>"
        "<h3>الكواكب</h3>" + planet_table(natal["planets"]) +
        "<h3>الزوايا الأساسية</h3>" + angle_table(natal["angles"]) +
        "<h3>البيوت الاثنا عشر</h3>" + houses_table(natal["houses"]),
        "Natal"
    ))

    blocks.append(section(
        "العبور الحالي",
        "<h3>التحليل المختصر</h3>" +
        analysis_cards(transits["aspects_to_natal"], "العبور") +
        "<h3>الكواكب العابرة</h3>" + planet_table(transits["planets"]) +
        "<h3>الجوانب إلى الخريطة الميلادية</h3>" + aspect_table(transits["aspects_to_natal"]),
        "Transits"
    ))

    blocks.append(section(
        "العودة الشمسية",
        "<h3>التحليل المختصر</h3>" +
        analysis_cards(sr["aspects_to_natal"], "العودة الشمسية") +
        "<h3>كواكب العودة</h3>" + planet_table(sr["planets"]) +
        "<h3>زوايا وبيوت العودة</h3>" + angle_table(sr["angles"]) +
        houses_table(sr["houses"]) +
        "<h3>زوايا العودة إلى الميلاد</h3>" + aspect_table(sr["aspects_to_natal"]),
        "Solar Return"
    ))

    blocks.append(section(
        "التقدمات الثانوية",
        "<h3>التحليل المختصر</h3>" +
        analysis_cards(prog["aspects_to_natal"], "التقدمات الثانوية") +
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
h4{font-size:16px;margin:0}
.badge{font-size:12px;padding:5px 9px;border-radius:999px;background:#28213f;color:#c9bdff;font-weight:normal}
.tabs-note{color:var(--muted);font-size:13px;margin-top:-6px}
label{display:block;margin:11px 0 6px;color:#d2d8e2}
input{width:100%;padding:13px;border-radius:11px;border:1px solid #3a4453;background:var(--panel2);color:white;font-size:16px}
button{width:100%;padding:15px;border:0;border-radius:12px;background:var(--accent);color:white;font-size:18px;font-weight:bold;margin-top:16px}
button:hover{background:var(--accent2)}
.module-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.module-link{display:block;text-decoration:none;text-align:center;padding:14px;border-radius:12px;background:#28213f;color:#d9d0ff;font-weight:bold}
.module-link:hover{background:#352a58}
.module-link.disabled{opacity:.55;pointer-events:none}
.compare-link{display:block;text-align:center;text-decoration:none;padding:15px;border-radius:12px;background:#28213f;color:#d9d0ff;font-size:17px;font-weight:bold}
.compare-link:hover{background:#352a58}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.summary-grid,.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.summary-grid{grid-template-columns:repeat(2,1fr)}
.summary-grid div,.stats div{background:var(--panel2);padding:12px;border-radius:12px}
.summary-grid span,.stats span{display:block;color:var(--muted);font-size:13px;margin-bottom:6px}
.summary-grid strong,.stats strong{font-size:18px;word-break:break-word}
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
.analysis-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.analysis-card{background:var(--panel2);border:1px solid var(--border);border-right:4px solid #6d7480;border-radius:14px;padding:14px}
.analysis-card.asp-good{border-right-color:#2fa878}
.analysis-card.asp-hard{border-right-color:#d65f70}
.analysis-card.asp-conj{border-right-color:#8b73e6}
.analysis-head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.analysis-card p{color:#d5d9e0;line-height:1.7;font-size:14px}
.analysis-card small{color:var(--muted)}
.score{font-size:12px;background:#242a35;padding:5px 8px;border-radius:999px;white-space:nowrap}
.climate{padding:13px;border-radius:12px;margin-bottom:12px;font-weight:bold}
.climate-good{background:#15362d;color:#92e7c2}
.climate-hard{background:#442329;color:#ffadb6}
.climate-neutral{background:#2d3040;color:#d6d8ff}
.muted{color:var(--muted);font-size:13px}
pre{white-space:pre-wrap;word-break:break-word;background:#090c10;padding:14px;border-radius:12px;direction:ltr;text-align:left;overflow:auto}
details summary{cursor:pointer;font-weight:bold}
.error{border-color:#a94a4a}

.wheel-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.wheel-card{background:var(--panel2);border:1px solid var(--border);border-radius:16px;padding:12px}
.wheel-card h3{margin:2px 0 10px;text-align:center}
.astro-wheel{width:100%;height:auto;display:block}
.wheel-bg{fill:#0b0f14;stroke:#343d4a;stroke-width:2}
.wheel-ring{fill:none;stroke:#4a5565;stroke-width:1.5}
.wheel-ring.inner{stroke:#323b47}
.zodiac-line{stroke:#596474;stroke-width:1}
.house-line{stroke:#394351;stroke-width:1}
.house-line.major{stroke:#8d7dff;stroke-width:2}
.zodiac-label{fill:#cfc5ff;font-size:22px;text-anchor:middle;dominant-baseline:middle}
.house-number{fill:#9ba7b8;font-size:12px;text-anchor:middle;dominant-baseline:middle}
.angle-label{fill:#ffd479;font-size:12px;font-weight:bold;text-anchor:middle;dominant-baseline:middle}
.planet-dot{fill:#2b2550;stroke:#8f7cff;stroke-width:1.5}
.planet-label{fill:white;font-size:17px;text-anchor:middle;dominant-baseline:middle}
.overlay-dot{fill:#173f33;stroke:#56d1a0;stroke-width:1.5}
.overlay-label{fill:#b8ffe2;font-size:15px;text-anchor:middle;dominant-baseline:middle}
.planet-group{cursor:help}
.planet-group:hover .planet-dot,.planet-group:hover .overlay-dot{filter:drop-shadow(0 0 5px rgba(255,255,255,.65))}
.axis-arrow{stroke-width:2.8;opacity:.92}
.asc-arrow{stroke:#ffd479}
.mc-arrow{stroke:#ff9f6e}
.orb-bg{fill:#11161d;stroke:#596474;stroke-width:.7;opacity:.94}
.orb-label{fill:#dce4f0;font-size:8px;text-anchor:middle;dominant-baseline:middle}
.aspect-line{stroke-width:1.6;opacity:.62}
.aspect-line.good{stroke:#5cc8ff}
.aspect-line.hard{stroke:#ff6478}
.aspect-line.conj{stroke:#b696ff;stroke-width:2.2}
.center-title{fill:#ffffff;font-size:16px;font-weight:bold;text-anchor:middle}
.center-text{fill:#aeb8c6;font-size:11px;text-anchor:middle}
.wheel-legend{display:flex;gap:14px;justify-content:center;color:var(--muted);font-size:12px;margin-top:8px}
.wheel-legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-left:5px}
.legend-natal{background:#8f7cff}
.legend-overlay{background:#56d1a0}
.legend-good{background:#5cc8ff}
.legend-hard{background:#ff6478}
.legend-conj{background:#b696ff}
@media(max-width:700px){
  .grid,.summary-grid,.stats,.analysis-grid,.wheel-grid,.module-grid{grid-template-columns:1fr}
  .hero h1{font-size:27px}
  .wrap{padding:12px}
}

@media print{
  body{background:white;color:black}
  .wheel-card{break-inside:avoid;background:white;border-color:#bbb}
  .wheel-bg{fill:white}
  .wheel-ring,.zodiac-line,.house-line{stroke:#555}
  .planet-label,.center-title{fill:black}
  .center-text,.house-number{fill:#333}
}

</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h1>Astro Assistant</h1>
    <p>Natal • Transits • Solar Return • Secondary Progressions • Primary Directions</p>
  </div>


  <div class="card">
    <h2>وضع المقارنة</h2>
    <p class="muted">قارن بين طرفين في نفس وقت ومكان المباراة.</p>
    <a class="compare-link" href="/match">⚔️ فتح مقارنة مباراة</a>
  </div>


  <div class="card">
    <h2>لوحة الأدوات</h2>
    <div class="module-grid">
      <a class="module-link" href="/forecast">📆 التوقع اليومي والأسبوعي</a>
      <a class="module-link" href="/electional">🎯 اختيار أفضل موعد</a>
      <a class="module-link" href="/match">⚔️ مقارنة مباراة</a>
      <a class="module-link disabled" href="#">🧭 التوجيهات الكاملة — قيد التطوير</a>
    </div>
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
    تنبيه: التحليلات رمزية وتعليمية وليست تنبؤًا علميًا أو ضمانًا لوقوع أحداث.
  </p>
</div>
</body>
</html>
"""



def _factor_weight(name: str) -> float:
    if name in ("ASC", "MC", "ARMC"):
        return 1.45
    if name.startswith("House "):
        return 1.30
    if name in ("Sun", "Moon", "Mars", "Jupiter", "Saturn"):
        return 1.12
    if name in ("Mercury", "Venus"):
        return 1.03
    return 0.94

def _aspect_polarity(aspect: str) -> float:
    return {
        "Trine": 1.0,
        "Sextile": 0.72,
        "Conjunction": 0.20,
        "Square": -0.90,
        "Opposition": -1.0,
    }.get(aspect, 0.0)

def _orb_precision(orb: float) -> float:
    orb = max(0.0, float(orb))
    if orb <= 0.25:
        return 1.35
    if orb <= 0.50:
        return 1.22
    if orb <= 1.00:
        return 1.08
    if orb <= 1.50:
        return 0.94
    return 0.80

def _source_weight(source_name: str) -> float:
    return {
        "العبور": 1.35,
        "العودة الشمسية": 1.15,
        "التقدمات": 1.20,
    }.get(source_name, 1.0)

def _theme_key(a: dict) -> str:
    moving = str(a.get("moving_factor", ""))
    natal = str(a.get("natal_factor", ""))
    aspect = str(a.get("aspect", ""))
    pair = "|".join(sorted((moving, natal)))
    tone = (
        "support" if aspect in ("Trine", "Sextile")
        else "hard" if aspect in ("Square", "Opposition")
        else "conj"
    )
    return f"{pair}|{tone}"

def comparison_metrics(result: dict) -> dict:
    source_sets = [
        ("العبور", clean_analysis_aspects(result["transits"]["aspects_to_natal"], "العبور")),
        ("العودة الشمسية", clean_analysis_aspects(result["solar_return"]["aspects_to_natal"], "العودة الشمسية")),
        ("التقدمات", clean_analysis_aspects(result["secondary_progressions"]["aspects_to_natal"], "التقدمات الثانوية")),
    ]

    all_items = []
    repetition_map = {}

    for source_name, aspects in source_sets:
        for a in aspects:
            item = dict(a)
            item["_source"] = source_name
            item["_theme"] = _theme_key(item)
            repetition_map.setdefault(item["_theme"], set()).add(source_name)
            all_items.append(item)

    supportive_count = hard_count = conjunction_count = 0
    positive_points = negative_points = 0.0
    angular_points = repeated_points = 0.0
    scored = []

    for item in all_items:
        asp = str(item.get("aspect", ""))
        moving = str(item.get("moving_factor", ""))
        natal = str(item.get("natal_factor", ""))
        orb = float(item.get("orb", 2.0))

        polarity = _aspect_polarity(asp)
        source_w = _source_weight(item["_source"])
        factor_w = max(_factor_weight(moving), _factor_weight(natal))
        precision_w = _orb_precision(orb)
        base_strength = strength_score(item) / 100.0

        repetitions = len(repetition_map.get(item["_theme"], set()))
        repeat_w = 1.0 + max(0, repetitions - 1) * 0.22

        raw = 10.0 * base_strength * source_w * factor_w * precision_w * repeat_w
        signed = raw * polarity

        item["_weighted"] = round(signed, 3)
        item["_absolute_weight"] = round(abs(raw), 3)
        item["_repetitions"] = repetitions
        scored.append(item)

        if asp in ("Trine", "Sextile"):
            supportive_count += 1
        elif asp in ("Square", "Opposition"):
            hard_count += 1
        elif asp == "Conjunction":
            conjunction_count += 1

        if signed >= 0:
            positive_points += signed
        else:
            negative_points += abs(signed)

        angular = (
            moving in ("ASC", "MC", "ARMC")
            or natal in ("ASC", "MC", "ARMC")
            or moving.startswith("House ")
            or natal.startswith("House ")
        )
        if angular:
            angular_points += signed
        if repetitions >= 2:
            repeated_points += signed

    net = positive_points - negative_points
    scale = max(24.0, math.sqrt(max(1, len(scored))) * 9.0)
    index = 50.0 + 38.0 * math.tanh(net / scale / 10.0)
    index = max(10.0, min(90.0, index))

    repeat_themes = sum(1 for s in repetition_map.values() if len(s) >= 2)
    tight_count = sum(1 for a in scored if float(a.get("orb", 9)) <= 0.50)
    angular_count = sum(
        1 for a in scored
        if str(a.get("moving_factor", "")) in ("ASC", "MC", "ARMC")
        or str(a.get("natal_factor", "")) in ("ASC", "MC", "ARMC")
        or str(a.get("moving_factor", "")).startswith("House ")
        or str(a.get("natal_factor", "")).startswith("House ")
    )

    confidence = (
        35
        + min(25, tight_count * 2.0)
        + min(20, repeat_themes * 4.0)
        + min(15, angular_count * 1.5)
    )
    confidence = round(max(25.0, min(92.0, confidence)), 1)

    ranked = sorted(
        scored,
        key=lambda a: (-a["_absolute_weight"], float(a.get("orb", 9)))
    )[:7]

    components = {
        "العبور": 0.0,
        "العودة الشمسية": 0.0,
        "التقدمات": 0.0,
        "الزوايا والبيوت": round(angular_points, 2),
        "التكرار بين التقنيات": round(repeated_points, 2),
    }
    for a in scored:
        components[a["_source"]] += a["_weighted"]
    for key in ("العبور", "العودة الشمسية", "التقدمات"):
        components[key] = round(components[key], 2)

    return {
        "index": round(index, 1),
        "confidence": confidence,
        "supportive": supportive_count,
        "hard": hard_count,
        "conjunctions": conjunction_count,
        "total": len(scored),
        "positive_points": round(positive_points, 2),
        "negative_points": round(negative_points, 2),
        "net_points": round(net, 2),
        "repeat_themes": repeat_themes,
        "tight_count": tight_count,
        "angular_count": angular_count,
        "components": components,
        "top": ranked,
    }

def comparison_top_table(metrics: dict) -> str:
    rows = []
    for a in metrics["top"]:
        moving = AR_PLANETS.get(str(a["moving_factor"]), str(a["moving_factor"]))
        natal = AR_PLANETS.get(str(a["natal_factor"]), str(a["natal_factor"]))
        aspect = ASPECT_AR.get(str(a["aspect"]), str(a["aspect"]))
        title = f"{moving} {aspect} {natal}"
        repetition = f"×{a['_repetitions']}" if a.get("_repetitions", 1) > 1 else "—"
        signed = float(a.get("_weighted", 0))
        rows.append(
            f"<tr><td>{html.escape(a['_source'])}</td>"
            f"<td>{html.escape(title)}</td>"
            f"<td>{strength_score(a)}/100</td>"
            f"<td>{float(a['orb']):.2f}°</td>"
            f"<td>{repetition}</td>"
            f"<td>{signed:+.2f}</td></tr>"
        )
    return table_wrap(
        "<tr><th>المصدر</th><th>الإشارة</th><th>القوة</th><th>الأورب</th><th>التكرار</th><th>النقاط</th></tr>",
        "".join(rows),
    )

def comparison_components_table(m1: dict, m2: dict, team1: str, team2: str) -> str:
    labels = ["العبور", "العودة الشمسية", "التقدمات", "الزوايا والبيوت", "التكرار بين التقنيات"]
    rows = []
    for label in labels:
        v1 = float(m1["components"].get(label, 0))
        v2 = float(m2["components"].get(label, 0))
        better = team1 if v1 > v2 else team2 if v2 > v1 else "متعادل"
        rows.append(
            f"<tr><td>{html.escape(label)}</td>"
            f"<td>{v1:+.2f}</td><td>{v2:+.2f}</td>"
            f"<td>{html.escape(better)}</td></tr>"
        )
    return table_wrap(
        f"<tr><th>الطبقة</th><th>{html.escape(team1)}</th><th>{html.escape(team2)}</th><th>الأفضل</th></tr>",
        "".join(rows),
    )

def comparison_summary(team1: str, m1: dict, team2: str, m2: dict) -> str:
    total = m1["index"] + m2["index"]
    share1 = round(m1["index"] / total * 100, 1) if total else 50.0
    share2 = round(100 - share1, 1)
    diff = abs(m1["index"] - m2["index"])
    combined_confidence = round((m1["confidence"] + m2["confidence"]) / 2, 1)

    if diff < 2.0:
        verdict = "المؤشرات شديدة التقارب ولا توجد أفضلية واضحة."
        strength = "ضعيفة جدًا"
    elif diff < 5.0:
        leader = team1 if m1["index"] > m2["index"] else team2
        verdict = f"أفضلية رمزية طفيفة لصالح {leader}."
        strength = "طفيفة"
    elif diff < 10.0:
        leader = team1 if m1["index"] > m2["index"] else team2
        verdict = f"أفضلية رمزية متوسطة لصالح {leader}."
        strength = "متوسطة"
    else:
        leader = team1 if m1["index"] > m2["index"] else team2
        verdict = f"أفضلية رمزية واضحة داخل النموذج لصالح {leader}."
        strength = "واضحة"

    return (
        '<section class="result-card highlight">'
        '<h2>نتيجة المقارنة المتقدمة</h2>'
        '<div class="comparison-score">'
        f'<div><span>{html.escape(team1)}</span><strong>{m1["index"]}/100</strong><small>حصة المؤشر: {share1}%</small></div>'
        '<div class="versus">VS</div>'
        f'<div><span>{html.escape(team2)}</span><strong>{m2["index"]}/100</strong><small>حصة المؤشر: {share2}%</small></div>'
        '</div>'
        f'<div class="climate climate-neutral">{html.escape(verdict)}</div>'
        '<div class="stats">'
        f'<div><span>قوة الأفضلية</span><strong>{strength}</strong></div>'
        f'<div><span>تماسك البيانات</span><strong>{combined_confidence}%</strong></div>'
        f'<div><span>فرق المؤشر</span><strong>{diff:.1f}</strong></div>'
        '<div><span>نوع النتيجة</span><strong>رمزية</strong></div>'
        '</div>'
        '<p class="muted">حصة المؤشر ودرجة التماسك ليستا احتمال فوز علميًا؛ إنهما تلخيص داخلي لطبقات المحرك.</p>'
        '</section>'
        '<section class="result-card">'
        '<h2>مقارنة طبقات التحليل</h2>'
        f'{comparison_components_table(m1, m2, team1, team2)}'
        '</section>'
    )

MATCH_PAGE = '''
<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>مقارنة مباراة</title><style>
:root{--bg:#0e1117;--panel:#171c24;--panel2:#11161d;--border:#2c3440;--text:#f4f6f8;--muted:#aeb8c6;--accent:#7c5cff;--accent2:#9b86ff}*{box-sizing:border-box}body{font-family:Arial,Tahoma,sans-serif;background:var(--bg);color:var(--text);margin:0}.wrap{max-width:1050px;margin:auto;padding:16px}.hero{text-align:center;padding:12px 0}.hero h1{font-size:30px;margin:0 0 8px}.hero p,.muted{color:var(--muted)}.card,.result-card{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:18px;margin:14px 0}h2{margin:0 0 14px;font-size:23px}h3{color:#d9ddff;margin:18px 0 10px}label{display:block;margin:11px 0 6px;color:#d2d8e2}input{width:100%;padding:13px;border-radius:11px;border:1px solid #3a4453;background:var(--panel2);color:white;font-size:16px}button{width:100%;padding:15px;border:0;border-radius:12px;background:var(--accent);color:white;font-size:18px;font-weight:bold;margin-top:16px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.teams-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.table-wrap{overflow-x:auto;border-radius:12px;border:1px solid var(--border)}table{width:100%;border-collapse:collapse;min-width:620px;background:var(--panel2)}th,td{padding:11px;border-bottom:1px solid var(--border);text-align:right;font-size:14px}th{background:#191f29;color:#dcd5ff}.highlight{border-color:#6f59db}.comparison-score{display:grid;grid-template-columns:1fr auto 1fr;gap:16px;align-items:center;margin:18px 0}.comparison-score>div:not(.versus){background:var(--panel2);border-radius:14px;padding:18px;text-align:center}.comparison-score span,.comparison-score small{display:block;color:var(--muted)}.comparison-score strong{display:block;font-size:34px;margin:8px 0}.versus{font-weight:bold;color:#9b86ff}.climate{padding:13px;border-radius:12px;margin-bottom:10px}.climate-neutral{background:#2d3040;color:#d6d8ff}.back{display:inline-block;color:#cbbfff;text-decoration:none;margin-bottom:8px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.stats div{background:var(--panel2);padding:12px;border-radius:12px}.stats span{display:block;color:var(--muted);font-size:13px}.stats strong{font-size:22px}@media(max-width:720px){.grid,.teams-grid,.comparison-score,.stats{grid-template-columns:1fr}.versus{text-align:center}}
</style></head><body><div class="wrap"><a class="back" href="/">← العودة للتحليل الفردي</a><div class="hero"><h1>⚔️ مقارنة مباراة — المحرك المتقدم</h1><p>أوزان مختلفة للعبور والعودة الشمسية والتقدمات والزوايا الدقيقة والتكرار بين التقنيات.</p></div>
<form method="post" action="/match-compare"><div class="teams-grid">
<div class="card"><h2>الطرف الأول</h2><label>اسم الفريق</label><input name="team1" value="Argentina"><label>اسم الشخص الممثل</label><input name="person1" value="Lionel Scaloni"><label>تاريخ ووقت الميلاد</label><input name="birth1" value="1978-05-16T12:00:00"><div class="grid"><div><label>UTC الميلاد</label><input name="birth_offset1" value="-3"></div><div><label>خط العرض</label><input name="birth_lat1" value="-33.01"></div><div><label>خط الطول</label><input name="birth_lon1" value="-61.04"></div></div><h3>مكان العودة الشمسية</h3><div class="grid"><div><label>خط العرض</label><input name="sr_lat1" value="-33.01"></div><div><label>خط الطول</label><input name="sr_lon1" value="-61.04"></div></div></div>
<div class="card"><h2>الطرف الثاني</h2><label>اسم الفريق</label><input name="team2" value="England"><label>اسم الشخص الممثل</label><input name="person2" value="Thomas Tuchel"><label>تاريخ ووقت الميلاد</label><input name="birth2" value="1973-08-29T12:00:00"><div class="grid"><div><label>UTC الميلاد</label><input name="birth_offset2" value="2"></div><div><label>خط العرض</label><input name="birth_lat2" value="48.25"></div><div><label>خط الطول</label><input name="birth_lon2" value="10.37"></div></div><h3>مكان العودة الشمسية</h3><div class="grid"><div><label>خط العرض</label><input name="sr_lat2" value="48.25"></div><div><label>خط الطول</label><input name="sr_lon2" value="10.37"></div></div></div></div>
<div class="card"><h2>بيانات المباراة</h2><label>تاريخ ووقت البداية</label><input name="event_datetime" value="2026-07-15T22:00:00"><div class="grid"><div><label>UTC مكان المباراة</label><input name="event_offset" value="3"></div><div><label>خط العرض</label><input name="event_lat" value="13.58"></div><div><label>خط الطول</label><input name="event_lon" value="44.02"></div></div><label>الأورب الأقصى</label><input name="max_orb" value="2.0"><button type="submit">احسب المقارنة</button></div></form>__MATCH_RESULT__<p class="muted">تنبيه: المؤشرات رمزية وتجريبية، وتعرض تماسك نموذج الحساب فقط، وليست ضمانًا أو احتمالًا علميًا لنتيجة المباراة.</p></div></body></html>
'''

@app.get("/match", response_class=HTMLResponse)
def match_page():
    return MATCH_PAGE.replace("__MATCH_RESULT__","")

@app.post("/match-compare", response_class=HTMLResponse)
def match_compare(team1:str=Form(...),person1:str=Form(...),birth1:str=Form(...),birth_offset1:float=Form(...),birth_lat1:float=Form(...),birth_lon1:float=Form(...),sr_lat1:float=Form(...),sr_lon1:float=Form(...),team2:str=Form(...),person2:str=Form(...),birth2:str=Form(...),birth_offset2:float=Form(...),birth_lat2:float=Form(...),birth_lon2:float=Form(...),sr_lat2:float=Form(...),sr_lon2:float=Form(...),event_datetime:str=Form(...),event_offset:float=Form(...),event_lat:float=Form(...),event_lon:float=Form(...),max_orb:float=Form(2.0)):
    try:
        common={"event_datetime":event_datetime,"event_utc_offset":event_offset,"event_lat":event_lat,"event_lon":event_lon,"max_orb":max_orb}
        p1={**common,"name":person1,"birth_datetime":birth1,"birth_utc_offset":birth_offset1,"birth_lat":birth_lat1,"birth_lon":birth_lon1,"solar_return_lat":sr_lat1,"solar_return_lon":sr_lon1}
        p2={**common,"name":person2,"birth_datetime":birth2,"birth_utc_offset":birth_offset2,"birth_lat":birth_lat2,"birth_lon":birth_lon2,"solar_return_lat":sr_lat2,"solar_return_lon":sr_lon2}
        r1,r2=calculate(p1),calculate(p2)
        m1,m2=comparison_metrics(r1),comparison_metrics(r2)
        output=comparison_summary(team1,m1,team2,m2)
        output+=f'<section class="result-card"><h2>{html.escape(team1)} — {html.escape(person1)}</h2><div class="stats"><div><span>المؤشر</span><strong>{m1["index"]}</strong></div><div><span>مساندة</span><strong>{m1["supportive"]}</strong></div><div><span>ضاغطة</span><strong>{m1["hard"]}</strong></div><div><span>اقترانات</span><strong>{m1["conjunctions"]}</strong></div></div><h3>أقوى خمس إشارات</h3>{comparison_top_table(m1)}</section>'
        output+=f'<section class="result-card"><h2>{html.escape(team2)} — {html.escape(person2)}</h2><div class="stats"><div><span>المؤشر</span><strong>{m2["index"]}</strong></div><div><span>مساندة</span><strong>{m2["supportive"]}</strong></div><div><span>ضاغطة</span><strong>{m2["hard"]}</strong></div><div><span>اقترانات</span><strong>{m2["conjunctions"]}</strong></div></div><h3>أقوى خمس إشارات</h3>{comparison_top_table(m2)}</section>'
    except Exception as exc:
        output=f'<section class="result-card"><h2>حدث خطأ في المقارنة</h2><pre>{html.escape(str(exc))}</pre></section>'
    return MATCH_PAGE.replace("__MATCH_RESULT__",output)


def forecast_score(result: dict) -> dict:
    metrics = comparison_metrics(result)
    score = float(metrics["index"])
    if score >= 65:
        label = "مساند"
        css = "good"
    elif score <= 40:
        label = "ضاغط"
        css = "hard"
    else:
        label = "متوازن"
        css = "neutral"
    return {
        "score": round(score, 1),
        "label": label,
        "css": css,
        "confidence": metrics["confidence"],
        "supportive": metrics["supportive"],
        "hard": metrics["hard"],
        "top": metrics["top"][:3],
    }

def forecast_day_card(day_dt: datetime, result: dict) -> str:
    info = forecast_score(result)
    top_rows = []
    for a in info["top"]:
        moving = AR_PLANETS.get(str(a["moving_factor"]), str(a["moving_factor"]))
        natal = AR_PLANETS.get(str(a["natal_factor"]), str(a["natal_factor"]))
        aspect = ASPECT_AR.get(str(a["aspect"]), str(a["aspect"]))
        top_rows.append(
            f"<li>{html.escape(moving)} {html.escape(aspect)} {html.escape(natal)} "
            f"<small>({float(a.get('orb',0)):.2f}°)</small></li>"
        )
    return (
        f'<article class="day-card {info["css"]}">'
        f'<div class="day-head"><div><strong>{day_dt.strftime("%Y-%m-%d")}</strong>'
        f'<span>{html.escape(info["label"])}</span></div>'
        f'<b>{info["score"]}/100</b></div>'
        f'<div class="mini-stats"><span>مساندة: {info["supportive"]}</span>'
        f'<span>ضاغطة: {info["hard"]}</span>'
        f'<span>تماسك: {info["confidence"]}%</span></div>'
        f'<ul>{"".join(top_rows)}</ul>'
        '</article>'
    )

FORECAST_PAGE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>التوقع اليومي والأسبوعي</title>
<style>
:root{--bg:#0e1117;--panel:#171c24;--panel2:#11161d;--border:#2c3440;--text:#f4f6f8;--muted:#aeb8c6;--accent:#7c5cff}
*{box-sizing:border-box}body{font-family:Arial,Tahoma,sans-serif;background:var(--bg);color:var(--text);margin:0}
.wrap{max-width:980px;margin:auto;padding:16px}.card,.result-card{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:18px;margin:14px 0}
h1,h2{margin-top:0}label{display:block;margin:10px 0 5px;color:#d2d8e2}
input,select{width:100%;padding:12px;border-radius:10px;border:1px solid #3a4453;background:var(--panel2);color:white;font-size:16px}
button{width:100%;padding:15px;border:0;border-radius:12px;background:var(--accent);color:white;font-size:18px;font-weight:bold;margin-top:15px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.days-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.day-card{background:var(--panel2);border:1px solid var(--border);border-right:5px solid #777;border-radius:15px;padding:14px}
.day-card.good{border-right-color:#42c58f}.day-card.hard{border-right-color:#e06676}.day-card.neutral{border-right-color:#8e83d8}
.day-head{display:flex;justify-content:space-between;align-items:center;gap:12px}.day-head span{display:block;color:var(--muted);font-size:13px;margin-top:4px}.day-head b{font-size:22px}
.mini-stats{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.mini-stats span{background:#202631;padding:5px 8px;border-radius:999px;font-size:12px;color:#cad2de}
ul{padding-right:19px;margin-bottom:0}li{margin:7px 0}.back{color:#cbbfff;text-decoration:none}.muted{color:var(--muted);font-size:13px}
@media(max-width:720px){.grid,.days-grid{grid-template-columns:1fr}}
</style>
</head>
<body><div class="wrap">
<a class="back" href="/">← العودة للرئيسية</a>
<div class="card">
<h1>📆 التوقع اليومي والأسبوعي</h1>
<p class="muted">يمسح من يوم واحد إلى 14 يومًا باستخدام العبور والعودة الشمسية والتقدمات. الدرجات مؤشرات رمزية داخلية وليست ضمانًا لأحداث.</p>
<form method="post" action="/forecast-run">
<label>الاسم</label><input name="name" value="Abdulhaq">
<label>تاريخ ووقت الميلاد</label><input name="birth_datetime" value="1994-05-23T03:30:00">
<div class="grid">
<div><label>UTC الميلاد</label><input name="birth_offset" value="3"></div>
<div><label>خط عرض الميلاد</label><input name="birth_lat" value="13.58"></div>
<div><label>خط طول الميلاد</label><input name="birth_lon" value="44.02"></div>
</div>
<label>تاريخ البداية</label><input name="start_date" value="2026-07-15">
<div class="grid">
<div><label>وقت القياس اليومي</label><input name="event_time" value="12:00:00"></div>
<div><label>عدد الأيام</label><input name="days" value="7"></div>
<div><label>UTC مكان التوقع</label><input name="event_offset" value="3"></div>
</div>
<div class="grid">
<div><label>خط عرض المكان</label><input name="event_lat" value="13.58"></div>
<div><label>خط طول المكان</label><input name="event_lon" value="44.02"></div>
<div><label>الأورب</label><input name="max_orb" value="2.0"></div>
</div>
<h2>مكان العودة الشمسية</h2>
<div class="grid">
<div><label>خط العرض</label><input name="sr_lat" value="13.58"></div>
<div><label>خط الطول</label><input name="sr_lon" value="44.02"></div>
</div>
<button type="submit">أنشئ التقرير</button>
</form>
</div>
__FORECAST_RESULT__
</div></body></html>
"""

@app.get("/forecast", response_class=HTMLResponse)
def forecast_page():
    return FORECAST_PAGE.replace("__FORECAST_RESULT__", "")

@app.post("/forecast-run", response_class=HTMLResponse)
def forecast_run(
    name: str = Form(...),
    birth_datetime: str = Form(...),
    birth_offset: float = Form(...),
    birth_lat: float = Form(...),
    birth_lon: float = Form(...),
    start_date: str = Form(...),
    event_time: str = Form("12:00:00"),
    days: int = Form(7),
    event_offset: float = Form(...),
    event_lat: float = Form(...),
    event_lon: float = Form(...),
    sr_lat: float = Form(...),
    sr_lon: float = Form(...),
    max_orb: float = Form(2.0),
):
    try:
        days = max(1, min(14, int(days)))
        start = datetime.fromisoformat(start_date + "T" + event_time)
        cards = []
        scored = []
        for i in range(days):
            day_dt = start + timedelta(days=i)
            payload = {
                "name": name,
                "birth_datetime": birth_datetime,
                "birth_utc_offset": birth_offset,
                "birth_lat": birth_lat,
                "birth_lon": birth_lon,
                "event_datetime": day_dt.isoformat(timespec="seconds"),
                "event_utc_offset": event_offset,
                "event_lat": event_lat,
                "event_lon": event_lon,
                "solar_return_lat": sr_lat,
                "solar_return_lon": sr_lon,
                "max_orb": max_orb,
            }
            result = calculate(payload)
            info = forecast_score(result)
            scored.append((day_dt, info))
            cards.append(forecast_day_card(day_dt, result))

        best = max(scored, key=lambda x: x[1]["score"])
        hardest = min(scored, key=lambda x: x[1]["score"])
        summary = (
            '<section class="result-card"><h2>خلاصة الفترة</h2>'
            f'<p>أفضل يوم داخل المؤشر: <strong>{best[0].strftime("%Y-%m-%d")}</strong> — {best[1]["score"]}/100</p>'
            f'<p>أكثر يوم ضغطًا داخل المؤشر: <strong>{hardest[0].strftime("%Y-%m-%d")}</strong> — {hardest[1]["score"]}/100</p>'
            '<p class="muted">المقصود قوة/ضغط رمزي داخل النموذج، لا وقوع حدث مؤكد.</p></section>'
        )
        output = summary + '<section class="result-card"><h2>الأيام</h2><div class="days-grid">' + "".join(cards) + "</div></section>"
    except Exception as exc:
        output = f'<section class="result-card"><h2>حدث خطأ</h2><pre>{html.escape(str(exc))}</pre></section>'
    return FORECAST_PAGE.replace("__FORECAST_RESULT__", output)

ELECTIONAL_PAGE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>اختيار أفضل موعد</title>
<style>
:root{--bg:#0e1117;--panel:#171c24;--panel2:#11161d;--border:#2c3440;--text:#f4f6f8;--muted:#aeb8c6;--accent:#7c5cff}
*{box-sizing:border-box}body{font-family:Arial,Tahoma,sans-serif;background:var(--bg);color:var(--text);margin:0}.wrap{max-width:980px;margin:auto;padding:16px}
.card,.result-card{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:18px;margin:14px 0}
label{display:block;margin:10px 0 5px;color:#d2d8e2}input,select{width:100%;padding:12px;border-radius:10px;border:1px solid #3a4453;background:var(--panel2);color:white;font-size:16px}
button{width:100%;padding:15px;border:0;border-radius:12px;background:var(--accent);color:white;font-size:18px;font-weight:bold;margin-top:15px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:12px}table{width:100%;border-collapse:collapse;min-width:650px;background:var(--panel2)}th,td{padding:11px;border-bottom:1px solid var(--border);text-align:right}th{background:#191f29}
.back{color:#cbbfff;text-decoration:none}.muted{color:var(--muted);font-size:13px}@media(max-width:720px){.grid{grid-template-columns:1fr}}
</style></head>
<body><div class="wrap"><a class="back" href="/">← العودة للرئيسية</a>
<div class="card"><h1>🎯 اختيار أفضل موعد</h1>
<p class="muted">يمسح حتى 31 يومًا ويصنف المواعيد وفق المؤشر الداخلي. لا يستخدم لاتخاذ قرارات طبية أو قانونية أو مالية عالية المخاطر.</p>
<form method="post" action="/electional-run">
<label>نوع الحدث</label>
<select name="event_type"><option>افتتاح مشروع</option><option>توقيع عقد</option><option>سفر</option><option>مقابلة</option><option>إطلاق منتج</option><option>مناسبة شخصية</option></select>
<label>الاسم</label><input name="name" value="Abdulhaq">
<label>تاريخ ووقت الميلاد</label><input name="birth_datetime" value="1994-05-23T03:30:00">
<div class="grid">
<div><label>UTC الميلاد</label><input name="birth_offset" value="3"></div>
<div><label>خط عرض الميلاد</label><input name="birth_lat" value="13.58"></div>
<div><label>خط طول الميلاد</label><input name="birth_lon" value="44.02"></div>
</div>
<div class="grid">
<div><label>من تاريخ</label><input name="start_date" value="2026-07-15"></div>
<div><label>إلى تاريخ</label><input name="end_date" value="2026-07-22"></div>
<div><label>وقت الاختبار</label><input name="event_time" value="10:00:00"></div>
</div>
<div class="grid">
<div><label>UTC المكان</label><input name="event_offset" value="3"></div>
<div><label>خط عرض المكان</label><input name="event_lat" value="15.37"></div>
<div><label>خط طول المكان</label><input name="event_lon" value="44.19"></div>
</div>
<div class="grid">
<div><label>خط عرض العودة</label><input name="sr_lat" value="15.37"></div>
<div><label>خط طول العودة</label><input name="sr_lon" value="44.19"></div>
<div><label>الأورب</label><input name="max_orb" value="1.5"></div>
</div>
<button type="submit">افحص المواعيد</button>
</form></div>
__ELECTION_RESULT__
</div></body></html>
"""

@app.get("/electional", response_class=HTMLResponse)
def electional_page():
    return ELECTIONAL_PAGE.replace("__ELECTION_RESULT__", "")

@app.post("/electional-run", response_class=HTMLResponse)
def electional_run(
    event_type: str = Form(...),
    name: str = Form(...),
    birth_datetime: str = Form(...),
    birth_offset: float = Form(...),
    birth_lat: float = Form(...),
    birth_lon: float = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    event_time: str = Form("10:00:00"),
    event_offset: float = Form(...),
    event_lat: float = Form(...),
    event_lon: float = Form(...),
    sr_lat: float = Form(...),
    sr_lon: float = Form(...),
    max_orb: float = Form(1.5),
):
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        if end < start:
            raise ValueError("تاريخ النهاية يجب أن يكون بعد تاريخ البداية.")
        total_days = min(31, (end - start).days + 1)
        ranked = []
        for i in range(total_days):
            day = start + timedelta(days=i)
            event_dt = datetime.fromisoformat(day.strftime("%Y-%m-%d") + "T" + event_time)
            payload = {
                "name": name,
                "birth_datetime": birth_datetime,
                "birth_utc_offset": birth_offset,
                "birth_lat": birth_lat,
                "birth_lon": birth_lon,
                "event_datetime": event_dt.isoformat(timespec="seconds"),
                "event_utc_offset": event_offset,
                "event_lat": event_lat,
                "event_lon": event_lon,
                "solar_return_lat": sr_lat,
                "solar_return_lon": sr_lon,
                "max_orb": max_orb,
            }
            info = forecast_score(calculate(payload))
            ranked.append((day, info))
        ranked.sort(key=lambda x: x[1]["score"], reverse=True)
        rows = []
        for rank, (day, info) in enumerate(ranked, 1):
            rows.append(
                f"<tr><td>{rank}</td><td>{day.strftime('%Y-%m-%d')}</td>"
                f"<td>{info['score']}/100</td><td>{html.escape(info['label'])}</td>"
                f"<td>{info['supportive']}</td><td>{info['hard']}</td><td>{info['confidence']}%</td></tr>"
            )
        output = (
            f'<section class="result-card"><h2>أفضل المواعيد لـ: {html.escape(event_type)}</h2>'
            '<div class="table-wrap"><table><thead><tr><th>الترتيب</th><th>التاريخ</th><th>المؤشر</th><th>الحالة</th><th>مساندة</th><th>ضاغطة</th><th>تماسك</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            '<p class="muted">هذا ترتيب رمزي أولي. النسخة القادمة ستضيف قواعد خاصة بكل نوع حدث بدل استخدام مؤشر عام واحد.</p></section>'
        )
    except Exception as exc:
        output = f'<section class="result-card"><h2>حدث خطأ</h2><pre>{html.escape(str(exc))}</pre></section>'
    return ELECTIONAL_PAGE.replace("__ELECTION_RESULT__", output)

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
