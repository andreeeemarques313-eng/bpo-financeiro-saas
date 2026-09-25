import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE INTERFACE E ENGENHARIA VISUAL
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
# 2. BANCO DE DADOS DE UNIDADES E CONFIGURAÇÕES
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
# 3. CONVERSORES E PARSERS DE DADOS MATEMÁTICOS
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
# 4. ENGINE DE CARREGAMENTO INTELIGENTE (API + FALLBACK TRANSPARENTE)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=10, show_spinner=False)
def load_operational_data_engine(sheet_id):
    # 1. Tentativa via Google Sheets API (gspread) se credenciais existirem nos Secrets
    if "gcp_service_account" in st.secrets:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
            client = gspread.authorize(creds)
            sh = client.open_by_key(sheet_id)
            
            df_ext = pd.DataFrame(sh.worksheet("EXTRATO BANCÁRIO").get_all_records())
            df_var = pd.DataFrame(sh.worksheet("CONTAS VARIÁVEIS").get_all_records())
            df_fix = pd.DataFrame(sh.worksheet("CONTAS FIXAS").get_all_records())
            
            return df_ext, df_var, df_fix, None
        except Exception as e_api:
            pass

    # 2. Fallback via Leitura Direta de URL com Tratamento de Erro Explícito
    def fetch_url_tab(sheet_id, tab_names):
        for tab in tab_names:
            encoded_tab = urllib.parse.quote(tab)
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={encoded_tab}"
            try:
                df = pd.read_csv(url)
                if not df.empty and len(df.columns) >= 2:
                    df.columns = [str(c).strip() for c in df.columns]
                    return df, None
            except Exception as e:
                continue
        return pd.DataFrame(), f"Aba inacessível ({tab_names})"

    df_ext, err_e = fetch_url_tab(sheet_id, ["EXTRATO BANCÁRIO", "EXTRATO BANCARIO", "EXTRATO"])
    df_var, err_v = fetch_url_tab(sheet_id, ["CONTAS VARIÁVEIS", "CONTAS VARIAVEIS", "VARIAVEIS"])
    df_fix, err_f = fetch_url_tab(sheet_id, ["CONTAS FIXAS", "FIXAS"])

    if df_ext.empty and df_var.empty and df_fix.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "A nuvem não conseguiu acessar a planilha. Verifique as permissões de compartilhamento no Google Drive."

    return df_ext, df_var, df_fix, None

# -----------------------------------------------------------------------------
# 5. CONTROLE LATERAL (SIDEBAR)
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Portal BPO Financeiro")
st.sidebar.caption("Engenharia de TI — Alex (CTO)")
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
if st.sidebar.button("🔄 Forçar Sincronização em Tempo Real"):
    st.cache_data.clear()
    st.rerun()

# Execute Data Engine
df_extrato, df_var, df_fixas, err_msg = load_operational_data_engine(cliente_info['sheet_id'])

if err_msg:
    st.error(f"⚠️ **Falha na Leitura Automática:** {err_msg}")
    st.info("💡 **Como Resolver:** Abra a planilha no Google Sheets, clique em **Compartilhar** no canto superior direito e marque como **'Qualquer pessoa com o link pode ver'**.")
    st.stop()

target_month = 8 if "Agosto" in periodo_selecionado else (9 if "Setembro" in periodo_selecionado else None)

# -----------------------------------------------------------------------------
# 6. ENGINE DE ANÁLISE COMERCIAL & FINANCEIRA (MARCOS / GUSTAVO)
# -----------------------------------------------------------------------------

# Processing Extrato
receita_real, saidas_extrato = 0.0, 0.0
df_extrato_f = pd.DataFrame()

if not df_extrato.empty:
    col_dt_e = match_col(df_extrato, ['DATA', 'DATA ', 'DATA DO LANÇAMENTO'])
    col_val_e = match_col(df_extrato, ['VALOR', 'VALOR (R$)', 'BANCO'])
    
    if col_dt_e and col_val_e:
        dt_e_series = parse_dates_robust(df_extrato[col_dt_e])
        df_extrato['DT_PARSED'] = dt_e_series
        df_extrato['VALOR_CLEAN'] = df_extrato[col_val_e].apply(clean_currency)
        
        if target_month:
            df_extrato_f = df_extrato[(dt_e_series.dt.month == target_month) & (dt_e_series.dt.year == 2026)].copy()
        else:
            df_extrato_f = df_extrato[dt_e_series.dt.year == 2026].copy()

        if not df_extrato_f.empty:
            receita_real = df_extrato_f[df_extrato_f['VALOR_CLEAN'] > 0]['VALOR_CLEAN'].sum()
            saidas_extrato = df_extrato_f[df_extrato_f['VALOR_CLEAN'] < 0]['VALOR_CLEAN'].sum()

# Processing Contas Variáveis
custo_var_pago, var_vencido = 0.0, 0.0
df_var_f = pd.DataFrame()

if not df_var.empty:
    col_pag_v = match_col(df_var, ['Data de Pagamento'])
    col_venc_v = match_col(df_var, ['Vencimento'])
    
    s_pag_v = parse_dates_robust(df_var[col_pag_v]) if col_pag_v else pd.Series(index=df_var.index, dtype='datetime64[ns]')
    s_venc_v = parse_dates_robust(df_var[col_venc_v]) if col_venc_v else pd.Series(index=df_var.index, dtype='datetime64[ns]')
    
    dt_final_v = s_pag_v.fillna(s_venc_v)
    df_var['DT_PARSED'] = dt_final_v

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

# Processing Contas Fixas
custo_fixo_pago, fixo_vencido = 0.0, 0.0
df_fixas_f = pd.DataFrame()

if not df_fixas.empty:
    col_pag_f = match_col(df_fixas, ['Data de Pagamento'])
    col_venc_f = match_col(df_fixas, ['Vencimento'])
    
    s_pag_f = parse_dates_robust(df_fixas[col_pag_f]) if col_pag_f else pd.Series(index=df_fixas.index, dtype='datetime64[ns]')
    s_venc_f = parse_dates_robust(df_fixas[col_venc_f]) if col_venc_f else pd.Series(index=df_fixas.index, dtype='datetime64[ns]')
    
    dt_final_f = s_pag_f.fillna(s_venc_f)
    df_fixas['DT_PARSED'] = dt_final_f

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

# -----------------------------------------------------------------------------
# 7. EXIBIÇÃO DO DASHBOARD E PAINEL EXECUTIVO
# -----------------------------------------------------------------------------
st.title(f"📊 Painel Executivo BPO Financeiro — {cliente_info['nome']}")
st.caption(f"Filtro Selecionado: **{periodo_selecionado}** | Sincronizado com o Google Sheets")

# CARDS DE METRICAS PRINCIPAIS
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Entradas (Extrato)</div><div class="kpi-value">{format_brl(receita_real)}</div><div class="kpi-sub">Total Recebido</div></div>', unsafe_allow_html=True)
with kpi2:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #EF4444;"><div class="kpi-title">Saídas Variáveis</div><div class="kpi-value">{format_brl(custo_var_pago)}</div><div class="kpi-sub">Insumos & Fornecedores</div></div>', unsafe_allow_html=True)
with kpi3:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #F59E0B;"><div class="kpi-title">Saídas Fixas</div><div class="kpi-value">{format_brl(custo_fixo_pago)}</div><div class="kpi-sub">Estrutura Operacional</div></div>', unsafe_allow_html=True)
with kpi4:
    st.markdown(f'<div class="kpi-card" style="border-left-color: {"#10B981" if resultado_caixa >= 0 else "#EF4444"};"><div class="kpi-title">Resultado de Caixa</div><div class="kpi-value">{format_brl(resultado_caixa)}</div><div class="kpi-sub">Geração Liquida</div></div>', unsafe_allow_html=True)
with kpi5:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #DC2626;"><div class="kpi-title">Contas Pendentes</div><div class="kpi-value">{format_brl(total_pendente)}</div><div class="kpi-sub">A Vencer / Vencidas</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 8. AGENDA FINANCEIRA VIGENTE (SEGUNDA A DOMINGO DA SEMANA) — CAMILA
# -----------------------------------------------------------------------------
st.subheader("📅 Agenda Financeira Vigente — Previsão Semanal (Segunda a Domingo)")

today = datetime.today()
start_week = today - timedelta(days=today.weekday()) # Segunda-feira da semana
end_week = start_week + timedelta(days=6)             # Domingo da semana

ag_col1, ag_col2 = st.columns([4, 6])

with ag_col1:
    modo_agenda = st.radio("Filtro Temporal da Agenda:", options=["Semana Vigente (Seg a Dom)", "Período Personalizado"], horizontal=True)

with ag_col2:
    if modo_agenda == "Período Personalizado":
        dates_selected = st.date_input("Selecione o Intervalo de Vencimento:", value=(start_week.date(), end_week.date()))
    else:
        st.info(f"📆 **Semana Vigente:** Segunda ({start_week.strftime('%d/%m/%Y')}) até Domingo ({end_week.strftime('%d/%m/%Y')})")

col_st_v_all = match_col(df_var, ['Status'])
col_st_f_all = match_col(df_fixas, ['Status'])

df_ag_v = df_var[df_var[col_st_v_all].astype(str).str.strip().str.upper().isin(['VENCIDO', 'PENDENTE'])].copy() if not df_var.empty and col_st_v_all else pd.DataFrame()
df_ag_f = df_fixas[df_fixas[col_st_f_all].astype(str).str.strip().str.upper().isin(['VENCIDO', 'PENDENTE'])].copy() if not df_fixas.empty and col_st_f_all else pd.DataFrame()

df_ag_all = pd.concat([df_ag_v, df_ag_f], ignore_index=True)

col_venc_all = match_col(df_ag_all, ['Vencimento', 'Data de Pagamento'])
col_stat_all = match_col(df_ag_all, ['Status'])

if not df_ag_all.empty and col_venc_all:
    df_ag_all['VENC_DT'] = parse_dates_robust(df_ag_all[col_venc_all])
    cond_venc = (df_ag_all[col_stat_all].astype(str).str.strip().str.upper() == 'VENCIDO') if col_stat_all else False
    
    if modo_agenda == "Semana Vigente (Seg a Dom)":
        cond_dt = (df_ag_all['VENC_DT'] >= pd.to_datetime(start_week.date())) & (df_ag_all['VENC_DT'] <= pd.to_datetime(end_week.date()))
    else:
        if isinstance(dates_selected, tuple) and len(dates_selected) == 2:
            cond_dt = (df_ag_all['VENC_DT'] >= pd.to_datetime(dates_selected[0])) & (df_ag_all['VENC_DT'] <= pd.to_datetime(dates_selected[1]))
        else:
            cond_dt = (df_ag_all['VENC_DT'] >= pd.to_datetime(start_week.date())) & (df_ag_all['VENC_DT'] <= pd.to_datetime(end_week.date()))

    df_ag_filt = df_ag_all[cond_venc | cond_dt].copy()
    col_val_ag = match_col(df_ag_filt, ['Valor', 'Valor (R$)'])
    
    if not df_ag_filt.empty and col_val_ag:
        df_ag_filt['Valor Formatado'] = df_ag_filt[col_val_ag].apply(lambda x: format_brl(clean_currency(x)))
        show_cols = [c for c in ['Vencimento', 'Fornecedor', 'Descrição', 'Categoria', 'Valor Formatado', 'Status'] if c in df_ag_filt.columns]
        st.dataframe(df_ag_filt[show_cols].sort_values(by='Vencimento'), use_container_width=True)
        
        tot_ag = df_ag_filt[col_val_ag].apply(clean_currency).sum()
        st.error(f"💸 **Compromissos Financeiros na Semana Vigente:** {format_brl(tot_ag)}")
    else:
        st.success("✅ **Nenhum compromisso pendente registrado para a semana vigente.**")
else:
    st.success("✅ **Sem pendências financeiras registradas.**")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 9. DEMONSTRATIVO VISUAL DE FLUXO E ESTRUTURA DE CUSTOS
# -----------------------------------------------------------------------------
st.subheader("📈 Demonstrativo Gerencial do Período")
g1, g2 = st.columns([6, 4])

with g1:
    fig_bar = go.Figure(go.Bar(
        x=['Entradas', 'Saídas Extrato', 'Variáveis Pagas', 'Fixas Pagas', 'Resultado Caixa'],
        y=[receita_real, abs(saidas_extrato), custo_var_pago, custo_fixo_pago, resultado_caixa],
        marker_color=['#1E3A8A', '#DC2626', '#EF4444', '#F59E0B', '#10B981' if resultado_caixa >= 0 else '#DC2626'],
        text=[format_brl(v) for v in [receita_real, abs(saidas_extrato), custo_var_pago, custo_fixo_pago, resultado_caixa]],
        textposition='auto'
    ))
    fig_bar.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20), title="Visão Comparativa de Entradas vs Saídas (R$)")
    st.plotly_chart(fig_bar, use_container_width=True)

with g2:
    if (custo_var_pago + custo_fixo_pago) > 0:
        fig_pie = px.pie(
            names=['Contas Variáveis', 'Contas Fixas'],
            values=[custo_var_pago, custo_fixo_pago],
            color_discrete_sequence=['#EF4444', '#F59E0B'],
            hole=0.5,
            title="Distribuição de Saídas Pagas"
        )
        fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")
st.subheader("📋 Tabela Operacional de Lançamentos do Período")
if not df_var_f.empty:
    df_var_disp = df_var_f.copy()
    c_v = match_col(df_var_disp, ['Valor', 'Valor (R$)'])
    if c_v:
        df_var_disp['Valor (R$)'] = df_var_disp[c_v].apply(lambda x: format_brl(clean_currency(x)))
    st.dataframe(df_var_disp, use_container_width=True)
else:
    st.info("Nenhum lançamento para a competência selecionada.")
