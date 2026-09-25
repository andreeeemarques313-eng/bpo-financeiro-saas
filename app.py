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

    /* OCULTAÇÃO DA BARRA SUPERIOR DE DESENVOLVEDOR */
    header[data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
    }
    #MainMenu, footer { visibility: hidden !important; }

    /* FORÇA FUNDO BRANCO GERAL */
    html, body, .stApp, [data-testid="stAppViewContainer"], .main {
        background-color: #FFFFFF !important;
        font-family: 'Poppins', sans-serif !important;
        color: #1B1C1D !important;
        padding-top: 10px !important;
    }

    /* BARRA LATERAL */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA !important;
        border-right: 1px solid #E5E7EB !important;
    }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div {
        color: #1B1C1D !important;
        font-weight: 600 !important;
    }

    /* PADRONIZAÇÃO DE INPUTS */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, div[data-baseweb="input"],
    div[data-testid="stDateInput"] > div, div[data-testid="stDateInput"] div[data-baseweb="input"] > div, div[data-testid="stDateInput"] input,
    input, select, textarea {
        background-color: #FFFFFF !important;
        color: #1B1C1D !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
    }
    div[data-testid="stDateInput"] *, div[data-baseweb="select"] *, div[data-baseweb="input"] * {
        color: #1B1C1D !important;
        background-color: #FFFFFF !important;
        fill: #1B1C1D !important;
    }

    /* BOTÃO */
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
    }
    div[data-testid="stButton"] > button * { color: #FFFFFF !important; }

    /* RADIO BUTTONS */
    div[data-testid="stRadio"] label, div[data-testid="stRadio"] p, div[data-testid="stRadio"] span, div[role="radiogroup"] * {
        color: #1B1C1D !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500 !important;
    }

    /* TÍTULOS */
    .brand-title {
        font-family: 'Zen Dots', cursive, sans-serif !important;
        font-size: 24px;
        color: #1B1C1D !important;
        letter-spacing: -0.55px;
        line-height: 1.2;
        margin-bottom: 2px;
    }
    .brand-highlight { color: #EA3D07 !important; }
    .section-title {
        font-family: 'Zen Dots', cursive, sans-serif !important;
        font-size: 16px;
        color: #1B1C1D !important;
        letter-spacing: -0.55px;
        margin-top: 18px; margin-bottom: 12px;
    }

    /* BANNER */
    .update-banner {
        background-color: #F8F9FA !important;
        border: 1px solid #E5E7EB;
        border-left: 4px solid #EA3D07;
        border-radius: 6px;
        padding: 9px 15px;
        margin-bottom: 16px;
        font-size: 13px;
        color: #1B1C1D !important;
        display: flex; align-items: center; gap: 8px;
    }
    .pulse-dot {
        height: 8px; width: 8px;
        background-color: #EA3D07;
        border-radius: 50%; display: inline-block;
    }

    /* KPIS */
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
        font-size: 11px; color: #555657 !important; font-weight: 700; 
        text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;
    }
    .kpi-value { 
        font-family: 'Poppins', sans-serif !important;
        font-size: clamp(16px, 1.25vw, 22px) !important; 
        color: #1B1C1D !important; font-weight: 800; 
        white-space: nowrap !important; overflow: visible !important;
    }
    .kpi-sub { 
        font-size: 11px; color: #555657 !important; margin-top: 4px; white-space: nowrap;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONFIGURAÇÃO DE UNIDADES — MULTI-TENANT COM GIDS FIXOS DEFINITIVOS
# -----------------------------------------------------------------------------
CLIENTES = {
    "Tere": {
        "nome": "Fiño House - Teresópolis (RJ)", 
        "id": "1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw",
        "gid_variaveis": "546478773",   # GID RJ
        "logo_file": "LOGO FINO HOUSE.png"
    },
    "OB": {
        "nome": "Fiño House - Minas Gerais (OB)", 
        "id": "1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw",
        "gid_variaveis": "1225326443",  # GID MG
        "logo_file": "LOGO FINO HOUSE.png"
    }
}

# -----------------------------------------------------------------------------
# 3. TRATAMENTO NUMÉRICO (FORÇA BRUTA) E PARSERS AVANÇADOS
# -----------------------------------------------------------------------------
def clean_currency(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    # Extrai APENAS números, vírgulas, pontos e sinais de negativo (ignora espaços ocultos)
    s = re.sub(r'[^\d.,-]', '', str(val))
    if not s or s == '-': return 0.0
    
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
    if series is None or series.empty: return pd.Series(dtype='datetime64[ns]')
    s = series.astype(str).str.strip().replace({'nan': None, 'None': None, '': None, 'NaT': None})
    try:
        return pd.to_datetime(s, format='mixed', dayfirst=True, errors='coerce')
    except:
        return pd.to_datetime(s, dayfirst=True, errors='coerce')

def extrair_mes_inteligente(val):
    if pd.isna(val): return None
    s = str(val).strip().upper()
    if not s or s in ['NAN', 'NONE', '']: return None
    
    mapa_meses = {'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6, 'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12}
    for abrev, num in mapa_meses.items():
        if abrev in s: return num

    try:
        dt = pd.to_datetime(s, format='mixed', dayfirst=True, errors='coerce')
        if pd.notna(dt): return dt.month
    except Exception:
        pass
    
    m = re.search(r'\b(0?[1-9]|1[0-2])[/.-]\d{2,4}\b', s)
    if m:
        try: return int(m.group(1))
        except: pass
    return None

def match_col(df, candidates):
    """Busca o nome correto da coluna blindando contra 'Forma de pagamento' e 'Status Conciliação'"""
    if df.empty: return None
    cols_map = {str(c).strip().lower(): c for c in df.columns}
    
    # 1. Tenta Match Exato primeiro
    for cand in candidates:
        clean = cand.strip().lower()
        if clean in cols_map: 
            return cols_map[clean]
            
    # 2. Match parcial seguro
    for cand in candidates:
        clean = cand.strip().lower()
        for k, v in cols_map.items():
            if clean in k:
                # Proteções vitais contra colisão
                if clean == 'pagamento' and 'forma' in k: continue
                if clean == 'status' and 'concilia' in k: continue
                return v
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
    return any('VALOR' in c or 'VENCIMENTO' in c or 'FORNECEDOR' in c for c in cols)

# -----------------------------------------------------------------------------
# 5. MOTOR DE DOWNLOAD COM LEITURA SEGURA
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
    return pd.DataFrame()

@st.cache_data(ttl=10, show_spinner=False)
def download_tab_robust(sheet_id, target_kind, candidate_names, manual_gid=""):
    validator = is_valid_extrato if target_kind == "extrato" else is_valid_contas

    if manual_gid and str(manual_gid).strip().isdigit():
        gid_clean = str(manual_gid).strip()
        for u in [
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid_clean}",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_clean}"
        ]:
            df = read_csv_safe(u)
            if validator(df):
                return df, f"GID ({gid_clean})"

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
    ext_names = ["EXTRATO BANCARIO", "EXTRATO", "EXTRATO BANCÁRIO", "Extrato Bancario"]
    var_names = ["CONTAS VARIAVEIS", "CONTAS VARIÁVEIS", "VARIAVEIS", "Contas Variaveis"]
    fix_names = ["CONTAS FIXAS", "FIXAS", "Contas Fixas"]

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

logo_path = CLIENTES["Tere"].get("logo_file", "")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_column_width=True)

st.sidebar.markdown("---")
unidade_chave = st.sidebar.selectbox("Unidade:", list(CLIENTES.keys()), format_func=lambda x: CLIENTES[x]["nome"])
periodo_filtro = st.sidebar.selectbox("Competência:", ["Setembro/2026", "Agosto/2026", "CONSOLIDADO DO ANO (2026)"])

default_gid = CLIENTES[unidade_chave].get("gid_variaveis", "")
manual_var_gid = st.sidebar.text_input(
    "🔑 GID Contas Variáveis:", value=default_gid, key=f"input_gid_{unidade_chave}",
    placeholder="Ex: 546478773 ou 2112595527"
)

data_ultimo_extrato = st.sidebar.date_input(
    "📅 Data do Último Extrato Bancário:", value=datetime.today().date(), format="DD/MM/YYYY"
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
# 7. PROCESSAMENTO FINANCEIRO COM ENGINE RESILIENTE BLINDADA
# -----------------------------------------------------------------------------

receita_extrato, saidas_extrato = 0.0, 0.0
if not df_ext.empty:
    c_dt_e = match_col(df_ext, ['DATA', 'DATA ', 'DATA DO LANÇAMENTO', 'DATA_LANCAMENTO'])
    c_val_e = match_col(df_ext, ['VALOR', 'VALOR (R$)', 'BANCO'])
    if c_dt_e and c_val_e:
        dt_s = parse_dates_robust(df_ext[c_dt_e])
        df_ext['VALOR_NUM'] = df_ext[c_val_e].apply(clean_currency)
        df_ext['DT_S'] = dt_s
        cond_mes = (dt_s.dt.month == target_month) if target_month else True
        df_ext_filtro = df_ext[cond_mes].copy()
        if not df_ext_filtro.empty:
            receita_extrato = df_ext_filtro[df_ext_filtro['VALOR_NUM'] > 0]['VALOR_NUM'].sum()
            saidas_extrato = df_ext_filtro[df_ext_filtro['VALOR_NUM'] < 0]['VALOR_NUM'].sum()

def process_contas_competencia(df):
    if df.empty: return 0.0, 0.0, 0.0, pd.DataFrame()
    c_comp = match_col(df, ['Competência', 'Competencia', 'MÊS', 'MES'])
    c_pag = match_col(df, ['Data de Pagamento', 'DATA_PAGAMENTO', 'Data Pagamento', 'ta de Pagame', 'Pagamento'])
    c_venc = match_col(df, ['Vencimento', 'Data de Vencimento', 'Data'])
    c_val = match_col(df, ['Valor', 'Valor (R$)', 'VALOR'])
    c_st = match_col(df, ['Status', 'Situação', 'STATUS'])
    
    if c_val and c_st:
        s_pag = parse_dates_robust(df[c_pag]) if c_pag else pd.Series(index=df.index, dtype='datetime64[ns]')
        s_venc = parse_dates_robust(df[c_venc]) if c_venc else pd.Series(index=df.index, dtype='datetime64[ns]')
        
        mes_comp = df[c_comp].apply(extrair_mes_inteligente) if c_comp else pd.Series(index=df.index, dtype='object')
        mes_pag = s_pag.dt.month
        mes_venc = s_venc.dt.month
        
        mes_final = mes_comp.fillna(mes_pag).fillna(mes_venc)
        
        df['DT_REF'] = s_pag.fillna(s_venc)
        df['VALOR_NUM'] = df[c_val].apply(clean_currency)
        df['ST_UP'] = df[c_st].astype(str).str.strip().str.upper()
        
        status_pago = df['ST_UP'].str.contains('PAG|LIQUID|CONCIL|SIM|BAIX|QUIT', regex=True, na=False)
        status_vencido = df['ST_UP'].str.contains('VENC|ATRAS', regex=True, na=False) & (~status_pago)
        status_pendente = df['ST_UP'].str.contains('PEND|ABERT|A VENCER', regex=True, na=False) & (~status_pago)
        
        if target_month:
            cond_pago_mes = status_pago & ((mes_comp == target_month) | (mes_pag == target_month) | (mes_final == target_month))
            cond_vencido_mes = status_vencido & (mes_final == target_month)
            cond_pendente_mes = status_pendente & (mes_final == target_month)
            cond_geral = (mes_final == target_month)
        else:
            cond_pago_mes = status_pago
            cond_vencido_mes = status_vencido
            cond_pendente_mes = status_pendente
            cond_geral = pd.Series(True, index=df.index)
            
        df_f = df[cond_geral].copy()
        
        pago = df[cond_pago_mes]['VALOR_NUM'].sum()
        vencido = df[cond_vencido_mes]['VALOR_NUM'].sum()
        a_vencer = df[cond_pendente_mes]['VALOR_NUM'].sum()
        
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
    if os.path.exists(current_logo): st.image(current_logo, width=80)
    else: st.markdown("<div style='font-size: 40px;'>🦊</div>", unsafe_allow_html=True)
with col_titulo:
    st.markdown(f"<div class='brand-title'>PAINEL K-BPO <span class='brand-highlight'>|</span> {CLIENTES[unidade_chave]['nome']}</div>", unsafe_allow_html=True)
    st.caption(f"Competência Ativa: **{periodo_filtro}** | Gestão de Tesouraria Integrada")

st.markdown(f"""
    <div class="update-banner"><span class="pulse-dot"></span><span>Os dados apresentados estão atualizados até o último envio dos extratos bancários: <strong>{data_ultimo_extrato.strftime('%d/%m/%Y')}</strong></span></div>
""", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f'<div class="kpi-card" style="border-left-color: #1B1C1D;"><div class="kpi-title">Entradas (Extrato)</div><div class="kpi-value">{format_brl(receita_extrato)}</div><div class="kpi-sub">Total Recebido</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="kpi-card" style="border-left-color: #EA3D07;"><div class="kpi-title">Variáveis Pagas</div><div class="kpi-value">{format_brl(var_pago)}</div><div class="kpi-sub">Insumos & Fornecedores</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="kpi-card" style="border-left-color: #555657;"><div class="kpi-title">Fixas Pagas</div><div class="kpi-value">{format_brl(fix_pago)}</div><div class="kpi-sub">Estrutura Operacional</div></div>', unsafe_allow_html=True)
with c4: 
    cor_caixa = "#10B981" if saldo_caixa_real >= 0 else "#EA3D07"
    st.markdown(f'<div class="kpi-card" style="border-left-color: {cor_caixa};"><div class="kpi-title">Resultado de Caixa</div><div class="kpi-value">{format_brl(saldo_caixa_real)}</div><div class="kpi-sub">Entradas − Saídas Extrato</div></div>', unsafe_allow_html=True)
with c5: 
    sub_pend = f"{format_brl(total_vencido_mes)} Vencidas | {format_brl(total_a_vencer_mes)} A Vencer" if total_pendente_mes > 0 else "Nenhuma Pendência"
    st.markdown(f'<div class="kpi-card" style="border-left-color: #1B1C1D;"><div class="kpi-title">Contas Pendentes</div><div class="kpi-value">{format_brl(total_pendente_mes)}</div><div class="kpi-sub">{sub_pend}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 9. AGENDA FINANCEIRA E BASE OPERACIONAL
# -----------------------------------------------------------------------------
st.markdown("<div class='section-title'>AGENDA FINANCEIRA VIGENTE</div>", unsafe_allow_html=True)
hoje = datetime.today()
segunda = hoje - timedelta(days=hoje.weekday())
domingo = segunda + timedelta(days=6)

ag1, ag2 = st.columns([4, 6])
with ag1: modo_ag = st.radio("Período da Agenda:", ["Semana Vigente (Seg a Dom)", "Intervalo Personalizado"], horizontal=True)
with ag2:
    if modo_ag == "Intervalo Personalizado": datas_sel = st.date_input("Intervalo de Vencimento:", value=(segunda.date(), domingo.date()))
    else: st.info(f"📆 **Semana Vigente:** Segunda-feira ({segunda.strftime('%d/%m/%Y')}) até Domingo ({domingo.strftime('%d/%m/%Y')})")

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
        
        cond_pago = df_temp['STATUS_UP'].str.contains('PAG|LIQUID|CONCIL|SIM|BAIX|QUIT', regex=True, na=False)
        cond_aberto = df_temp['STATUS_UP'].str.contains('PEND|VENC|ATRAS|ABERT', regex=True, na=False) & (~cond_pago)
        
        # Filtro de segurança: exige data válida e valor maior que zero para existir como obrigação
        cond_dado_valido = df_temp['VENC_DT'].notna() & (df_temp['VALOR_NUM'] > 0)
        
        pendentes = df_temp[cond_aberto & cond_dado_valido].copy()
        
        pendentes['Tipo de Despesa'] = tipo
        pendentes['Fornecedor_Display'] = pendentes[c_forn] if c_forn else '-'
        pendentes['Descricao_Display'] = pendentes[c_desc] if c_desc else '-'
        pendentes['Categoria_Display'] = pendentes[c_cat] if c_cat else '-'
        return pendentes
    return pd.DataFrame()

df_agenda_dinamica = pd.concat([extrair_pendencias(df_var, "Variável"), extrair_pendencias(df_fix, "Fixa")], ignore_index=True)

if not df_agenda_dinamica.empty:
    cond_vencido = df_agenda_dinamica['STATUS_UP'].str.contains('VENC|ATRAS', regex=True, na=False)
    if modo_ag == "Semana Vigente (Seg a Dom)": cond_data = (df_agenda_dinamica['VENC_DT'] >= pd.to_datetime(segunda.date())) & (df_agenda_dinamica['VENC_DT'] <= pd.to_datetime(domingo.date()))
    else: cond_data = (df_agenda_dinamica['VENC_DT'] >= pd.to_datetime(datas_sel[0])) & (df_agenda_dinamica['VENC_DT'] <= pd.to_datetime(datas_sel[1])) if isinstance(datas_sel, tuple) and len(datas_sel) == 2 else (df_agenda_dinamica['VENC_DT'] >= pd.to_datetime(segunda.date())) & (df_agenda_dinamica['VENC_DT'] <= pd.to_datetime(domingo.date()))
            
    df_agenda_view = df_agenda_dinamica[cond_vencido | cond_data].copy()
    if not df_agenda_view.empty:
        df_agenda_view['Valor Formatado'] = df_agenda_view['VALOR_NUM'].apply(format_brl)
        df_agenda_view['Data Vencimento'] = df_agenda_view['VENC_DT'].dt.strftime('%d/%m/%Y')
        col_rename = {'Data Vencimento': 'Vencimento', 'Tipo de Despesa': 'Tipo', 'Fornecedor_Display': 'Fornecedor', 'Descricao_Display': 'Descrição', 'Categoria_Display': 'Categoria', 'Valor Formatado': 'Valor (R$)', 'STATUS_UP': 'Status'}
        st.dataframe(df_agenda_view[['Data Vencimento', 'Tipo de Despesa', 'Fornecedor_Display', 'Descricao_Display', 'Categoria_Display', 'Valor Formatado', 'STATUS_UP']].rename(columns=col_rename).sort_values(by='Vencimento'), use_container_width=True)
        st.error(f"💸 **Total de Pagamentos da Semana / Atrasados:** {format_brl(df_agenda_view['VALOR_NUM'].sum())}")
    else: st.success("✅ Nenhum pagamento pendente registrado para a semana atual.")
else: st.info("Nenhuma pendência financeira encontrada.")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>DEMONSTRATIVO GERENCIAL DE FLUXO</div>", unsafe_allow_html=True)
g1, g2 = st.columns([6, 4])

with g1:
    fig_bar = go.Figure(go.Bar(
        x=['Entradas', 'Saídas', 'Variáveis Pagas', 'Fixas Pagas', 'Caixa'],
        y=[receita_extrato, abs(saidas_extrato), var_pago, fix_pago, saldo_caixa_real],
        marker_color=['#1B1C1D', '#555657', '#EA3D07', '#555657', cor_caixa],
        text=[format_brl(v) for v in [receita_extrato, abs(saidas_extrato), var_pago, fix_pago, saldo_caixa_real]],
        textposition='auto', textfont=dict(color='#FFFFFF', size=11, family='Poppins')
    ))
    fig_bar.update_layout(height=340, margin=dict(l=10, r=10, t=25, b=25), title=dict(text="Fluxo Financeiro (R$)", font=dict(color="#1B1C1D", family="Poppins", size=14)), font=dict(family="Poppins", color="#1B1C1D"), plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
    st.plotly_chart(fig_bar, use_container_width=True)

with g2:
    if (var_pago + fix_pago) > 0:
        fig_pie = px.pie(names=['Contas Variáveis', 'Contas Fixas'], values=[var_pago, fix_pago], color_discrete_sequence=['#EA3D07', '#1B1C1D'], hole=0.45, title="Distribuição de Saídas")
        fig_pie.update_layout(height=340, margin=dict(l=10, r=10, t=25, b=25), title=dict(font=dict(color="#1B1C1D", family="Poppins", size=14)), font=dict(family="Poppins", color="#1B1C1D"), paper_bgcolor="#FFFFFF", legend=dict(font=dict(color="#1B1C1D", family="Poppins")))
        st.plotly_chart(fig_pie, use_container_width=True)
