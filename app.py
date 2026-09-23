import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(
    page_title="Portal BPO Financeiro | BI Operacional",
    page_icon="📊",
    layout="wide"
)

# Estilização CSS Customizada
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .kpi-card {
        background-color: #ffffff;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #1E3A8A;
        margin-bottom: 10px;
    }
    .kpi-title { font-size: 12px; color: #6B7280; font-weight: 600; text-transform: uppercase; }
    .kpi-value { font-size: 22px; color: #111827; font-weight: bold; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MAPEAMENTO DE UNIDADES
# -----------------------------------------------------------------------------
CLIENT_DATABASE = {
    "consolidado": {
        "nome": "🏢 TODAS AS UNIDADES (CONSOLIDADO GROUP)",
        "sheet_id": "CONSOLIDADO"
    },
    "cliente_tere": {
        "nome": "Fino House - Unidade Teresópolis",
        "sheet_id": "1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw"
    },
    "cliente_ob": {
        "nome": "Fino House - Unidade Minas Gerais",
        "sheet_id": "1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw"
    }
}

# -----------------------------------------------------------------------------
# FUNÇÕES DEFENSIVAS DE TRATAMENTO
# -----------------------------------------------------------------------------
def parse_currency(val):
    if pd.isna(val): return 0.0
    s = str(val).strip().replace('R$', '').replace(' ', '').strip()
    if not s or s in ['-', '#REF!', '#N/A', 'nan', 'None']: return 0.0
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except:
        return 0.0

def format_brl(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_any_date(series):
    if series is None or series.empty:
        return pd.Series(dtype='datetime64[ns]')
    clean_series = series.astype(str).str.strip()
    return pd.to_datetime(clean_series, dayfirst=True, errors='coerce')

def find_column(df, possible_names):
    """Busca uma coluna no dataframe de forma flexível"""
    if df.empty:
        return None
    cols_clean = {str(c).strip().lower(): c for c in df.columns}
    for name in possible_names:
        name_clean = name.strip().lower()
        if name_clean in cols_clean:
            return cols_clean[name_clean]
    return None

# -----------------------------------------------------------------------------
# CARREGAMENTO DE DADOS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=10)
def load_operational_data(sheet_id):
    def get_df(s_id, sheet_name):
        url = f"https://docs.google.com/spreadsheets/d/{s_id}/export?format=csv&sheet={sheet_name.replace(' ', '%20')}"
        try:
            df = pd.read_csv(url)
            df.columns = df.columns.astype(str).str.strip()
            return df
        except:
            return pd.DataFrame()

    if sheet_id == "CONSOLIDADO":
        e1, v1, f1 = load_operational_data("1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw")
        e2, v2, f2 = load_operational_data("1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw")
        df_ext = pd.concat([e1, e2], ignore_index=True) if not e1.empty or not e2.empty else pd.DataFrame()
        df_v = pd.concat([v1, v2], ignore_index=True) if not v1.empty or not v2.empty else pd.DataFrame()
        df_f = pd.concat([f1, f2], ignore_index=True) if not f1.empty or not f2.empty else pd.DataFrame()
        return df_ext, df_v, df_f
    else:
        return get_df(sheet_id, "EXTRATO BANCARIO"), get_df(sheet_id, "CONTAS VARIAVEIS"), get_df(sheet_id, "CONTAS FIXAS")

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Painel BPO Financeiro")
st.sidebar.markdown("---")

cliente_selected_key = st.sidebar.selectbox(
    "Unidade Selecionada:",
    options=list(CLIENT_DATABASE.keys()),
    format_func=lambda x: CLIENT_DATABASE[x]["nome"]
)

cliente_info = CLIENT_DATABASE[cliente_selected_key]
st.sidebar.success(f"Conectado: **{cliente_info['nome']}**")

st.sidebar.markdown("### 🔍 Filtro de Período Mês a Mês")
periodo_opcoes = ["Setembro/2026", "Agosto/2026", "Julho/2026", "CONSOLIDADO DO ANO (2026)"]
periodo_selecionado = st.sidebar.selectbox("Competência / Filtro:", periodo_opcoes)

# Carregamento dos dados
df_extrato, df_var, df_fixas = load_operational_data(cliente_info['sheet_id'])

target_month = 9 if "Setembro" in periodo_selecionado else (8 if "Agosto" in periodo_selecionado else (7 if "Julho" in periodo_selecionado else None))

# -----------------------------------------------------------------------------
# FILTRAGEM SEGURA - EXTRATO
# -----------------------------------------------------------------------------
df_extrato_f = pd.DataFrame()
if not df_extrato.empty:
    col_date = find_column(df_extrato, ['DATA', 'DATA ', 'DATA DO LANÇAMENTO'])
    if col_date:
        df_extrato['DT_PARSED'] = parse_any_date(df_extrato[col_date])
        if target_month:
            df_extrato_f = df_extrato[(df_extrato['DT_PARSED'].dt.month == target_month) & (df_extrato['DT_PARSED'].dt.year == 2026)]
        else:
            df_extrato_f = df_extrato[df_extrato['DT_PARSED'].dt.year == 2026]

receita_real = 0.0
if not df_extrato_f.empty:
    col_val = find_column(df_extrato_f, ['BANCO', 'VALOR', 'VALOR (R$)'])
    if col_val:
        vals = df_extrato_f[col_val].apply(parse_currency)
        receita_real = vals[vals > 0].sum()

# -----------------------------------------------------------------------------
# FILTRAGEM SEGURA - CONTAS VARIÁVEIS
# -----------------------------------------------------------------------------
df_var_f = pd.DataFrame()
if not df_var.empty:
    col_date_var = find_column(df_var, ['Data de Pagamento', 'Vencimento', 'Competência'])
    if col_date_var:
        df_var['DT_PARSED'] = parse_any_date(df_var[col_date_var])
        if target_month:
            df_var_f = df_var[(df_var['DT_PARSED'].dt.month == target_month) & (df_var['DT_PARSED'].dt.year == 2026)]
        else:
            df_var_f = df_var[df_var['DT_PARSED'].dt.year == 2026]

custo_var_pago = 0.0
var_vencido = 0.0
if not df_var_f.empty:
    col_val_var = find_column(df_var_f, ['Valor', 'Valor (R$)'])
    col_status_var = find_column(df_var_f, ['Status'])
    if col_val_var:
        df_var_f['VALOR_CLEAN'] = df_var_f[col_val_var].apply(parse_currency)
        if col_status_var:
            custo_var_pago = df_var_f[df_var_f[col_status_var] == 'PAGO']['VALOR_CLEAN'].sum()
            var_vencido = df_var_f[df_var_f[col_status_var].isin(['VENCIDO', 'PENDENTE'])]['VALOR_CLEAN'].sum()

# -----------------------------------------------------------------------------
# FILTRAGEM SEGURA - CONTAS FIXAS
# -----------------------------------------------------------------------------
df_fixas_f = pd.DataFrame()
if not df_fixas.empty:
    col_date_fix = find_column(df_fixas, ['Data de Pagamento', 'Vencimento', 'Competência'])
    if col_date_fix:
        df_fixas['DT_PARSED'] = parse_any_date(df_fixas[col_date_fix])
        if target_month:
            df_fixas_f = df_fixas[(df_fixas['DT_PARSED'].dt.month == target_month) & (df_fixas['DT_PARSED'].dt.year == 2026)]
        else:
            df_fixas_f = df_fixas[df_fixas['DT_PARSED'].dt.year == 2026]

custo_fixo_pago = 0.0
fixo_vencido = 0.0
if not df_fixas_f.empty:
    col_val_fix = find_column(df_fixas_f, ['Valor', 'Valor (R$)'])
    col_status_fix = find_column(df_fixas_f, ['Status'])
    if col_val_fix:
        df_fixas_f['VALOR_CLEAN'] = df_fixas_f[col_val_fix].apply(parse_currency)
        if col_status_fix:
            custo_fixo_pago = df_fixas_f[df_fixas_f[col_status_fix] == 'PAGO']['VALOR_CLEAN'].sum()
            fixo_vencido = df_fixas_f[df_fixas_f[col_status_fix].isin(['VENCIDO', 'PENDENTE'])]['VALOR_CLEAN'].sum()

resultado_liquido = receita_real - (custo_var_pago + custo_fixo_pago)
total_vencido_pendente = var_vencido + fixo_vencido

# -----------------------------------------------------------------------------
# PAINEL PRINCIPAL
# -----------------------------------------------------------------------------
st.title(f"📊 Gestão Financeira Real — {cliente_info['nome']}")
st.caption(f"Filtro Ativo: **{periodo_selecionado}**")

# KPI Cards
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Entradas Reais (Extrato)</div><div class="kpi-value">{format_brl(receita_real)}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #EF4444;"><div class="kpi-title">Contas Variáveis Pagas</div><div class="kpi-value">{format_brl(custo_var_pago)}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #F59E0B;"><div class="kpi-title">Contas Fixas Pagas</div><div class="kpi-value">{format_brl(custo_fixo_pago)}</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="kpi-card" style="border-left-color: {"#10B981" if resultado_liquido >= 0 else "#EF4444"};"><div class="kpi-title">Resultado de Caixa Real</div><div class="kpi-value">{format_brl(resultado_liquido)}</div></div>', unsafe_allow_html=True)
with col5:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #DC2626;"><div class="kpi-title">Total Pendente / Vencido</div><div class="kpi-value">{format_brl(total_vencido_pendente)}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# AGENDA FINANCEIRA
# -----------------------------------------------------------------------------
st.subheader("📅 Agenda Financeira (Atrasados + Semana Vigente / Calendário)")

ag_col1, ag_col2 = st.columns([4, 6])

today = datetime.today()
start_current_week = today - timedelta(days=today.weekday())
end_current_week = start_current_week + timedelta(days=6)

with ag_col1:
    modo_agenda = st.radio(
        "Modo de Exibição da Agenda:",
        options=["Semana Atual Vigente", "Selecionar Período no Calendário"],
        horizontal=True
    )

with ag_col2:
    if modo_agenda == "Selecionar Período no Calendário":
        dates_selected = st.date_input(
            "Selecione o intervalo no calendário:",
            value=(start_current_week.date(), end_current_week.date())
        )
    else:
        st.info(f"📆 **Semana Vigente:** {start_current_week.strftime('%d/%m/%Y')} até {end_current_week.strftime('%d/%m/%Y')}")

# Unificação de pendências
col_status_var_all = find_column(df_var, ['Status'])
col_status_fix_all = find_column(df_fixas, ['Status'])

df_agenda_var = df_var[df_var[col_status_var_all].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_var.empty and col_status_var_all else pd.DataFrame()
df_agenda_fix = df_fixas[df_fixas[col_status_fix_all].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_fixas.empty and col_status_fix_all else pd.DataFrame()

df_agenda = pd.concat([df_agenda_var, df_agenda_fix], ignore_index=True)

col_venc = find_column(df_agenda, ['Vencimento', 'Data de Pagamento'])
col_status_ag = find_column(df_agenda, ['Status'])

if not df_agenda.empty and col_venc:
    df_agenda['VENC_DT'] = parse_any_date(df_agenda[col_venc])
    
    cond_vencidos = (df_agenda[col_status_ag] == 'VENCIDO') if col_status_ag else False
    
    if modo_agenda == "Semana Atual Vigente":
        cond_datas = (df_agenda['VENC_DT'] >= pd.to_datetime(start_current_week)) & (df_agenda['VENC_DT'] <= pd.to_datetime(end_current_week))
    else:
        if isinstance(dates_selected, tuple) and len(dates_selected) == 2:
            cond_datas = (df_agenda['VENC_DT'] >= pd.to_datetime(dates_selected[0])) & (df_agenda['VENC_DT'] <= pd.to_datetime(dates_selected[1]))
        else:
            cond_datas = (df_agenda['VENC_DT'] >= pd.to_datetime(start_current_week)) & (df_agenda['VENC_DT'] <= pd.to_datetime(end_current_week))

    df_agenda_filtered = df_agenda[cond_vencidos | cond_datas].copy()
    
    col_val_ag = find_column(df_agenda_filtered, ['Valor', 'Valor (R$)'])
    if not df_agenda_filtered.empty and col_val_ag:
        df_agenda_filtered['Valor (R$)'] = df_agenda_filtered[col_val_ag].apply(lambda x: format_brl(parse_currency(x)))
        cols_show = [c for c in ['Vencimento', 'Fornecedor', 'Descrição', 'Categoria', 'Valor (R$)', 'Status'] if c in df_agenda_filtered.columns]
        
        st.dataframe(
            df_agenda_filtered[cols_show].style.map(
                lambda v: 'color: red; font-weight: bold;' if v == 'VENCIDO' else 'color: orange; font-weight: bold;',
                subset=['Status'] if 'Status' in cols_show else []
            ),
            use_container_width=True
        )
        total_agenda = df_agenda_filtered[col_val_ag].apply(parse_currency).sum()
        st.error(f"⚠️ **Total de Compromissos Exibidos na Agenda:** {format_brl(total_agenda)}")
    else:
        st.success("✅ **Nenhum compromisso pendente ou vencido para os critérios selecionados.**")
else:
    st.success("✅ **Nenhum compromisso pendente ou vencido no sistema.**")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# GRÁFICOS E TABELA OPERACIONAL
# -----------------------------------------------------------------------------
st.subheader("📈 Resultado Financeiro Real do Período")

g_col1, g_col2 = st.columns([6, 4])

with g_col1:
    fig_bar = go.Figure(go.Bar(
        x=['Entradas Extrato', 'Saídas Variáveis', 'Saídas Fixas', 'Resultado Líquido'],
        y=[receita_real, -custo_var_pago, -custo_fixo_pago, resultado_liquido],
        marker_color=['#1E3A8A', '#EF4444', '#F59E0B', '#10B981' if resultado_liquido >= 0 else '#DC2626'],
        text=[format_brl(v) for v in [receita_real, -custo_var_pago, -custo_fixo_pago, resultado_liquido]],
        textposition='auto'
    ))
    fig_bar.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
    st.plotly_chart(fig_bar, use_container_width=True)

with g_col2:
    if (custo_var_pago + custo_fixo_pago) > 0:
        fig_pie = px.pie(
            names=['Contas Variáveis', 'Contas Fixas'],
            values=[custo_var_pago, custo_fixo_pago],
            color_discrete_sequence=['#EF4444', '#F59E0B'],
            hole=0.5
        )
        fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")
st.subheader("📋 Lançamentos de Contas Variáveis (Tabela Real do Período)")

if not df_var_f.empty:
    df_var_display = df_var_f.copy()
    col_val_disp = find_column(df_var_display, ['Valor', 'Valor (R$)'])
    if col_val_disp:
        df_var_display['Valor (R$)'] = df_var_display[col_val_disp].apply(lambda x: format_brl(parse_currency(x)))
    st.dataframe(df_var_display, use_container_width=True)
else:
    st.info("Nenhum lançamento encontrado na aba CONTAS VARIAVEIS para este período.")
