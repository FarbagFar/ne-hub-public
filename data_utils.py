from __future__ import annotations

import json
import math
import os
import re
import subprocess
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
ASSETS = BASE / "assets"


def find_tracker_dir() -> Path:
    """Localise le dossier du tracker sans imposer un nom exact.

    Priorité au dossier historique, puis recherche limitée autour de NE Hub.
    Cela évite que l'Observatoire devienne vide simplement parce que le dossier
    a été renommé (espace, underscore, faute mineure) ou placé un niveau plus bas.
    """
    for name in ("SuiviLisnard", "suivi lisnard", "suivi_lisnard", "suivi lisnaard", "Suivi Lisnard"):
        candidate = BASE / name
        if (candidate / "suivi_reseaux_politiques.xlsx").exists():
            return candidate

    # Recherche courte et prudente : NE Hub + ses sous-dossiers (hors environnements lourds).
    excluded = {".venv", "venv", "chrome_profile", ".git", "__pycache__", "node_modules"}
    for root in (BASE, BASE.parent):
        try:
            for child in root.iterdir():
                if not child.is_dir() or child.name in excluded:
                    continue
                if (child / "suivi_reseaux_politiques.xlsx").exists():
                    return child
                # Un niveau supplémentaire suffit pour les structures usuelles.
                try:
                    for sub in child.iterdir():
                        if sub.is_dir() and sub.name not in excluded and (sub / "suivi_reseaux_politiques.xlsx").exists():
                            return sub
                except OSError:
                    pass
        except OSError:
            pass

    return BASE / "SuiviLisnard"


TRACKER_DIR = find_tracker_dir()
SOCIAL_XLSX = TRACKER_DIR / "suivi_reseaux_politiques.xlsx"
PRESS_XLSX = TRACKER_DIR / "articles_presse.xlsx"
CANDIDATES_JSON = TRACKER_DIR / "candidats.json"
PUBLIC_DATA_JSON = DATA / "public_data.json"
DOCS_FILE = DATA / "documents.json"
EVENTS_FILE = DATA / "events.json"
RELAYS_FILE = DATA / "relays.json"
META_FILE = DATA / "meta.json"

NETWORKS = ("Instagram", "X", "Facebook", "LinkedIn")


def tracker_diagnostics() -> dict:
    return {
        "tracker_dir": str(TRACKER_DIR),
        "social_path": str(SOCIAL_XLSX),
        "social_exists": SOCIAL_XLSX.exists(),
        "press_path": str(PRESS_XLSX),
        "press_exists": PRESS_XLSX.exists(),
        "candidates_path": str(CANDIDATES_JSON),
        "candidates_exists": CANDIDATES_JSON.exists(),
    }


def social_history_days(social: pd.DataFrame) -> int:
    if social.empty or "Date" not in social.columns:
        return 0
    x = social["Date"].dropna()
    return int(x.dt.normalize().nunique()) if not x.empty else 0


def norm(s: Any) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


STOP = set(
    "le la les de des du un une et ou en a au aux pour par sur dans avec que qui quoi quel quelle quels quelles est sont il elle ils elles ce cette ces se sa son ses notre votre leur leurs plus ne pas".split()
)


def tokens(s: Any) -> list[str]:
    return [t for t in norm(s).split() if len(t) > 2 and t not in STOP]


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except Exception:
        return 0.0


@st.cache_data(show_spinner=False)
def read_excel_cached(path_str: str, file_mtime: float, sheet_name: str):
    return pd.read_excel(path_str, sheet_name=sheet_name, engine="openpyxl")


@st.cache_data(show_spinner=False)
def read_json_cached(path_str: str, file_mtime: float):
    try:
        return json.loads(Path(path_str).read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_site_data():
    return (
        load_json(DOCS_FILE, []),
        load_json(EVENTS_FILE, []),
        load_json(RELAYS_FILE, []),
        load_json(META_FILE, {}),
    )


def load_public_data() -> dict:
    if PUBLIC_DATA_JSON.exists():
        return read_json_cached(str(PUBLIC_DATA_JSON), mtime(PUBLIC_DATA_JSON)) or {}
    return {}


def load_tracker_data():
    social = pd.DataFrame()
    press_articles = pd.DataFrame()
    press_comparison = pd.DataFrame()
    press_topics = pd.DataFrame()
    candidates = {}
    errors: list[str] = []
    try:
        if SOCIAL_XLSX.exists():
            social = read_excel_cached(str(SOCIAL_XLSX), mtime(SOCIAL_XLSX), "DONNEES").copy()
            if "Date" in social.columns:
                social["Date"] = pd.to_datetime(social["Date"], dayfirst=True, errors="coerce")
            for col in (*NETWORKS, "Total"):
                if col in social.columns:
                    social[col] = pd.to_numeric(social[col], errors="coerce")
            social = social.dropna(subset=["Date", "Personne"]).sort_values(["Date", "Personne"])
    except Exception as ex:
        errors.append(f"Réseaux : {ex}")
    try:
        if PRESS_XLSX.exists():
            press_articles = read_excel_cached(str(PRESS_XLSX), mtime(PRESS_XLSX), "ARTICLES").copy()
            press_comparison = read_excel_cached(str(PRESS_XLSX), mtime(PRESS_XLSX), "COMPARAISON").copy()
            press_topics = read_excel_cached(str(PRESS_XLSX), mtime(PRESS_XLSX), "SUJETS").copy()
            for c in ("Date", "DatePublication"):
                if c in press_articles.columns:
                    press_articles[c] = pd.to_datetime(press_articles[c], dayfirst=True, errors="coerce")
            if "Date" in press_topics.columns:
                press_topics["Date"] = pd.to_datetime(press_topics["Date"], dayfirst=True, errors="coerce")
    except Exception as ex:
        errors.append(f"Presse : {ex}")
    try:
        if CANDIDATES_JSON.exists():
            candidates = read_json_cached(str(CANDIDATES_JSON), mtime(CANDIDATES_JSON)) or {}
    except Exception as ex:
        errors.append(f"Candidats : {ex}")
    return social, press_articles, press_comparison, press_topics, candidates, errors


def fmt_int(v) -> str:
    try:
        if pd.isna(v):
            return "—"
        return f"{int(round(float(v))):,}".replace(",", " ")
    except Exception:
        return "—"


def fmt_pct(v, digits: int = 2) -> str:
    try:
        if v is None or pd.isna(v):
            return "—"
        return f"{float(v):+.{digits}f} %".replace(".", ",")
    except Exception:
        return "—"


def fmt_date(v) -> str:
    try:
        if pd.isna(v):
            return "—"
        return pd.Timestamp(v).strftime("%d/%m/%Y")
    except Exception:
        return str(v or "—")


def parse_date(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
        except Exception:
            return None


def social_current_date(social: pd.DataFrame):
    if social.empty or "Date" not in social.columns:
        return None
    x = social["Date"].dropna()
    return x.max() if not x.empty else None


def person_current_row(social: pd.DataFrame, person: str):
    if social.empty:
        return None
    g = social[social["Personne"] == person].sort_values("Date")
    return None if g.empty else g.iloc[-1]


def person_baseline_row(social: pd.DataFrame, person: str, days: int | None = None):
    if social.empty:
        return None
    g = social[social["Personne"] == person].dropna(subset=["Date"]).sort_values("Date")
    if g.empty:
        return None
    if days is None:
        return g.iloc[0]
    target = g.iloc[-1]["Date"] - pd.Timedelta(days=days)
    before = g[g["Date"] <= target]
    return None if before.empty else before.iloc[-1]


def network_coverage(row) -> set[str]:
    if row is None:
        return set()
    return {n for n in NETWORKS if n in row.index and not pd.isna(row.get(n))}


def coverage_changed(social: pd.DataFrame, person: str, days: int = 7) -> bool:
    cur = person_current_row(social, person)
    base = person_baseline_row(social, person, days)
    if cur is None or base is None:
        return False
    return network_coverage(cur) != network_coverage(base)


def change_for_person(social: pd.DataFrame, person: str, column: str = "Total", days: int = 7):
    cur = person_current_row(social, person)
    base = person_baseline_row(social, person, days)
    if cur is None or base is None or column not in cur.index:
        return None, None
    a, b = cur.get(column), base.get(column)
    if pd.isna(a) or pd.isna(b):
        return None, None
    if column == "Total" and network_coverage(cur) != network_coverage(base):
        return None, None
    gain = float(a) - float(b)
    pct = gain / float(b) * 100 if float(b) else None
    return gain, pct


def social_ranking(social: pd.DataFrame, column: str = "Total", days: int = 7) -> pd.DataFrame:
    rows = []
    if social.empty:
        return pd.DataFrame()
    for person in sorted(social["Personne"].dropna().unique()):
        cur = person_current_row(social, person)
        if cur is None or column not in cur.index or pd.isna(cur.get(column)):
            continue
        gain, pct = change_for_person(social, person, column, days)
        quality = "Périmètre changé" if column == "Total" and coverage_changed(social, person, days) else "OK"
        rows.append({"Personne": person, "Actuel": cur.get(column), "Gain": gain, "Croissance %": pct, "Qualité": quality})
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["Croissance %", "Gain"], ascending=False, na_position="last")
    return out


def social_base100(social: pd.DataFrame, column: str = "Total") -> pd.DataFrame:
    if social.empty or column not in social.columns:
        return pd.DataFrame()
    parts = []
    for person, g in social[["Date", "Personne", column]].dropna().groupby("Personne"):
        g = g.sort_values("Date").copy()
        g = g[g[column] > 0]
        if g.empty:
            continue
        base = float(g.iloc[0][column])
        g["Indice"] = g[column].astype(float) / base * 100
        parts.append(g[["Date", "Personne", "Indice"]])
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def current_social_table(social: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if social.empty:
        return pd.DataFrame()
    for person in social["Personne"].dropna().unique():
        cur = person_current_row(social, person)
        if cur is None:
            continue
        rows.append({k: cur.get(k) for k in ["Personne", *NETWORKS, "Total"]})
    return pd.DataFrame(rows).sort_values("Total", ascending=False, na_position="last") if rows else pd.DataFrame()


def press_counts_from_articles(press_articles: pd.DataFrame, days: int = 7, language: str | None = None) -> pd.DataFrame:
    if press_articles.empty or "Personne" not in press_articles.columns:
        return pd.DataFrame()
    date_col = "DatePublication" if "DatePublication" in press_articles.columns else "Date"
    df = press_articles.dropna(subset=[date_col]).copy()
    if language and language != "Toutes":
        if "Langue" in df.columns:
            if language == "Français":
                df = df[df["Langue"].astype(str).str.lower().str.startswith(("fr", "french", "fran"))]
            else:
                df = df[df["Langue"].astype(str).str.lower() == language.lower()]
    if df.empty:
        return pd.DataFrame()
    end = df[date_col].max().normalize()
    start = end - pd.Timedelta(days=max(days - 1, 0))
    prev_start = start - pd.Timedelta(days=days)
    current = df[(df[date_col] >= start) & (df[date_col] < end + pd.Timedelta(days=1))].groupby("Personne").size()
    previous = df[(df[date_col] >= prev_start) & (df[date_col] < start)].groupby("Personne").size()
    people = sorted(set(current.index) | set(previous.index))
    rows = []
    for p in people:
        c, old = int(current.get(p, 0)), int(previous.get(p, 0))
        pct = ((c / old) - 1) * 100 if old else (None if c else 0.0)
        rows.append({"Personne": p, f"Articles {days}j": c, "Période précédente": old, "Évolution %": pct})
    return pd.DataFrame(rows).sort_values(f"Articles {days}j", ascending=False)


def press_daily_series(press_articles: pd.DataFrame, people: list[str] | None = None, days: int = 30, language: str | None = None) -> pd.DataFrame:
    if press_articles.empty:
        return pd.DataFrame()
    date_col = "DatePublication" if "DatePublication" in press_articles.columns else "Date"
    df = press_articles.dropna(subset=[date_col]).copy()
    if people:
        df = df[df["Personne"].isin(people)]
    if language and language != "Toutes" and "Langue" in df.columns:
        if language == "Français":
            df = df[df["Langue"].astype(str).str.lower().str.startswith(("fr", "french", "fran"))]
    if df.empty:
        return pd.DataFrame()
    end = df[date_col].max().normalize()
    df = df[df[date_col] >= end - pd.Timedelta(days=days - 1)]
    out = df.groupby([df[date_col].dt.normalize().rename("Date"), "Personne"]).size().reset_index(name="Articles")
    return out.sort_values(["Date", "Personne"])


def latest_topics(press_topics: pd.DataFrame, person: str | None = None) -> pd.DataFrame:
    if press_topics.empty or "Personne" not in press_topics.columns:
        return pd.DataFrame()
    df = press_topics.copy()
    if person:
        df = df[df["Personne"] == person]
    if "Date" in df.columns and df["Date"].notna().any():
        d = df["Date"].max()
        df = df[df["Date"] == d]
    if "Rang" in df.columns:
        df = df.sort_values("Rang")
    return df


def candidate_names(candidates: dict, social: pd.DataFrame) -> list[str]:
    names = list(candidates.keys()) if isinstance(candidates, dict) else []
    if not social.empty and "Personne" in social.columns:
        for p in social["Personne"].dropna().unique():
            if p not in names:
                names.append(p)
    return names


def detect_people(question: str, names: list[str]) -> list[str]:
    nq = norm(question)
    full = [n for n in names if norm(n) and norm(n) in nq]
    if full:
        return list(dict.fromkeys(full))
    words = set(nq.split())
    found = []
    for n in names:
        parts = [p for p in norm(n).split() if len(p) >= 4]
        if parts and parts[-1] in words:
            found.append(n)
    return list(dict.fromkeys(found))


def detect_network(question: str) -> str:
    nq = f" {norm(question)} "
    for key, val in (("instagram", "Instagram"), ("linkedin", "LinkedIn"), ("facebook", "Facebook"), ("twitter", "X"), (" x ", "X")):
        if key in nq:
            return val
    return "Total"


def detect_days(question: str, default: int = 7) -> int:
    nq = norm(question)
    if "24h" in nq or "24 h" in question.lower() or ("jour" in nq and "30" not in nq and "7" not in nq):
        return 1
    if "90" in nq or "3 mois" in nq:
        return 90
    if "30" in nq or "mois" in nq:
        return 30
    if "7" in nq or "semaine" in nq:
        return 7
    return default


def wiki_items(public_data: dict, person: str) -> list[dict]:
    return (((public_data or {}).get("wikipedia") or {}).get("series") or {}).get(person, []) or []


def wiki_sum(public_data: dict, person: str, days: int = 30):
    items = wiki_items(public_data, person)
    if not items:
        return None
    rows = sorted(items, key=lambda x: x.get("date", ""))[-days:]
    vals = [float(x.get("views", 0) or 0) for x in rows]
    return sum(vals) if vals else None


def wiki_ranking(public_data: dict, days: int = 30) -> pd.DataFrame:
    series = (((public_data or {}).get("wikipedia") or {}).get("series") or {})
    rows = []
    for person in series:
        total = wiki_sum(public_data, person, days)
        if total is not None:
            rows.append({"Personne": person, f"Vues {days}j": total})
    return pd.DataFrame(rows).sort_values(f"Vues {days}j", ascending=False) if rows else pd.DataFrame()


def wiki_series_df(public_data: dict, people: list[str] | None = None, days: int = 90) -> pd.DataFrame:
    series = (((public_data or {}).get("wikipedia") or {}).get("series") or {})
    rows = []
    selected = people or list(series.keys())
    for p in selected:
        vals = sorted(series.get(p, []) or [], key=lambda x: x.get("date", ""))[-days:]
        for item in vals:
            rows.append({"Date": pd.to_datetime(item.get("date"), errors="coerce"), "Personne": p, "Vues": item.get("views", 0)})
    return pd.DataFrame(rows).dropna(subset=["Date"]) if rows else pd.DataFrame()


def quality_table(social: pd.DataFrame, press_topics: pd.DataFrame) -> pd.DataFrame:
    if social.empty:
        return pd.DataFrame()
    rows = []
    last = social_current_date(social)
    for person in sorted(social["Personne"].dropna().unique()):
        cur = person_current_row(social, person)
        coverage = network_coverage(cur)
        missing = [n for n in NETWORKS if n not in coverage]
        changed = False
        g = social[social["Personne"] == person].sort_values("Date")
        if len(g) >= 2:
            changed = network_coverage(g.iloc[-1]) != network_coverage(g.iloc[-2])
        press_flag = False
        if not press_topics.empty and "Personne" in press_topics.columns and "Sujet" in press_topics.columns:
            sub = press_topics[press_topics["Personne"] == person]
            press_flag = sub["Sujet"].astype(str).str.contains("hors-sujet|homonyme", case=False, regex=True).any()
        rows.append({
            "Personne": person,
            "Dernier relevé": last,
            "Réseaux disponibles": len(coverage),
            "Réseaux manquants": ", ".join(missing) if missing else "Aucun",
            "Périmètre modifié": "Oui" if changed else "Non",
            "Alerte presse": "À vérifier" if press_flag else "—",
        })
    return pd.DataFrame(rows)


def score_doc(query: str, d: dict) -> float:
    q = tokens(query)
    if not q:
        return 0
    title = norm(d.get("title", ""))
    text = norm(d.get("text", ""))
    tags = norm(" ".join(d.get("tags", [])))
    score = 0.0
    for t in q:
        if t in title:
            score += 5
        if t in tags:
            score += 3
        score += min(text.count(t), 6) * 0.7
    phrase = norm(query)
    if phrase and phrase in text:
        score += 8
    return score


def search_docs(query: str, docs: list[dict], limit: int = 8) -> list[dict]:
    ranked = [(score_doc(query, d), d) for d in docs]
    ranked = [(s, d) for s, d in ranked if s > 0]
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in ranked[:limit]]


def snippet(text: str, query: str, max_chars: int = 520) -> str:
    text = " ".join(str(text or "").split())
    if not text:
        return ""
    q = tokens(query)
    low = norm(text)
    pos = next((low.find(t) for t in q if low.find(t) >= 0), -1)
    if pos < 0:
        return text[:max_chars] + ("…" if len(text) > max_chars else "")
    start = max(0, pos - 150)
    end = min(len(text), start + max_chars)
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def universal_search(query: str, docs: list[dict], events: list[dict], relays: list[dict], press_articles: pd.DataFrame, public_data: dict, limit: int = 8):
    nq = norm(query)
    qtokens = tokens(query)[:3]
    result = {"Programme & questions": [], "Actualités officielles": [], "Agenda": [], "Relais": [], "Presse": []}

    def matches(hay: str) -> bool:
        return bool(nq) and (all(t in hay for t in qtokens) if qtokens else nq in hay)

    result["Programme & questions"] = search_docs(query, docs, limit)
    for n in (public_data.get("official_news") or []):
        if matches(norm(" ".join(str(n.get(k, "")) for k in ("title", "excerpt", "category")))):
            result["Actualités officielles"].append(n)
    for e in events:
        if matches(norm(" ".join(str(e.get(k, "")) for k in ("title", "location", "description", "address")))):
            result["Agenda"].append(e)
    for r in relays:
        if matches(norm(" ".join(str(r.get(k, "")) for k in ("department_code", "department_name", "name", "email")))):
            result["Relais"].append(r)
    if not press_articles.empty:
        date_col = "DatePublication" if "DatePublication" in press_articles.columns else None
        iterator = press_articles.sort_values(date_col, ascending=False, na_position="last").iterrows() if date_col else press_articles.iterrows()
        for _, r in iterator:
            if matches(norm(" ".join(str(r.get(k, "")) for k in ("Personne", "Media", "Titre")))):
                result["Presse"].append(r.to_dict())
                if len(result["Presse"]) >= limit:
                    break
    for k in result:
        result[k] = result[k][:limit]
    return result


def geocode(q: str):
    if not q:
        return None
    try:
        r = requests.get(
            "https://data.geopf.fr/geocodage/search",
            params={"q": q, "limit": 1},
            headers={"User-Agent": "NE-Hub/4.0"},
            timeout=8,
        )
        r.raise_for_status()
        fs = r.json().get("features", [])
        if not fs:
            return None
        f = fs[0]
        lon, lat = f["geometry"]["coordinates"]
        p = f.get("properties", {})
        return {"lat": lat, "lon": lon, "label": p.get("label", q), "postcode": p.get("postcode"), "city": p.get("city"), "context": p.get("context", "")}
    except Exception:
        return None


def hav(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def dep_from_postcode(cp):
    if not cp:
        return None
    cp = str(cp)
    if cp.startswith(("971", "972", "973", "974", "976")):
        return cp[:3]
    if cp.startswith("20"):
        return "20"
    return cp[:2]


def location_department(loc, relays: list[dict]):
    code = dep_from_postcode(loc.get("postcode")) if loc else None
    name = None
    if loc:
        parts = [x.strip() for x in str(loc.get("context", "") or "").split(",") if x.strip()]
        if len(parts) >= 2:
            name = parts[1]
    if code and not name:
        match = next((r for r in relays if str(r.get("department_code", "")) == code), None)
        if match:
            name = match.get("department_name")
    return code, name


def territory_context(place: str, loc: dict | None = None) -> dict:
    """Contexte administratif public : commune, population, département, région."""
    try:
        params = {"fields": "nom,code,codeDepartement,codeRegion,population,codesPostaux,departement,region", "limit": 1}
        if loc and loc.get("postcode"):
            params["codePostal"] = loc["postcode"]
        else:
            params["nom"] = place
            params["boost"] = "population"
        r = requests.get("https://geo.api.gouv.fr/communes", params=params, timeout=8, headers={"User-Agent": "NE-Hub/4.0"})
        r.raise_for_status()
        arr = r.json()
        if not arr:
            return {}
        c = arr[0]
        return {
            "commune": c.get("nom"),
            "population": c.get("population"),
            "code_insee": c.get("code"),
            "department_code": c.get("codeDepartement") or (c.get("departement") or {}).get("code"),
            "department_name": (c.get("departement") or {}).get("nom"),
            "region_code": c.get("codeRegion") or (c.get("region") or {}).get("code"),
            "region_name": (c.get("region") or {}).get("nom"),
            "source": "geo.api.gouv.fr",
        }
    except Exception:
        return {}


def claude_available() -> bool:
    import shutil

    return shutil.which("claude") is not None


def answer_with_claude(question: str, results: list[dict]):
    if not results or not claude_available():
        return None
    source_chunks = []
    for i, d in enumerate(results[:6], 1):
        source_chunks.append(f"[{i}] {d.get('title')}\nURL: {d.get('url')}\nEXTRAIT:\n{snippet(d.get('text',''), question, 1800)}")
    prompt = f"""Tu réponds à une question documentaire à partir EXCLUSIVEMENT des sources officielles Nouvelle Énergie ci-dessous.
Règles :
- Réponds en français, factuellement et sans ajouter d'information externe.
- Si les sources ne permettent pas de répondre, dis-le clairement.
- N'invente aucun chiffre ni aucune position.
- Cite les sources sous la forme [1], [2].
- 5 à 12 lignes maximum.

QUESTION:
{question}

SOURCES:
{chr(10).join(source_chunks)}
"""
    try:
        cp = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=55, encoding="utf-8", errors="replace")
        return cp.stdout.strip() if cp.returncode == 0 and cp.stdout.strip() else None
    except Exception:
        return None


def movement_stats(public_data: dict) -> dict:
    """Retourne les chiffres du mouvement avec garde-fous anti-valeur aberrante."""
    raw = dict((public_data or {}).get("movement", {}) or {})
    if not raw:
        return {}
    try:
        members = int(raw.get("members")) if raw.get("members") is not None else None
    except Exception:
        members = None
    try:
        elected = int(raw.get("elected")) if raw.get("elected") is not None else None
    except Exception:
        elected = None

    # Filet de sécurité fondé sur la dernière valeur officielle vérifiée au 31/08/2026.
    if members is None or not (1000 <= members <= 2_000_000):
        raw["members"] = 30100
        raw.setdefault("as_of_label", "31 août 2026")
        raw["quality_warning"] = "Valeur adhérents aberrante neutralisée"
    if elected is None or not (1 <= elected <= 600_000):
        raw["elected"] = 1800
        raw.setdefault("as_of_label", "31 août 2026")
        raw["quality_warning"] = "Valeur élus aberrante neutralisée"
    raw.setdefault("source_url", "https://www.unenouvelleenergie.fr/questions/combien-d-adherents-compte-nouvelle-energie/")
    return raw


def data_snapshot_text(social: pd.DataFrame, press_articles: pd.DataFrame, public_data: dict) -> str:
    lines = []
    if not social.empty:
        for p in sorted(social["Personne"].dropna().unique()):
            cur = person_current_row(social, p)
            if cur is None:
                continue
            vals = [f"{p}: total={fmt_int(cur.get('Total'))}"]
            for net in NETWORKS:
                vals.append(f"{net}={fmt_int(cur.get(net))}")
            for d in (1, 7, 30):
                g, pc = change_for_person(social, p, "Total", d)
                vals.append(f"delta_{d}j={fmt_int(g)} ({fmt_pct(pc)})")
            w = wiki_sum(public_data, p, 30)
            if w is not None:
                vals.append(f"wikipedia_30j={fmt_int(w)}")
            lines.append("; ".join(vals))
    p7 = press_counts_from_articles(press_articles, 7)
    if not p7.empty:
        lines.append("PRESSE 7 JOURS:")
        for _, r in p7.iterrows():
            lines.append(f"{r['Personne']}: {int(r['Articles 7j'])} articles; évolution={fmt_pct(r['Évolution %'])}")
    mv = movement_stats(public_data)
    if mv:
        lines.append(f"MOUVEMENT: adherents={mv.get('members')}; elus={mv.get('elected')}; publications={mv.get('official_publications')}")
    return "\n".join(lines)


def ask_data_with_claude(question: str, social: pd.DataFrame, press_articles: pd.DataFrame, public_data: dict):
    if not claude_available():
        return None
    prompt = f"""Tu es le module Ask Data de NE Hub. Réponds UNIQUEMENT à partir des données structurées ci-dessous.
Ces mesures décrivent la visibilité publique (abonnés, articles, vues Wikipédia) et les chiffres officiels du mouvement. Elles ne mesurent pas des intentions de vote.
Si l'historique ne permet pas le calcul demandé, dis-le clairement. Ne déduis aucune causalité.
Réponse française courte, précise, avec chiffres et période.

QUESTION: {question}

DONNEES:
{data_snapshot_text(social, press_articles, public_data)}"""
    try:
        cp = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=45, encoding="utf-8", errors="replace")
        return cp.stdout.strip() if cp.returncode == 0 and cp.stdout.strip() else None
    except Exception:
        return None


def deterministic_ask_data(question: str, social: pd.DataFrame, press_articles: pd.DataFrame, candidates: dict, public_data: dict):
    qn = norm(question)
    names = candidate_names(candidates, social)
    people = detect_people(question, names)
    net = detect_network(question)
    days = detect_days(question)

    if any(w in qn for w in ("adherent", "elus", "mouvement", "publication officielle")):
        mv = movement_stats(public_data)
        if not mv:
            return "Les chiffres officiels du mouvement n'ont pas encore été synchronisés."
        return (
            f"**Nouvelle Énergie** : {fmt_int(mv.get('members'))} adhérents et {fmt_int(mv.get('elected'))} élus recensés selon la dernière source officielle synchronisée. "
            f"Le site affiche également {fmt_int(mv.get('official_publications'))} publications dans l'espace Actualités."
        )

    if "wikipedia" in qn or "wiki" in qn or "recherche web" in qn or "attention web" in qn:
        if people:
            return "\n".join(f"**{p}** : {fmt_int(wiki_sum(public_data, p, days))} vues Wikipédia sur les {days} derniers jours disponibles." for p in people)
        rank = wiki_ranking(public_data, days)
        if rank.empty:
            return "Les données Wikipédia n'ont pas encore été synchronisées."
        return f"**Attention Wikipédia — {days} jours**\n\n" + "\n".join(f"{i+1}. **{r['Personne']}** — {fmt_int(r[f'Vues {days}j'])} vues" for i, (_, r) in enumerate(rank.head(5).iterrows()))

    if any(w in qn for w in ("article", "presse", "media", "mediat")):
        ptab = press_counts_from_articles(press_articles, days)
        if ptab.empty:
            return "Les données presse disponibles ne permettent pas encore cette comparaison."
        if people:
            rows = ptab[ptab["Personne"].isin(people)]
            if rows.empty:
                return "Je n'ai pas de données presse pour la personne demandée sur cette période."
            return "\n".join(
                f"**{r['Personne']}** : {int(r[f'Articles {days}j'])} article(s) détecté(s) sur {days} jour(s), contre {int(r['Période précédente'])} sur la période précédente ({fmt_pct(r['Évolution %'])})."
                for _, r in rows.iterrows()
            )
        top = ptab.head(5)
        return "**Couverture presse détectée — classement**\n\n" + "\n".join(
            f"{i+1}. **{r['Personne']}** — {int(r[f'Articles {days}j'])} article(s) ({fmt_pct(r['Évolution %'])})" for i, (_, r) in enumerate(top.iterrows())
        )

    if social.empty:
        return None

    if "compare" in qn and len(people) >= 2:
        out = []
        for p in people[:4]:
            cur = person_current_row(social, p)
            g, pc = change_for_person(social, p, net, days)
            if net == "Total" and coverage_changed(social, p, days):
                out.append(f"**{p}** — Total : {fmt_int(cur.get(net) if cur is not None else None)} ; comparaison {days}j non classée car le périmètre de réseaux disponibles a changé.")
            else:
                out.append(f"**{p}** — {net} : {fmt_int(cur.get(net) if cur is not None else None)} ; évolution {days}j : {fmt_int(g)} ({fmt_pct(pc)}).")
        return "\n".join(out)

    if any(w in qn for w in ("plus progresse", "progression", "classement", "qui a", "qui progresse", "plus forte")) and not people:
        rank = social_ranking(social, net, days).dropna(subset=["Croissance %"])
        if rank.empty:
            return f"L'historique n'est pas encore assez long pour calculer un classement sur {days} jours."
        return f"**Croissance {net} sur {days} jours**\n\n" + "\n".join(
            f"{i+1}. **{r['Personne']}** : {fmt_int(r['Gain'])} ({fmt_pct(r['Croissance %'])})" for i, (_, r) in enumerate(rank.head(5).iterrows())
        )

    if people:
        out = []
        for p in people[:3]:
            cur = person_current_row(social, p)
            g, pc = change_for_person(social, p, net, days)
            if cur is None:
                continue
            if net == "Total" and coverage_changed(social, p, days):
                out.append(f"**{p}** — Total : {fmt_int(cur.get(net))}. Évolution sur {days} jour(s) non classée : le périmètre de plateformes a changé.")
            else:
                out.append(f"**{p}** — {net} : {fmt_int(cur.get(net))}. Évolution sur {days} jour(s) : {fmt_int(g)} ({fmt_pct(pc)}).")
        if out:
            return "\n".join(out)
    return None
