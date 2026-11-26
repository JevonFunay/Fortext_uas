"""
Sistem desain dan konfigurasi kustomisasi UI untuk Tugas A Forensic Text.

File ini memisahkan seluruh token tampilan (warna, tipografi, radius, teks label,
preset ambang, dan ikon SVG) dari logika aplikasi di `app.py` agar tampilan
sangat mudah dikustomisasi cukup dari satu file ini.

Mengikuti arah desain Minimalism & Swiss Style (ui-ux-pro-max):
- Tipografi: Outfit (judul/angka) + Work Sans (teks isi) + JetBrains Mono (biner/kode)
- Kontras teks >= 4.5:1 pada permukaan terang
- Ikon vektor SVG konsisten (stroke 1.75px), tanpa emoji sebagai ikon struktural
- Mendukung `prefers-reduced-motion` dan fokus keyboard yang jelas
"""

from __future__ import annotations

from dataclasses import dataclass
import html
from typing import Dict, List, Tuple


# ======================================================================
# 1. KONFIGURASI TEKS & PRESET (UBAH DI SINI UNTUK KUSTOMISASI CEPAT)
# ======================================================================
APP_CONFIG: Dict[str, object] = {
    "page_title": "ForText — Pemeriksa Kemiripan Dokumen (Simhash)",
    "eyebrow": "FORENSIC TEXT  •  SIMHASH 64-BIT",
    "title": "Pemeriksa Kemiripan Dokumen Berita",
    "subtitle": (
        "Bandingkan artikel klarifikasi hoaks Sri Sultan HB X menghentikan MBG "
        "menggunakan sidik jari kalimat 64-bit. Menampilkan kemiripan teks secara "
        "objektif — bukan vonis plagiarisme."
    ),
    "default_theme": "Navy Editorial",
    "default_threshold": 3,
    # Preset ketelitian untuk pengguna biasa (Label, nilai K, penjelasan singkat)
    "threshold_presets": [
        ("Identik", 0, "Hanya mencocokkan kalimat dengan sidik jari 100% sama persis (0 bit berbeda)."),
        ("Standar", 3, "Standar Simhash 64-bit — toleransi beda sangat kecil (maks. 3 dari 64 bit)."),
        ("Longgar", 10, "Menangkap kalimat bertopik sama yang susunan katanya agak berbeda (maks. 10 bit)."),
    ],
}


# ======================================================================
# 2. PALET TEMA WARNA (SIAP PILIH DI APLIKASI ATAU TAMBAH PALET BARU)
# ======================================================================
@dataclass(frozen=True)
class ThemePalette:
    """Kumpulan token warna semantik untuk satu tema antarmuka."""

    name: str
    description: str
    primary: str          # Warna utama judul aksen, tombol aktif, ring fokus
    primary_soft: str     # Latar tipis beraksen warna utama
    secondary: str        # Aksen sekunder / interaksi
    background: str       # Latar halaman utama
    surface: str          # Latar kartu / kontainer
    surface_subtle: str   # Latar lembut (header tabel / kotak info)
    text: str             # Warna teks utama (kontras tinggi >= 7:1)
    text_muted: str       # Warna teks sekunder (kontras >= 4.5:1)
    border: str           # Garis pembatas kartu dan bagian
    success: str          # Status Duplikat / Cocok
    success_soft: str
    warning: str          # Status Hampir Duplikat / Catatan
    warning_soft: str
    info: str             # Status Kemiripan Rendah / Informasi
    info_soft: str
    radius_md: str = "12px"
    radius_lg: str = "16px"


THEME_PRESETS: Dict[str, ThemePalette] = {
    "Navy Editorial": ThemePalette(
        name="Navy Editorial",
        description="Navy institusional + emerald bersih (Gaya Riset & Cek Fakta)",
        primary="#1E3A5F",
        primary_soft="rgba(30, 58, 95, 0.08)",
        secondary="#2563EB",
        background="#F8FAFC",
        surface="#FFFFFF",
        surface_subtle="#F1F5F9",
        text="#0F172A",
        text_muted="#475569",
        border="#E2E8F0",
        success="#059669",
        success_soft="rgba(5, 150, 105, 0.10)",
        warning="#B45309",
        warning_soft="rgba(217, 119, 6, 0.11)",
        info="#1D4ED8",
        info_soft="rgba(37, 99, 235, 0.09)",
    ),
    "Cobalt Modern": ThemePalette(
        name="Cobalt Modern",
        description="Biru modern cerah dengan latar putih bersih",
        primary="#1D4ED8",
        primary_soft="rgba(29, 78, 216, 0.08)",
        secondary="#0EA5E9",
        background="#F8FAFC",
        surface="#FFFFFF",
        surface_subtle="#EFF6FF",
        text="#0F172A",
        text_muted="#475569",
        border="#DBEAFE",
        success="#047857",
        success_soft="rgba(4, 120, 87, 0.10)",
        warning="#B45309",
        warning_soft="rgba(217, 119, 6, 0.11)",
        info="#1E40AF",
        info_soft="rgba(30, 64, 175, 0.09)",
    ),
    "Emerald Tenang": ThemePalette(
        name="Emerald Tenang",
        description="Hijau zamrud editorial yang teduh di mata",
        primary="#065F46",
        primary_soft="rgba(6, 95, 70, 0.08)",
        secondary="#059669",
        background="#F7FAF9",
        surface="#FFFFFF",
        surface_subtle="#ECFDF5",
        text="#0F172A",
        text_muted="#475569",
        border="#D1FAE5",
        success="#047857",
        success_soft="rgba(4, 120, 87, 0.11)",
        warning="#B45309",
        warning_soft="rgba(217, 119, 6, 0.11)",
        info="#0F766E",
        info_soft="rgba(15, 118, 110, 0.09)",
    ),
    "Monokrom Swiss": ThemePalette(
        name="Monokrom Swiss",
        description="Hitam-putih minimalis bergaya publikasi Swiss",
        primary="#18181B",
        primary_soft="rgba(24, 24, 27, 0.07)",
        secondary="#3F3F46",
        background="#FAFAFA",
        surface="#FFFFFF",
        surface_subtle="#F4F4F5",
        text="#09090B",
        text_muted="#52525B",
        border="#E4E4E7",
        success="#047857",
        success_soft="rgba(4, 120, 87, 0.10)",
        warning="#B45309",
        warning_soft="rgba(217, 119, 6, 0.11)",
        info="#27272A",
        info_soft="rgba(39, 39, 42, 0.08)",
    ),
}


# ======================================================================
# 3. IKON VEKTOR SVG KONSISTEN (TANPA EMOJI STRUKTURAL)
# ======================================================================
def svg_icon(name: str, size: int = 18) -> str:
    """Mengembalikan ikon SVG inline konsisten (stroke 1.75px, aria-hidden='true')."""
    paths = {
        "fingerprint": (
            '<path d="M12 10a2 2 0 0 0-2 2c0 1.02-.1 2.51-.26 4"/>'
            '<path d="M14 13.12c0 2.38 0 6.38-1 8.88"/>'
            '<path d="M17.29 21.02c.12-.6.43-2.3.5-3.02"/>'
            '<path d="M2 12a10 10 0 0 1 18-6"/>'
            '<path d="M2 16h.01"/>'
            '<path d="M21.8 16c.2-2 .131-5.354 0-6"/>'
            '<path d="M5 19.5C5.5 18 6 15 6 12a6 6 0 0 1 .34-2"/>'
            '<path d="M8.65 22c.21-.66.45-1.32.57-2"/>'
            '<path d="M9 6.8a6 6 0 0 1 9 5.2v2"/>'
        ),
        "check": '<path d="M20 6 9 17l-5-5"/>',
        "info": (
            '<circle cx="12" cy="12" r="10"/>'
            '<path d="M12 16v-4"/>'
            '<path d="M12 8h.01"/>'
        ),
        "alert": (
            '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
            '<path d="M12 9v4"/>'
            '<path d="M12 17h.01"/>'
        ),
        "file": (
            '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
            '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
            '<path d="M10 13H8"/>'
            '<path d="M16 17H8"/>'
            '<path d="M16 13h-2"/>'
        ),
        "sliders": (
            '<line x1="4" x2="4" y1="21" y2="14"/>'
            '<line x1="4" x2="4" y1="10" y2="3"/>'
            '<line x1="12" x2="12" y1="21" y2="12"/>'
            '<line x1="12" x2="12" y1="8" y2="3"/>'
            '<line x1="20" x2="20" y1="21" y2="16"/>'
            '<line x1="20" x2="20" y1="12" y2="3"/>'
            '<line x1="2" x2="6" y1="14" y2="14"/>'
            '<line x1="10" x2="14" y1="8" y2="8"/>'
            '<line x1="18" x2="22" y1="16" y2="16"/>'
        ),
        "compare": (
            '<rect width="8" height="14" x="3" y="5" rx="2"/>'
            '<rect width="8" height="14" x="13" y="5" rx="2"/>'
        ),
    }
    body = paths.get(name, paths["info"])
    return (
        f'<svg aria-hidden="true" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.75" '
        'stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align: -3px; flex-shrink: 0;">'
        f"{body}</svg>"
    )


# ======================================================================
# 4. GENERATOR CSS BERBASIS TOKEN DESAIN
# ======================================================================
def build_theme_css(theme: ThemePalette) -> str:
    """Menghasilkan blok CSS lengkap berdasarkan ThemePalette aktif."""
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Outfit:wght@500;600;700&family=Work+Sans:wght@400;500;600&display=swap');

    :root {{
        --ft-primary: {theme.primary};
        --ft-primary-soft: {theme.primary_soft};
        --ft-secondary: {theme.secondary};
        --ft-bg: {theme.background};
        --ft-surface: {theme.surface};
        --ft-surface-subtle: {theme.surface_subtle};
        --ft-text: {theme.text};
        --ft-text-muted: {theme.text_muted};
        --ft-border: {theme.border};
        --ft-success: {theme.success};
        --ft-success-soft: {theme.success_soft};
        --ft-warning: {theme.warning};
        --ft-warning-soft: {theme.warning_soft};
        --ft-info: {theme.info};
        --ft-info-soft: {theme.info_soft};
        --ft-radius-md: {theme.radius_md};
        --ft-radius-lg: {theme.radius_lg};
        --ft-font-head: 'Outfit', 'Segoe UI', system-ui, sans-serif;
        --ft-font-body: 'Work Sans', 'Segoe UI', system-ui, sans-serif;
        --ft-font-mono: 'JetBrains Mono', Consolas, monospace;
    }}

    /* Latar & tipografi global */
    .stApp {{
        background-color: var(--ft-bg);
        color: var(--ft-text);
        font-family: var(--ft-font-body);
    }}
    [data-testid="stHeader"] {{
        background-color: rgba(248, 250, 252, 0.85);
        backdrop-filter: blur(8px);
    }}
    .block-container {{
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }}
    h1, h2, h3, h4 {{
        font-family: var(--ft-font-head) !important;
        color: var(--ft-text) !important;
        letter-spacing: -0.02em;
    }}
    p, li, label, .stMarkdown {{
        font-family: var(--ft-font-body);
        color: var(--ft-text);
    }}
    code {{
        font-family: var(--ft-font-mono) !important;
        font-size: 0.88em;
    }}

    /* Sidebar rapi & bersih */
    [data-testid="stSidebar"] {{
        background-color: var(--ft-surface);
        border-right: 1px solid var(--ft-border);
    }}
    [data-testid="stSidebar"] .block-container {{
        padding-top: 1.5rem;
    }}

    /* Tab navigasi bergaya modern Swiss */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.35rem;
        background-color: var(--ft-surface-subtle);
        padding: 0.35rem;
        border-radius: var(--ft-radius-md);
        border: 1px solid var(--ft-border);
        margin-bottom: 1.25rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-family: var(--ft-font-head);
        font-weight: 500;
        font-size: 0.96rem;
        color: var(--ft-text-muted);
        border-radius: 9px;
        padding: 0.5rem 1.05rem;
        cursor: pointer;
        transition: background-color 180ms ease, color 180ms ease, box-shadow 180ms ease;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: var(--ft-surface) !important;
        color: var(--ft-primary) !important;
        font-weight: 600;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        display: none;
    }}

    /* Tombol & fokus aksesibilitas */
    .stButton > button {{
        border-radius: 9px;
        border: 1px solid var(--ft-border);
        background-color: var(--ft-surface);
        color: var(--ft-text);
        font-family: var(--ft-font-body);
        font-weight: 500;
        cursor: pointer;
        transition: border-color 180ms ease, background-color 180ms ease, color 180ms ease;
    }}
    .stButton > button:hover {{
        border-color: var(--ft-primary);
        background-color: var(--ft-primary-soft);
        color: var(--ft-primary);
    }}
    .stButton > button:focus-visible,
    [data-baseweb="tab"]:focus-visible {{
        outline: 2px solid var(--ft-primary) !important;
        outline-offset: 2px;
    }}

    /* Header merek bersih */
    .ft-header {{
        padding: 0.25rem 0 1.1rem 0;
        border-bottom: 1px solid var(--ft-border);
        margin-bottom: 1.2rem;
    }}
    .ft-eyebrow {{
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        font-family: var(--ft-font-head);
        font-size: 0.76rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        color: var(--ft-primary);
        background-color: var(--ft-primary-soft);
        padding: 0.28rem 0.7rem;
        border-radius: 999px;
        margin-bottom: 0.65rem;
    }}
    .ft-title {{
        font-family: var(--ft-font-head);
        font-size: clamp(1.55rem, 2.6vw, 2.05rem);
        font-weight: 700;
        color: var(--ft-text);
        line-height: 1.2;
        margin: 0 0 0.4rem 0;
    }}
    .ft-subtitle {{
        font-size: 1rem;
        color: var(--ft-text-muted);
        line-height: 1.55;
        max-width: 78ch;
        margin: 0;
    }}

    /* Panduan 3 langkah untuk pengguna baru */
    .ft-steps {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 0.85rem;
        margin-top: 0.25rem;
    }}
    .ft-step {{
        background-color: var(--ft-surface);
        border: 1px solid var(--ft-border);
        border-radius: var(--ft-radius-md);
        padding: 0.95rem 1.05rem;
    }}
    .ft-step-tag {{
        font-family: var(--ft-font-head);
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--ft-primary);
        margin-bottom: 0.3rem;
    }}
    .ft-step-title {{
        font-family: var(--ft-font-head);
        font-size: 1rem;
        font-weight: 600;
        color: var(--ft-text);
        margin-bottom: 0.25rem;
    }}
    .ft-step-desc {{
        font-size: 0.9rem;
        color: var(--ft-text-muted);
        line-height: 1.5;
    }}

    /* Kartu kesimpulan hasil perbandingan */
    .ft-verdict {{
        display: grid;
        grid-template-columns: minmax(195px, 240px) 1fr;
        gap: 1.4rem;
        align-items: center;
        background-color: var(--ft-surface);
        border: 1px solid var(--ft-border);
        border-left: 5px solid var(--ft-primary);
        border-radius: var(--ft-radius-lg);
        padding: 1.3rem 1.5rem;
        margin: 0.9rem 0 1rem 0;
        box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
    }}
    @media (max-width: 760px) {{
        .ft-verdict {{
            grid-template-columns: 1fr;
            gap: 0.85rem;
        }}
    }}
    .ft-verdict--success {{ border-left-color: var(--ft-success); }}
    .ft-verdict--warning {{ border-left-color: var(--ft-warning); }}
    .ft-verdict--info {{ border-left-color: var(--ft-info); }}
    .ft-verdict--muted {{ border-left-color: var(--ft-text-muted); }}

    .ft-score-num {{
        font-family: var(--ft-font-head);
        font-size: 2.35rem;
        font-weight: 700;
        line-height: 1.05;
        color: var(--ft-text);
        margin: 0.15rem 0 0.4rem 0;
    }}
    .ft-pill {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.22rem 0.65rem;
        border-radius: 999px;
        font-family: var(--ft-font-head);
        font-size: 0.8rem;
        font-weight: 600;
    }}
    .ft-pill--success {{ background-color: var(--ft-success-soft); color: var(--ft-success); }}
    .ft-pill--warning {{ background-color: var(--ft-warning-soft); color: var(--ft-warning); }}
    .ft-pill--info {{ background-color: var(--ft-info-soft); color: var(--ft-info); }}
    .ft-pill--muted {{ background-color: var(--ft-surface-subtle); color: var(--ft-text-muted); }}

    .ft-bar-track {{
        width: 100%;
        height: 8px;
        border-radius: 999px;
        background-color: var(--ft-surface-subtle);
        overflow: hidden;
        margin-top: 0.65rem;
    }}
    .ft-bar-fill {{
        height: 100%;
        border-radius: 999px;
        transition: width 260ms ease;
    }}

    .ft-verdict-title {{
        font-family: var(--ft-font-head);
        font-size: 1.12rem;
        font-weight: 600;
        color: var(--ft-text);
        margin-bottom: 0.35rem;
    }}
    .ft-verdict-body {{
        font-size: 0.95rem;
        color: var(--ft-text-muted);
        line-height: 1.6;
    }}
    .ft-verdict-body strong {{
        color: var(--ft-text);
    }}

    /* Grid KPI bersih */
    .ft-kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
        gap: 0.8rem;
        margin-bottom: 0.75rem;
    }}
    .ft-kpi {{
        background-color: var(--ft-surface);
        border: 1px solid var(--ft-border);
        border-radius: var(--ft-radius-md);
        padding: 0.9rem 1.05rem;
    }}
    .ft-kpi-label {{
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--ft-text-muted);
        margin-bottom: 0.3rem;
    }}
    .ft-kpi-val {{
        font-family: var(--ft-font-head);
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--ft-text);
        line-height: 1.2;
    }}
    .ft-kpi-sub {{
        font-size: 0.82rem;
        color: var(--ft-text-muted);
        margin-top: 0.2rem;
    }}

    /* Kartu kalimat baca berdampingan yang rapi */
    .ft-sent {{
        background-color: var(--ft-surface);
        border: 1px solid var(--ft-border);
        border-left: 4px solid var(--ft-border);
        border-radius: 10px;
        padding: 0.72rem 0.9rem;
        margin-bottom: 0.55rem;
        font-size: 0.93rem;
        line-height: 1.55;
        color: var(--ft-text);
    }}
    .ft-sent--match {{
        border-left-color: var(--ft-success);
        background-color: var(--ft-success-soft);
    }}
    .ft-sent--cand {{
        border-left-color: var(--ft-warning);
        background-color: var(--ft-warning-soft);
    }}
    .ft-sent-meta {{
        font-family: var(--ft-font-head);
        font-size: 0.77rem;
        font-weight: 600;
        color: var(--ft-text-muted);
        margin-bottom: 0.22rem;
    }}
    .ft-sent--match .ft-sent-meta {{ color: var(--ft-success); }}
    .ft-sent--cand .ft-sent-meta {{ color: var(--ft-warning); }}

    /* Kotak judul bagian */
    .ft-section-title {{
        font-family: var(--ft-font-head);
        font-size: 1.15rem;
        font-weight: 600;
        color: var(--ft-text);
        margin: 1.35rem 0 0.35rem 0;
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }}
    .ft-section-caption {{
        font-size: 0.88rem;
        color: var(--ft-text-muted);
        margin-bottom: 0.75rem;
    }}

    /* Badge aturan ambang di sidebar */
    .ft-rule-box {{
        background-color: var(--ft-primary-soft);
        border: 1px solid var(--ft-border);
        border-radius: 10px;
        padding: 0.7rem 0.85rem;
        margin: 0.45rem 0 0.85rem 0;
        font-size: 0.86rem;
        line-height: 1.45;
        color: var(--ft-text);
    }}
    .ft-rule-box strong {{
        color: var(--ft-primary);
    }}

    /* Hormati prefers-reduced-motion */
    @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{
            transition: none !important;
            animation: none !important;
        }}
    }}
    </style>
    """


# ======================================================================
# 5. KOMPONEN HTML BERSIH & TERKAPSULASI (SEMUA TEKS DI-ESCAPE AMAN)
# ======================================================================
def render_brand_header_html() -> str:
    """Header utama minimalis dengan ikon SVG vektor."""
    return (
        '<div class="ft-header">'
        f'<div class="ft-eyebrow">{svg_icon("fingerprint", 14)} '
        f'{html.escape(str(APP_CONFIG["eyebrow"]))}</div>'
        f'<h1 class="ft-title">{html.escape(str(APP_CONFIG["title"]))}</h1>'
        f'<p class="ft-subtitle">{html.escape(str(APP_CONFIG["subtitle"]))}</p>'
        "</div>"
    )


def render_how_it_works_html() -> str:
    """Kartu 3 langkah sederhana untuk pengguna awam."""
    steps = [
        (
            "Langkah 1",
            "Pisahkan Isi Berita",
            "Judul, tanggal, dan nama penulis dipisahkan otomatis ke folder bersih agar hanya isi kalimat berita yang dibandingkan.",
        ),
        (
            "Langkah 2",
            "Buat Sidik Jari 64-Bit",
            "Setiap kalimat diberi kode (mis. D1-K1) lalu diringkas menjadi 64 angka 0 dan 1 (Simhash berbasis SHA-256).",
        ),
        (
            "Langkah 3",
            "Hitung Selisih & Persentase",
            "Jarak Hamming menghitung berapa bit yang berbeda (0 = kembar persis). Pencocokan 1-ke-1 mencegah kalimat dihitung ganda.",
        ),
    ]
    cards = "".join(
        f'<div class="ft-step">'
        f'<div class="ft-step-tag">{html.escape(tag)}</div>'
        f'<div class="ft-step-title">{html.escape(title)}</div>'
        f'<div class="ft-step-desc">{html.escape(desc)}</div>'
        f"</div>"
        for tag, title, desc in steps
    )
    return f'<div class="ft-steps">{cards}</div>'


def render_verdict_card_html(
    similarity_percent: float,
    category: str,
    headline: str,
    explanation_html: str,
    theme: ThemePalette,
    is_empty: bool = False,
) -> str:
    """Kartu ringkasan hasil perbandingan bergaya Swiss dengan bar progres visual."""
    if is_empty:
        tone = "muted"
        bar_color = theme.text_muted
        icon = svg_icon("info", 14)
    elif category == "Duplikat":
        tone = "success"
        bar_color = theme.success
        icon = svg_icon("check", 14)
    elif category == "Hampir Duplikat":
        tone = "warning"
        bar_color = theme.warning
        icon = svg_icon("alert", 14)
    else:
        tone = "info"
        bar_color = theme.info
        icon = svg_icon("info", 14)

    clamped_pct = max(0.0, min(100.0, similarity_percent))
    return (
        f'<div class="ft-verdict ft-verdict--{tone}">'
        "<div>"
        f'<span class="ft-pill ft-pill--{tone}">{icon} {html.escape(category)}</span>'
        f'<div class="ft-score-num">{similarity_percent:.2f}%</div>'
        '<div style="font-size:0.8rem; color:var(--ft-text-muted);">Tingkat Kemiripan Dokumen</div>'
        '<div class="ft-bar-track">'
        f'<div class="ft-bar-fill" style="width:{clamped_pct:.2f}%; background-color:{bar_color};"></div>'
        "</div>"
        "</div>"
        "<div>"
        f'<div class="ft-verdict-title">{html.escape(headline)}</div>'
        f'<div class="ft-verdict-body">{explanation_html}</div>'
        "</div>"
        "</div>"
    )


def render_kpi_strip_html(items: List[Tuple[str, str, str]]) -> str:
    """Baris kartu metrik KPI bersih dengan label, angka utama, dan keterangan singkat."""
    cards = "".join(
        '<div class="ft-kpi">'
        f'<div class="ft-kpi-label">{html.escape(label)}</div>'
        f'<div class="ft-kpi-val">{html.escape(value)}</div>'
        f'<div class="ft-kpi-sub">{html.escape(sub)}</div>'
        "</div>"
        for label, value, sub in items
    )
    return f'<div class="ft-kpi-grid">{cards}</div>'


def render_section_header_html(icon_name: str, title: str, caption: str = "") -> str:
    """Header bagian yang konsisten dengan ikon SVG dan subteks opsional."""
    cap_html = f'<div class="ft-section-caption">{html.escape(caption)}</div>' if caption else ""
    return (
        f'<div class="ft-section-title">{svg_icon(icon_name, 18)} '
        f"{html.escape(title)}</div>{cap_html}"
    )
