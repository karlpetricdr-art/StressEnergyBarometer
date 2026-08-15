import streamlit as st
import pandas as pd
import re
import math
import json
import time
import html
import base64
from io import BytesIO
from collections import Counter, defaultdict
from typing import List, Literal

import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import streamlit.components.v1 as components

from pyvis.network import Network

from pydantic import BaseModel
from google import genai
from google.genai import types


# ============================================================
# 1. PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Stress degree and kcal analysis PRO",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ============================================================
# 2. CSS
# ============================================================

st.markdown(
    """
    <style>

    .main {
        background-color: #f7f9fc;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    h1 {
        font-weight: 800;
        letter-spacing: -0.5px;
    }

    h2, h3 {
        font-weight: 700;
    }

    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #e5e9f0;
        box-shadow: 0 4px 14px rgba(0,0,0,0.05);
        min-height: 145px;
    }

    .small-muted {
        color: #64748b;
        font-size: 0.82rem;
    }

    .stress-high {
        color: #dc2626;
        font-weight: 800;
    }

    .stress-medium {
        color: #ea580c;
        font-weight: 700;
    }

    .stress-low {
        color: #16a34a;
        font-weight: 700;
    }

    .network-help {
        background: #f8fafc;
        border: 1px solid #dbe3ec;
        border-radius: 10px;
        padding: 12px 15px;
        margin: 10px 0 15px 0;
        color: #475569;
        font-size: 0.9rem;
    }

    .st-key-action_btn_container button {
        background: linear-gradient(145deg, #16a34a, #15803d) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: none !important;
        box-shadow:
            3px 3px 8px rgba(21, 128, 61, 0.35),
            -2px -2px 6px rgba(255, 255, 255, 0.25) !important;
    }

    .st-key-action_btn_container button:hover {
        background: linear-gradient(145deg, #15803d, #166534) !important;
        color: #ffffff !important;
    }

    .settings-card {
        background: white;
        border-radius: 16px;
        padding: 22px 24px;
        border: 1px solid #e5e9f0;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        margin-bottom: 18px;
    }

    .settings-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 2b. SIDEBAR LOGO
# ============================================================

SIDEBAR_LOGO_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: linear-gradient(160deg, #0f172a 0%, #1e293b 45%, #0f172a 100%);
    font-family: 'Segoe UI', Arial, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 150px;
    padding: 18px 12px 14px;
    overflow: hidden;
  }
  .logo-wrap {
    text-align: center;
    position: relative;
  }
  .ornament {
    color: #38bdf8;
    font-size: 11px;
    letter-spacing: 6px;
    margin-bottom: 6px;
    opacity: 0.85;
  }
  .title {
    color: #f8fafc;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.4px;
    line-height: 1.25;
  }
  .subtitle {
    color: #94a3b8;
    font-size: 10.5px;
    margin-top: 5px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
  }
  .line {
    width: 70%;
    height: 2px;
    background: linear-gradient(90deg, transparent, #38bdf8, #22d3ee, #38bdf8, transparent);
    margin: 10px auto 0;
    border-radius: 2px;
  }
  .dots {
    margin-top: 8px;
    color: #64748b;
    font-size: 9px;
    letter-spacing: 4px;
  }
</style>
</head>
<body>
  <div class="logo-wrap">
    <div class="ornament">◆ ━━━ ◆ ━━━ ◆</div>
    <div class="title">Stress Analysis</div>
    <div class="subtitle">PRO · Scientific Edition</div>
    <div class="line"></div>
    <div class="dots">● ● ●</div>
  </div>
</body>
</html>
"""


# ============================================================
# 3. CONSTANTS & MAPPINGS
# ============================================================

CATEGORIES_MAP = {
    "Physical/attentive": "Physical/attentive",
    "Performance": "Performance",
    "Psychological": "Psychological",
    "Social": "Social",
    "Health": "Health",
}

CATEGORY_SHORT = {
    "Physical/attentive": "Physical/attentive",
    "Performance": "Performance",
    "Psychological": "Psychological",
    "Social": "Social",
    "Health": "Health",
}

SHORT_TO_FULL = {v: k for k, v in CATEGORY_SHORT.items()}

ROLE_LABELS = {
    "PF": "Positive factor",
    "SF": "Stress-related factor",
    "PR": "Suggestion / opinion",
}

SLOPE_WEIGHTS = {
    "Physical/attentive": 1.15,
    "Performance": 1.10,
    "Psychological": 1.20,
    "Social": 1.05,
    "Health": 1.00,
}

NETWORK_CATEGORY_COLORS = {
    "Physical/attentive": "#3b82f6",
    "Performance": "#f59e0b",
    "Psychological": "#8b5cf6",
    "Social": "#ec4899",
    "Health": "#10b981",
}

# Current free-tier capable Gemini models (Aug 2026)
# Deprecated / shut down: gemini-2.0-flash, gemini-2.0-flash-lite, gemini-1.5-*
AVAILABLE_MODELS = [
    "— Select a model —",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]

MODEL_NOTES = {
    "gemini-3.7-flash": "Latest & most capable Flash (recommended)",
    "gemini-3.6-flash": "Previous-gen Flash, strong balance",
    "gemini-3.5-flash": "High intelligence Flash",
    "gemini-3.5-flash-lite": "Fast & cost-efficient (great for bulk)",
    "gemini-3.1-flash-lite": "Lightweight, high volume",
    "gemini-2.5-flash": "Excellent price/performance",
    "gemini-2.5-flash-lite": "Fastest & cheapest in 2.5 family",
    "gemini-2.5-pro": "Higher reasoning (may have tighter free limits)",
}

# Offline dictionary
OFFLINE_DICT = {
    "Physical/attentive": [
        "attention", "focus", "concentration", "fatigue", "tired", "sleep",
        "energy", "alert", "physical", "body", "movement", "exercise",
        "rest", "exhaustion", "overload", "workload", "busy",
        "pozornost", "osredotočenost", "koncentracija", "utrujenost", "spanje",
        "energija", "telo", "gibanje", "vadba", "počitek", "izčrpanost",
        "preobremenjenost", "delovna obremenitev",
    ],
    "Performance": [
        "performance", "productivity", "efficiency", "deadline", "task",
        "achievement", "goal", "success", "failure", "output", "quality",
        "speed", "competence", "skill", "result",
        "uspešnost", "produktivnost", "učinkovitost", "rok", "naloga",
        "dosežek", "cilj", "uspeh", "neuspeh", "kakovost", "hitrost",
        "kompetenca", "spretnost", "rezultat",
    ],
    "Psychological": [
        "anxiety", "stress", "worry", "fear", "depression", "mood",
        "emotion", "mental", "pressure", "burnout", "motivation",
        "confidence", "self-esteem", "frustration", "anger", "sadness",
        "anksioznost", "stres", "skrb", "strah", "depresija", "razpoloženje",
        "čustvo", "duševni", "pritisk", "izgorelost", "motivacija",
        "samozavest", "frustracija", "jeza", "žalost",
    ],
    "Social": [
        "family", "friend", "community", "relationship", "support", "lonely",
        "isolation", "society", "social", "colleague", "team", "belonging",
        "connection", "trust", "respect", "conflict", "communication",
        "družina", "prijatelj", "skupnost", "odnos", "podpora", "osamljen",
        "izolacija", "družba", "sodelavec", "ekipa", "pripadnost",
        "povezanost", "zaupanje", "spoštovanje", "konflikt", "komunikacija",
    ],
    "Health": [
        "health", "illness", "pain", "disease", "medical", "doctor",
        "symptom", "wellbeing", "well-being", "fitness", "nutrition",
        "diet", "chronic", "recovery", "therapy", "medication",
        "zdravje", "bolezen", "bolečina", "zdravnik", "simptom",
        "počutje", "fitnes", "prehrana", "kronično", "okrevanje",
        "terapija", "zdravilo",
    ],
}


# ============================================================
# 4. HELPER FUNCTIONS
# ============================================================

def rate_sigma(sigma: float) -> str:
    if sigma >= 70:
        return "Very high"
    if sigma >= 50:
        return "High"
    if sigma >= 30:
        return "Moderate"
    if sigma >= 15:
        return "Low"
    return "Very low"


def get_client(api_key: str):
    return genai.Client(api_key=api_key)


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def split_phrases(text: str) -> List[str]:
    if not text:
        return []
    parts = re.split(r"[;,/\n\|]+", text)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]


# ============================================================
# 5. OFFLINE CLASSIFICATION
# ============================================================

def classify_offline_phrase(phrase: str, active_shorts: List[str]) -> str:
    phrase_l = phrase.lower()
    scores = {}
    for full, keywords in OFFLINE_DICT.items():
        short = CATEGORY_SHORT[full]
        if short not in active_shorts:
            continue
        score = sum(1 for kw in keywords if kw in phrase_l)
        if score > 0:
            scores[full] = score
    if not scores:
        return "Psychological"
    return max(scores, key=scores.get)


def run_offline_classification(df, col, included_shorts):
    classified = []
    per_row = []
    per_row_items = []

    for _, val in df[col].dropna().items():
        text = clean_text(str(val))
        phrases = split_phrases(text)
        row_cats = []
        row_items = []
        for ph in phrases:
            cat = classify_offline_phrase(ph, included_shorts)
            classified.append((ph, cat))
            row_cats.append(cat)
            row_items.append((ph, cat))
        per_row.append(row_cats)
        per_row_items.append(row_items)

    return classified, per_row, per_row_items


# ============================================================
# 6. AI CLASSIFICATION
# ============================================================

class ClassificationItem(BaseModel):
    phrase: str
    unit: Literal[
        "Physical/attentive",
        "Performance",
        "Psychological",
        "Social",
        "Health",
    ]


class ClassificationBatch(BaseModel):
    items: List[ClassificationItem]


def build_classification_prompt(texts: List[str], included_shorts: List[str]) -> str:
    units_str = ", ".join(included_shorts)
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    return f"""You are a scientific classifier of qualitative survey answers about stress factors, positive factors and suggestions.

Classify each answer (or each distinct phrase inside an answer) into exactly one of these scientific units:
{units_str}

Definitions:
- Physical/attentive: physical state, attention, concentration, fatigue, sleep, energy, bodily load
- Performance: work performance, productivity, deadlines, tasks, achievement, efficiency, results
- Psychological: emotions, anxiety, mental pressure, motivation, self-esteem, burnout, mood
- Social: interpersonal relations, family, colleagues, support, isolation, communication, belonging
- Health: physical or mental health, illness, pain, wellbeing, medical issues, recovery

Rules:
1. Extract meaningful phrases (split by commas, semicolons, slashes if needed).
2. Assign exactly one unit per phrase.
3. Prefer the most specific and dominant meaning.
4. Return only structured data matching the schema.

Answers to classify:
{numbered}
"""


def run_ai_classification(
    client,
    model_name,
    df,
    col,
    included_shorts,
    batch_size,
    progress_label,
):
    classified = []
    per_row = []
    per_row_items = []

    non_empty = [
        (idx, clean_text(str(val)))
        for idx, val in df[col].dropna().items()
        if clean_text(str(val))
    ]

    if not non_empty:
        return [], [], []

    progress = st.progress(0, text=progress_label)
    total = len(non_empty)
    done = 0

    for start in range(0, total, batch_size):
        batch = non_empty[start:start + batch_size]
        texts = [t for _, t in batch]

        prompt = build_classification_prompt(texts, included_shorts)

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ClassificationBatch,
                    temperature=0.1,
                ),
            )

            parsed = ClassificationBatch.model_validate_json(response.text)
            all_items = list(parsed.items)

        except Exception as e:
            st.warning(f"AI batch error: {e}. Falling back to offline for this batch.")
            all_items = []
            for _, text in batch:
                phrases = split_phrases(text)
                for ph in phrases:
                    cat = classify_offline_phrase(ph, included_shorts)
                    all_items.append(
                        ClassificationItem(
                            phrase=ph,
                            unit=CATEGORY_SHORT.get(cat, "Psychological"),
                        )
                    )

        item_idx = 0
        for _, text in batch:
            phrases = split_phrases(text)
            row_cats = []
            row_items = []
            for ph in phrases:
                if item_idx < len(all_items):
                    item = all_items[item_idx]
                    unit_full = SHORT_TO_FULL.get(item.unit, item.unit)
                    if unit_full not in CATEGORIES_MAP:
                        unit_full = "Psychological"
                    classified.append((item.phrase or ph, unit_full))
                    row_cats.append(unit_full)
                    row_items.append((item.phrase or ph, unit_full))
                    item_idx += 1
                else:
                    cat = classify_offline_phrase(ph, included_shorts)
                    classified.append((ph, cat))
                    row_cats.append(cat)
                    row_items.append((ph, cat))
            per_row.append(row_cats)
            per_row_items.append(row_items)

        done += len(batch)
        progress.progress(
            min(done / total, 1.0),
            text=f"{progress_label} ({done}/{total})",
        )

    progress.empty()
    return classified, per_row, per_row_items


# ============================================================
# 7. FACTOR CALCULATIONS
# ============================================================

def calculate_fo_real_aggregate(classified, n_input):
    if not classified or n_input <= 0:
        return 0.0, 0.0, 0.0
    counts = Counter(cat for _, cat in classified)
    total_mentions = sum(counts.values())
    diversity = len(counts)
    f = (total_mentions / n_input) * (1 + 0.15 * math.log1p(diversity))
    return f, total_mentions, diversity


def compute_category_factors(classified, n_input, active_categories, weighting_mode):
    if not classified or n_input <= 0:
        return {c: 0.0 for c in active_categories}

    counts = Counter(cat for _, cat in classified if cat in active_categories)
    total = sum(counts.values()) or 1

    result = {}
    for cat in active_categories:
        c = counts.get(cat, 0)
        if weighting_mode == "volume":
            result[cat] = c / n_input
        else:
            share = c / total
            result[cat] = (c / n_input) * (1 + share)
    return result


def sigma_argument(f_sf, f_pr, f_pf):
    denom = f_sf + f_pr + f_pf + 1e-9
    raw = (f_sf + 0.55 * f_pr) / denom
    return max(0.0, min(raw, 1.0))


def sigma_deg(f_sf, f_pr, f_pf):
    arg = sigma_argument(f_sf, f_pr, f_pf)
    return 90.0 * arg


def calculate_energy(sigma):
    eta = max(5.0, 100.0 - 0.85 * sigma)
    total_kcal = 2200.0
    W_EU = total_kcal * (eta / 100.0)
    loss = total_kcal - W_EU
    return W_EU, eta, loss


def compute_category_sigmas(
    f_sf_cat,
    f_pf_cat,
    f_pr_cat,
    sig_total_arg,
    is_summary,
    active_categories,
):
    cat_sigmas = {}
    weights = []

    for cat in active_categories:
        f_sf = f_sf_cat.get(cat, 0.0)
        f_pf = f_pf_cat.get(cat, 0.0)
        f_pr = f_pr_cat.get(cat, 0.0)

        if is_summary:
            f_pr = min(f_pr, f_sf * 1.5)

        local_arg = sigma_argument(f_sf, f_pr, f_pf)
        blended = 0.65 * local_arg + 0.35 * sig_total_arg
        sigma = 90.0 * blended * SLOPE_WEIGHTS.get(cat, 1.0)
        sigma = max(0.0, min(sigma, 90.0))

        w = (f_sf + f_pr + f_pf + 0.01) * SLOPE_WEIGHTS.get(cat, 1.0)
        weights.append(w)
        cat_sigmas[cat] = {
            "sigma": sigma,
            "weight": w,
        }

    total_w = sum(weights) or 1.0
    for cat in cat_sigmas:
        cat_sigmas[cat]["weight_share"] = cat_sigmas[cat]["weight"] / total_w

    return cat_sigmas, total_w


# ============================================================
# 8. NETWORK BUILDING
# ============================================================

def build_network_data(analysis, max_nodes=25):
    node_info = defaultdict(lambda: {
        "count": 0,
        "category": "Psychological",
        "role": "SF",
        "criticality": 0.0,
    })

    cooccur = Counter()
    role_weight = {"SF": 1.35, "PR": 1.10, "PF": 0.85}

    for role in ["PF", "SF", "PR"]:
        items_by_row = analysis[role].get("items_by_original_row", {})
        for row_idx, items in items_by_row.items():
            phrases_in_row = []
            for phrase, cat in items:
                key = phrase.strip()[:80]
                if not key:
                    continue
                node_info[key]["count"] += 1
                node_info[key]["category"] = cat
                if role == "SF" or node_info[key]["role"] != "SF":
                    if role == "SF" or node_info[key]["role"] == "PF":
                        node_info[key]["role"] = role
                phrases_in_row.append(key)

            unique = list(dict.fromkeys(phrases_in_row))
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    a, b = sorted([unique[i], unique[j]])
                    cooccur[(a, b)] += 1

    if not node_info:
        return None

    for key, data in node_info.items():
        rw = role_weight.get(data["role"], 1.0)
        sw = SLOPE_WEIGHTS.get(data["category"], 1.0)
        data["criticality"] = data["count"] * rw * sw

    ranked = sorted(
        node_info.items(),
        key=lambda x: x[1]["criticality"],
        reverse=True,
    )[:max_nodes]

    selected = {k for k, _ in ranked}

    G = nx.Graph()
    for key in selected:
        data = node_info[key]
        G.add_node(
            key,
            count=data["count"],
            category=data["category"],
            role=data["role"],
            criticality=data["criticality"],
        )

    for (a, b), strength in cooccur.items():
        if a in selected and b in selected:
            G.add_edge(a, b, strength=strength)

    return G


# ============================================================
# 9. PLOTLY NETWORK
# ============================================================

def build_plotly_network(graph):
    if graph is None or len(graph.nodes) == 0:
        return None

    pos = nx.spring_layout(graph, k=0.85, iterations=50, seed=42)
    fig = go.Figure()

    edge_styles = [
        ("strong", 3, 4, "solid", "Strong co-occurrence"),
        ("moderate", 2, 2, "solid", "Moderate co-occurrence"),
        ("weak", 1, 1, "dash", "Weak co-occurrence"),
    ]

    for style_name, strength, width, dash, legend_name in edge_styles:
        x, y = [], []
        for a, b, data in graph.edges(data=True):
            s = int(data.get("strength", 1))
            qualifies = (
                (style_name == "strong" and s >= 3)
                or (style_name == "moderate" and s == 2)
                or (style_name == "weak" and s == 1)
            )
            if not qualifies:
                continue
            x.extend([pos[a][0], pos[b][0], None])
            y.extend([pos[a][1], pos[b][1], None])

        if x:
            fig.add_trace(
                go.Scatter(
                    x=x, y=y, mode="lines",
                    line=dict(width=width, dash=dash),
                    hoverinfo="skip", name=legend_name,
                )
            )

    for category in CATEGORY_SHORT:
        nodes = [
            n for n in graph.nodes
            if graph.nodes[n]["category"] == category
        ]
        if not nodes:
            continue

        xs = [pos[n][0] for n in nodes]
        ys = [pos[n][1] for n in nodes]
        sizes = [
            16 + 9 * math.sqrt(max(graph.nodes[n]["criticality"], 0.1))
            for n in nodes
        ]
        hover = [
            (
                f"<b>{html.escape(n)}</b><br>"
                f"Unit: {CATEGORY_SHORT[graph.nodes[n]['category']]}<br>"
                f"Role: {ROLE_LABELS[graph.nodes[n]['role']]}<br>"
                f"Occurrences: {graph.nodes[n]['count']}<br>"
                f"Criticality: {graph.nodes[n]['criticality']:.2f}"
            )
            for n in nodes
        ]

        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="markers+text",
                text=nodes, textposition="top center",
                marker=dict(size=sizes, line=dict(width=1)),
                hovertext=hover, hoverinfo="text",
                name=CATEGORY_SHORT[category],
            )
        )

    fig.update_layout(
        title="Factor & opinion network — node size = criticality",
        height=720,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=20, r=20, t=80, b=20),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(
        showgrid=False, zeroline=False, visible=False,
        scaleanchor="x", scaleratio=1,
    )
    return fig


# ============================================================
# 10. PYVIS INTERACTIVE NETWORK
# ============================================================

def build_pyvis_network(graph):
    if graph is None or len(graph.nodes) == 0:
        return None

    net = Network(
        height="720px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#1f2937",
        directed=False,
        notebook=False,
        cdn_resources="in_line",
    )

    net.set_options(
        """
        {
          "interaction": {
            "dragNodes": true,
            "dragView": true,
            "zoomView": true,
            "hover": true,
            "navigationButtons": true,
            "keyboard": true
          },
          "physics": {
            "enabled": true,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
              "gravitationalConstant": -70,
              "centralGravity": 0.008,
              "springLength": 160,
              "springConstant": 0.045,
              "damping": 0.82,
              "avoidOverlap": 1.0
            },
            "minVelocity": 0.75,
            "stabilization": {
              "enabled": true,
              "iterations": 250,
              "updateInterval": 25,
              "fit": true
            }
          },
          "nodes": {
            "shape": "dot",
            "font": {
              "size": 15,
              "face": "Arial",
              "strokeWidth": 3,
              "strokeColor": "#ffffff"
            },
            "borderWidth": 1.5
          },
          "edges": {
            "smooth": {
              "enabled": true,
              "type": "dynamic"
            },
            "color": {
              "inherit": false,
              "color": "#94a3b8",
              "highlight": "#334155"
            },
            "selectionWidth": 2,
            "hoverWidth": 2
          }
        }
        """
    )

    for node in graph.nodes:
        data = graph.nodes[node]
        category = data["category"]
        role = data["role"]
        criticality = float(data["criticality"])
        size = 18 + 10 * math.sqrt(max(criticality, 0.1))
        color = NETWORK_CATEGORY_COLORS.get(category, "#64748b")
        role_label = ROLE_LABELS.get(role, role)

        tooltip = (
            f"<b>{html.escape(node)}</b><br>"
            f"Unit: {html.escape(CATEGORY_SHORT.get(category, category))}<br>"
            f"Role: {html.escape(role_label)}<br>"
            f"Occurrences: {data['count']}<br>"
            f"Criticality: {criticality:.2f}<br>"
            f"Slope weight: {SLOPE_WEIGHTS.get(category, 1.0):.2f}"
        )

        net.add_node(
            node,
            label=node,
            title=tooltip,
            size=size,
            color={
                "background": color,
                "border": "#334155",
                "highlight": {"background": color, "border": "#111827"},
                "hover": {"background": color, "border": "#111827"},
            },
            borderWidth=2,
            font={
                "size": 15,
                "face": "Arial",
                "strokeWidth": 3,
                "strokeColor": "#ffffff",
            },
        )

    for a, b, data in graph.edges(data=True):
        strength = int(data.get("strength", 1))
        if strength >= 3:
            width = 5
            color = {"color": "#64748b", "highlight": "#1e293b", "hover": "#1e293b"}
        elif strength == 2:
            width = 3
            color = {"color": "#94a3b8", "highlight": "#475569", "hover": "#475569"}
        else:
            width = 1.5
            color = {"color": "#cbd5e1", "highlight": "#64748b", "hover": "#64748b"}

        net.add_edge(
            a, b,
            value=strength,
            width=width,
            dashes=(strength == 1),
            title=f"Co-occurrence: {strength}",
            color=color,
        )

    return net.generate_html()


# ============================================================
# 11. NETWORK TABLE
# ============================================================

def build_network_table(graph):
    if graph is None:
        return None
    rows = []
    for node in sorted(
        graph.nodes,
        key=lambda x: graph.nodes[x]["criticality"],
        reverse=True,
    ):
        rows.append({
            "Node": node,
            "Unit": CATEGORY_SHORT[graph.nodes[node]["category"]],
            "Role": ROLE_LABELS[graph.nodes[node]["role"]],
            "Occurrences": graph.nodes[node]["count"],
            "Criticality": round(graph.nodes[node]["criticality"], 2),
        })
    return pd.DataFrame(rows)


# ============================================================
# 12. HTML REPORT EXPORT
# ============================================================

def build_report_html(
    title,
    model_name,
    classification_mode,
    sigma_total,
    W_EU,
    eta,
    loss,
    n_input,
    res_df,
    unit_fig,
    role_tree_fig,
    network_fig,
    net_df,
    text_sections=None,
):
    generated = time.strftime("%Y-%m-%d %H:%M")

    parts = [
        f"<h1>{html.escape(title)}</h1>",
        (
            f"<p>"
            f"<b>Generated / Ustvarjeno:</b> {generated}<br>"
            f"<b>Mode / Način:</b> {html.escape(classification_mode)}<br>"
            f"<b>Model:</b> {html.escape(model_name or 'Offline dictionary')}<br>"
            f"<b>N:</b> {n_input}"
            f"</p>"
        ),
        "<h2>Overall results / Skupni rezultati</h2>",
        (
            "<div class='result-box'>"
            "<p>"
            f"<b>Stress intensity / Stresna intenzivnost:</b> {sigma_total:.2f} °S<br>"
            f"<b>Rating / Ocena:</b> {html.escape(rate_sigma(sigma_total))}<br>"
            f"<b>Efficiency / Učinkovitost:</b> {eta:.1f}%<br>"
            f"<b>Energy loss / Izguba energije:</b> {loss:.0f} Kcal<br>"
            f"<b>Useful energy / Koristna energija:</b> {W_EU:.0f} Kcal"
            "</p>"
            "</div>"
        ),
        (
            "<h2>Distribution by scientific unit / "
            "Porazdelitev po znanstvenih enotah</h2>"
        ),
        res_df.to_html(
            index=False,
            border=0,
            classes="report-table",
            justify="left",
        ),
    ]

    if text_sections:
        for heading, body in text_sections:
            safe_body = html.escape(str(body)).replace("\n", "<br>")
            parts.append(f"<h2>{html.escape(str(heading))}</h2>")
            parts.append(f"<div class='text-section'>{safe_body}</div>")

    plotly_added = False
    visualizations = [
        (
            "Stress intensity by scientific unit / "
            "Stresna intenzivnost po znanstvenih enotah",
            unit_fig,
        ),
        (
            "All classified phrases by role and unit / "
            "Vsi klasificirani izrazi po vlogi in enoti",
            role_tree_fig,
        ),
        (
            "Factor and opinion network / "
            "Omrežje dejavnikov in mnenj",
            network_fig,
        ),
    ]

    for heading, fig in visualizations:
        if fig is None:
            continue
        parts.append(f"<h2>{html.escape(heading)}</h2>")
        try:
            plot_html = fig.to_html(
                full_html=False,
                include_plotlyjs="cdn" if not plotly_added else False,
                config={"responsive": True, "displaylogo": False},
            )
            parts.append(plot_html)
            plotly_added = True
        except Exception as e:
            parts.append(
                "<p><i>Visualization could not be embedded "
                f"in the HTML report: {html.escape(str(e))}</i></p>"
            )

    if net_df is not None and not net_df.empty:
        parts.append(
            "<h2>Critical network nodes / Kritična vozlišča omrežja</h2>"
        )
        parts.append(
            net_df.to_html(
                index=False,
                border=0,
                classes="report-table",
                justify="left",
            )
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
* {{ box-sizing: border-box; }}
body {{
    font-family: "Segoe UI", "Noto Sans", Arial, Helvetica, sans-serif;
    margin: 0; padding: 35px;
    color: #1f2937; background: #ffffff;
    line-height: 1.55; font-size: 15px;
}}
h1 {{ color: #111827; font-size: 30px; margin-bottom: 8px; }}
h2 {{
    color: #1f2937; font-size: 21px;
    margin-top: 42px; margin-bottom: 15px;
    border-bottom: 2px solid #e5e7eb; padding-bottom: 7px;
}}
p {{ margin: 8px 0 14px; }}
.result-box {{
    background: #f8fafc; border: 1px solid #dbe3ec;
    border-radius: 12px; padding: 16px 20px; margin: 15px 0 25px;
}}
.text-section {{
    white-space: normal; background: #f8fafc;
    border-left: 4px solid #94a3b8;
    padding: 12px 16px; margin: 10px 0 20px;
}}
.report-table {{
    border-collapse: collapse; width: 100%;
    margin: 15px 0 30px; font-size: 14px;
}}
.report-table th, .report-table td {{
    border: 1px solid #d1d5db; padding: 8px 10px;
    text-align: left; vertical-align: top;
}}
.report-table th {{ background: #f1f5f9; font-weight: 700; }}
.report-table tr:nth-child(even) {{ background: #f8fafc; }}
.js-plotly-plot {{ width: 100% !important; margin: 10px 0 35px 0; }}
.footer {{
    margin-top: 50px; padding-top: 15px;
    border-top: 1px solid #e5e7eb;
    color: #64748b; font-size: 12px;
}}
@media print {{
    body {{ padding: 15px; font-size: 12px; }}
    h1 {{ font-size: 24px; }}
    h2 {{ font-size: 17px; page-break-after: avoid; }}
    .js-plotly-plot, .report-table {{ page-break-inside: avoid; }}
}}
</style>
</head>
<body>
{''.join(parts)}
<div class="footer">
    Stress Analysis Pro<br>
    Scientific basis: Karl Petrič, <i>Gaining knowledge through understanding distress and positive factors in social environments</i>, European Review of Applied Sociology, 2025. DOI: 10.2478/eras-2025-0003
</div>
</body>
</html>"""


# ============================================================
# 13. MAIN STREAMLIT APPLICATION
# ============================================================

def main():

    # --------------------------------------------------------
    # SIDEBAR — logo + reset
    # --------------------------------------------------------

    with st.sidebar:
        components.html(
            SIDEBAR_LOGO_HTML,
            height=158,
            scrolling=False,
        )

        st.markdown("")
        if st.button("🔄 Reset session", use_container_width=True):
            reset_app()

        st.caption("Scientific · Interactive · Report-ready")

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.markdown("# 📊 Stress degree and kcal analysis PRO")
    st.caption(
        "Classification with Google Gemini models · "
        "5 scientific units "
        "(Physical/attentive · Performance · Psychological · Social · Health)"
    )

    # --------------------------------------------------------
    # MAIN SETTINGS PANEL
    # --------------------------------------------------------

    st.markdown("## ⚙️ Analysis settings")

    c1, c2, c3 = st.columns([2.2, 1, 1.2])

    with c1:
        uploaded_file = st.file_uploader(
            "📁 Upload data (TXT / CSV / XLSX)",
            type=["txt", "csv", "xlsx"],
            help="Upload the survey export containing positive factors, stress factors and suggestions.",
        )

    with c2:
        n_input = st.number_input(
            "Number of respondents (N)",
            min_value=1,
            value=210,
        )

    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        is_summary = st.checkbox(
            "The file contains a SUMMARY",
            value=True,
            help="If checked, suggestions are capped relative to stress factors.",
        )

    if uploaded_file is not None:
        file_signature = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("uploaded_file_signature") != file_signature:
            st.session_state["uploaded_file_signature"] = file_signature
            st.session_state["analysis_triggered"] = False
    else:
        st.session_state["analysis_triggered"] = False

    st.divider()

    st.markdown("### 🤖 Classification")

    classification_mode = st.radio(
        "Classification mode",
        [
            "AI model (Gemini)",
            "Dictionary (offline, no API call)",
        ],
        horizontal=True,
    )

    api_key = None
    model_name = None
    batch_size = 15

    if classification_mode.startswith("AI"):
        ac1, ac2, ac3 = st.columns([1.6, 1.4, 1])
        with ac1:
            api_key = st.text_input(
                "Google AI API key",
                type="password",
                help="Get a free key at https://aistudio.google.com/apikey",
            )
        with ac2:
            model_name = st.selectbox(
                "Model",
                AVAILABLE_MODELS,
                index=0,
            )
            if model_name != AVAILABLE_MODELS[0]:
                st.caption(MODEL_NOTES.get(model_name, ""))
        with ac3:
            batch_size = st.slider(
                "Batch size (rows per call)",
                1,
                50,
                15,
            )
    else:
        st.info("Offline dictionary mode — no API key required.", icon="📖")

    st.divider()

    st.markdown("### 🧭 Units, weighting & display")

    u1, u2, u3, u4 = st.columns(4)

    with u1:
        included_shorts = st.multiselect(
            "Included scientific units",
            list(CATEGORY_SHORT.values()),
            default=list(CATEGORY_SHORT.values()),
        )
        active_categories = [
            SHORT_TO_FULL[s] for s in included_shorts
        ]
        if not active_categories:
            active_categories = list(CATEGORIES_MAP.keys())

    with u2:
        weighting_label = st.radio(
            "Weighting within the unit",
            ["Volume (frequency)", "Concentration (repeatability)"],
        )
        weighting_mode = (
            "volume" if "Volume" in weighting_label else "concentration"
        )

    with u3:
        chart_mode = st.radio(
            "Distribution display",
            ["Bar chart", "Treemap (colorful)", "Both"],
        )

    with u4:
        network_nodes = st.slider(
            "Network nodes",
            min_value=5,
            max_value=50,
            value=25,
            step=1,
            help="Most critical factors/opinions become the largest nodes.",
        )

    st.divider()

    with st.container(key="action_btn_container"):
        run_clicked = st.button(
            "▶️ Action — Run analysis",
            use_container_width=True,
            type="primary",
            disabled=(uploaded_file is None),
        )

    if run_clicked:
        st.session_state["analysis_triggered"] = True

    if uploaded_file is not None and not st.session_state.get("analysis_triggered", False):
        st.caption("File loaded. Click **Action — Run analysis** to start.")

    # --------------------------------------------------------
    # EMPTY STATE
    # --------------------------------------------------------

    if not uploaded_file:
        st.info(
            "📁 Upload a file above and configure the settings, then press **Action**.",
            icon="ℹ️",
        )
        st.markdown("### 📚 Scientific basis")
        st.markdown(
            "**Petrič, K.** *Gaining knowledge through understanding distress and positive factors in social environments.* "
            "**European Review of Applied Sociology**, 2025-06-03, Journal article. "
            "DOI: [10.2478/eras-2025-0003](https://doi.org/10.2478/eras-2025-0003)"
        )
        return

    if not st.session_state.get("analysis_triggered", False):
        st.info(
            "▶️ File loaded. Click the **Action — Run analysis** button to run the analysis.",
            icon="▶️",
        )
        return

    # --------------------------------------------------------
    # AI SETTINGS CHECK
    # --------------------------------------------------------

    if classification_mode.startswith("AI"):
        if not api_key:
            st.warning(
                "⚠️ Enter a Google AI API key above to use AI classification."
            )
            return
        if model_name == AVAILABLE_MODELS[0]:
            st.warning("⚠️ Select a model above.")
            return

    # --------------------------------------------------------
    # READ DATA
    # --------------------------------------------------------

    try:
        if uploaded_file.name.lower().endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.lower().endswith(".txt"):
            df = pd.read_csv(
                uploaded_file,
                sep="\t",
                engine="python",
                on_bad_lines="skip",
            )
        else:
            df = pd.read_csv(
                uploaded_file,
                engine="python",
                on_bad_lines="skip",
            )
    except Exception as e:
        st.error(f"Error reading the file: {e}")
        return

    if df.empty:
        st.error("The uploaded dataset is empty.")
        return
    if len(df.columns) == 0:
        st.error("The uploaded dataset contains no columns.")
        return

    target_cols = df.columns.tolist()

    # --------------------------------------------------------
    # COLUMN SELECTION
    # --------------------------------------------------------

    st.markdown("### 🧩 Column mapping")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        col_pf = st.selectbox(
            "Positive factors (PF)",
            target_cols,
            index=0,
        )
    with col_b:
        col_sf = st.selectbox(
            "Stress-related factors (SF)",
            target_cols,
            index=min(1, len(target_cols) - 1),
        )
    with col_c:
        col_pr = st.selectbox(
            "Suggestions (PR)",
            target_cols,
            index=min(2, len(target_cols) - 1),
        )

    st.divider()

    # ========================================================
    # CLASSIFICATION
    # ========================================================

    analysis = {}

    if classification_mode.startswith("AI"):
        try:
            client = get_client(api_key)
        except Exception as e:
            st.error(f"Could not initialize Google AI client: {e}")
            return

        for role, col, label in [
            ("PF", col_pf, "🔵 Classifying positive factors ..."),
            ("SF", col_sf, "🔴 Classifying stress-related factors ..."),
            ("PR", col_pr, "🟢 Classifying suggestions ..."),
        ]:
            try:
                cls, per_row, per_row_items = run_ai_classification(
                    client,
                    model_name,
                    df,
                    col,
                    included_shorts,
                    batch_size,
                    label,
                )
            except Exception as e:
                st.error(f"Classification error for {role}: {e}")
                cls, per_row, per_row_items = [], [], []

            items_by_original_row = {}
            non_empty_rows = [
                (i, str(v)) for i, v in df[col].dropna().items()
            ]
            for index, items in zip(
                [i for i, _ in non_empty_rows],
                per_row_items,
            ):
                items_by_original_row[index] = items

            analysis[role] = {
                "classified": cls,
                "per_row": per_row,
                "per_row_items": per_row_items,
                "items_by_original_row": items_by_original_row,
                "col_name": col,
            }
    else:
        for role, col in [
            ("PF", col_pf),
            ("SF", col_sf),
            ("PR", col_pr),
        ]:
            try:
                cls, per_row, per_row_items = run_offline_classification(
                    df, col, included_shorts
                )
            except Exception as e:
                st.error(f"Offline classification error for {role}: {e}")
                cls, per_row, per_row_items = [], [], []

            items_by_original_row = {}
            non_empty_rows = [
                (i, v) for i, v in df[col].dropna().items()
            ]
            for index, items in zip(
                [i for i, _ in non_empty_rows],
                per_row_items,
            ):
                items_by_original_row[index] = items

            analysis[role] = {
                "classified": cls,
                "per_row": per_row,
                "per_row_items": per_row_items,
                "items_by_original_row": items_by_original_row,
                "col_name": col,
            }

    # ========================================================
    # GLOBAL CALCULATION
    # ========================================================

    f_pf_agg, _, _ = calculate_fo_real_aggregate(
        analysis["PF"]["classified"], n_input
    )
    f_sf_agg, _, _ = calculate_fo_real_aggregate(
        analysis["SF"]["classified"], n_input
    )
    f_pr_agg, _, _ = calculate_fo_real_aggregate(
        analysis["PR"]["classified"], n_input
    )

    if is_summary:
        f_pr_agg = min(f_pr_agg, f_sf_agg * 1.5)

    sigma_total = sigma_deg(f_sf_agg, f_pr_agg, f_pf_agg)
    W_EU, eta, loss = calculate_energy(sigma_total)

    # ========================================================
    # OVERALL RESULTS
    # ========================================================

    st.markdown("## 🎯 Overall Results")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Stress intensity", f"{sigma_total:.2f} °S", rate_sigma(sigma_total))
    m2.metric("Efficiency", f"{eta:.1f} %")
    m3.metric("Energy loss", f"{loss:.0f} Kcal")
    m4.metric("Sample (N)", n_input)

    st.progress(min(sigma_total / 90.0, 1.0))

    # ========================================================
    # BREAKDOWN BY UNIT
    # ========================================================

    st.divider()

    f_pf_cat = compute_category_factors(
        analysis["PF"]["classified"], n_input, active_categories, weighting_mode
    )
    f_sf_cat = compute_category_factors(
        analysis["SF"]["classified"], n_input, active_categories, weighting_mode
    )
    f_pr_cat = compute_category_factors(
        analysis["PR"]["classified"], n_input, active_categories, weighting_mode
    )

    sig_total_arg = min(
        sigma_argument(f_sf_agg, f_pr_agg, f_pf_agg), 1.0
    )

    cat_sigmas, _ = compute_category_sigmas(
        f_sf_cat, f_pf_cat, f_pr_cat,
        sig_total_arg, is_summary, active_categories,
    )

    rows = []
    for cat, data in cat_sigmas.items():
        rows.append({
            "Unit": CATEGORY_SHORT[cat],
            "σ (°S)": round(data["sigma"], 2),
            "Share (%)": round(data["weight_share"] * 100, 1),
            "Rating": rate_sigma(data["sigma"]),
        })

    res_df = (
        pd.DataFrame(rows)
        .sort_values(by="σ (°S)", ascending=False)
    )

    # ========================================================
    # DISTRIBUTION BY SCIENTIFIC UNIT
    # ========================================================

    st.markdown("### Distribution by Scientific Unit")

    col_left, col_right = st.columns([1, 1])

    unit_fig = px.bar(
        res_df,
        x="Unit",
        y="σ (°S)",
        color="σ (°S)",
        color_continuous_scale="Reds",
        height=300,
        title="Stress intensity by scientific unit",
    )

    with col_left:
        st.dataframe(res_df, use_container_width=True, hide_index=True)

    with col_right:
        if chart_mode in ("Bar chart", "Both"):
            st.plotly_chart(unit_fig, use_container_width=True)
        if chart_mode in ("Treemap (colorful)", "Both"):
            unit_treemap_fig = px.treemap(
                res_df,
                path=["Unit"],
                values="σ (°S)",
                color="σ (°S)",
                color_continuous_scale="RdYlGn_r",
                height=350,
                title="Stress profile by scientific unit",
            )
            st.plotly_chart(unit_treemap_fig, use_container_width=True)

    # ========================================================
    # TREEMAP PF / SF / PR
    # ========================================================

    st.markdown("### 🗺️ Treemap: All Phrases by Role and Unit")

    tree_rows = []
    role_labels = {
        "PF": "Positive",
        "SF": "Stress-related",
        "PR": "Suggestions",
    }

    for role, label in role_labels.items():
        freq = Counter(c for _, c in analysis[role]["classified"])
        for cat, count in freq.items():
            tree_rows.append({
                "Role": label,
                "Unit": CATEGORY_SHORT[cat],
                "Frequency": count,
            })

    role_tree_fig = None
    if tree_rows:
        tree_df = pd.DataFrame(tree_rows)
        role_tree_fig = px.treemap(
            tree_df,
            path=["Role", "Unit"],
            values="Frequency",
            color="Frequency",
            color_continuous_scale="Turbo",
            height=450,
            title="All classified phrases by role and unit",
        )
        st.plotly_chart(role_tree_fig, use_container_width=True)
    else:
        st.caption("There are no classified expressions to display in the treemap.")

    # ========================================================
    # FACTOR / OPINION NETWORK
    # ========================================================

    st.divider()
    st.markdown("## 🕸️ Factor and Opinion Network")

    st.markdown(
        """
        <div class="network-help">
        <b>Interactive network:</b>
        drag individual nodes with the mouse to reposition them.
        Use the mouse wheel to zoom, drag the background to move the
        entire network, and use the navigation controls for additional
        positioning. Larger nodes represent higher criticality.
        </div>
        """,
        unsafe_allow_html=True,
    )

    graph = build_network_data(analysis, network_nodes)
    network_fig = build_plotly_network(graph)
    interactive_network_html = build_pyvis_network(graph)
    net_df = build_network_table(graph)

    if interactive_network_html is not None:
        components.html(
            interactive_network_html,
            height=750,
            scrolling=False,
        )
        st.caption(
            "Node size = criticality. "
            "Strong links are thick solid lines, "
            "moderate links are thinner solid lines, "
            "and weak links are dashed. "
            "Links represent co-occurrence in the same "
            "respondent answer. "
            "Nodes can be freely moved with the mouse."
        )
        with st.expander("Critical Nodes / Opinions"):
            if net_df is not None:
                st.dataframe(
                    net_df,
                    use_container_width=True,
                    hide_index=True,
                )
    else:
        st.info(
            "No classified factors/opinions are available for the network."
        )

    # ========================================================
    # QUALITATIVE REVIEW
    # ========================================================

    with st.expander("🔍 Classification Details for Words/Phrases"):
        t1, t2, t3 = st.tabs([
            "🟢 Positive",
            "🔴 Stress-related",
            "🔵 Suggestions",
        ])
        for tab, role in zip([t1, t2, t3], ["PF", "SF", "PR"]):
            with tab:
                freq = Counter(
                    category for _, category in analysis[role]["classified"]
                )
                if freq:
                    st.table(
                        pd.DataFrame([
                            {
                                "Unit": CATEGORY_SHORT.get(category, category),
                                "Frequency": count,
                            }
                            for category, count in freq.items()
                        ])
                    )
                else:
                    st.caption("No classified expressions.")

                st.markdown("**Examples of classified phrases:**")
                sample = analysis[role]["classified"][:40]
                if sample:
                    sample_df = pd.DataFrame([
                        {
                            "Phrase": phrase,
                            "Unit": CATEGORY_SHORT[category],
                        }
                        for phrase, category in sample
                    ])
                    st.dataframe(
                        sample_df,
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("No examples available.")

    # ========================================================
    # HTML REPORT EXPORT
    # ========================================================

    st.divider()
    st.markdown("## 💾 Save report")
    st.caption(
        "The HTML report contains all calculations, tables, "
        "text and interactive Plotly visualizations. "
        "Slovenian and English characters "
        "(č, š, ž, Č, Š, Ž) are fully supported."
    )

    report_title = "Stress degree and kcal analysis PRO — Report"

    html_report = build_report_html(
        report_title,
        model_name,
        classification_mode,
        sigma_total,
        W_EU,
        eta,
        loss,
        n_input,
        res_df,
        unit_fig,
        role_tree_fig,
        network_fig,
        net_df,
        text_sections=[
            (
                "Method",
                (
                    "PF = positive factors; "
                    "SF = stress-related factors; "
                    "PR = suggestions/opinions. "
                    "The network is based on co-occurrence "
                    "of classified expressions within the "
                    "same respondent answer."
                ),
            ),
            (
                "Network interpretation",
                (
                    "Node size represents criticality. "
                    "Stress-related expressions receive "
                    "the highest role weight, followed by "
                    "suggestions/opinions and positive factors. "
                    "Scientific unit slope weights are also applied. "
                    "The interactive application network allows "
                    "nodes to be freely repositioned with the mouse."
                ),
            ),
        ],
    )

    st.download_button(
        "⬇️ Save Complete Report as HTML",
        data=html_report.encode("utf-8"),
        file_name="petric_stress_analysis_report.html",
        mime="text/html; charset=utf-8",
        use_container_width=True,
    )


# ============================================================
# 14. APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
