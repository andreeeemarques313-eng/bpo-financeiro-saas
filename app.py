import streamlit as st
import pandas as pd
import requests
import urllib.parse
import re
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO VISUAL ENTERPRISE — CONTRASTE ABSOLUTO & IDENTIDADE K-BPO
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Painel K-BPO | Gestão Financeira Kairós",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injeção CSS com foco cirúrgico no date_input, contraste e ocultação do header de dev
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&family=Zen+Dots&display=swap');

    /* 1. OCULTAÇÃO DA BARRA SUPERIOR DE DESENVOLVEDOR (REMOVE SHARE, GITHUB E ÍCONES) */
    header[data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
    }
    
    #MainMenu {
        visibility: hidden !important;
    }

    footer {
        visibility: hidden !important;
    }

    /* 2. FORÇA FUNDO BRANCO GERAL */
    html, body, .stApp, [data-testid="stAppViewContainer"], .main {
        background-color: #FFFFFF !important;
        font-family: 'Poppins', sans-serif !important;
        color: #1B1C1D !important;
        padding-top: 10px !important;
    }

    /* 3. BARRA LATERAL */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA !important;
        border-right: 1px solid #E5E7EB !important;
    }

    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: #1B1C1D !important;
        font-weight: 600 !important;
    }

    /* 4. PADRONIZAÇÃO TOTAL DE TODOS OS INPUTS (INCLUINDO DATE INPUT) */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="input"],
    div[data-testid="stDateInput"] > div,
    div[data-testid="stDateInput"] div[data-baseweb="input"] > div,
    div[data-testid="stDateInput"] input,
    input, select, textarea {
        background-color: #FFFFFF !important;
        color: #1B1C1D !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
    }

    /* Força texto digitado, números de data e ícones internos para preto */
    div[data-testid="stDateInput"] *,
    div[data-baseweb="select"] *,
    div[data-baseweb="input"] * {
        color: #1B1C1D !important;
        background-color: #FFFFFF !important;
        fill: #1B1C1D !important;
    }

    /* 5. CORREÇÃO DO BOTÃO NA BARRA LATERAL */
    div[data-testid="stButton"] > button {
        background-color: #1B1C1D !important;
        color: #FFFFFF !important;
        border: 1px solid #1B1C1D !important;
        border-radius: 6px !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
        width: 100% !important;
        padding: 10px 16px !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #EA3D07 !important;
        border-color: #EA3D07 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stButton"] > button * {
        color: #FFFFFF !important;
    }

    /* 6. CORREÇÃO DOS TEXTOS DO RADIO BUTTON (SEMANA VIGENTE / PERSONALIZADO) */
    div[data-testid="stRadio"] label,
    div[data-testid="stRadio"] p,
    div[data-testid="stRadio"] span,
    div[role="radiogroup"] * {
        color: #1B1C1D !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500 !important;
    }

    /* 7. TÍTULOS EM ZEN DOTS */
    .brand-title {
        font-family: 'Zen Dots', cursive, sans-serif !important;
        font-size: 24px;
        color: #1B1C1D !important;
        letter-spacing: -0.55px;
        line-height: 1.2;
        margin-bottom: 2px;
    }

    .brand-highlight {
        color: #EA3D07 !important;
    }

    .section-title {
        font-family: 'Zen Dots', cursive, sans-serif !important;
        font-size: 16px;
        color: #1B1C1D !important;
        letter-spacing: -0.55px;
        margin-top: 18px;
        margin-bottom: 12px;
    }

    /* 8. BANNER INFORMATIVO */
    .update-banner {
        background-color: #F8F9FA !important;
        border: 1px solid #E5E7EB;
        border-left: 4px solid #EA3D07;
        border-radius: 6px;
        padding: 9px 15px;
        margin-bottom: 16px;
        font-size: 13px;
        color: #1B1C1D !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .pulse-dot {
        height: 8px;
        width: 8px;
        background-color: #EA3D07;
        border-radius: 50%;
        display: inline-block;
    }

    /* 9. CAIXAS DE KPIS EM CINZA CLARO COM MÁXIMA NITIDEZ */
    .kpi-card {
        background-color: #F1F2F4 !important;
        padding: 16px 14px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #E2E4E8;
        border-left: 5px solid #EA3D07;
        min-height: 105px;
    }

    .kpi-title { 
        font-size: 11px; 
        color: #555657 !important; 
        font-weight: 700; 
        text-transform: uppercase; 
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }

    .kpi-value { 
        font-family: 'Poppins', sans-serif !important;
        font-size: clamp(16px, 1.25vw, 22px) !important; 
        color: #1B1C1D !important; 
        font-weight: 800; 
        white-space: nowrap !important;
        overflow: visible !important;
    }

    .kpi-sub { 
        font-size: 11px; 
        color: #555657 !important; 
        margin-top: 4px;
        white-space: nowrap;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONFIGURAÇÃO DE UNIDADES — MULTI-TENANT COM GIDS FIXOS
# -----------------------------------------------------------------------------
CLIENTES = {
    "Tere": {
        "nome": "Fiño House - Teresópolis (RJ)", 
        "id": "1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw",
        "gid_variaveis": "546478773",   # GID FIXO RJ
        "logo_file": "LOGO FINO HOUSE.png"
    },
    "OB": {
        "nome": "Fiño House - Minas Gerais (OB)", 
        "id": "1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw",
        "gid_variaveis": "2112595527",  # GID FIXO MG
        "logo_file": "LOGO FINO HOUSE.png"
    }
}

# -----------------------------------------------------------------------------
# 3. TRATAMENTO NUMÉRICO E PARSERS AVANÇADOS
# -----------------------------------------------------------------------------
def clean_currency(val):
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace('R$', '').replace(' ', '')
    if not s or s in ['-', '#REF!', '#N/A', 'nan', 'None']:
        return 0.0
    if '(' in s and ')' in s:
        s = '-' + s.replace('(', '').replace(')', '')
    if '.' in s and ',' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except:
        return 0.0

def format_brl(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_dates_robust(series):
    if series is None or series.empty:
        return pd.Series(dtype='datetime64[ns]')
    s = series.astype(str).str.strip().replace({'nan': None, 'None': None, '': None, 'NaT': None})
    try:
        return pd.to_datetime(s, format='mixed', dayfirst=True, errors='coerce')
    except:
        return pd.to_datetime(s, dayfirst=True, errors='coerce')

def extrair_mes_competencia(val):
    """Extrai o mês da competência aceitando datas ISO, BR, texto (Setembro, 09/2026, Set/26)."""
    if pd.isna(val):
        return None
    s = str(val).strip().upper()
    if not s or s in ['NAN', 'NONE', '']:
        return None
    
    # Mapeamento textual
    mapa_meses = {
        'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
        'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
    }
    for abrev, num in mapa_meses.items():
        if abrev in s:
            return num

    # Tenta parsing direto de data
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(dt):
            return dt.month
    except Exception:
        pass
    
    # Busca por padrões como 08/2026 ou 09/2026
    m = re.search(r'\b(0?[1-9]|1[0-2])[/.-]\d{2,4}\b', s)
    if m:
        try:
            return int(m.group(1))
        except:
            pass

    return None

def match_col(df, candidates):
    if df.empty: return None
    cols_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        clean = cand.strip().lower()
        if clean in cols_map: return cols_map[clean]
    return None

# -----------------------------------------------------------------------------
# 4. VALIDAÇÃO DE ESQUEMA DAS TABELAS
# -----------------------------------------------------------------------------
def is_valid_extrato(df):
    if df.empty or len(df.columns) < 2: return False
    cols = [str(c).strip().upper() for c in df.columns]
    if 'INDICADOR' in cols: return False
    return any('DATA' in c for c in cols) and (any('VALOR' in c for c in cols) or any('BANCO' in c for c in cols))

def is_valid_contas(df):
    if df.empty or len(df.columns) < 3: return False
    cols = [str(c).strip().upper() for c in df.columns]
    if 'INDICADOR' in cols: return False
    has_date = any('VENCIMENTO' in c or 'PAGAMENTO' in c or 'COMPETÊNCIA' in c or 'COMPETENCIA' in c for c in cols)
    has_val = any('VALOR' in c for c in cols)
    return has_date and has_val

# -----------------------------------------------------------------------------
# 5. MOTOR DE DOWNLOAD COM LEITURA SEGURA (on_bad_lines)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=10, show_spinner=False)
def read_csv_safe(url):
    try:
        df = pd.read_csv(url, on_bad_lines='skip', encoding='utf-8')
        if not df.empty and len(df.columns) >= 2:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception:
        pass
    try:
        df = pd.read_csv(url, on_bad_lines='skip', sep=None, engine='python', encoding='utf-8')
        if not df.empty and len(df.columns) >= 2:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=10, show_spinner=False)
def download_tab_robust(sheet_id, target_kind, candidate_names, manual_gid=""):
    validator = is_valid_extrato if target_kind == "extrato" else is_valid_contas

    # 1. Prioridade Absoluta: GID Direto Fixo ou Manual
    if manual_gid and str(manual_gid).strip().isdigit():
        gid_clean = str(manual_gid).strip()
        for u in [
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid_clean}",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_clean}"
        ]:
            df = read_csv_safe(u)
            if validator(df):
                return df, f"GID ({gid_clean})"

    # 2. Variações Nominais da Aba
    for name in candidate_names:
        for enc in [urllib.parse.quote(name), urllib.parse.quote_plus(name), name]:
            for u in [
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={enc}",
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={enc}"
            ]:
                df = read_csv_safe(u)
                if validator(df):
                    return df, f"Aba ('{name.strip()}')"

    return pd.DataFrame(), None

def load_data_pipeline(sheet_id, manual_var_gid=""):
    ext_names = [
        "EXTRATO BANCARIO", "EXTRATO BANCARIO ", "EXTRATO", "EXTRATO ", 
        "EXTRATO BANCÁRIO", "EXTRATO BANCÁRIO ", "Extrato Bancario"
    ]
    var_names = [
        "CONTAS VARIAVEIS", "CONTAS VARIAVEIS ", "CONTAS VARIÁVEIS", "CONTAS VARIÁVEIS ",
        "VARIAVEIS", "VARIÁVEIS", "Contas Variaveis"
    ]
    fix_names = [
        "CONTAS FIXAS", "CONTAS FIXAS ", "FIXAS", "Contas Fixas"
    ]

    df_ext, m_e = download_tab_robust(sheet_id, "extrato", ext_names)
    df_var, m_v = download_tab_robust(sheet_id, "variaveis", var_names, manual_var_gid)
    df_fix, m_f = download_tab_robust(sheet_id, "fixas", fix_names)

    return {
        "extrato": df_ext,
        "variaveis": df_var,
        "fixas": df_fix,
        "status": {
            "extrato": (not df_ext.empty, m_e, len(df_ext)),
            "variaveis": (not df_var.empty, m_v, len(df_var)),
            "fixas": (not df_fix.empty, m_f, len(df_fix))
        }
    }

# -----------------------------------------------------------------------------
# 6. BARRA LATERAL (CONTROLES E CONFIGURAÇÕES)
# -----------------------------------------------------------------------------
st.sidebar.markdown("<div style='font-family: Zen Dots; font-size: 20px; color: #1B1C1D;'>K-BPO <span style='color: #EA3D07;'>•</span></div>", unsafe_allow_html=True)
st.sidebar.caption("Gestão Financeira Estratégica")

# Logo da Fiño House na barra lateral
logo_path = CLIENTES["Tere"].get("logo_file", "")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_column_width=True)

st.sidebar.markdown("---")

unidade_chave = st.sidebar.selectbox("Unidade:", list(CLIENTES.keys()), format_func=lambda x: CLIENTES[x]["nome"])
periodo_filtro = st.sidebar.selectbox("Competência:", ["Setembro/2026", "Agosto/2026", "CONSOLIDADO DO ANO (2026)"])

# GID fixo dinâmico conforme a unidade ativa
default_gid = CLIENTES[unidade_chave].get("gid_variaveis", "")
manual_var_gid = st.sidebar.text_input(
    "🔑 GID Contas Variáveis:",
    value=default_gid,
    placeholder="Ex: 546478773 ou 2112595527",
    help="O GID desta unidade já está fixo nativamente."
)

data_ultimo_extrato = st.sidebar.date_input(
    "📅 Data do Último Extrato Bancário:",
    value=datetime.today().date(),
    format="DD/MM/YYYY",
    help="Atualiza o aviso de fechamento no topo do painel."
)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
if st.sidebar.button("🔄 Sincronizar Base de Dados"):
    st.cache_data.clear()
    st.rerun()

dados = load_data_pipeline(CLIENTES[unidade_chave]["id"], manual_var_gid)

st.sidebar.markdown("---")
st.sidebar.markdown("<small style='font-weight: 700; color: #555657;'>STATUS DAS FONTES</small>", unsafe_allow_html=True)
st_ext_ok, st_ext_mod, st_ext_rows = dados["status"]["extrato"]
st_var_ok, st_var_mod, st_var_rows = dados["status"]["variaveis"]
st_fix_ok, st_fix_mod, st_fix_rows = dados["status"]["fixas"]

st.sidebar.markdown(f"{'🟢' if st_ext_ok else '🔴'} <small>Extrato: {st_ext_rows} reg</small>", unsafe_allow_html=True)
st.sidebar.markdown(f"{'🟢' if st_var_ok else '🔴'} <small>Variáveis: {st_var_rows} reg</small>", unsafe_allow_html=True)
st.sidebar.markdown(f"{'🟢' if st_fix_ok else '🔴'} <small>Fixas: {st_fix_rows} reg</small>", unsafe_allow_html=True)

target_month = 9 if "Setembro" in periodo_filtro else (8 if "Agosto" in periodo_filtro else None)

df_ext = dados["extrato"]
df_var = dados["variaveis"]
df_fix = dados["fixas"]

# -----------------------------------------------------------------------------
# 7. PROCESSAMENTO FINANCEIRO COM ENGINE RESILIENTE
# -----------------------------------------------------------------------------

# REGRA 1: ENTRADAS EXCLUSIVAS DO EXTRATO BANCÁRIO
receita_extrato, saidas_extrato = 0.0, 0.0
df_ext_filtro = pd.DataFrame()

if not df_ext.empty:
    c_dt_e = match_col(df_ext, ['DATA', 'DATA ', 'DATA DO LANÇAMENTO', 'DATA_LANCAMENTO'])
    c_val_e = match_col(df_ext, ['VALOR', 'VALOR (R$)', 'BANCO'])
    if c_dt_e and c_val_e:
        dt_s = parse_dates_robust(df_ext[c_dt_e])
        df_ext['VALOR_NUM'] = df_ext[c_val_e].apply(clean_currency)
        df_ext['DT_S'] = dt_s
        
        # Filtro com fallback de ano
        cond_mes = (dt_s.dt.month == target_month) if target_month else True
        cond_ano = (dt_s.dt.year == 2026) if (dt_s.dt.year == 2026).any() else True
        df_ext_filtro = df_ext[cond_mes & cond_ano].copy()
        
        if not df_ext_filtro.empty:
            receita_extrato = df_ext_filtro[df_ext_filtro['VALOR_NUM'] > 0]['VALOR_NUM'].sum()
            saidas_extrato = df_ext_filtro[df_ext_filtro['VALOR_NUM'] < 0]['VALOR_NUM'].sum()

# REGRA 2: SAÍDAS FIXAS E VARIÁVEIS SOMENTE DA COMPETÊNCIA (COM PARSER MULTI-FORMATO)
def process_contas_competencia(df):
    if df.empty: return 0.0, 0.0, 0.0, pd.DataFrame()
    c_comp = match_col(df, ['Competência', 'Competencia', 'COMPETENCIA', 'COMPETÊNCIA'])
    c_pag = match_col(df, ['Data de Pagamento', 'Pagamento', 'DATA_PAGAMENTO', 'DATA PAGAMENTO'])
    c_venc = match_col(df, ['Vencimento', 'Data de Vencimento', 'Data', 'DATA_VENCIMENTO'])
    c_val = match_col(df, ['Valor', 'Valor (R$)', 'VALOR'])
    c_st = match_col(df, ['Status', 'Situação', 'STATUS', 'SITUACAO'])
    
    if c_val and c_st:
        s_pag = parse_dates_robust(df[c_pag]) if c_pag else pd.Series(index=df.index, dtype='datetime64[ns]')
        s_venc = parse_dates_robust(df[c_venc]) if c_venc else pd.Series(index=df.index, dtype='datetime64[ns]')
        
        # Extração inteligente do mês
        mes_comp_series = df[c_comp].apply(extrair_mes_competencia) if c_comp else pd.Series(index=df.index, dtype='object')
        
        # Se a competência foi identificada, usa ela; senão, usa a data de pagamento ou vencimento
        mes_final = mes_comp_series.fillna(s_pag.dt.month).fillna(s_venc.dt.month)
        
        df['DT_REF'] = s_pag.fillna(s_venc)
        df['VALOR_NUM'] = df[c_val].apply(clean_currency)
        df['ST_UP'] = df[c_st].astype(str).str.strip().str.upper()
        
        # Filtro de mês
        if target_month:
            cond = (mes_final == target_month)
        else:
            cond = pd.Series(True, index=df.index)
            
        df_f = df[cond].copy()
        
        # Filtros de Status tolerantes a sinônimos
        status_pago = df_f['ST_UP'].isin(['PAGO', 'PAGA', 'LIQUIDADO', 'CONCILIADO'])
        status_vencido = df_f['ST_UP'].isin(['VENCIDO', 'VENCIDA', 'ATRASADO', 'ATRASADA'])
        status_pendente = df_f['ST_UP'].isin(['PENDENTE', 'A VENCER', 'ABERTO'])
        
        pago = df_f[status_pago]['VALOR_NUM'].sum()
        vencido = df_f[status_vencido]['VALOR_NUM'].sum()
        a_vencer = df_f[status_pendente]['VALOR_NUM'].sum()
        
        return pago, vencido, a_vencer, df_f
    return 0.0, 0.0, 0.0, pd.DataFrame()

var_pago, var_venc, var_pend, df_var_f = process_contas_competencia(df_var)
fix_pago, fix_venc, fix_pend, df_fix_f = process_contas_competencia(df_fix)

saldo_caixa_real = receita_extrato + saidas_extrato
total_vencido_mes = var_venc + fix_venc
total_a_vencer_mes = var_pend + fix_pend
total_pendente_mes = total_vencido_mes + total_a_vencer_mes

# -----------------------------------------------------------------------------
# 8. CABEÇALHO EXECUTIVO COM LOGO E AVISO DE ATUALIZAÇÃO
# -----------------------------------------------------------------------------
col_logo, col_titulo = st.columns([1, 7])

with col_logo:
    current_logo = CLIENTES[unidade_chave].get("logo_file", "")
    if os.path.exists(current_logo):
        st.image(current_logo, width=80)
    else:
        st.markdown("<div style='font-size: 40px;'>🦊</div>", unsafe_allow_html=True)

with col_titulo:
    st.markdown(f"<div class='brand-title'>PAINEL K-BPO <span class='brand-highlight'>|</span> {CLIENTES[unidade_chave]['nome']}</div>", unsafe_allow_html=True)
    st.caption(f"Competência Ativa: **{periodo_filtro}** | Gestão de Tesouraria Integrada")

# Banner Informativo
st.markdown(f"""
    <div class="update-banner">
        <span class="pulse-dot"></span>
        <span>Os dados apresentados estão atualizados até o último envio dos extratos bancários: <strong>{data_ultimo_extrato.strftime('%d/%m/%Y')}</strong></span>
    </div>
""", unsafe_allow_html=True)

# CARDS KPIS COM FUNDO CINZA E MÁXIMO CONTRASTE
c1, c2, c3, c4, c5 = st.columns(5)
with c1: 
    st.markdown(f'<div class="kpi-card" style="border-left-color: #1B1C1D;"><div class="kpi-title">Entradas (Extrato)</div><div class="kpi-value">{format_brl(receita_extrato)}</div><div class="kpi-sub">Total Recebido</div></div>', unsafe_allow_html=True)
with c2: 
    st.markdown(f'<div class="kpi-card" style="border-left-color: #EA3D07;"><div class="kpi-title">Variáveis Pagas</div><div class="kpi-value">{format_brl(var_pago)}</div><div class="kpi-sub">Insumos & Fornecedores</div></div>', unsafe_allow_html=True)
with c3: 
    st.markdown(f'<div class="kpi-card" style="border-left-color: #555657;"><div class="kpi-title">Fixas Pagas</div><div class="kpi-value">{format_brl(fix_pago)}</div><div class="kpi-sub">Estrutura Operacional</div></div>', unsafe_allow_html=True)
with c4: 
    cor_caixa = "#10B981" if saldo_caixa_real >= 0 else "#EA3D07"
    st.markdown(f'<div class="kpi-card" style="border-left-color: {cor_caixa};"><div class="kpi-title">Resultado de Caixa</div><div class="kpi-value">{format_brl(saldo_caixa_real)}</div><div class="kpi-sub">Entradas − Saídas Extrato</div></div>', unsafe_allow_html=True)
with c5: 
    sub_pend = f"{format_brl(total_vencido_mes)} Vencidas | {format_brl(total_a_vencer_mes)} A Vencer" if total_pendente_mes > 0 else "Nenhuma Pendência"
    st.markdown(f'<div class="kpi-card" style="border-left-color: #1B1C1D;"><div class="kpi-title">Contas Pendentes</div><div class="kpi-value">{format_brl(total_pendente_mes)}</div><div class="kpi-sub">{sub_pend}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 9. AGENDA FINANCEIRA DINÂMICA (SEMANA VIGENTE SEGUNDA A DOMINGO)
# -----------------------------------------------------------------------------
st.markdown("<div class='section-title'>AGENDA FINANCEIRA VIGENTE</div>", unsafe_allow_html=True)

hoje = datetime.today()
segunda = hoje - timedelta(days=hoje.weekday())
domingo = segunda + timedelta(days=6)

ag1, ag2 = st.columns([4, 6])
with ag1:
    modo_ag = st.radio("Período da Agenda:", ["Semana Vigente (Seg a Dom)", "Intervalo Personalizado"], horizontal=True)
with ag2:
    if modo_ag == "Intervalo Personalizado":
        datas_sel = st.date_input("Intervalo de Vencimento:", value=(segunda.date(), domingo.date()))
    else:
        st.info(f"📆 **Semana Vigente:** Segunda-feira ({segunda.strftime('%d/%m/%Y')}) até Domingo ({domingo.strftime('%d/%m/%Y')})")

def extrair_pendencias(df, tipo):
    if df.empty: return pd.DataFrame()
    c_venc = match_col(df, ['Vencimento', 'Data de Vencimento', 'Data', 'DATA_VENCIMENTO'])
    c_val = match_col(df, ['Valor', 'Valor (R$)', 'VALOR'])
    c_st = match_col(df, ['Status', 'Situação', 'STATUS', 'SITUACAO'])
    c_forn = match_col(df, ['Fornecedor', 'Razão Social', 'Beneficiário', 'FORNECEDOR'])
    c_desc = match_col(df, ['Descrição', 'Descricao', 'Item', 'DESCRICAO'])
    c_cat = match_col(df, ['Categoria', 'CATEGORIA'])
    
    if c_venc and c_val and c_st:
        df_temp = df.copy()
        df_temp['VALOR_NUM'] = df_temp[c_val].apply(clean_currency)
        df_temp['VENC_DT'] = parse_dates_robust(df_temp[c_venc])
        df_temp['STATUS_UP'] = df_temp[c_st].astype(str).str.strip().str.upper()
        
        # Filtra pendências reais
        cond_aberto = df_temp['STATUS_UP'].isin(['PENDENTE', 'VENCIDO', 'A VENCER', 'ATRASADO', 'VENCIDA', 'ABERTO'])
        pendentes = df_temp[cond_aberto].copy()
        
        pendentes['Tipo de Despesa'] = tipo
        pendentes['Fornecedor_Display'] = pendentes[c_forn] if c_forn else '-'
        pendentes['Descricao_Display'] = pendentes[c_desc] if c_desc else '-'
        pendentes['Categoria_Display'] = pendentes[c_cat] if c_cat else '-'
        return pendentes
    return pd.DataFrame()

pend_var = extrair_pendencias(df_var, "Variável")
pend_fix = extrair_pendencias(df_fix, "Fixa")

df_agenda_dinamica = pd.concat([pend_var, pend_fix], ignore_index=True)

if not df_agenda_dinamica.empty:
    cond_vencido = df_agenda_dinamica['STATUS_UP'].isin(['VENCIDO', 'ATRASADO', 'VENCIDA'])
    
    if modo_ag == "Semana Vigente (Seg a Dom)":
        cond_data = (df_agenda_dinamica['VENC_DT'] >= pd.to_datetime(segunda.date())) & (df_agenda_dinamica['VENC_DT'] <= pd.to_datetime(domingo.date()))
    else:
        if isinstance(datas_sel, tuple) and len(datas_sel) == 2:
            cond_data = (df_agenda_dinamica['VENC_DT'] >= pd.to_datetime(datas_sel[0])) & (df_agenda_dinamica['VENC_DT'] <= pd.to_datetime(datas_sel[1]))
        else:
            cond_data = (df_agenda_dinamica['VENC_DT'] >= pd.to_datetime(segunda.date())) & (df_agenda_dinamica['VENC_DT'] <= pd.to_datetime(domingo.date()))
            
    df_agenda_view = df_agenda_dinamica[cond_vencido | cond_data].copy()
    
    if not df_agenda_view.empty:
        df_agenda_view['Valor Formatado'] = df_agenda_view['VALOR_NUM'].apply(format_brl)
        df_agenda_view['Data Vencimento'] = df_agenda_view['VENC_DT'].dt.strftime('%d/%m/%Y')
        
        cols_grid = ['Data Vencimento', 'Tipo de Despesa', 'Fornecedor_Display', 'Descricao_Display', 'Categoria_Display', 'Valor Formatado', 'STATUS_UP']
        col_rename = {
            'Data Vencimento': 'Vencimento',
            'Tipo de Despesa': 'Tipo',
            'Fornecedor_Display': 'Fornecedor',
            'Descricao_Display': 'Descrição',
            'Categoria_Display': 'Categoria',
            'Valor Formatado': 'Valor (R$)',
            'STATUS_UP': 'Status'
        }
        
        st.dataframe(
            df_agenda_view[cols_grid].rename(columns=col_rename).sort_values(by='Vencimento'),
            use_container_width=True
        )
        total_previsto = df_agenda_view['VALOR_NUM'].sum()
        st.error(f"💸 **Total de Pagamentos da Semana / Atrasados:** {format_brl(total_previsto)}")
    else:
        st.success("✅ Nenhum pagamento pendente registrado para a semana atual.")
else:
    st.info("Nenhuma pendência financeira encontrada.")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 10. GRÁFICOS GERENCIAIS COM EIXOS E TEXTOS DE ALTO CONTRASTE
# -----------------------------------------------------------------------------
st.markdown("<div class='section-title'>DEMONSTRATIVO GERENCIAL DE FLUXO</div>", unsafe_allow_html=True)
g1, g2 = st.columns([6, 4])

with g1:
    fig_bar = go.Figure(go.Bar(
        x=['Entradas Extrato', 'Saídas Extrato', 'Variáveis Pagas', 'Fixas Pagas', 'Resultado de Caixa'],
        y=[receita_extrato, abs(saidas_extrato), var_pago, fix_pago, saldo_caixa_real],
        marker_color=['#1B1C1D', '#555657', '#EA3D07', '#555657', cor_caixa],
        text=[format_brl(v) for v in [receita_extrato, abs(saidas_extrato), var_pago, fix_pago, saldo_caixa_real]],
        textposition='auto',
        textfont=dict(color='#FFFFFF', size=11, family='Poppins')
    ))
    fig_bar.update_layout(
        height=340, 
        margin=dict(l=10, r=10, t=25, b=25), 
        title=dict(text="Fluxo Financeiro do Período (R$)", font=dict(color="#1B1C1D", family="Poppins", size=14)),
        font=dict(family="Poppins", color="#1B1C1D"),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        xaxis=dict(
            tickfont=dict(color="#1B1C1D", size=11, family="Poppins"),
            showline=True,
            linecolor="#CBD5E1"
        ),
        yaxis=dict(
            tickfont=dict(color="#1B1C1D", size=11, family="Poppins"),
            showgrid=True,
            gridcolor="#F1F2F4"
        )
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with g2:
    if (var_pago + fix_pago) > 0:
        fig_pie = px.pie(
            names=['Contas Variáveis', 'Contas Fixas'],
            values=[var_pago, fix_pago],
            color_discrete_sequence=['#EA3D07', '#1B1C1D'],
            hole=0.45,
            title="Distribuição de Saídas Realizadas"
        )
        fig_pie.update_layout(
            height=340, 
            margin=dict(l=10, r=10, t=25, b=25),
            title=dict(font=dict(color="#1B1C1D", family="Poppins", size=14)),
            font=dict(family="Poppins", color="#1B1C1D"),
            paper_bgcolor="#FFFFFF",
            legend=dict(font=dict(color="#1B1C1D", family="Poppins"))
        )
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")
st.markdown("<div class='section-title'>BASE OPERACIONAL — LANÇAMENTOS DO PERÍODO</div>", unsafe_allow_html=True)
if not df_var_f.empty:
    df_var_view = df_var_f.copy()
    c_v_show = match_col(df_var_view, ['Valor', 'Valor (R$)'])
    if c_v_show:
        df_var_view['Valor (R$)'] = df_var_view[c_v_show].apply(clean_currency).apply(format_brl)
    drop_cols = [c for c in ['DT_REF', 'VALOR_NUM', 'ST_UP'] if c in df_var_view.columns]
    st.dataframe(df_var_view.drop(columns=drop_cols), use_container_width=True)
else:
    st.info("Nenhum lançamento de contas variáveis registrado para o filtro ativo.")
