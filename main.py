
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import html
import json
from collections import Counter

from astro_core import calculate

app = FastAPI(title="Astro Assistant", version="1.5")

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

def chart_wheel(planets: dict, houses: dict, angles: dict, title: str, overlay: dict = None) -> str:
    size = 640
    cx = cy = size / 2
    outer = 292
    zodiac_r = 256
    house_r = 214
    planet_r = 176
    inner = 92

    svg = [
        f"<div class='wheel-card'><h3>{html.escape(title)}</h3>",
        f"<svg class='astro-wheel' viewBox='0 0 {size} {size}' role='img' aria-label='{html.escape(title)}'>",
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
        svg.append(f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' class='zodiac-line'/>")
        lx, ly = polar(cx, cy, 274, lon + 15)
        svg.append(f"<text x='{lx:.2f}' y='{ly:.2f}' class='zodiac-label'>{SIGN_SYMBOLS[i]}</text>")

    # House cusps
    for i in range(1, 13):
        lon = float(houses[f"House {i}"])
        x1, y1 = polar(cx, cy, zodiac_r, lon)
        x2, y2 = polar(cx, cy, inner, lon)
        css = "house-line major" if i in (1,4,7,10) else "house-line"
        svg.append(f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' class='{css}'/>")
        lx, ly = polar(cx, cy, 198, lon + 7)
        svg.append(f"<text x='{lx:.2f}' y='{ly:.2f}' class='house-number'>{i}</text>")

    # ASC / MC labels
    for key in ("ASC","MC"):
        if key in angles:
            lon = float(angles[key])
            lx, ly = polar(cx, cy, 228, lon)
            svg.append(f"<text x='{lx:.2f}' y='{ly:.2f}' class='angle-label'>{key}</text>")

    # Planet placement with simple staggering for close longitudes
    placed = []
    for idx, (name, data) in enumerate(planets.items()):
        lon = float(data["longitude"])
        ring = planet_r
        for prev_lon, prev_ring in placed:
            diff = abs((lon - prev_lon + 180) % 360 - 180)
            if diff < 5:
                ring = 152 if prev_ring == planet_r else 132
        placed.append((lon, ring))
        px, py = polar(cx, cy, ring, lon)
        label = SYMBOLS.get(name, name[:2])
        retro = " ℞" if data.get("retrograde") else ""
        svg.append(f"<circle cx='{px:.2f}' cy='{py:.2f}' r='15' class='planet-dot'/>")
        svg.append(f"<text x='{px:.2f}' y='{py:.2f}' class='planet-label'>{html.escape(label + retro)}</text>")

    # Optional overlay ring (for transits / solar return comparison)
    if overlay:
        placed_overlay = []
        for name, data in overlay.items():
            lon = float(data["longitude"])
            ring = 112
            for prev_lon, prev_ring in placed_overlay:
                diff = abs((lon - prev_lon + 180) % 360 - 180)
                if diff < 5:
                    ring = 96
            placed_overlay.append((lon, ring))
            px, py = polar(cx, cy, ring, lon)
            label = SYMBOLS.get(name, name[:2])
            retro = " ℞" if data.get("retrograde") else ""
            svg.append(f"<circle cx='{px:.2f}' cy='{py:.2f}' r='13' class='overlay-dot'/>")
            svg.append(f"<text x='{px:.2f}' y='{py:.2f}' class='overlay-label'>{html.escape(label + retro)}</text>")

    svg.append("</svg>")
    if overlay:
        svg.append("<div class='wheel-legend'><span><i class='legend-natal'></i> الميلاد</span><span><i class='legend-overlay'></i> الخريطة المقارنة</span></div>")
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

    blocks.append(section(
        "عجلات الخرائط",
        "<div class='wheel-grid'>" +
        chart_wheel(natal["planets"], natal["houses"], natal["angles"], "الخريطة الميلادية") +
        chart_wheel(natal["planets"], natal["houses"], natal["angles"], "العبور فوق الميلاد", transits["planets"]) +
        chart_wheel(sr["planets"], sr["houses"], sr["angles"], "العودة الشمسية") +
        chart_wheel(prog["planets"], prog["houses"], prog["angles"], "التقدمات الثانوية") +
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
.wheel-legend{display:flex;gap:14px;justify-content:center;color:var(--muted);font-size:12px;margin-top:8px}
.wheel-legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-left:5px}
.legend-natal{background:#8f7cff}
.legend-overlay{background:#56d1a0}
@media(max-width:700px){
  .grid,.summary-grid,.stats,.analysis-grid,.wheel-grid{grid-template-columns:1fr}
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
    تنبيه: التحليلات رمزية وتعليمية وليست تنبؤًا علميًا أو ضمانًا لوقوع أحداث.
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
