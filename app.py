from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from impact_simulator import render_impact_simulator

from data_utils import (
    ASSETS,
    BASE,
    CANDIDATES_JSON,
    PRESS_XLSX,
    PUBLIC_DATA_JSON,
    SOCIAL_XLSX,
    NETWORKS,
    answer_with_claude,
    ask_data_with_claude,
    candidate_names,
    change_for_person,
    claude_available,
    coverage_changed,
    current_social_table,
    deterministic_ask_data,
    fmt_date,
    fmt_int,
    fmt_pct,
    geocode,
    hav,
    latest_topics,
    load_public_data,
    load_site_data,
    load_tracker_data,
    location_department,
    movement_stats,
    norm,
    parse_date,
    person_current_row,
    press_counts_from_articles,
    press_daily_series,
    quality_table,
    search_docs,
    snippet,
    social_base100,
    social_current_date,
    social_ranking,
    social_history_days,
    tracker_diagnostics,
    territory_context,
    universal_search,
    wiki_ranking,
    wiki_series_df,
    wiki_sum,
)

# -----------------------------------------------------------------------------
# Configuration / marque
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="NE Hub — Nouvelle Énergie",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

NE_BLUE = "#032F67"
NE_BLUE_2 = "#0B4A8B"
NE_OLIVE = "#9A9D75"
NE_OLIVE_LIGHT = "#EDEEE5"
NE_INK = "#111827"
NE_MUTED = "#667085"
NE_SOFT = "#F5F7FA"
NE_LINE = "#E5E7EB"
NE_ACCENT = "#C33B72"
GOOD = "#17745A"
WARN = "#B7791F"
BAD = "#B42318"

st.markdown(
    f"""
<style>
:root {{
  --ne-blue:{NE_BLUE}; --ne-blue-2:{NE_BLUE_2}; --ne-olive:{NE_OLIVE}; --ne-olive-light:{NE_OLIVE_LIGHT};
  --ne-ink:{NE_INK}; --ne-muted:{NE_MUTED}; --ne-soft:{NE_SOFT}; --ne-line:{NE_LINE}; --ne-accent:{NE_ACCENT};
}}
html, body, [class*="css"] {{ font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Arial, sans-serif; }}
.block-container {{ max-width: 1380px; padding-top: 1.2rem; padding-bottom: 4rem; }}
[data-testid="stSidebar"] {{ background:#fff; border-right:1px solid var(--ne-line); }}
[data-testid="stSidebar"] > div:first-child {{ padding-top:1rem; }}
[data-testid="stSidebar"] hr {{ border-color:var(--ne-line); }}
[data-testid="stSidebar"] [role="radiogroup"] label {{
  border-radius:12px; padding:.32rem .45rem; margin:.05rem 0; transition:background .15s ease;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background:var(--ne-soft); }}
[data-testid="stMetric"] {{ background:#fff; border:1px solid var(--ne-line); border-radius:18px; padding:.9rem 1rem; box-shadow:0 1px 2px rgba(16,24,40,.03); }}
[data-testid="stMetricLabel"] {{ color:var(--ne-muted); font-weight:650; }}
[data-testid="stMetricValue"] {{ color:var(--ne-blue); font-size:1.55rem; font-weight:850; }}
[data-testid="stMetricDelta"] {{ font-weight:700; }}
.stButton button, .stLinkButton a {{ border-radius:12px !important; font-weight:700 !important; }}
.ne-brand-wrap {{ display:flex; align-items:center; gap:.8rem; padding:.4rem .1rem .9rem; }}
.ne-brand-label {{ color:var(--ne-blue); font-weight:900; letter-spacing:.04em; line-height:1.05; font-size:1.05rem; }}
.ne-brand-label small {{ display:block; color:var(--ne-olive); font-size:.58rem; letter-spacing:.14em; margin-top:.18rem; }}
.ne-hero {{
  position:relative; overflow:hidden; border-radius:26px; padding:2.4rem 2.5rem; margin:.1rem 0 1.25rem;
  background:linear-gradient(120deg,#022956 0%,var(--ne-blue) 58%,#0a4a86 100%); color:white;
  box-shadow:0 18px 48px rgba(3,47,103,.16); min-height:230px;
}}
.ne-hero:after {{ content:""; position:absolute; width:350px; height:350px; right:-135px; top:-125px; border:2px solid rgba(154,157,117,.52); transform:rotate(31deg); border-radius:56px; }}
.ne-hero:before {{ content:""; position:absolute; width:240px; height:240px; right:95px; bottom:-190px; border:2px solid rgba(255,255,255,.10); transform:rotate(31deg); border-radius:42px; }}
.ne-kicker {{ position:relative; z-index:1; font-size:.74rem; text-transform:uppercase; letter-spacing:.16em; font-weight:800; opacity:.82; }}
.ne-title {{ position:relative; z-index:1; max-width:880px; font-size:2.75rem; font-weight:900; line-height:1.03; margin:.55rem 0 .7rem; letter-spacing:-.035em; }}
.ne-sub {{ position:relative; z-index:1; max-width:880px; font-size:1.02rem; line-height:1.55; opacity:.9; }}
.ne-badges {{ position:relative; z-index:1; display:flex; flex-wrap:wrap; gap:.45rem; margin-top:1.1rem; }}
.ne-badge {{ border:1px solid rgba(255,255,255,.24); background:rgba(255,255,255,.07); border-radius:999px; padding:.3rem .65rem; font-size:.78rem; font-weight:700; }}
.ne-section {{ margin-top:.7rem; margin-bottom:.55rem; }}
.ne-section .eyebrow {{ color:var(--ne-accent); font-size:.74rem; text-transform:uppercase; letter-spacing:.13em; font-weight:900; }}
.ne-section h2 {{ color:var(--ne-blue); font-size:1.55rem; margin:.15rem 0 .12rem; letter-spacing:-.02em; }}
.ne-section p {{ color:var(--ne-muted); margin:.1rem 0 0; font-size:.93rem; }}
.ne-card {{ border:1px solid var(--ne-line); background:#fff; border-radius:18px; padding:1rem 1.05rem; height:100%; box-shadow:0 1px 2px rgba(16,24,40,.025); }}
.ne-card h4 {{ color:var(--ne-blue); margin:.05rem 0 .3rem; font-size:1rem; }}
.ne-card p {{ color:var(--ne-muted); margin:.1rem 0; line-height:1.45; font-size:.89rem; }}
.ne-card .meta {{ color:var(--ne-muted); font-size:.76rem; margin-top:.5rem; }}
.ne-callout {{ border-left:4px solid var(--ne-olive); background:#fbfbf7; border-radius:0 14px 14px 0; padding:.75rem .9rem; color:#4f5140; }}
.ne-alert {{ border-left:4px solid var(--ne-accent); background:#fff8fb; border-radius:0 14px 14px 0; padding:.75rem .9rem; color:#5a2740; }}
.ne-profile {{ display:flex; gap:.9rem; align-items:center; margin:.2rem 0 1rem; }}
.ne-avatar {{ width:54px; height:54px; border-radius:16px; display:flex; align-items:center; justify-content:center; background:var(--ne-blue); color:#fff; font-weight:900; font-size:1.05rem; letter-spacing:.04em; }}
.ne-profile h3 {{ margin:0; color:var(--ne-blue); font-size:1.35rem; }}
.ne-profile p {{ margin:.15rem 0 0; color:var(--ne-muted); font-size:.86rem; }}
.ne-chip {{ display:inline-block; padding:.2rem .5rem; margin:.12rem .16rem .12rem 0; border:1px solid var(--ne-line); border-radius:999px; background:var(--ne-soft); color:var(--ne-blue); font-size:.75rem; font-weight:700; }}
.ne-kpi {{ border-top:3px solid var(--ne-blue); background:#fff; border-radius:15px; padding:.8rem .9rem; border-left:1px solid var(--ne-line); border-right:1px solid var(--ne-line); border-bottom:1px solid var(--ne-line); }}
.ne-kpi .label {{ color:var(--ne-muted); font-size:.75rem; font-weight:700; }}
.ne-kpi .value {{ color:var(--ne-blue); font-size:1.35rem; font-weight:900; margin:.12rem 0; }}
.ne-kpi .sub {{ color:var(--ne-muted); font-size:.73rem; }}
.ne-fresh {{ font-size:.75rem; color:var(--ne-muted); border:1px solid var(--ne-line); background:var(--ne-soft); border-radius:999px; padding:.28rem .58rem; display:inline-block; margin:.1rem .25rem .1rem 0; }}
.ne-source {{ color:var(--ne-muted); font-size:.77rem; }}
.ne-footer {{ color:var(--ne-muted); font-size:.78rem; padding-top:.6rem; }}
.ne-search-box {{ border:1px solid var(--ne-line); background:linear-gradient(180deg,#fff,#fbfcfd); padding:1.05rem 1.1rem; border-radius:18px; }}
.ne-rank {{ display:flex; gap:.65rem; align-items:center; padding:.55rem 0; border-bottom:1px solid var(--ne-line); }}
.ne-rank:last-child {{ border-bottom:none; }}
.ne-rank .rank {{ width:1.75rem; height:1.75rem; border-radius:9px; display:flex; align-items:center; justify-content:center; background:var(--ne-soft); color:var(--ne-blue); font-weight:900; font-size:.8rem; }}
.ne-rank .who {{ color:var(--ne-ink); font-weight:750; flex:1; }}
.ne-rank .value {{ color:var(--ne-blue); font-weight:900; }}
[data-baseweb="tab-list"] {{ gap:.2rem; }}
[data-baseweb="tab"] {{ border-radius:999px; padding:.35rem .75rem; }}
@media(max-width:760px) {{
 .ne-hero {{ padding:1.35rem 1rem; min-height:0; border-radius:20px; }} .ne-title {{ font-size:1.8rem; line-height:1.08; }}
 .ne-sub {{ font-size:.92rem; }} .ne-badges {{ gap:.3rem; }} .ne-badge {{ font-size:.68rem; padding:.22rem .45rem; }}
 .block-container {{ padding-left:.65rem; padding-right:.65rem; padding-top:.55rem; }}
 [data-testid="stMetric"] {{ padding:.72rem .75rem; border-radius:14px; }}
 [data-testid="stMetricValue"] {{ font-size:1.28rem; }}
 .ne-section h2 {{ font-size:1.3rem; }}
 [data-baseweb="tab-list"] {{ overflow-x:auto; flex-wrap:nowrap; }}
 [data-baseweb="tab"] {{ white-space:nowrap; }}
}}
.ne-today {{ border:1px solid var(--ne-line); border-radius:22px; padding:1rem 1.1rem; background:linear-gradient(180deg,#fff,#fbfcfd); margin:.65rem 0 1.05rem; }}
.ne-today-title {{ display:flex; align-items:center; justify-content:space-between; gap:.6rem; flex-wrap:wrap; margin-bottom:.6rem; }}
.ne-today-title h3 {{ margin:0; color:var(--ne-blue); font-size:1.15rem; }}
.ne-fresh.good {{ background:#ECFDF3; border-color:#ABEFC6; color:#067647; }}
.ne-fresh.warn {{ background:#FFFAEB; border-color:#FEDF89; color:#B54708; }}
.ne-quick {{ border:1px solid var(--ne-line); border-radius:16px; padding:.8rem .85rem; background:#fff; min-height:110px; }}
.ne-quick b {{ color:var(--ne-blue); }}
.ne-quick p {{ margin:.25rem 0 0; color:var(--ne-muted); font-size:.83rem; line-height:1.35; }}
</style>
""",
    unsafe_allow_html=True,
)


def get_setting(name: str, default=None):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)


def public_mode() -> bool:
    # prepare_public.py crée ce flag dans la copie destinée au web.
    if (BASE / "public_mode.flag").exists():
        return True
    return str(get_setting("NE_HUB_PUBLIC_MODE", "0")).lower().strip() in ("1", "true", "yes", "oui")


def admin_authorized() -> bool:
    pwd = str(get_setting("NE_HUB_ADMIN_PASSWORD", "") or "")
    if not pwd:
        return not public_mode()
    return st.session_state.get("ne_admin_password", "") == pwd


def brand_logo_path() -> Path | None:
    from PIL import Image

    for name in ("logo.png", "logo.webp", "logo.jpg", "logo.jpeg"):
        p = ASSETS / name
        if not p.exists():
            continue
        try:
            with Image.open(p) as im:
                im.verify()
            return p
        except Exception:
            continue
    return None


def initials(name: str) -> str:
    return "".join([p[0] for p in str(name).split()[:2]]).upper() or "NE"


def section(eyebrow: str, title: str, subtitle: str = ""):
    st.markdown(
        f'<div class="ne-section"><div class="eyebrow">{eyebrow}</div><h2>{title}</h2><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def hero():
    st.markdown(
        """
<div class="ne-hero">
  <div class="ne-kicker">NE HUB · INFORMATIONS PUBLIQUES · DONNÉES SOURCÉES</div>
  <div class="ne-title">Comprendre les propositions. Voir les données. Mesurer les ordres de grandeur.</div>
  <div class="ne-sub">Programme, simulateur d’impact, observatoire de visibilité publique, agenda et relais locaux réunis dans une interface simple. Les calculs affichent leurs hypothèses et leurs sources.</div>
  <div class="ne-badges"><span class="ne-badge">⚡ 30 secondes</span><span class="ne-badge">🧮 Simulateur</span><span class="ne-badge">📊 Observatoire</span><span class="ne-badge">🔎 Recherche globale</span><span class="ne-badge">📍 Territoires</span></div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_sidebar(meta: dict, public_data: dict):
    logo = brand_logo_path()
    if logo:
        st.image(str(logo), width=155)
    else:
        st.markdown('<div class="ne-brand-label">NOUVELLE<br>ÉNERGIE<small>POUR LA FRANCE</small></div>', unsafe_allow_html=True)
    st.caption("NE Hub · portail documentaire et observatoire")
    st.divider()
    nav_items = ["🏠 Accueil", "📊 Observatoire", "🧮 Simulateur d’impact", "🤖 Ask Data", "🔎 Explorer", "🧭 Mon département", "🗓️ Agenda", "💬 Ask NE", "🧰 Ressources"]
    if not public_mode():
        nav_items.append("⚙️ Administration")
    requested_page = str(st.query_params.get("page", "") or "").lower()
    page_map = {
        "simulateur": "🧮 Simulateur d’impact", "simulator": "🧮 Simulateur d’impact", "impact": "🧮 Simulateur d’impact",
        "observatoire": "📊 Observatoire", "observer": "📊 Observatoire",
        "explorer": "🔎 Explorer", "recherche": "🔎 Explorer",
        "departement": "🧭 Mon département", "territoire": "🧭 Mon département",
        "agenda": "🗓️ Agenda", "askne": "💬 Ask NE", "askdata": "🤖 Ask Data",
    }
    requested_nav = page_map.get(requested_page)
    default_index = nav_items.index(requested_nav) if requested_nav in nav_items else 0
    nav = st.radio(
        "Navigation",
        nav_items,
        index=default_index,
        label_visibility="collapsed",
    )
    if public_mode():
        st.caption("🔒 Version publique · lecture seule")
    st.divider()
    last_site = meta.get("last_sync", "—")
    last_public = public_data.get("last_sync", "—")
    st.markdown("**Fraîcheur des données**")
    st.caption(f"Site officiel : {last_site}")
    st.caption(f"Données ouvertes : {last_public}")
    if SOCIAL_XLSX.exists():
        st.caption(f"Réseaux : {datetime.fromtimestamp(SOCIAL_XLSX.stat().st_mtime).strftime('%d/%m %H:%M')}")
    if PRESS_XLSX.exists():
        st.caption(f"Presse : {datetime.fromtimestamp(PRESS_XLSX.stat().st_mtime).strftime('%d/%m %H:%M')}")
    st.divider()
    st.markdown("**Sources de référence**")
    st.markdown("[🌐 Site officiel](https://www.unenouvelleenergie.fr/)  \n[📚 Programme](https://www.unenouvelleenergie.fr/notre-programme/)  \n[📍 Agenda](https://www.unenouvelleenergie.fr/agenda/)  \n[👥 Relais](https://www.unenouvelleenergie.fr/decouvrir-notre-parti/les-relais/)")
    return nav


def compact_plot(fig, height=380):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=45, b=15),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", color=NE_INK),
        legend_title_text="",
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(gridcolor="#EFF1F5", linecolor="#E5E7EB")
    fig.update_yaxes(gridcolor="#EFF1F5", linecolor="#E5E7EB")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_search_results(results: dict):
    total = sum(len(v) for v in results.values())
    if not total:
        st.info("Aucun résultat suffisamment proche dans les sources indexées.")
        return
    for category, vals in results.items():
        if not vals:
            continue
        st.markdown(f"#### {category} · {len(vals)}")
        for item in vals[:6]:
            with st.container(border=True):
                if category == "Programme & questions":
                    st.markdown(f"**{item.get('title','Source')}**")
                    st.write(snippet(item.get("text", ""), st.session_state.get("global_query", ""), 360))
                    st.markdown(f"[Ouvrir la source officielle]({item.get('url')})")
                elif category == "Actualités officielles":
                    st.markdown(f"**{item.get('title','Actualité')}**")
                    st.caption(item.get("date", ""))
                    st.markdown(f"[Lire sur le site officiel]({item.get('url')})")
                elif category == "Agenda":
                    st.markdown(f"**{item.get('title','Événement')}**")
                    st.caption(f"{item.get('date_label') or item.get('date','')} · {item.get('location','')}")
                    st.markdown(f"[Voir le rendez-vous]({item.get('url')})")
                elif category == "Relais":
                    st.markdown(f"**{item.get('department_name','')} — {item.get('name','Relais')}**")
                    if item.get("email"):
                        st.markdown(f"[{item['email']}](mailto:{item['email']})")
                    if item.get("source_url"):
                        st.markdown(f"[Source officielle]({item['source_url']})")
                else:
                    st.markdown(f"**{item.get('Titre','Article')}**")
                    st.caption(f"{item.get('Personne','')} · {item.get('Media','')} · {fmt_date(item.get('DatePublication'))}")
                    if item.get("URL"):
                        st.markdown(f"[Lire l'article]({item['URL']})")


def _freshness_info(path: Path, label: str) -> tuple[str, str]:
    if not path.exists():
        return f"{label} : indisponible", "warn"
    dt = datetime.fromtimestamp(path.stat().st_mtime)
    age_h = max(0.0, (datetime.now() - dt).total_seconds() / 3600.0)
    state = "good" if age_h <= 36 else "warn"
    return f"{label} : {dt.strftime('%d/%m %H:%M')}", state


def render_freshness_strip(meta: dict, public_data: dict):
    items = []
    social_label, social_state = _freshness_info(SOCIAL_XLSX, "Réseaux")
    press_label, press_state = _freshness_info(PRESS_XLSX, "Presse")
    items.append((social_label, social_state))
    items.append((press_label, press_state))
    site = meta.get("last_sync") or "non synchronisé"
    pub = public_data.get("last_sync") or "non synchronisé"
    items.append((f"Site officiel : {site}", "good" if meta.get("last_sync") else "warn"))
    items.append((f"Données ouvertes : {pub}", "good" if public_data.get("last_sync") else "warn"))
    html_items = "".join(f'<span class="ne-fresh {state}">{text}</span>' for text, state in items)
    st.markdown(html_items, unsafe_allow_html=True)


def render_today_30_seconds():
    focus = "David Lisnard" if (not social_df.empty and "David Lisnard" in set(social_df["Personne"])) else (social_df["Personne"].iloc[0] if not social_df.empty else None)
    future = sorted([e for e in events if (parse_date(e.get("date")) or date.min) >= date.today()], key=lambda x: parse_date(x.get("date")) or date.max)
    news = public_data.get("official_news", []) or []
    trend7 = None
    press7n = None
    if focus:
        _, trend7 = change_for_person(social_df, focus, "Total", 7)
        p7 = press_counts_from_articles(press_articles_df, 7)
        row = p7[p7["Personne"] == focus] if not p7.empty else pd.DataFrame()
        press7n = int(row.iloc[0]["Articles 7j"]) if not row.empty else 0
    st.markdown('<div class="ne-today"><div class="ne-today-title"><h3>⚡ Aujourd’hui en 30 secondes</h3><span class="ne-source">Les signaux essentiels, sans interprétation électorale.</span></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tendance réseaux · 7 j", fmt_pct(trend7) if trend7 is not None else "—")
    c2.metric("Articles détectés · 7 j", press7n if press7n is not None else "—")
    if news:
        c3.markdown(f"**Dernière publication**  \n{news[0].get('title','Actualité')[:85]}")
        if news[0].get("url"):
            c3.markdown(f"[Lire la source]({news[0]['url']})")
    else:
        c3.markdown("**Dernière publication**  \n—")
    if future:
        c4.markdown(f"**Prochain rendez-vous**  \n{future[0].get('title','Événement')[:75]}")
        c4.caption(f"{future[0].get('date_label') or future[0].get('date','')} · {future[0].get('location','')}")
    else:
        c4.markdown("**Prochain rendez-vous**  \n—")
    st.markdown('</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Chargement des données
# -----------------------------------------------------------------------------

docs, events, relays, meta = load_site_data()
public_data = load_public_data()
social_df, press_articles_df, press_comparison_df, press_topics_df, tracked_candidates, tracker_errors = load_tracker_data()
with st.sidebar:
    nav = render_sidebar(meta, public_data)

# -----------------------------------------------------------------------------
# ACCUEIL
# -----------------------------------------------------------------------------

if nav == "🏠 Accueil":
    hero()
    render_freshness_strip(meta, public_data)
    render_today_30_seconds()

    mv = movement_stats(public_data)
    future_events = [e for e in events if (parse_date(e.get("date")) or date.min) >= date.today()]
    section("Vue d’ensemble", "Les repères utiles", "Quelques chiffres de contexte avant d’explorer le programme et les données.")
    cols = st.columns(4)
    cols[0].metric("Adhérents", fmt_int(mv.get("members")) if mv else "—")
    cols[1].metric("Élus recensés", fmt_int(mv.get("elected")) if mv else "—")
    cols[2].metric("Rendez-vous à venir", len(future_events))
    cols[3].metric("Publications officielles", fmt_int(mv.get("official_publications")) if mv else "—")
    if mv:
        as_of = mv.get("as_of_label") or "date non disponible"
        source_url = mv.get("source_url") or "https://www.unenouvelleenergie.fr/questions/combien-d-adherents-compte-nouvelle-energie/"
        st.caption(f"Chiffres du mouvement au {as_of} · [source officielle]({source_url}).")

    section("Recherche", "Trouver une information en une seule requête", "Programme, questions officielles, actualités, agenda, relais et presse détectée.")
    q = st.text_input("Recherche globale", key="home_global_query", placeholder="Ex. retraites, nucléaire, dette, Tours, David Lisnard…", label_visibility="collapsed")
    if q:
        st.session_state["global_query"] = q
        render_search_results(universal_search(q, docs, events, relays, press_articles_df, public_data, 6))

    section("Accès rapide", "Aller directement à l’essentiel", "Des parcours courts pour ne pas avoir à connaître la structure du site.")
    qcols = st.columns(4)
    qcols[0].markdown('<a href="?page=simulateur" target="_self" style="text-decoration:none"><div class="ne-quick"><b>🧮 Simulateur d’impact →</b><p>Voir l’effet mécanique des mesures chiffrées sur déficit, prélèvements et niveau de vie.</p></div></a>', unsafe_allow_html=True)
    qcols[1].markdown('<a href="?page=observatoire" target="_self" style="text-decoration:none"><div class="ne-quick"><b>📊 Observatoire →</b><p>Réseaux, presse et attention web, avec fraîcheur et qualité des données.</p></div></a>', unsafe_allow_html=True)
    qcols[2].markdown('<a href="?page=explorer" target="_self" style="text-decoration:none"><div class="ne-quick"><b>🔎 Explorer →</b><p>Rechercher dans toutes les sources officielles et les données indexées.</p></div></a>', unsafe_allow_html=True)
    qcols[3].markdown('<a href="?page=departement" target="_self" style="text-decoration:none"><div class="ne-quick"><b>📍 Mon département →</b><p>Relais local, contexte territorial et rendez-vous autour d’une commune.</p></div></a>', unsafe_allow_html=True)

    left, right = st.columns([1.15, 1])
    with left:
        section("À la une", "Dernières publications officielles", "Synchronisées depuis le site Nouvelle Énergie.")
        news = public_data.get("official_news", []) or []
        if news:
            for item in news[:4]:
                st.markdown(f"**{item.get('title','Actualité')}**")
                st.caption(item.get("date", ""))
                if item.get("url"):
                    st.markdown(f"[Lire sur le site officiel]({item.get('url')})")
                st.divider()
        else:
            st.info("Aucune actualité officielle synchronisée.")
    with right:
        section("Agenda", "Prochains rendez-vous", "Les prochains événements détectés sur l'agenda officiel.")
        for e in sorted(future_events, key=lambda x: parse_date(x.get("date")) or date.max)[:4]:
            st.markdown(f"**{e.get('title','Événement')}**")
            st.caption(f"{e.get('date_label') or e.get('date','')} · {e.get('location','')}")
            if e.get("url"):
                st.markdown(f"[Voir le rendez-vous]({e['url']})")
            st.divider()

# -----------------------------------------------------------------------------
# OBSERVATOIRE
# -----------------------------------------------------------------------------
elif nav == "📊 Observatoire":
    section("Observatoire", "Visibilité publique comparée", "Trois signaux complémentaires : réseaux sociaux, presse détectée et attention Wikipédia. Aucun de ces indicateurs ne mesure une intention de vote.")
    render_freshness_strip(meta, public_data)
    if tracker_errors:
        for err in tracker_errors:
            st.warning(err)

    tabs = st.tabs(["Vue d'ensemble", "Réseaux", "Presse", "Attention web", "Fiches", "Qualité des données"])

    with tabs[0]:
        if social_df.empty:
            st.error("Le Hub ne trouve pas le classeur de suivi réseaux. Ce n'est pas un problème de calcul : c'est un problème de chemin ou de fichier indisponible.")
            diag = tracker_diagnostics()
            st.code(f"Dossier recherché : {diag['tracker_dir']}\nRéseaux : {diag['social_path']} — {'OK' if diag['social_exists'] else 'INTROUVABLE'}\nPresse : {diag['press_path']} — {'OK' if diag['press_exists'] else 'INTROUVABLE'}")
            st.caption("Le dossier peut s'appeler SuiviLisnard, Suivi Lisnard ou une variante courante : la V4.1 tente désormais de le retrouver automatiquement.")
        else:
            hist_days = social_history_days(social_df)
            if hist_days < 8:
                st.markdown(f'<div class="ne-alert">Historique réseaux encore très court : <b>{hist_days} jour(s) de relevé</b>. Le 24 h fonctionne, mais les comparaisons 7 j et 30 j deviendront disponibles automatiquement après accumulation des relevés.</div>', unsafe_allow_html=True)
            people = candidate_names(tracked_candidates, social_df)
            focus = st.selectbox("Personnalité mise en avant", people, index=people.index("David Lisnard") if "David Lisnard" in people else 0)
            cur = person_current_row(social_df, focus)
            g1, p1 = change_for_person(social_df, focus, "Total", 1)
            g7, p7 = change_for_person(social_df, focus, "Total", 7)
            press7 = press_counts_from_articles(press_articles_df, 7)
            pr = press7[press7["Personne"] == focus] if not press7.empty else pd.DataFrame()
            wiki30 = wiki_sum(public_data, focus, 30)

            st.markdown(f'<div class="ne-profile"><div class="ne-avatar">{initials(focus)}</div><div><h3>{focus}</h3><p>Dernier relevé réseaux : {fmt_date(cur.get("Date") if cur is not None else None)}</p></div></div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Abonnements*", fmt_int(cur.get("Total") if cur is not None else None), delta=fmt_int(g1) if g1 is not None else None)
            c2.metric("Croissance 7 j", fmt_pct(p7) if p7 is not None else "—")
            c3.metric("Presse · 7 j", int(pr.iloc[0]["Articles 7j"]) if not pr.empty else 0)
            c4.metric("Wikipédia · 30 j", fmt_int(wiki30))
            if coverage_changed(social_df, focus, 7):
                st.markdown('<div class="ne-alert">Le périmètre de plateformes disponibles a changé : la variation du total n’est volontairement pas classée sur cette période.</div>', unsafe_allow_html=True)
            st.caption("* Somme des compteurs disponibles par plateforme, sans déduplication des personnes.")

            l, r = st.columns(2)
            with l:
                rank = social_ranking(social_df, "Total", 1).dropna(subset=["Croissance %"])
                st.markdown("#### Croissance réseaux · 24 h")
                if rank.empty:
                    st.caption("Historique insuffisant.")
                else:
                    for i, (_, row) in enumerate(rank.head(6).iterrows()):
                        st.markdown(f'<div class="ne-rank"><div class="rank">{i+1}</div><div class="who">{row["Personne"]}</div><div class="value">{fmt_pct(row["Croissance %"])}</div></div>', unsafe_allow_html=True)
            with r:
                pr = press_counts_from_articles(press_articles_df, 7)
                st.markdown("#### Articles détectés · 7 jours")
                if pr.empty:
                    st.caption("Aucune donnée presse.")
                else:
                    for i, (_, row) in enumerate(pr.head(6).iterrows()):
                        st.markdown(f'<div class="ne-rank"><div class="rank">{i+1}</div><div class="who">{row["Personne"]}</div><div class="value">{int(row["Articles 7j"])}</div></div>', unsafe_allow_html=True)

    with tabs[1]:
        if social_df.empty:
            st.info("Aucune donnée réseaux disponible.")
        else:
            c1, c2, c3 = st.columns([1, 1, 1])
            network = c1.selectbox("Réseau", ["Total", *NETWORKS], index=0)
            period = c2.selectbox("Période", [1, 7, 30, 90], format_func=lambda x: "24 h" if x == 1 else f"{x} jours")
            nprof = int(social_df["Personne"].nunique())
            min_prof = 1 if nprof < 5 else 5
            topn = c3.slider("Nombre de profils", min_prof, max(min_prof, min(10, nprof)), min(max(min_prof, 8), max(min_prof, min(10, nprof))))
            rank = social_ranking(social_df, network, period).head(topn)
            if not rank.empty:
                disp = rank.copy()
                disp["Actuel"] = disp["Actuel"].map(fmt_int)
                disp["Gain"] = disp["Gain"].map(fmt_int)
                disp["Croissance %"] = disp["Croissance %"].map(fmt_pct)
                st.dataframe(disp, use_container_width=True, hide_index=True)
            base = social_base100(social_df, network)
            if not base.empty and base["Date"].nunique() >= 2:
                fig = px.line(base, x="Date", y="Indice", color="Personne", markers=True, title=f"Évolution {network} — base 100 au premier relevé")
                fig.add_hline(y=100, line_dash="dot", line_color="#9CA3AF")
                compact_plot(fig, 420)
            else:
                st.info("Il faut au moins deux relevés pour afficher une courbe de tendance.")

            st.markdown("#### Derniers compteurs")
            curtab = current_social_table(social_df)
            if not curtab.empty:
                show = curtab.copy()
                for col in [*NETWORKS, "Total"]:
                    show[col] = show[col].map(fmt_int)
                st.dataframe(show, use_container_width=True, hide_index=True)

    with tabs[2]:
        language = st.selectbox("Langue", ["Toutes", "Français"], index=0)
        period = st.selectbox("Fenêtre d'analyse", [7, 30, 60], index=1, format_func=lambda x: f"{x} jours")
        pr = press_counts_from_articles(press_articles_df, period, language)
        if pr.empty:
            st.info("Pas de données presse pour ce filtre.")
        else:
            fig = px.bar(pr.head(10), x="Personne", y=f"Articles {period}j", title=f"Articles détectés sur {period} jours")
            compact_plot(fig, 390)
            st.caption("Le radar compte des articles détectés par sa source ; il ne représente pas l'intégralité de la presse et peut contenir des faux positifs/homonymes.")
        daily = press_daily_series(press_articles_df, days=min(period, 60), language=language)
        if not daily.empty:
            fig = px.line(daily, x="Date", y="Articles", color="Personne", markers=True, title="Volume quotidien détecté")
            compact_plot(fig, 430)

        st.markdown("#### Sujets les plus récents")
        topics = latest_topics(press_topics_df)
        if topics.empty:
            st.caption("Aucune synthèse de sujets disponible.")
        else:
            cols = [c for c in ["Personne", "Rang", "Sujet", "NombreArticles", "Resume"] if c in topics.columns]
            st.dataframe(topics[cols], use_container_width=True, hide_index=True)

    with tabs[3]:
        st.markdown('<div class="ne-callout">Les vues Wikipédia donnent un signal indépendant d’intérêt informationnel. Elles ne disent ni pourquoi la page a été consultée, ni ce que pense le lecteur.</div>', unsafe_allow_html=True)
        period = st.selectbox("Période Wikipédia", [7, 30, 90], index=1, format_func=lambda x: f"{x} jours")
        wr = wiki_ranking(public_data, period)
        if wr.empty:
            st.info("Les données Wikipédia ne sont pas encore disponibles. Elles sont indépendantes du tracker réseaux/presse.")
            if not public_mode():
                if st.button("↻ Charger les données Wikipédia maintenant", key="wiki_sync_now"):
                    with st.spinner("Récupération des vues Wikipédia…"):
                        try:
                            cp = subprocess.run([sys.executable, str(BASE / "sync_public_data.py")], capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
                            if cp.returncode == 0:
                                st.success("Données publiques synchronisées.")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(cp.stderr[-1200:] or cp.stdout[-1200:] or "Échec de synchronisation Wikimedia.")
                        except Exception as ex:
                            st.error(f"Synchronisation impossible : {ex}")
            else:
                st.caption("La version publique est en lecture seule ; ces données seront mises à jour lors de la prochaine publication.")
            st.caption("Si Wikimedia est momentanément indisponible, le reste de l'Observatoire continue de fonctionner.")
        else:
            fig = px.bar(wr.head(10), x="Personne", y=f"Vues {period}j", title=f"Vues des pages Wikipédia françaises — {period} jours")
            compact_plot(fig, 400)
            ws = wiki_series_df(public_data, wr.head(6)["Personne"].tolist(), min(period, 90))
            if not ws.empty:
                fig = px.line(ws, x="Date", y="Vues", color="Personne", title="Évolution quotidienne des consultations")
                compact_plot(fig, 430)
            src = (public_data.get("wikipedia") or {}).get("source_url")
            if src:
                st.caption(f"Source : Wikimedia Pageviews API · {src}")

    with tabs[4]:
        names = candidate_names(tracked_candidates, social_df)
        if not names:
            st.info("Aucune personnalité configurée.")
        else:
            person = st.selectbox("Choisir une personnalité", names, index=names.index("David Lisnard") if "David Lisnard" in names else 0, key="profile_person")
            cur = person_current_row(social_df, person)
            st.markdown(f'<div class="ne-profile"><div class="ne-avatar">{initials(person)}</div><div><h3>{person}</h3><p>Fiche descriptive issue des données publiques collectées</p></div></div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Abonnements*", fmt_int(cur.get("Total") if cur is not None else None))
            g1, p1 = change_for_person(social_df, person, "Total", 1)
            c2.metric("24 h", fmt_pct(p1) if p1 is not None else "—", delta=fmt_int(g1) if g1 is not None else None)
            p30 = press_counts_from_articles(press_articles_df, 30)
            prow = p30[p30["Personne"] == person] if not p30.empty else pd.DataFrame()
            c3.metric("Presse · 30 j", int(prow.iloc[0]["Articles 30j"]) if not prow.empty else 0)
            c4.metric("Wikipédia · 30 j", fmt_int(wiki_sum(public_data, person, 30)))
            st.caption("* Somme des compteurs des plateformes disponibles.")

            if cur is not None:
                nets = pd.DataFrame({"Réseau": list(NETWORKS), "Abonnés": [cur.get(n) for n in NETWORKS]}).dropna()
                if not nets.empty:
                    fig = px.bar(nets, x="Réseau", y="Abonnés", title="Répartition des compteurs publics")
                    compact_plot(fig, 360)
            topics = latest_topics(press_topics_df, person)
            if not topics.empty:
                st.markdown("#### Principaux sujets presse détectés")
                for _, row in topics.head(5).iterrows():
                    st.markdown(f"- **{row.get('Sujet','Sujet')}** — {fmt_int(row.get('NombreArticles'))} article(s)")
                first_resume = topics["Resume"].dropna().astype(str).iloc[0] if "Resume" in topics.columns and topics["Resume"].notna().any() else None
                if first_resume:
                    st.caption(first_resume)
            links = tracked_candidates.get(person, {}) if isinstance(tracked_candidates, dict) else {}
            if links:
                st.markdown("#### Profils configurés")
                cols = st.columns(4)
                for idx, (key, url) in enumerate(links.items()):
                    if url:
                        cols[idx % 4].link_button(key.capitalize(), url, use_container_width=True)

    with tabs[5]:
        st.markdown('<div class="ne-callout">NE Hub préfère afficher “—” plutôt qu’un chiffre trompeur. Les variations du total sont neutralisées si le nombre de plateformes disponibles change entre deux relevés.</div>', unsafe_allow_html=True)
        qt = quality_table(social_df, press_topics_df)
        if not qt.empty:
            st.dataframe(qt, use_container_width=True, hide_index=True)
        st.markdown("#### Règles de lecture")
        st.markdown("- **Total réseaux** : somme des compteurs disponibles, jamais un nombre de personnes uniques.\n- **Périmètre changé** : une plateforme vient d’apparaître/disparaître ; la variation du total est neutralisée.\n- **Presse** : volume détecté par le radar, susceptible de faux positifs ou d’articles hors-sujet.\n- **Wikipédia** : consultations d’une page, pas opinion favorable/défavorable.\n- **Valeurs arrondies** : conservées comme telles si la plateforme ne fournit pas plus de précision.")


# -----------------------------------------------------------------------------
# SIMULATEUR D’IMPACT
# -----------------------------------------------------------------------------
elif nav == "🧮 Simulateur d’impact":
    render_impact_simulator()

# -----------------------------------------------------------------------------
# ASK DATA
# -----------------------------------------------------------------------------
elif nav == "🤖 Ask Data":
    section("Ask Data", "Interroger l'observatoire en langage naturel", "Le moteur répond à partir des données collectées : réseaux, presse, Wikipédia et chiffres officiels du mouvement.")
    examples = [
        "Compare David Lisnard et Édouard Philippe sur 24 h",
        "Qui progresse le plus sur Instagram ?",
        "Qui a le plus de vues Wikipédia sur 30 jours ?",
        "Combien d'articles ont été détectés pour Marine Le Pen sur 7 jours ?",
        "Combien d'adhérents compte Nouvelle Énergie ?",
    ]
    if "ask_data_input" not in st.session_state:
        st.session_state["ask_data_input"] = ""
    cols = st.columns(3)
    for i, ex in enumerate(examples):
        if cols[i % 3].button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state["ask_data_input"] = ex
    q = st.text_input("Question", key="ask_data_input", placeholder="Posez une question sur les données…")
    if q:
        ans = deterministic_ask_data(q, social_df, press_articles_df, tracked_candidates, public_data)
        if ans is None:
            ans = ask_data_with_claude(q, social_df, press_articles_df, public_data)
        if ans:
            st.markdown("### Réponse")
            st.markdown(ans)
        else:
            st.info("Je n'ai pas assez d'éléments structurés pour répondre automatiquement à cette question. Essayez de préciser une personne, un réseau et une période.")
        st.caption("Ask Data décrit des données publiques. Il ne produit ni intention de vote, ni causalité politique.")

# -----------------------------------------------------------------------------
# EXPLORER
# -----------------------------------------------------------------------------
elif nav == "🔎 Explorer":
    section("Explorer", "Recherche universelle", "Une requête, puis filtrez par type de source. Les résultats officiels restent séparés de la presse détectée.")
    render_freshness_strip(meta, public_data)
    if "explore_input" not in st.session_state:
        st.session_state["explore_input"] = ""
    themes = ["Éducation", "Sécurité", "Santé", "Agriculture", "Immigration", "Retraites", "Fiscalité", "Dette", "Décentralisation", "Énergie"]
    cols = st.columns(5)
    for i, th in enumerate(themes):
        if cols[i % 5].button(th, use_container_width=True, key=f"theme_{i}"):
            st.session_state["explore_input"] = th
            st.rerun()
    q = st.text_input("Recherche", placeholder="Ex. capitalisation, nucléaire, Tours, Haute-Garonne, David Lisnard…", key="explore_input")
    category_labels = ["Toutes", "Programme & questions", "Actualités officielles", "Agenda", "Relais", "Presse"]
    selected_cat = st.segmented_control("Type de source", category_labels, default="Toutes", key="explore_category") if hasattr(st, "segmented_control") else st.radio("Type de source", category_labels, horizontal=True, key="explore_category")
    if q:
        st.session_state["global_query"] = q
        results = universal_search(q, docs, events, relays, press_articles_df, public_data, 12)
        if selected_cat != "Toutes":
            results = {k: (v if k == selected_cat else []) for k, v in results.items()}
        counts = " · ".join(f"{k}: {len(v)}" for k, v in results.items() if v)
        if counts:
            st.caption(counts)
        render_search_results(results)
    else:
        st.markdown("#### Suggestions")
        st.caption("Choisissez un thème ci-dessus ou saisissez quelques mots. La recherche accepte les titres, thèmes, lieux, personnes et médias.")
        kinds = sorted(set(d.get("kind", "autre") for d in docs))
        selected = st.multiselect("Types de contenus officiels", kinds, default=[k for k in kinds if k in ("programme", "question", "faq", "vision")])
        filtered = [d for d in docs if not selected or d.get("kind") in selected]
        for d in filtered[:12]:
            st.markdown(f"**{d.get('title','Source')}**")
            st.caption(" · ".join(d.get("tags", [])[:4]) or d.get("kind", ""))
            st.write(snippet(d.get("text", ""), d.get("title", ""), 260))
            st.markdown(f"[Lire la source officielle]({d.get('url')})")
            st.divider()

# -----------------------------------------------------------------------------
# MON DEPARTEMENT
# -----------------------------------------------------------------------------
elif nav == "🧭 Mon département":
    section("Territoires", "Mon département", "Une fiche locale : commune, contexte public, relais Nouvelle Énergie et rendez-vous à proximité.")
    place = st.text_input("Ville ou code postal", placeholder="Ex. 78000 Versailles")
    radius = st.slider("Rayon pour les événements", 10, 250, 60, 10, format="%d km")
    if place:
        loc = geocode(place)
        if not loc:
            st.warning("Localisation non trouvée.")
        else:
            ctx = territory_context(place, loc)
            dep_code, dep_name = location_department(loc, relays)
            if ctx.get("department_code"):
                dep_code = ctx.get("department_code")
            if ctx.get("department_name"):
                dep_name = ctx.get("department_name")
            st.markdown(f"### {ctx.get('commune') or loc.get('city') or loc.get('label')}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Population communale", fmt_int(ctx.get("population")))
            c2.metric("Département", f"{dep_name or '—'} ({dep_code or '—'})")
            c3.metric("Région", ctx.get("region_name") or "—")
            st.caption("Contexte administratif : API Découpage administratif de l'État. La localisation saisie n'est pas enregistrée par NE Hub.")

            nearby = []
            for e in events:
                d = parse_date(e.get("date"))
                if d and d < date.today():
                    continue
                if e.get("lat") is None or e.get("lon") is None:
                    continue
                dist = hav(loc["lat"], loc["lon"], float(e["lat"]), float(e["lon"]))
                if dist <= radius:
                    item = dict(e)
                    item["distance_km"] = dist
                    nearby.append(item)
            nearby.sort(key=lambda x: (x["distance_km"], x.get("date", "")))

            l, r = st.columns([1, 1.1])
            with l:
                st.markdown("#### Votre relais")
                matches = [x for x in relays if str(x.get("department_code", "")) == str(dep_code) or (dep_code == "20" and str(x.get("department_code", "")).startswith("2"))]
                if matches:
                    for relay in matches[:4]:
                        with st.container(border=True):
                            st.markdown(f"**{relay.get('name','Relais départemental')}**")
                            st.caption(relay.get("department_name", dep_name or ""))
                            if relay.get("email"):
                                st.markdown(f"✉️ [{relay['email']}](mailto:{relay['email']})")
                            if relay.get("source_url"):
                                st.markdown(f"[Source officielle]({relay['source_url']})")
                else:
                    st.info("Aucun relais indexé localement pour ce département.")
                    st.link_button("Ouvrir la carte officielle des relais", "https://www.unenouvelleenergie.fr/decouvrir-notre-parti/les-relais/", use_container_width=True)
            with r:
                st.markdown(f"#### Rendez-vous à moins de {radius} km · {len(nearby)}")
                if nearby:
                    map_df = pd.DataFrame([{"lat": e["lat"], "lon": e["lon"], "nom": e.get("title", "")} for e in nearby])
                    st.map(map_df, latitude="lat", longitude="lon", size=45)
                else:
                    st.info("Aucun rendez-vous géolocalisé dans ce rayon.")
            for e in nearby[:8]:
                with st.container(border=True):
                    a, b = st.columns([5, 1])
                    a.markdown(f"**{e.get('title','Événement')}**")
                    a.caption(f"{e.get('date_label') or e.get('date','')} · {e.get('location','')} · {e['distance_km']:.0f} km")
                    if e.get("description"):
                        a.write(str(e.get("description"))[:350])
                    link = e.get("registration_url") or e.get("url")
                    if link:
                        b.link_button("Détails", link, use_container_width=True)

# -----------------------------------------------------------------------------
# AGENDA
# -----------------------------------------------------------------------------
elif nav == "🗓️ Agenda":
    section("Agenda", "Tous les rendez-vous", "Filtrez les événements officiels indexés et repérez-les sur la carte.")
    rows = []
    for e in events:
        x = dict(e)
        x["_date"] = parse_date(e.get("date"))
        rows.append(x)
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("Aucun événement indexé.")
    else:
        f1, f2 = st.columns(2)
        show_past = f1.toggle("Afficher les archives", False)
        text_filter = f2.text_input("Ville, département ou titre")
        if not show_past:
            df = df[df["_date"].apply(lambda x: x is not None and x >= date.today())]
        if text_filter:
            n = norm(text_filter)
            df = df[df.apply(lambda r: n in norm(f"{r.get('title','')} {r.get('location','')} {r.get('description','')}"), axis=1)]
        df = df.sort_values("_date", na_position="last")
        geo = df.dropna(subset=["lat", "lon"]) if "lat" in df.columns and "lon" in df.columns else pd.DataFrame()
        if not geo.empty:
            st.map(geo[["lat", "lon", "title"]].rename(columns={"title": "nom"}), latitude="lat", longitude="lon", size=42)
        for _, e in df.iterrows():
            with st.container(border=True):
                a, b = st.columns([5, 1])
                a.markdown(f"**{e.get('title','Événement')}**")
                a.caption(f"{e.get('date_label') or e.get('date','')} · {e.get('location','')}")
                if e.get("description"):
                    a.write(str(e.get("description"))[:420])
                link = e.get("registration_url") or e.get("url")
                if link:
                    b.link_button("Voir", link, use_container_width=True)

# -----------------------------------------------------------------------------
# ASK NE
# -----------------------------------------------------------------------------
elif nav == "💬 Ask NE":
    section("Ask NE", "Poser une question aux sources officielles", "Le moteur cherche dans les pages officielles indexées et renvoie systématiquement vers les textes de référence.")
    examples = ["Que propose Nouvelle Énergie sur les retraites ?", "Quelle est la position sur la dette ?", "Que propose le programme pour l'école ?", "Quelle vision de la décentralisation ?"]
    if "ask_ne_input" not in st.session_state:
        st.session_state["ask_ne_input"] = ""
    cols = st.columns(4)
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"askne_{i}", use_container_width=True):
            st.session_state["ask_ne_input"] = ex
    q = st.text_input("Question", key="ask_ne_input", placeholder="Votre question sur le programme…")
    if q:
        res = search_docs(q, docs, 7)
        if not res:
            st.warning("Aucune source officielle suffisamment proche n'a été trouvée.")
        else:
            ans = answer_with_claude(q, res)
            if ans:
                st.markdown("### Réponse sourcée")
                st.write(ans)
            else:
                st.markdown("### Passages officiels les plus pertinents")
                for i, d in enumerate(res[:5], 1):
                    with st.container(border=True):
                        st.markdown(f"**[{i}] {d.get('title','Source')}**")
                        st.write(snippet(d.get("text", ""), q, 520))
                        st.markdown(f"[Lire la source]({d.get('url')})")
            st.markdown("#### Sources")
            for i, d in enumerate(res[:6], 1):
                st.markdown(f"{i}. [{d.get('title','Source')}]({d.get('url')})")
        if not claude_available():
            st.caption("Claude Code n'est pas détecté : Ask NE fonctionne en mode recherche/extraits, sans synthèse IA.")

# -----------------------------------------------------------------------------
# RESSOURCES
# -----------------------------------------------------------------------------
elif nav == "🧰 Ressources":
    section("Ressources", "Accès aux documents et pages officielles", "Une porte d'entrée propre vers les ressources déjà publiées par Nouvelle Énergie.")
    resources = [
        ("🎨", "Kit militant", "Logos, charte graphique, kit réseaux sociaux et documents.", "https://www.unenouvelleenergie.fr/kit-militant/"),
        ("📚", "Programme", "Axes, pages thématiques, carnets et grands discours.", "https://www.unenouvelleenergie.fr/notre-programme/"),
        ("❓", "Questions", "Réponses thématiques avec citations datées et sources.", "https://www.unenouvelleenergie.fr/questions/"),
        ("👤", "David Lisnard", "Biographie et parcours publiés sur le site officiel.", "https://www.unenouvelleenergie.fr/david-lisnard/"),
        ("📰", "Actualités", "Publications et interventions du mouvement.", "https://www.unenouvelleenergie.fr/actualites/"),
        ("👥", "Relais", "Carte et contacts départementaux officiels.", "https://www.unenouvelleenergie.fr/decouvrir-notre-parti/les-relais/"),
        ("📍", "Agenda", "Conférences, déplacements et rencontres.", "https://www.unenouvelleenergie.fr/agenda/"),
        ("☎️", "Contacts utiles", "Coordonnées officielles du mouvement.", "https://www.unenouvelleenergie.fr/contacts-utiles/"),
    ]
    cols = st.columns(4)
    for i, (ico, title, desc, url) in enumerate(resources):
        with cols[i % 4]:
            st.markdown(f'<div class="ne-card"><h4>{ico} {title}</h4><p>{desc}</p></div>', unsafe_allow_html=True)
            st.link_button("Ouvrir", url, use_container_width=True)
    st.divider()
    st.markdown("#### Participer")
    p1, p2, p3 = st.columns(3)
    p1.link_button("Devenir bénévole", "https://www.unenouvelleenergie.fr/devenir-benevole/", use_container_width=True)
    p2.link_button("Proposer des idées", "https://www.unenouvelleenergie.fr/notre-programme/pole-de-travail-et-didees/", use_container_width=True)
    p3.link_button("Site de soutien / adhésion", "https://soutenir.unenouvelleenergie.fr/", use_container_width=True)

# -----------------------------------------------------------------------------
# ADMINISTRATION
# -----------------------------------------------------------------------------
elif nav == "⚙️ Administration":
    section("Administration", "Synchronisation et diagnostic", "Cette page peut être protégée par mot de passe en mode public.")
    configured_pwd = str(get_setting("NE_HUB_ADMIN_PASSWORD", "") or "")
    if configured_pwd:
        st.text_input("Mot de passe administrateur", type="password", key="ne_admin_password")
    if not admin_authorized():
        st.warning("Mode lecture seule. Entrez le mot de passe administrateur pour synchroniser les données.")
    else:
        c1, c2, c3 = st.columns(3)
        if c1.button("Synchroniser le site officiel", use_container_width=True):
            with st.spinner("Indexation du site…"):
                cp = subprocess.run([sys.executable, str(BASE / "sync_ne.py")], capture_output=True, text=True, timeout=240, encoding="utf-8", errors="replace")
                if cp.returncode == 0:
                    st.success(cp.stdout.strip() or "Synchronisation terminée.")
                    st.cache_data.clear()
                else:
                    st.error(cp.stderr[-1500:] or "Échec.")
        if c2.button("Synchroniser données ouvertes", use_container_width=True):
            with st.spinner("Actualités, chiffres officiels et Wikipédia…"):
                cp = subprocess.run([sys.executable, str(BASE / "sync_public_data.py")], capture_output=True, text=True, timeout=240, encoding="utf-8", errors="replace")
                if cp.returncode == 0:
                    st.success(cp.stdout.strip() or "Synchronisation terminée.")
                    st.cache_data.clear()
                else:
                    st.error(cp.stderr[-1500:] or "Échec.")
        if c3.button("Tout synchroniser", type="primary", use_container_width=True):
            with st.spinner("Synchronisation complète…"):
                messages = []
                ok = True
                for script in ("sync_ne.py", "sync_public_data.py"):
                    cp = subprocess.run([sys.executable, str(BASE / script)], capture_output=True, text=True, timeout=240, encoding="utf-8", errors="replace")
                    ok = ok and cp.returncode == 0
                    messages.append((cp.stdout or cp.stderr).strip())
                st.cache_data.clear()
                st.success("\n".join(messages)) if ok else st.warning("\n".join(messages))

    st.markdown("#### État des sources")
    status_rows = []
    for name, path in [
        ("Programme / agenda / relais", BASE / "data" / "meta.json"),
        ("Données publiques", PUBLIC_DATA_JSON),
        ("Réseaux sociaux", SOCIAL_XLSX),
        ("Radar presse", PRESS_XLSX),
        ("Personnalités", CANDIDATES_JSON),
    ]:
        status_rows.append({
            "Source": name,
            "Disponible": "Oui" if path.exists() else "Non",
            "Dernière modification": datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y %H:%M") if path.exists() else "—",
            "Fichier": str(path.relative_to(BASE)) if path.exists() and path.is_relative_to(BASE) else str(path),
        })
    st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)
    st.markdown("#### Mode de déploiement")
    st.code("NE_HUB_PUBLIC_MODE=1\nNE_HUB_ADMIN_PASSWORD=un-mot-de-passe-solide", language="text")
    st.caption("En mode public, la consultation reste ouverte mais les boutons de synchronisation nécessitent le mot de passe administrateur.")

st.divider()
st.markdown('<div class="ne-footer"><b>NE Hub</b> · portail non officiel de consultation et d’analyse de données publiques. Les positions politiques sont restituées depuis les sources officielles ; les mesures de visibilité ne constituent pas des intentions de vote. Les marques, logos et contenus restent la propriété de leurs titulaires.</div>', unsafe_allow_html=True)
