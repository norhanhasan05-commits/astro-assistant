\
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import numpy as np
import swisseph as swe
from scipy.optimize import brentq

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Mean Node": swe.MEAN_NODE,
}

ASPECTS = {
    "Conjunction": 0.0,
    "Sextile": 60.0,
    "Square": 90.0,
    "Trine": 120.0,
    "Opposition": 180.0,
}

TOPOCENTRIC = b"T"
NAIBOD_DEG_PER_YEAR = (59 + 8.33 / 60) / 60


def normalize(x: float) -> float:
    return x % 360.0


def local_to_utc(dt_local: datetime, utc_offset: float) -> datetime:
    tz = timezone(timedelta(hours=utc_offset))
    return dt_local.replace(tzinfo=tz).astimezone(timezone.utc)


def dt_to_jd(dt: datetime) -> float:
    dt = dt.astimezone(timezone.utc)
    hour = dt.hour + dt.minute / 60 + dt.second / 3600
    return swe.julday(dt.year, dt.month, dt.day, hour, swe.GREG_CAL)


def jd_to_iso(jd: float) -> str:
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    hh = int(h)
    mmf = (h - hh) * 60
    mm = int(mmf)
    ss = min(int(round((mmf - mm) * 60)), 59)
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc).isoformat()


def angular_distance(a: float, b: float) -> float:
    d = abs((a - b) % 360)
    return min(d, 360 - d)


def planets(jd: float) -> Dict[str, Dict[str, Any]]:
    out = {}
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    for name, code in PLANETS.items():
        xx, _ = swe.calc_ut(jd, code, flags)
        out[name] = {
            "longitude": round(normalize(xx[0]), 6),
            "latitude": round(xx[1], 6),
            "speed": round(xx[3], 6),
            "retrograde": xx[3] < 0,
        }
    return out


def houses(jd: float, lat: float, lon: float):
    cusps, ascmc = swe.houses_ex(jd, lat, lon, TOPOCENTRIC, 0)
    return (
        {f"House {i+1}": round(normalize(cusps[i]), 6) for i in range(12)},
        {
            "ASC": round(normalize(ascmc[0]), 6),
            "MC": round(normalize(ascmc[1]), 6),
            "ARMC": round(normalize(ascmc[2]), 6),
            "Vertex": round(normalize(ascmc[3]), 6),
        },
    )


def factors(planets_map, houses_map=None, angles_map=None):
    result = {k: v["longitude"] for k, v in planets_map.items()}
    if houses_map:
        result.update(houses_map)
    if angles_map:
        result.update(angles_map)
    return result


def aspect_rows(moving, natal, max_orb=2.0):
    rows = []
    for m_name, m_lon in moving.items():
        for n_name, n_lon in natal.items():
            sep = angular_distance(m_lon, n_lon)
            for asp_name, asp_deg in ASPECTS.items():
                orb = abs(sep - asp_deg)
                if orb <= max_orb:
                    rows.append({
                        "moving_factor": m_name,
                        "aspect": asp_name,
                        "natal_factor": n_name,
                        "orb": round(orb, 4),
                        "separation": round(sep, 4),
                    })
    return sorted(rows, key=lambda x: x["orb"])


def sun_lon(jd: float) -> float:
    xx, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
    return normalize(xx[0])


def signed_diff(a: float, b: float) -> float:
    return ((a - b + 180) % 360) - 180


def solar_return_jd(natal_jd: float, year: int) -> float:
    natal_sun = sun_lon(natal_jd)
    y, m, d, _ = swe.revjul(natal_jd, swe.GREG_CAL)
    guess = dt_to_jd(datetime(year, m, d, 12, tzinfo=timezone.utc))

    def f(jd):
        return signed_diff(sun_lon(jd), natal_sun)

    xs = np.linspace(guess - 3, guess + 3, 145)
    vals = [f(x) for x in xs]
    for a, b, fa, fb in zip(xs[:-1], xs[1:], vals[:-1], vals[1:]):
        if abs(fa - fb) < 30 and fa * fb <= 0:
            return brentq(f, a, b, xtol=1e-10)
    raise ValueError("تعذر تحديد العودة الشمسية. راجع البيانات.")


def secondary_progressed_jd(natal_jd: float, target_jd: float) -> float:
    age_years = (target_jd - natal_jd) / 365.2422
    return natal_jd + age_years


def primary_directions_asc_mc(natal_jd, target_jd, lat, lon, natal_factors, max_orb_arcmin=11.0):
    age_years = (target_jd - natal_jd) / 365.2422
    arc = age_years * NAIBOD_DEG_PER_YEAR
    _, natal_angles = houses(natal_jd, lat, lon)
    natal_armc = natal_angles["ARMC"]
    rows = []

    for direction, sign in (("Direct", 1), ("Converse", -1)):
        synthetic_jd = natal_jd + sign * arc / 360.98564736629
        _, directed_angles = houses(synthetic_jd, lat, lon)
        for sig in ("ASC", "MC"):
            sig_lon = directed_angles[sig]
            for natal_name, natal_lon in natal_factors.items():
                if natal_name.startswith("House "):
                    continue
                sep = angular_distance(sig_lon, natal_lon)
                for asp_name, asp_deg in ASPECTS.items():
                    orb_arcmin = abs(sep - asp_deg) * 60
                    if orb_arcmin <= max_orb_arcmin:
                        rows.append({
                            "direction": direction,
                            "significator": sig,
                            "aspect": asp_name,
                            "natal_factor": natal_name,
                            "orb_arcmin": round(orb_arcmin, 3),
                            "naibod_arc_deg": round(arc, 6),
                            "directed_armc": round(normalize(natal_armc + sign * arc), 6),
                        })
    return sorted(rows, key=lambda x: x["orb_arcmin"])


def calculate(payload: Dict[str, Any]) -> Dict[str, Any]:
    birth_local = datetime.fromisoformat(payload["birth_datetime"])
    event_local = datetime.fromisoformat(payload["event_datetime"])

    birth_utc = local_to_utc(birth_local, float(payload["birth_utc_offset"]))
    event_utc = local_to_utc(event_local, float(payload["event_utc_offset"]))

    natal_jd = dt_to_jd(birth_utc)
    event_jd = dt_to_jd(event_utc)

    n_planets = planets(natal_jd)
    n_houses, n_angles = houses(natal_jd, payload["birth_lat"], payload["birth_lon"])
    n_factors = factors(n_planets, n_houses, n_angles)

    t_planets = planets(event_jd)
    _, t_angles = houses(event_jd, payload["event_lat"], payload["event_lon"])
    t_factors = factors(t_planets, None, t_angles)

    sr_jd = solar_return_jd(natal_jd, event_utc.year)
    sr_planets = planets(sr_jd)
    sr_houses, sr_angles = houses(sr_jd, payload["solar_return_lat"], payload["solar_return_lon"])
    sr_factors = factors(sr_planets, sr_houses, sr_angles)

    prog_jd = secondary_progressed_jd(natal_jd, event_jd)
    prog_planets = planets(prog_jd)
    prog_houses, prog_angles = houses(prog_jd, payload["birth_lat"], payload["birth_lon"])
    prog_factors = factors(prog_planets, prog_houses, prog_angles)

    max_orb = float(payload.get("max_orb", 2.0))

    return {
        "metadata": {
            "name": payload.get("name", ""),
            "birth_utc": birth_utc.isoformat(),
            "event_utc": event_utc.isoformat(),
            "solar_return_utc": jd_to_iso(sr_jd),
            "progressed_utc": jd_to_iso(prog_jd),
            "house_system": "Topocentric (Polich/Page)",
            "primary_directions_scope": "Experimental ASC/MC only, Direct+Converse, Naibod",
        },
        "natal": {"planets": n_planets, "houses": n_houses, "angles": n_angles},
        "transits": {
            "planets": t_planets,
            "angles": t_angles,
            "aspects_to_natal": aspect_rows(t_factors, n_factors, max_orb),
        },
        "solar_return": {
            "planets": sr_planets,
            "houses": sr_houses,
            "angles": sr_angles,
            "aspects_to_natal": aspect_rows(sr_factors, n_factors, max_orb),
        },
        "secondary_progressions": {
            "planets": prog_planets,
            "houses": prog_houses,
            "angles": prog_angles,
            "aspects_to_natal": aspect_rows(prog_factors, n_factors, max_orb),
        },
        "primary_directions_experimental": primary_directions_asc_mc(
            natal_jd, event_jd, payload["birth_lat"], payload["birth_lon"], n_factors
        ),
    }
