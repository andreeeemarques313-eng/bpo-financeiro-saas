import streamlit as st
import pandas as pd
import requests
import urllib.parse
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO VISUAL ENTERPRISE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Portal BPO Financeiro | Grupo Fiño House",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .kpi-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #0052CC;
        margin-bottom: 12px;
    }
    .kpi-title { font-size: 11px; color: #5E6C84; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { 
        font-size: 22px; 
        color: #172B4D; 
        font-weight: 800; 
        margin-top: 4px; 
        white-space: nowrap !important;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .kpi-sub { font-size: 12px; color: #7A869A; margin-top: 2px; }
    </style>
""", unsafe_allow_html=True)

CLIENTES = {
    "Tere": {"nome": "Fiño House - Teresópolis (RJ)", "id": "1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw"},
    "OB": {"nome": "Fiño House - Minas Gerais (OB)", "id": "1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw"}
}

# -----------------------------------------------------------------------------
# 2. TRATAMENTO NUMÉRICO E CONVERSÃO DE DADOS
# -----------------------------------------------------------------------------
def clean_currency(val):
    if pd.isna(val): return 0.0
    s = str(val).replace('R$', '').replace(' ', '').strip()
    if not s or s in ['-', '#REF!', '#N/A', 'nan', 'None']: return 0.0
    if '(' in s and ')' in s: s = '-' + s.replace('(', '').replace(')', '')
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
    return pd.to_datetime(series.astype(str).str.strip(), errors='coerce', dayfirst=True)

def match_col(df, candidates):
    if df.empty: return None
    cols_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        clean = cand.strip().lower()
        if clean in cols_map: return cols_map[clean]
    return None

# -----------------------------------------------------------------------------
# 3. VALIDADOR DE ESQUEMA DAS ABAS
# -----------------------------------------------------------------------------
def is_valid_extrato(df):
    if df.empty: return False
    cols = [str(c).strip().upper() for c in df.columns]
    has_date = any('DATA' in c for c in cols)
    has_val = any('VALOR' in c or 'BANCO' in c for c in cols)
    return has_date and has_val

def is_valid_contas(df):
    if df.empty: return False
    cols = [str(c).strip().upper() for c in df.columns]
    has_date = any('VENCIMENTO' in c or 'PAGAMENTO' in c for c in cols)
    has_val = any('VALOR' in c for c in cols)
    return has_date and has_val

@st.cache_data(ttl=5, show_spinner=False)
def fetch_tab_verified(sheet_id, tab_candidates, validator_type, api_key=""):
    validator = is_valid_extrato if validator_type == "extrato" else is_valid_contas
    
    # 1. Tentativa via Google Sheets API v4 (se houver API Key)
    if api_key:
        for tab in tab_candidates:
            range_fmt = urllib.parse.quote(f"'{tab}'!A1:Z500")
            url_api = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_fmt}?key={api_key}"
            try:
                res = requests.get(url_api, timeout=5)
                if res.status_code == 200:
                    rows = res.json().get('values', [])
                    if len(rows) > 1:
                        df = pd.DataFrame(rows[1:], columns=rows[0])
                        df.columns = [str(c).strip() for c in df.columns]
                        if validator(df):
                            return df, "Google API v4"
            except Exception:
                pass

    # 2. Tentativa via GViz e Export CSV (testando com e sem acento)
    for tab in tab_candidates:
        for route in [
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(tab)}",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={urllib.parse.quote(tab)}"
        ]:
            try:
                df = pd.read_csv(route)
                if not df.empty and len(df.columns) >= 2:
                    df.columns = [str(c).strip() for c in df.columns]
                    if validator(df):
                        return df, "Google GViz"
            except Exception:
                continue

    return pd.DataFrame(), None

def load_data_pipeline(sheet_id, api_key=""):
    # Ordem de busca: nomes sem acento primeiro para evitar falha no GViz
    df_ext, m_e = fetch_tab_verified(sheet_id, ["EXTRATO BANCARIO", "EXTRATO", "EXTRATO BANCÁRIO"], "extrato", api_key)
    df_var, m_v = fetch_tab_verified(sheet_id, ["CONTAS VARIAVEIS", "VARIAVEIS", "CONTAS VARIÁVEIS"], "contas", api_key)
    df_fix, m_f = fetch_tab_verified(sheet_id, ["CONTAS FIXAS", "FIXAS"], "contas", api_key)
    
    return {
        "extrato": df_ext,
        "variaveis": df_var,
        "fixas": df_fix,
        "modo": m_e or m_v or m_f,
        "erro": df_ext.empty and df_var.empty and df_fix.empty
    }

# -----------------------------------------------------------------------------
# 4. SIDEBAR E FILTROS DE COMPETÊNCIA
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Painel BPO Financeiro")
st.sidebar.caption("Alex — Diretor de Tecnologia (CTO)")
st.sidebar.markdown("---")

api_key_manual = st.sidebar.text_input("🔑 Chave API Google (Opcional):", type="password", help="Chave da API oficial do Google Cloud se configurada.")
key_to_use = api_key_manual or st.secrets.get("GOOGLE_API_KEY", "")

unidade_chave = st.sidebar.selectbox("Unidade:", list(CLIENTES.keys()), format_func=lambda x: CLIENTES[x]["nome"])
periodo_filtro = st.sidebar.selectbox("Competência:", ["Agosto/2026", "Setembro/2026", "CONSOLIDADO DO ANO (2026)"])

if st.sidebar.button("🔄 Sincronizar em Tempo Real"):
    st.cache_data.clear()
    st.rerun()

dados = load_data_pipeline(CLIENTES[unidade_chave]["id"], key_to_use)

if dados["erro"]:
    st.error("🚨 **Não foi possível aceder à planilha.**")
    st.warning("Verifique se o link está como 'Qualquer pessoa com o link pode ver' no Google Sheets.")
    st.stop()

st.sidebar.success(f"Ligação Ativa: **{dados['modo']}**")

target_month = 8 if "Agosto" in periodo_filtro else (9 if "Setembro" in periodo_filtro else None)

# -----------------------------------------------------------------------------
# 5. REGRA 1 & 2: EXTRATO (ENTRADAS) E CONTAS (SAÍDAS DO MÊS)
# -----------------------------------------------------------------------------
df_ext = dados["extrato"]
df_var = dados["variaveis"]
df_fix = dados["fixas"]

# REGRA 1: ENTRADAS EXCLUSIVAS DA ABA EXTRATO BANCÁRIO
receita_extrato, saidas_extrato = 0.0, 0.0
df_ext_filtro = pd.DataFrame()

if not df_ext.empty:
    c_dt_e = match_col(df_ext, ['DATA', 'DATA ', 'DATA DO LANÇAMENTO'])
    c_val_e = match_col(df_ext, ['VALOR', 'VALOR (R$)', 'BANCO'])
    if c_dt_e and c_val_e:
        dt_s = parse_dates_robust(df_ext[c_dt_e])
        df_ext['VALOR_NUM'] = df_ext[c_val_e].apply(clean_currency)
        df_ext['DT_S'] = dt_s
        cond = (dt_s.dt.month == target_month) & (dt_s.dt.year == 2026) if target_month else (dt_s.dt.year == 2026)
        df_ext_filtro = df_ext[cond].copy()
        if not df_ext_filtro.empty:
            receita_extrato = df_ext_filtro[df_ext_filtro['VALOR_NUM'] > 0]['VALOR_NUM'].sum()
            saidas_extrato = df_ext_filtro[df_ext_filtro['VALOR_NUM'] < 0]['VALOR_NUM'].sum()

# REGRA 2: SAÍDAS FIXAS E VARIÁVEIS SOMENTE DO MÊS VIGENTE
def process_contas_mes(df):
    if df.empty: return 0.0, 0.0, pd.DataFrame()
    c_pag = match_col(df, ['Data de Pagamento', 'Pagamento'])
    c_venc = match_col(df, ['Vencimento', 'Data de Vencimento', 'Data'])
    c_val = match_col(df, ['Valor', 'Valor (R$)'])
    c_st = match_col(df, ['Status', 'Situação'])
    
    if c_val and c_st:
        s_pag = parse_dates_robust(df[c_pag]) if c_pag else pd.Series(index=df.index, dtype='datetime64[ns]')
        s_venc = parse_dates_robust(df[c_venc]) if c_venc else pd.Series(index=df.index, dtype='datetime64[ns]')
        df['DT_REF'] = s_pag.fillna(s_venc)
        df['VALOR_NUM'] = df[c_val].apply(clean_currency)
        df['ST_UP'] = df[c_st].astype(str).str.strip().str.upper()
        
        cond = (df['DT_REF'].dt.month == target_month) & (df['DT_REF'].dt.year == 2026) if target_month else (df['DT_REF'].dt.year == 2026)
        df_f = df[cond].copy()
        
        pago = df_f[df_f['ST_UP'] == 'PAGO']['VALOR_NUM'].sum()
        pend = df_f[df_f['ST_UP'].isin(['VENCIDO', 'PENDENTE'])]['VALOR_NUM'].sum()
        return pago, pend, df_f
    return 0.0, 0.0, pd.DataFrame()

var_pago, var_pend, df_var_f = process_contas_mes(df_var)
fix_pago, fix_pend, df_fix_f = process_contas_mes(df_fix)

saldo_caixa_real = receita_extrato + saidas_extrato
total_pendente_mes = var_pend + fix_pend

# -----------------------------------------------------------------------------
# 6. DASHBOARD EXECUTIVO: KPI CARDS
# -----------------------------------------------------------------------------
st.title(f"📊 Painel Executivo BPO Financeiro — {CLIENTES[unidade_chave]['nome']}")
st.caption(f"Competência: **{periodo_filtro}** | Monitorização Automatizada em Tempo Real")

c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Entradas (Extrato)</div><div class="kpi-value">{format_brl(receita_extrato)}</div><div class="kpi-sub">Total Recebido</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="kpi-card" style="border-left-color: #FF5630;"><div class="kpi-title">Variáveis Pagas</div><div class="kpi-value">{format_brl(var_pago)}</div><div class="kpi-sub">Insumos & Fornecedores</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="kpi-card" style="border-left-color: #FFAB00;"><div class="kpi-title">Fixas Pagas</div><div class="kpi-value">{format_brl(fix_pago)}</div><div class="kpi-sub">Estrutura Operacional</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="kpi-card" style="border-left-color: {"#36B37E" if saldo_caixa_real >= 0 else "#FF5630"};"><div class="kpi-title">Resultado de Caixa</div><div class="kpi-value">{format_brl(saldo_caixa_real)}</div><div class="kpi-sub">Entradas − Saídas Extrato</div></div>', unsafe_allow_html=True)
with c5: st.markdown(f'<div class="kpi-card" style="border-left-color: #6554C0;"><div class="kpi-title">Contas Pendentes</div><div class="kpi-value">{format_brl(total_pendente_mes)}</div><div class="kpi-sub">A Vencer / Vencidas</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. REGRA 3: AGENDA FINANCEIRA DINÂMICA (SEGUNDA A DOMINGO DA SEMANA)
# -----------------------------------------------------------------------------
st.subheader("📅 Agenda Financeira Vigente — Previsão Semanal (Segunda a Domingo)")

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

# Consolidação dinâmica a partir de CONTAS VARIÁVEIS e CONTAS FIXAS
def extrair_pendencias(df, tipo):
    if df.empty: return pd.DataFrame()
    c_venc = match_col(df, ['Vencimento', 'Data de Vencimento', 'Data'])
    c_val = match_col(df, ['Valor', 'Valor (R$)'])
    c_st = match_col(df, ['Status', 'Situação'])
    c_forn = match_col(df, ['Fornecedor', 'Razão Social', 'Beneficiário'])
    c_desc = match_col(df, ['Descrição', 'Descricao', 'Item'])
    c_cat = match_col(df, ['Categoria'])
    
    if c_venc and c_val and c_st:
        df_temp = df.copy()
        df_temp['VALOR_NUM'] = df_temp[c_val].apply(clean_currency)
        df_temp['VENC_DT'] = parse_dates_robust(df_temp[c_venc])
        df_temp['STATUS_UP'] = df_temp[c_st].astype(str).str.strip().str.upper()
        
        # Filtra apenas o que precisa ser pago (PENDENTE ou VENCIDO)
        pendentes = df_temp[df_temp['STATUS_UP'].isin(['PENDENTE', 'VENCIDO'])].copy()
        pendentes['Tipo de Conta'] = tipo
        pendentes['Fornecedor_Display'] = pendentes[c_forn] if c_forn else '-'
        pendentes['Descricao_Display'] = pendentes[c_desc] if c_desc else '-'
        pendentes['Categoria_Display'] = pendentes[c_cat] if c_cat else '-'
        return pendentes
    return pd.DataFrame()

pend_var = extrair_pendencias(df_var, "Variável")
pend_fix = extrair_pendencias(df_fix, "Fixa")

df_agenda_dinamica = pd.concat([pend_var, pend_fix], ignore_index=True)

if not df_agenda_dinamica.empty:
    cond_vencido = (df_agenda_dinamica['STATUS_UP'] == 'VENCIDO')
    
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
        
        cols_grid = ['Data Vencimento', 'Tipo de Conta', 'Fornecedor_Display', 'Descricao_Display', 'Categoria_Display', 'Valor Formatado', 'STATUS_UP']
        col_rename = {
            'Data Vencimento': 'Vencimento',
            'Tipo de Conta': 'Tipo',
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
        st.success("✅ Nenhum pagamento pendente registado para a semana atual.")
else:
    st.success("✅ Nenhuma conta a pagar pendente encontrada no sistema.")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 8. GRÁFICOS GERENCIAIS E DEMONSTRATIVO DE FLUXO
# -----------------------------------------------------------------------------
st.subheader("📈 Demonstrativo Gerencial do Período")
g1, g2 = st.columns([6, 4])

with g1:
    fig_bar = go.Figure(go.Bar(
        x=['Entradas Extrato', 'Saídas Extrato', 'Variáveis Pagas', 'Fixas Pagas', 'Resultado de Caixa'],
        y=[receita_extrato, abs(saidas_extrato), var_pago, fix_pago, saldo_caixa_real],
        marker_color=['#0052CC', '#172B4D', '#FF5630', '#FFAB00', '#36B37E' if saldo_caixa_real >= 0 else '#FF5630'],
        text=[format_brl(v) for v in [receita_extrato, abs(saidas_extrato), var_pago, fix_pago, saldo_caixa_real]],
        textposition='auto'
    ))
    fig_bar.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20), title="Visão Comparativa do Período (R$)")
    st.plotly_chart(fig_bar, use_container_width=True)

with g2:
    if (var_pago + fix_pago) > 0:
        fig_pie = px.pie(
            names=['Contas Variáveis', 'Contas Fixas'],
            values=[var_pago, fix_pago],
            color_discrete_sequence=['#FF5630', '#FFAB00'],
            hole=0.4,
            title="Distribuição de Saídas Realizadas"
        )
        fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")
st.subheader("📋 Tabela Operacional de Lançamentos (Variáveis do Período)")
if not df_var_f.empty:
    df_var_view = df_var_f.copy()
    c_v_show = match_col(df_var_view, ['Valor', 'Valor (R$)'])
    if c_v_show:
        df_var_view['Valor (R$)'] = df_var_view[c_v_show].apply(clean_currency).apply(format_brl)
    drop_cols = [c for c in ['DT_REF', 'VALOR_NUM', 'ST_UP'] if c in df_var_view.columns]
    st.dataframe(df_var_view.drop(columns=drop_cols), use_container_width=True)
else:
    st.info("Nenhum lançamento de contas variáveis registado para o filtro ativo.")
