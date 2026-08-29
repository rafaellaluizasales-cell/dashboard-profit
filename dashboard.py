import streamlit as st
import subprocess
import sys

# --- FALLBACK INSTALLER ---
try:
    import gspread
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gspread", "oauth2client"])
    import gspread

import pandas as pd
import datetime

# --- Modules ---
from utils import data_loader
from utils import metrics as m
from tabs import resumo, operacoes, graficos, calendario, ativos, relatorio, mentoria, swing, opcoes, risk

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Relatório de Performance - ProfitPro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- AUTHENTICATION ---
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        input_pass = st.session_state["password"]
        if input_pass == "123456":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Digite a senha de acesso ao Dashboard", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Senha incorreta. Digite novamente", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Senha incorreta.")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()

# --- PRIVACY LOGIC ---
if "hide_values" not in st.session_state:
    st.session_state["hide_values"] = False

def mask_val(val, val_type="money"):
    if not st.session_state["hide_values"]:
        return val
    
    if val_type == "money":
        return "R$ ••••"
    elif val_type == "text":
        return "••••"
    elif val_type == "time":
        return "••:••"
    return "••••"

# --- CSS STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Outfit:wght@500;700&display=swap');

    :root {
        --glass-bg: rgba(255, 255, 255, 0.03);
        --glass-border: rgba(255, 255, 255, 0.08);
        --accent: #00aaff;
        --success: #00fa9a;
        --danger: #ff4d4d;
    }

    * { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Outfit', sans-serif; }

    /* Glass Cards */
    .glass-card {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid var(--glass-border);
        border-radius: 12px;
        padding: 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 20px;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        border-color: rgba(0, 170, 255, 0.3);
    }
    .glass-label {
        font-size: 0.75em;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #888;
        font-weight: 600;
        display: block;
        margin-bottom: 8px;
    }
    .glass-value {
        font-size: 1.8em;
        font-weight: 700;
        color: #fff;
        margin-bottom: 4px;
        font-family: 'Outfit', sans-serif;
    }
    .glass-subtitle {
        font-size: 0.85em;
        color: #666;
    }

    /* Metric Containers Overrides */
    div[data-testid="metric-container"] {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: 12px;
        padding: 15px;
    }

    /* ProfitPro Specific Colors */
    .profit-val { color: var(--success) !important; font-weight: bold; }
    .loss-val { color: var(--danger) !important; font-weight: bold; }
    .neutral-val { color: #888 !important; font-weight: bold; }
    
    /* Tabs Sidebar / Nav */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 10px; 
        border-bottom: 1px solid var(--glass-border);
        padding-bottom: 5px;
    }
    .stTabs [data-baseweb="tab"] { 
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] { 
        background-color: rgba(0, 170, 255, 0.1);
        color: var(--accent) !important;
    }

    /* Hide redundant elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Custom Grid Layout */
    .grid-row { 
        display: flex; 
        justify-content: space-between; 
        border-bottom: 1px solid rgba(255,255,255,0.05); 
        padding: 12px 0; 
        font-size: 0.9em; 
    }
    .grid-label { color: #888; }
    .grid-value { font-weight: 600; text-align: right; }
</style>
""", unsafe_allow_html=True)

# Sidebar: Refresh Button
with st.sidebar:
    st.markdown("### Configurações")
    if st.button("🔄 Recarregar Dados"):
        st.cache_data.clear()
        # Full session state clear to be 100% sure
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    if 'last_refresh' in st.session_state:
        st.caption(f"Última atualização: {st.session_state['last_refresh']}")
    
    # Debug Expander for data verification
    st.markdown("---")
    st.caption(f"🚀 **Versão:** `2.3.9-stable` | **Sync:** ✅")
    
    if 'df_raw' in st.session_state and not st.session_state['df_raw'].empty:
        with st.sidebar.expander("🔍 Debug de Sincronização"):
            df = st.session_state['df_raw']
            st.write("**Padrões encontrados na planilha:**")
            pats = df['RealPattern_View'].unique().tolist()
            for p in sorted(pats):
                st.write(f"- {p}")
            st.info("Se você deletou um nome na planilha e ele ainda aparece aqui, verifique se a coluna 'Setup Real' também foi limpa.")

# --- LOAD DATA (Session State Caching) ---
if 'df_raw' not in st.session_state:
    with st.spinner("Carregando dados..."):
        try:
            st.session_state['df_raw'], st.session_state['col_map'] = data_loader.load_data()
            st.session_state['df_swing'] = data_loader.load_swing_trade_data()
            st.session_state['last_refresh'] = datetime.datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            st.error(f"Erro no carregamento: {e}")
            st.stop()

df_raw = st.session_state['df_raw']
col_map = st.session_state['col_map']

if df_raw.empty:
    st.error("Erro ao carregar os dados. Verifique a conexão ou a URL do Google Sheets.")
    st.stop()

# --- TOP BAR FILTERS ---
c_filter1, c_filter2, c_filter3, c_spacer = st.columns([1.5, 1.5, 2, 6])

with c_filter1:
    ativo_col = col_map.get('Ativo', 'Ativo')
    if ativo_col in df_raw.columns:
        assets = sorted(df_raw[ativo_col].astype(str).unique())
        selected_asset = st.selectbox("Ativo", ["Todos"] + assets)
    else:
        selected_asset = "Todos"

with c_filter2:
    period_options = ["Hoje", "Esta Semana", "Este Mês", "Semana Passada", "Mês Passado", "2026", "Total", "Personalizado"]
    # Default to Total (index 6)
    selected_period = st.selectbox("Periodicidade", period_options, index=6) 

with c_spacer:
    # Visibility Toggle (Eye Icon)
    st.markdown("<div style='margin-bottom: -30px;'></div>", unsafe_allow_html=True)
    icon = "👁️" if not st.session_state["hide_values"] else "🙈"
    label = "Ocultar Valores" if not st.session_state["hide_values"] else "Mostrar Valores"
    if st.button(f"{icon} {label}", help="Alternar visibilidade de dados sensíveis"):
        st.session_state["hide_values"] = not st.session_state["hide_values"]
        st.rerun()

# Date Logic
today = datetime.date.today()
start_date = df_raw['Date'].min()
end_date = df_raw['Date'].max()

if selected_period == "Hoje":
    start_date = end_date = today
elif selected_period == "Esta Semana":
    start_date = today - datetime.timedelta(days=today.weekday()) # Monday
    end_date = today
elif selected_period == "Este Mês":
    start_date = today.replace(day=1)
    end_date = today
elif selected_period == "Semana Passada":
    end_date = today - datetime.timedelta(days=today.weekday() + 1)
    start_date = end_date - datetime.timedelta(days=6)
elif selected_period == "Mês Passado":
    end_date = today.replace(day=1) - datetime.timedelta(days=1)
    start_date = end_date.replace(day=1)
elif selected_period == "2026":
    start_date = datetime.date(2026, 1, 1)
    end_date = datetime.date(2026, 12, 31)
elif selected_period == "Personalizado":
    with c_filter3:
        d_range = st.date_input("Intervalo", [start_date, end_date])
        if len(d_range) == 2: start_date, end_date = d_range

st.caption(f"Filtro: {start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')} ({selected_period})")

# Filter DataFrame
mask = (df_raw['Date'] >= start_date) & (df_raw['Date'] <= end_date)
if selected_asset != "Todos" and ativo_col in df_raw.columns: 
    mask = mask & (df_raw[ativo_col] == selected_asset)
df = df_raw[mask].copy()

# Calculate Metrics for Shared Use
metrics = m.calculate_metrics(df)

# --- NAVIGATION ---
tab_options = ["🏠 Resumo", "📊 Swing Trade", "💰 Gastos", "📢 Mentoria", "⚡ Day Trade", "🛡️ Risco", "📈 Gráficos", "🌍 Ativos", "📅 Calendário", "📝 Relatórios", "💎 Opções"]
if "selected_main_tab" not in st.session_state: 
    st.session_state.selected_main_tab = "🏠 Resumo"
else:
    # Migrate old names to names with emojis for compatibility
    mapping = {
        "Resumo": "🏠 Resumo",
        "Mentoria": "📢 Mentoria",
        "Operações": "⚡ Day Trade",
        "Day Trade": "⚡ Day Trade",
        "Gráficos": "📈 Gráficos",
        "Ativos": "🌍 Ativos",
        "Calendário": "📅 Calendário",
        "Relatórios": "📝 Relatórios"
    }
    if st.session_state.selected_main_tab in mapping:
        st.session_state.selected_main_tab = mapping[st.session_state.selected_main_tab]

# Use radio for persistence
selected_main_tab = st.radio("Navegação Principal", tab_options, horizontal=True, label_visibility="collapsed", key="selected_main_tab")
st.markdown("---")

# --- RENDER TABS ---
if selected_main_tab == "🏠 Resumo":
    resumo.render(df, metrics, mask_val)

elif selected_main_tab == "📊 Swing Trade":
    swing.render(st.session_state.get('df_swing', pd.DataFrame()), mask_val)

elif selected_main_tab == "💰 Gastos":
    try:
        from tabs import gastos
        gastos.render(mask_val)
    except ImportError:
        st.error("ERRO CRÍTICO: O módulo `gspread` não foi encontrado!")
        st.info("Por favor, verifique se o arquivo `requirements.txt` foi sincronizado corretamente com o GitHub.")
        if st.button("Tentar instalar manualmente agora (Experimental)"):
            with st.spinner("Instalando gspread..."):
                subprocess.check_call([sys.executable, "-m", "pip", "install", "gspread", "oauth2client"])
                st.success("Instalado! Por favor, recarregue a página (F5).")

elif selected_main_tab == "📢 Mentoria":
    mentoria.render()

elif selected_main_tab == "⚡ Day Trade":
    operacoes.render(df, df_raw, mask_val)

elif selected_main_tab == "🛡️ Risco":
    risk.render()

elif selected_main_tab == "📈 Gráficos":
    graficos.render(df, df_raw)

elif selected_main_tab == "🌍 Ativos":
    ativos.render(df)

elif selected_main_tab == "📅 Calendário":
    calendario.render(df_raw, selected_asset)

elif selected_main_tab == "📝 Relatórios":
    relatorio.render()

elif selected_main_tab == "💎 Opções":
    opcoes.render()
# --- REBUILD TRIGGER ---
# Last Sync: 2026-03-06 07:35 BRT
# Version: 2.2.1-stable
