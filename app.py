import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
import os
warnings.filterwarnings('ignore')

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(page_title='Tx Weekly Report', page_icon='📡', layout='wide')

# ── PASSWORD PROTECTION ───────────────────────────────────────────────────────
password = st.sidebar.text_input('🔑 Enter Password', type='password')
if password != 'tx@qos!2026':   # ← replace with your own password
    st.sidebar.warning('Enter password to access the dashboard.')
    st.markdown("""
        <div style='text-align:center; padding-top:150px'>
            <h1>📡 Tx Weekly Report</h1>
            <h3 style='color:#173563'>🔒 Please enter the password in the sidebar to access the dashboard.</h3>
        </div>
    """, unsafe_allow_html=True)
    st.stop()
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("<h1 style='color:#173563;text-align:center'>📡 Tx Weekly Report</h1>", unsafe_allow_html=True)

# ── FILE PATHS ────────────────────────────────────────────────────────────────
# Auto-load if running locally, fallback to upload if on cloud
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MAIN_FILE = os.path.join(BASE_DIR, 'final_data.csv')
REV_FILE  = os.path.join(BASE_DIR, 'Revenue.csv')

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('⚙️ Configuration')
    CRITICAL   = st.number_input('Critical threshold (%)', value=3.0, step=0.5)
    DEGRADED   = st.number_input('Degraded threshold (%)', value=1.0, step=0.5)
    TOP_N      = st.number_input('Top N sites', value=10, min_value=5, max_value=30, step=5)
    SITE_TYPES = ['BB', 'AGG', 'ACC']
    st.divider()
    st.subheader('📂 Data Files')

    # Smart load: auto if local, upload if cloud
    if os.path.exists(MAIN_FILE):
        st.success('✅ final_data.csv — auto loaded')
        main_source = MAIN_FILE
    else:
        st.info('Upload final_data.csv')
        main_source = st.file_uploader('final_data.csv', type='csv', key='main')

    if os.path.exists(REV_FILE):
        st.success('✅ Revenue.csv — auto loaded')
        rev_source = REV_FILE
    else:
        st.info('Upload Revenue.csv (optional)')
        rev_source = st.file_uploader('Revenue.csv', type='csv', key='rev')

# ── HELPERS ───────────────────────────────────────────────────────────────────
def pl_colors(values):
    return ['#d32f2f' if v > CRITICAL else '#f57c00' if v >= DEGRADED else '#388e3c' for v in values]

def status_label(x):
    return 'Critical' if x > CRITICAL else ('Degraded' if x >= DEGRADED else 'Healthy')

def norm_ssc(series):
    return (series.astype(str).str.strip()
            .str.replace(r'\.0$', '', regex=True)
            .str.zfill(4).str.upper())

def color_status(val):
    c = {'Critical': 'background-color:#ffd6d6',
         'Degraded': 'background-color:#fff0d6',
         'Healthy':  'background-color:#d6f0d6'}
    return c.get(val, '')

def hbar_fig(labels, values, title, xlabel, vlines=True, figsize=(10, 5)):
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.barh(list(labels), list(values), color=pl_colors(list(values)))
    ax.invert_yaxis()
    if vlines:
        ax.axvline(CRITICAL, color='red',    linestyle='--', linewidth=1.2, label=f'Critical ({CRITICAL}%)')
        ax.axvline(DEGRADED, color='orange', linestyle='--', linewidth=1.2, label=f'Degraded ({DEGRADED}%)')
        ax.legend(fontsize=8)
    mx = max(values) if len(values) > 0 and max(values) > 0 else 1
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + mx * 0.01, bar.get_y() + bar.get_height()/2,
                f'{val:.2f}' if isinstance(val, float) else str(int(val)), va='center', fontsize=8)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontweight='bold')
    plt.tight_layout()
    return fig

# ── LOAD MAIN DATA ────────────────────────────────────────────────────────────
if main_source is None:
    st.info('👈 Upload **final_data.csv** in the sidebar to get started.')
    st.stop()

@st.cache_data
def load_main(source):
    df = pd.read_csv(source)
    df['collecttime'] = pd.to_datetime(df['collecttime'], errors='coerce')
    df['packet_loss'] = pd.to_numeric(
        df['packet_loss'].astype(str).str.replace('%', '', regex=False), errors='coerce'
    ).fillna(0)
    df['Site_Type'] = df['Site_Type'].astype(str).str.strip().str.upper()
    df['ssc']       = norm_ssc(df['ssc'])
    df['vendor']    = df['vendor'].astype(str).str.strip().str.upper()
    df['PROVINCE']  = df['PROVINCE'].astype(str).str.strip()
    df.dropna(subset=['collecttime'], inplace=True)
    return df

df_raw = load_main(main_source)

# ── DATA QUALITY ──────────────────────────────────────────────────────────────
with st.expander('🔍 Data Quality Report', expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Total Rows',   f'{len(df_raw):,}')
    c2.metric('Unique Sites', f'{df_raw["OFFICIAL SITE NAME"].nunique():,}')
    c3.metric('Provinces',    df_raw['PROVINCE'].nunique())
    c4.metric('PL > 100%',   f'{(df_raw["packet_loss"] > 100).sum():,}')
    st.write(f'**Date range:** {df_raw["collecttime"].min()} → {df_raw["collecttime"].max()}')
    st.write(f'**Vendors:** {list(df_raw["vendor"].unique())}')
    st.dataframe(df_raw['Site_Type'].value_counts().reset_index(), use_container_width=False)

# ── GLOBAL FILTERS ────────────────────────────────────────────────────────────
st.markdown("### 🔎 Global Filters")
fc1, fc2, fc3, fc4 = st.columns(4)

all_provinces = sorted(df_raw['PROVINCE'].dropna().unique())
all_bb        = sorted(df_raw['BB Ring'].dropna().astype(str).unique())
all_agg       = sorted(df_raw['AGG Ring'].dropna().astype(str).unique())
all_sites     = sorted(df_raw['OFFICIAL SITE NAME'].dropna().unique())

sel_province = fc1.multiselect('Province',  all_provinces, placeholder='All provinces')
sel_bb       = fc2.multiselect('BB Ring',   all_bb,        placeholder='All BB rings')
sel_agg      = fc3.multiselect('AGG Ring',  all_agg,       placeholder='All AGG rings')
sel_site     = fc4.multiselect('Site Name', all_sites,     placeholder='All sites')

df = df_raw.copy()
if sel_province: df = df[df['PROVINCE'].isin(sel_province)]
if sel_bb:       df = df[df['BB Ring'].astype(str).isin(sel_bb)]
if sel_agg:      df = df[df['AGG Ring'].astype(str).isin(sel_agg)]
if sel_site:     df = df[df['OFFICIAL SITE NAME'].isin(sel_site)]

if len(df) == 0:
    st.warning('No data matches the selected filters. Please adjust.')
    st.stop()

active_filters = []
if sel_province: active_filters.append(f'Province: {", ".join(sel_province)}')
if sel_bb:       active_filters.append(f'BB Ring: {", ".join(sel_bb)}')
if sel_agg:      active_filters.append(f'AGG Ring: {", ".join(sel_agg)}')
if sel_site:     active_filters.append(f'Site: {", ".join(sel_site)}')
if active_filters:
    st.caption(f'🔵 Active filters — {" | ".join(active_filters)} | Rows: {len(df):,}')
else:
    st.caption(f'No filters applied — showing all {len(df):,} rows')

st.divider()

# ── RECOMPUTE AFTER FILTER ────────────────────────────────────────────────────
site_avg = (
    df.groupby(['PROVINCE', 'OFFICIAL SITE NAME'])['packet_loss']
    .mean().reset_index(name='Avg_PL')
)
site_avg['Status'] = site_avg['Avg_PL'].apply(status_label)

summary = (
    site_avg.groupby(['PROVINCE', 'Status'])['OFFICIAL SITE NAME']
    .nunique().unstack(fill_value=0).reset_index()
)
for col in ['Critical', 'Degraded', 'Healthy']:
    if col not in summary.columns: summary[col] = 0
summary['Total']          = summary[['Critical','Degraded','Healthy']].sum(axis=1)
summary['Critical_Ratio'] = (summary['Critical'] / summary['Total'] * 100).round(1)
summary['Degraded_Ratio'] = (summary['Degraded']  / summary['Total'] * 100).round(1)
summary['Healthy_Ratio']  = (summary['Healthy']   / summary['Total'] * 100).round(1)

site_meta = (
    df.drop_duplicates('OFFICIAL SITE NAME')
    .set_index('OFFICIAL SITE NAME')[['ssc', 'SITES_STATUS']]
)

def make_label(name):
    ssc    = site_meta.loc[name, 'ssc']          if name in site_meta.index else 'N/A'
    status = site_meta.loc[name, 'SITES_STATUS'] if name in site_meta.index else 'N/A'
    return f'{name}  (SSC:{ssc} | {status})'

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    '📊 1. High Level', '🔗 2. Middle Level',
    '📍 3. Detail Sites', '📈 4. Dashboard', '💰 5. Revenue Impact'
])

# ── TAB 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("<h2 style='color:#2a693d'>1. High Level Analysis</h2>", unsafe_allow_html=True)

    st.subheader('1. Top Provinces by Avg Packet Loss')
    prov_pl = (
        site_avg.groupby('PROVINCE')['Avg_PL'].mean()
        .sort_values(ascending=False).head(int(TOP_N))
    )
    st.pyplot(hbar_fig(prov_pl.index, prov_pl.values,
                       f'Top {TOP_N} Provinces — Avg Packet Loss', 'Avg PL (%)'))
    st.divider()

    st.subheader('2. Avg Packet Loss by Vendor')
    vendor_pl = (
        df.groupby('vendor')['packet_loss'].mean()
        .sort_values(ascending=False).reset_index(name='Avg_PL')
    )
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(vendor_pl['vendor'], vendor_pl['Avg_PL'],
                  color=pl_colors(vendor_pl['Avg_PL']), width=0.5, edgecolor='white')
    ax.axhline(CRITICAL, color='red',    linestyle='--', linewidth=1.2)
    ax.axhline(DEGRADED, color='orange', linestyle='--', linewidth=1.2)
    for bar, val in zip(bars, vendor_pl['Avg_PL']):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.2f}%', ha='center', fontsize=9, fontweight='bold')
    ax.set_ylabel('Avg PL (%)')
    ax.set_title('Avg Packet Loss by Vendor', fontweight='bold')
    plt.tight_layout()
    st.pyplot(fig)
    st.divider()

    st.subheader('3. Total Sites per Province')
    s = summary.sort_values('Total', ascending=False)
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(s['PROVINCE'], s['Total'], color='#1565c0')
    ax.invert_yaxis()
    for bar, val in zip(bars, s['Total']):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                str(int(val)), va='center', fontsize=9)
    ax.set_xlabel('Number of Unique Sites')
    ax.set_title('Total Sites per Province', fontweight='bold')
    plt.tight_layout()
    st.pyplot(fig)
    st.divider()

    st.subheader('4+5. Critical & Degraded Sites by Province')
    s = summary.sort_values('Critical', ascending=False)
    x, w = range(len(s)), 0.4
    fig, ax = plt.subplots(figsize=(16, 7))
    bars_c = ax.bar([i - w/2 for i in x], s['Critical'], width=w, color='#c84545', label='Critical (>3%)')
    bars_d = ax.bar([i + w/2 for i in x], s['Degraded'], width=w, color='#e38c35', label='Degraded (1-3%)')
    for bar, cnt, ratio in zip(bars_c, s['Critical'], s['Critical_Ratio']):
        if cnt > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    f'{cnt}\n({ratio}%)', ha='center', va='bottom', fontsize=7, color='#c84545')
    for bar, cnt, ratio in zip(bars_d, s['Degraded'], s['Degraded_Ratio']):
        if cnt > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    f'{cnt}\n({ratio}%)', ha='center', va='bottom', fontsize=7, color='#b35000')
    ax.set_xticks(list(x))
    ax.set_xticklabels(s['PROVINCE'], rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('Number of Sites')
    ax.set_title('Critical & Degraded Sites by Province', fontweight='bold')
    ax.legend()
    plt.tight_layout()
    st.pyplot(fig)
    st.divider()

    st.subheader('6. Healthy Sites per Province')
    s = summary.sort_values('Healthy', ascending=False)
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(s['PROVINCE'], s['Healthy'], color='#388e3c')
    ax.invert_yaxis()
    for bar, cnt, ratio in zip(bars, s['Healthy'], s['Healthy_Ratio']):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f'{cnt} ({ratio}%)', va='center', fontsize=9)
    ax.set_xlabel('Number of Healthy Sites')
    ax.set_title('Healthy Sites per Province (Avg PL < 1%)', fontweight='bold')
    plt.tight_layout()
    st.pyplot(fig)

# ── TAB 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("<h2 style='color:#2a693d'>2. Middle Level Analysis</h2>", unsafe_allow_html=True)

    def ring_fig(ring_col, title):
        data = (
            df.groupby(ring_col)['packet_loss'].mean()
            .sort_values(ascending=False).head(int(TOP_N)).reset_index(name='Avg_PL')
        )
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.barh(data[ring_col], data['Avg_PL'], color=pl_colors(data['Avg_PL']))
        ax.invert_yaxis()
        ax.axvline(CRITICAL, color='red',    linestyle='--', linewidth=1.2, label=f'Critical ({CRITICAL}%)')
        ax.axvline(DEGRADED, color='orange', linestyle='--', linewidth=1.2, label=f'Degraded ({DEGRADED}%)')
        for bar, val in zip(bars, data['Avg_PL']):
            ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2,
                    f'{val:.2f}%', va='center', fontsize=9)
        ax.set_xlabel('Avg Packet Loss (%)')
        ax.set_title(title, fontweight='bold')
        ax.legend()
        plt.tight_layout()
        return fig, data

    st.subheader('7. Top BB Rings')
    fig, data = ring_fig('BB Ring', f'Top {TOP_N} BB Rings — Avg Packet Loss')
    st.pyplot(fig)
    st.dataframe(data, use_container_width=True)
    st.divider()

    st.subheader('8. Top AGG Rings')
    fig, data = ring_fig('AGG Ring', f'Top {TOP_N} AGG Rings — Avg Packet Loss')
    st.pyplot(fig)
    st.dataframe(data, use_container_width=True)

# ── TAB 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("<h2 style='color:#2a693d'>3. Detail Site Status</h2>", unsafe_allow_html=True)

    st.subheader(f'9. Top {TOP_N} Sites — Avg Packet Loss')
    top_sites = (
        df.groupby(['OFFICIAL SITE NAME','HOP1','PROVINCE','vendor','Site_Type'])['packet_loss']
        .mean().sort_values(ascending=False).head(int(TOP_N))
        .reset_index(name='Avg_PL')
    )
    top_sites['Avg_PL'] = top_sites['Avg_PL'].round(2)
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(top_sites['OFFICIAL SITE NAME'], top_sites['Avg_PL'],
                   color=pl_colors(top_sites['Avg_PL']))
    ax.invert_yaxis()
    ax.axvline(CRITICAL, color='red',    linestyle='--', linewidth=1.2)
    ax.axvline(DEGRADED, color='orange', linestyle='--', linewidth=1.2)
    for bar, val in zip(bars, top_sites['Avg_PL']):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                f'{val:.2f}%', va='center', fontsize=9)
    ax.set_xlabel('Avg Packet Loss (%)')
    ax.set_title(f'Top {TOP_N} Sites — Avg Packet Loss', fontweight='bold')
    plt.tight_layout()
    st.pyplot(fig)
    st.dataframe(top_sites[['OFFICIAL SITE NAME','PROVINCE','vendor','Site_Type','HOP1','Avg_PL']],
                 use_container_width=True)
    st.divider()

    st.subheader('12. Site Status Table — All High PL Sites')
    all_top_sites = []
    for s_type in SITE_TYPES:
        all_top_sites.extend(
            df[df['Site_Type'] == s_type]
            .groupby('OFFICIAL SITE NAME')['packet_loss']
            .mean().sort_values(ascending=False).head(int(TOP_N)).index.tolist()
        )
    all_top_sites = list(dict.fromkeys(all_top_sites))

    status_df = (
        df[df['OFFICIAL SITE NAME'].isin(all_top_sites)]
        .drop_duplicates('OFFICIAL SITE NAME')
        [['OFFICIAL SITE NAME','ssc','vendor','PROVINCE','Site_Type',
          'BB Ring','AGG Ring','ACC Ring','SITES_STATUS']].copy()
    )
    status_df['ssc'] = norm_ssc(status_df['ssc'])
    avg_pl_map = df.groupby('OFFICIAL SITE NAME')['packet_loss'].mean().round(2).reset_index(name='Avg_PL')
    status_df  = status_df.merge(avg_pl_map, on='OFFICIAL SITE NAME', how='left')
    status_df['PL_Status'] = status_df['Avg_PL'].apply(status_label)
    status_df  = status_df.sort_values(['Site_Type','Avg_PL'], ascending=[True, False]).reset_index(drop=True)

    st.dataframe(
        status_df.style.map(color_status, subset=['PL_Status']),
        use_container_width=True
    )

# ── TAB 4 ─────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("<h2 style='color:#2a693d'>4. Dashboard — Top 10 per Site Type</h2>", unsafe_allow_html=True)
    grid_color = '#e0e0e0'

    st.subheader('Ranking — Avg PL by Site Type')
    fig, axes = plt.subplots(1, 3, figsize=(28, 8))
    plt.subplots_adjust(wspace=0.7)
    for col, s_type in enumerate(SITE_TYPES):
        type_df = df[df['Site_Type'] == s_type]
        top10   = (
            type_df.groupby('OFFICIAL SITE NAME')['packet_loss']
            .mean().sort_values(ascending=False).head(int(TOP_N))
        )
        ax = axes[col]
        if not top10.empty:
            labeled = top10.rename(index=make_label)
            bars = ax.barh(labeled.index, labeled.values, color=pl_colors(labeled.values))
            ax.invert_yaxis()
            ax.axvline(CRITICAL, color='red',    linestyle='--', linewidth=1)
            ax.axvline(DEGRADED, color='orange', linestyle='--', linewidth=1)
            for bar, val in zip(bars, labeled.values):
                ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2,
                        f'{val:.2f}%', va='center', fontsize=8, fontweight='bold')
            ax.set_title(f'Top {TOP_N} {s_type} Sites', fontsize=12, fontweight='bold')
            ax.set_xlabel('Avg PL (%)')
            ax.grid(axis='x', linestyle='--', alpha=0.5, color=grid_color)
        else:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center')
    plt.tight_layout()
    st.pyplot(fig)
    st.divider()

    st.subheader('Raw PL Trend per Site Type')
    for s_type in SITE_TYPES:
        st.markdown(f'**{s_type} Sites**')
        type_df     = df[df['Site_Type'] == s_type]
        top10_names = (
            type_df.groupby('OFFICIAL SITE NAME')['packet_loss']
            .mean().sort_values(ascending=False).head(int(TOP_N)).index.tolist()
        )
        fig, ax = plt.subplots(figsize=(16, 6))
        if top10_names:
            trend = type_df[type_df['OFFICIAL SITE NAME'].isin(top10_names)].sort_values('collecttime')
            for name in top10_names:
                d = trend[trend['OFFICIAL SITE NAME'] == name]
                ax.plot(d['collecttime'], d['packet_loss'], label=make_label(name),
                        marker='.', markersize=2, linewidth=1.5, alpha=0.8)
            ax.axhline(CRITICAL, color='red',    linestyle='--', linewidth=1)
            ax.axhline(DEGRADED, color='orange', linestyle='--', linewidth=1)
            ax.set_ylabel('Packet Loss (%)')
            ax.grid(True, linestyle='--', alpha=0.4, color=grid_color)
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=7, frameon=True)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
        else:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center')
        ax.set_title(f'{s_type} — Raw PL Trend', fontsize=13, fontweight='bold')
        plt.tight_layout(rect=[0, 0.12, 1, 1])
        st.pyplot(fig)

# ── TAB 5 ─────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown("<h2 style='color:#2a693d'>5. Revenue Impact</h2>", unsafe_allow_html=True)

    if rev_source is None:
        st.info('👈 Upload **Revenue.csv** in the sidebar to see this section.')
        st.stop()

    @st.cache_data
    def load_revenue(source):
        r = pd.read_csv(source)
        r.columns = r.columns.str.strip()
        site_col  = r.columns[0]
        r[site_col] = norm_ssc(r[site_col])
        month_cols  = [c for c in r.columns if c != site_col and r[c].notna().any()]
        return r, site_col, month_cols

    rev_df, site_code_col, month_cols = load_revenue(rev_source)
    selected_month = st.selectbox('Select revenue month', month_cols, index=len(month_cols)-1)

    rev_lookup = (
        rev_df[[site_code_col, selected_month]]
        .dropna(subset=[selected_month])
        .set_index(site_code_col)[selected_month]
        .apply(lambda x: pd.to_numeric(str(x).replace(',', ''), errors='coerce') or 0)
        .to_dict()
    )

    ssc_lookup = (
        df.drop_duplicates('OFFICIAL SITE NAME')
        .set_index('OFFICIAL SITE NAME')['ssc']
        .apply(lambda x: norm_ssc(pd.Series([x])).iloc[0])
        .to_dict()
    )

    matched = sum(1 for ssc in ssc_lookup.values() if ssc in rev_lookup)
    st.info(f'SSC match: **{matched} / {len(ssc_lookup)}** sites have revenue data for {selected_month}')

    fig, axes = plt.subplots(1, 3, figsize=(28, 9))
    plt.subplots_adjust(wspace=0.6)
    for ax, s_type in zip(axes, SITE_TYPES):
        top10 = (
            df[df['Site_Type'] == s_type]
            .groupby('OFFICIAL SITE NAME')['packet_loss']
            .mean().sort_values(ascending=False).head(int(TOP_N))
        )
        rev_vals, labels, bar_colors, flags = [], [], [], []
        for name, avg_pl in top10.items():
            ssc    = ssc_lookup.get(name, '')
            rev    = rev_lookup.get(ssc, 0)
            status = site_meta.loc[name, 'SITES_STATUS'] if name in site_meta.index else 'N/A'
            rev_vals.append(rev)
            labels.append(f'{name}  (SSC:{ssc} | {status})')
            bar_colors.append('#c84545' if avg_pl > CRITICAL else '#e38c35' if avg_pl >= DEGRADED else '#388e3c')
            flags.append('No Revenue!' if rev == 0 else '')

        bars = ax.barh(labels, rev_vals, color=bar_colors, edgecolor='white')
        ax.invert_yaxis()
        ax.set_title(f'{s_type} — Revenue ({selected_month})', fontsize=12, fontweight='bold')
        ax.set_xlabel('Revenue')
        ax.grid(axis='x', linestyle='--', alpha=0.5)
        for bar, val, flag in zip(bars, rev_vals, flags):
            ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2,
                    f' {val:,.0f}', va='center', fontsize=8, fontweight='bold')
            if flag:
                ax.text(0.02, bar.get_y() + bar.get_height()/2, f'⚠ {flag}',
                        va='center', fontsize=7.5, color='#b71c1c', transform=ax.get_yaxis_transform())
        ax.text(0.99, 0.01, 'Red=Critical  Orange=Degraded  Green=Healthy',
                transform=ax.transAxes, fontsize=7, ha='right', va='bottom', color='gray')

    plt.suptitle(f'Revenue Impact of High Loss Sites ({selected_month})', fontsize=14, fontweight='bold')
    plt.tight_layout()
    st.pyplot(fig)
    st.divider()

    st.subheader('Detail Table — High PL Sites with Revenue')
    all_top = []
    for s_type in SITE_TYPES:
        all_top.extend(
            df[df['Site_Type'] == s_type]
            .groupby('OFFICIAL SITE NAME')['packet_loss']
            .mean().sort_values(ascending=False).head(int(TOP_N)).index.tolist()
        )
    all_top = list(dict.fromkeys(all_top))

    tbl = (
        df[df['OFFICIAL SITE NAME'].isin(all_top)]
        .drop_duplicates('OFFICIAL SITE NAME')
        [['OFFICIAL SITE NAME','ssc','vendor','PROVINCE','Site_Type',
          'BB Ring','AGG Ring','ACC Ring','SITES_STATUS']].copy()
    )
    tbl['ssc'] = norm_ssc(tbl['ssc'])
    avg_pl_map = df.groupby('OFFICIAL SITE NAME')['packet_loss'].mean().round(2).reset_index(name='Avg_PL')
    tbl = tbl.merge(avg_pl_map, on='OFFICIAL SITE NAME', how='left')
    tbl['PL_Status'] = tbl['Avg_PL'].apply(status_label)
    tbl['Revenue']   = tbl['ssc'].map(rev_lookup).fillna(0).apply(
        lambda x: pd.to_numeric(str(x).replace(',', ''), errors='coerce') or 0
    )
    tbl = tbl.sort_values(['Site_Type','Avg_PL'], ascending=[True, False]).reset_index(drop=True)

    st.dataframe(
        tbl.style.map(color_status, subset=['PL_Status']),
        use_container_width=True
    )
