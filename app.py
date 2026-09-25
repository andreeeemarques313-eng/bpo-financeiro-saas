import streamlit as st
import pandas as pd
import requests

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE INTERFACE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Portal BPO Financeiro | Grupo Fiño House",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS Enterprise
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .kpi-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.04);
        border-left: 6px solid #1E3A8A;
        margin-bottom: 12px;
    }
    .kpi-title { font-size: 11px; color: #6B7280; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }
    .kpi-value { font-size: 24px; color: #111827; font-weight: 800; margin-top: 6px; }
    .kpi-sub { font-size: 12px; color: #9CA3AF; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. BANCO DE DADOS DE UNIDADES
# -----------------------------------------------------------------------------
CLIENT_DATABASE = {
    "cliente_tere": {
        "nome": "Fiño House - Unidade Teresópolis (RJ)",
        "sheet_id": "1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw"
    },
    "cliente_ob": {
        "nome": "Fiño House - Unidade Minas Gerais (OB)",
        "sheet_id": "1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw"
    }
}

# -----------------------------------------------------------------------------
# 3. TRATAMENTO E CONVERSÃO DE DADOS
# -----------------------------------------------------------------------------
def clean_currency(val):
    if pd.isna(val): 
        return 0.0
    s = str(val).strip().replace('R$', '').replace(' ', '').replace('(', '-').replace(')', '').strip()
    if not s or s in ['-', '#REF!', '#N/A', 'nan', 'None', 'NoneType']: 
        return 0.0
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except Exception:
        return 0.0

def format_brl(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_dates_robust(series):
    if series is None or series.empty:
        return pd.Series(dtype='datetime64[ns]')
    parsed = pd.to_datetime(series.astype(str).str.strip(), errors='coerce', dayfirst=True)
    if parsed.isna().sum() > len(series) * 0.5:
        parsed = pd.to_datetime(series.astype(str).str.strip(), errors='coerce')
    return parsed

def match_col(df, candidates):
    if df.empty: 
        return None
    cols_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        c_clean = cand.strip().lower()
        if c_clean in cols_map:
            return cols_map[c_clean]
    return None

# -----------------------------------------------------------------------------
# 4. DATA ENGINE COM LEITURA SEGURA
# -----------------------------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
def fetch_tab_via_api(sheet_id, sheet_name, api_key):
    if api_key:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{requests.utils.quote(sheet_name)}?key={api_key}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                values = data.get('values', [])
                if len(values) > 1:
                    df = pd.DataFrame(values[1:], columns=values[0])
                    df.columns = [str(c).strip() for c in df.columns]
                    return df, None
        except Exception:
            pass
    
    # Fallback leitor direto
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={requests.utils.quote(sheet_name)}"
    try:
        df_csv = pd.read_csv(url_csv)
        if not df_csv.empty and len(df_csv.columns) >= 2:
            df_csv.columns = [str(c).strip() for c in df_csv.columns]
            return df_csv, None
    except Exception:
        pass

    return pd.DataFrame(), f"Aba '{sheet_name}' inacessível."

def load_all_operational_data(sheet_id):
    # Puxa a chave oculta dos secrets
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    
    df_ext, _ = fetch_tab_via_api(sheet_id, "EXTRATO BANCÁRIO", api_key)
    if df_ext.empty:
        df_ext, _ = fetch_tab_via_api(sheet_id, "EXTRATO BANCARIO", api_key)

    df_var, _ = fetch_tab_via_api(sheet_id, "CONTAS VARIÁVEIS", api_key)
    if df_var.empty:
        df_var, _ = fetch_tab_via_api(sheet_id, "CONTAS VARIAVEIS", api_key)

    df_fix, _ = fetch_tab_via_api(sheet_id, "CONTAS FIXAS", api_key)

    is_empty = df_ext.empty and df_var.empty and df_fix.empty
    return df_ext, df_var, df_fix, is_empty

# -----------------------------------------------------------------------------
# 5. SIDEBAR E NAVEGAÇÃO
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Portal BPO Financeiro")
st.sidebar.caption("Alex — Diretor de Tecnologia (CTO)")
st.sidebar.markdown("---")

cliente_key = st.sidebar.selectbox(
    "Unidade Selecionada:",
    options=list(CLIENT_DATABASE.keys()),
    format_func=lambda x: CLIENT_DATABASE[x]["nome"]
)

cliente_info = CLIENT_DATABASE[cliente_key]
st.sidebar.success(f"Conectado: **{cliente_info['nome']}**")

periodo_selecionado = st.sidebar.selectbox(
    "Competência do Dashboard:",
    ["Agosto/2026", "Setembro/2026", "CONSOLIDADO DO ANO (2026)"]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Sincronizar com Google Sheets"):
    st.cache_data.clear()
    st.rerun()

# Execute Engine
df_extrato, df_var, df_fixas, is_empty = load_all_operational_data(cliente_info['sheet_id'])

if is_empty:
    st.error("🚨 **Aviso do Alex (CTO): Não foi possível conectar ao Google Sheets.**")
    st.info("💡 Certifique-se de que a chave `GOOGLE_API_KEY` foi configurada nos Secrets do Streamlit Cloud.")
    st.stop()

target_month = 8 if "Agosto" in periodo_selecionado else (9 if "Setembro" in periodo_selecionado else None)

# -----------------------------------------------------------------------------
# 6. CÁLCULOS E DASHBOARD
# -----------------------------------------------------------------------------
receita_real, saidas_extrato = 0.0, 0.0
df_extrato_f = pd.DataFrame()

if not df_extrato.empty:
    col_dt_e = match_col(df_extrato, ['DATA', 'DATA ', 'DATA DO LANÇAMENTO'])
    col_val_e = match_col(df_extrato, ['VALOR', 'VALOR (R$)', 'BANCO'])
    
    if col_dt_e and col_val_e:
        dt_e_series = parse_dates_robust(df_extrato[col_dt_e])
        df_extrato['VALOR_CLEAN'] = df_extrato[col_val_e].apply(clean_currency)
        
        if target_month:
            df_extrato_f = df_extrato[(dt_e_series.dt.month == target_month) & (dt_e_series.dt.year == 2026)].copy()
        else:
            df_extrato_f = df_extrato[dt_e_series.dt.year == 2026].copy()

        if not df_extrato_f.empty:
            receita_real = df_extrato_f[df_extrato_f['VALOR_CLEAN'] > 0]['VALOR_CLEAN'].sum()
            saidas_extrato = df_extrato_f[df_extrato_f['VALOR_CLEAN'] < 0]['VALOR_CLEAN'].sum()

custo_var_pago, var_vencido = 0.0, 0.0
df_var_f = pd.DataFrame()

if not df_var.empty:
    col_pag_v = match_col(df_var, ['Data de Pagamento'])
    col_venc_v = match_col(df_var, ['Vencimento'])
    
    s_pag_v = parse_dates_robust(df_var[col_pag_v]) if col_pag_v else pd.Series(index=df_var.index, dtype='datetime64[ns]')
    s_venc_v = parse_dates_robust(df_var[col_venc_v]) if col_venc_v else pd.Series(index=df_var.index, dtype='datetime64[ns]')
    
    dt_final_v = s_pag_v.fillna(s_venc_v)

    if target_month:
        df_var_f = df_var[(dt_final_v.dt.month == target_month) & (dt_final_v.dt.year == 2026)].copy()
    else:
        df_var_f = df_var[dt_final_v.dt.year == 2026].copy()

    if not df_var_f.empty:
        col_val_v = match_col(df_var_f, ['Valor', 'Valor (R$)'])
        col_st_v = match_col(df_var_f, ['Status'])
        if col_val_v:
            df_var_f['VALOR_CLEAN'] = df_var_f[col_val_v].apply(clean_currency)
            if col_st_v:
                st_upper_v = df_var_f[col_st_v].astype(str).str.strip().str.upper()
                custo_var_pago = df_var_f[st_upper_v == 'PAGO']['VALOR_CLEAN'].sum()
                var_vencido = df_var_f[st_upper_v.isin(['VENCIDO', 'PENDENTE'])]['VALOR_CLEAN'].sum()

custo_fixo_pago, fixo_vencido = 0.0, 0.0
df_fixas_f = pd.DataFrame()

if not df_fixas.empty:
    col_pag_f = match_col(df_fixas, ['Data de Pagamento'])
    col_venc_f = match_col(df_fixas, ['Vencimento'])
    
    s_pag_f = parse_dates_robust(df_fixas[col_pag_f]) if col_pag_f else pd.Series(index=df_fixas.index, dtype='datetime64[ns]')
    s_venc_f = parse_dates_robust(df_fixas[col_venc_f]) if col_venc_f else pd.Series(index=df_fixas.index, dtype='datetime64[ns]')
    
    dt_final_f = s_pag_f.fillna(s_venc_f)

    if target_month:
        df_fixas_f = df_fixas[(dt_final_f.dt.month == target_month) & (dt_final_f.dt.year == 2026)].copy()
    else:
        df_fixas_f = df_fixas[dt_final_f.dt.year == 2026].copy()

    if not df_fixas_f.empty:
        col_val_f = match_col(df_fixas_f, ['Valor', 'Valor (R$)'])
        col_st_f = match_col(df_fixas_f, ['Status'])
        if col_val_f:
            df_fixas_f['VALOR_CLEAN'] = df_fixas_f[col_val_f].apply(clean_currency)
            if col_st_f:
                st_upper_f = df_fixas_f[col_st_f].astype(str).str.strip().str.upper()
                custo_fixo_pago = df_fixas_f[st_upper_f == 'PAGO']['VALOR_CLEAN'].sum()
                fixo_vencido = df_fixas_f[st_upper_f.isin(['VENCIDO', 'PENDENTE'])]['VALOR_CLEAN'].sum()

resultado_caixa = receita_real + saidas_extrato
total_pendente = var_vencido + fixo_vencido

# EXIBIÇÃO NO STREAMLIT
st.title(f"📊 Painel Executivo BPO Financeiro — {cliente_info['nome']}")
st.caption(f"Filtro Ativo: **{periodo_selecionado}**")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Entradas (Extrato)</div><div class="kpi-value">{format_brl(receita_real)}</div></div>', unsafe_allow_html=True)
with kpi2:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #EF4444;"><div class="kpi-title">Saídas Variáveis</div><div class="kpi-value">{format_brl(custo_var_pago)}</div></div>', unsafe_allow_html=True)
with kpi3:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #F59E0B;"><div class="kpi-title">Saídas Fixas</div><div class="kpi-value">{format_brl(custo_fixo_pago)}</div></div>', unsafe_allow_html=True)
with kpi4:
    st.markdown(f'<div class="kpi-card" style="border-left-color: {"#10B981" if resultado_caixa >= 0 else "#EF4444"};"><div class="kpi-title">Resultado de Caixa</div><div class="kpi-value">{format_brl(resultado_caixa)}</div></div>', unsafe_allow_html=True)
with kpi5:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #DC2626;"><div class="kpi-title">Contas Pendentes</div><div class="kpi-value">{format_brl(total_pendente)}</div></div>', unsafe_allow_html=True)
