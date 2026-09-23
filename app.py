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
# FUNÇÕES ROBUSTAS DE TRATAMENTO DE MOEDA E DATAS MISTAS
# -----------------------------------------------------------------------------
def parse_currency(val):
    if pd.isna(val): return 0.0
    s = str(val).strip().replace('R$', '').replace(' ', '').strip()
    if not s or s == '-': return 0.0
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

def parse_dates_robust(series):
    res = pd.to_datetime(series, dayfirst=True, errors='coerce')
    mask_nat = res.isna()
    if mask_nat.any():
        month_map = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                     'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}
        def map_str(s):
            if pd.isna(s): return pd.NaT
            s_str = str(s).lower().strip()
            for m_name, m_num in month_map.items():
                if m_name in s_str:
                    parts = s_str.split('-')
                    if len(parts) > 1:
                        yr = int('20' + parts[1].strip()) if len(parts[1].strip()) == 2 else int(parts[1].strip())
                        return pd.Timestamp(year=yr, month=m_num, day=1)
            return pd.NaT
        res[mask_nat] = series[mask_nat].apply(map_str)
    return res

# -----------------------------------------------------------------------------
# LEITURA DAS ABAS OPERACIONAIS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=30)
def load_operational_data(sheet_id):
    def get_df(s_id, sheet_name):
        url = f"https://docs.google.com/spreadsheets/d/{s_id}/export?format=csv&sheet={sheet_name.replace(' ', '%20')}"
        try:
            df = pd.read_csv(url)
            df.columns = df.columns.str.strip()
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

# Carregamento Integral dos Dados
df_extrato, df_var, df_fixas = load_operational_data(cliente_info['sheet_id'])

# -----------------------------------------------------------------------------
# FILTRAGEM INTELIGENTE POR MÊS E ANO
# -----------------------------------------------------------------------------
def filter_dataframe_by_period(df, primary_date_col, secondary_date_col=None):
    if df.empty:
        return df
    
    # Determina a melhor coluna de data disponível
    date_series = None
    if primary_date_col in df.columns:
        date_series = df[primary_date_col]
    elif secondary_date_col and secondary_date_col in df.columns:
        date_series = df[secondary_date_col]
    elif 'Competência' in df.columns:
        date_series = df['Competência']
    else:
        return df

    parsed_dates = parse_dates_robust(date_series)
    df['DATA_PARSED_TEMP'] = parsed_dates

    if periodo_selecionado == "Setembro/2026":
        return df[(df['DATA_PARSED_TEMP'].dt.month == 9) & (df['DATA_PARSED_TEMP'].dt.year == 2026)]
    elif periodo_selecionado == "Agosto/2026":
        return df[(df['DATA_PARSED_TEMP'].dt.month == 8) & (df['DATA_PARSED_TEMP'].dt.year == 2026)]
    elif periodo_selecionado == "Julho/2026":
        return df[(df['DATA_PARSED_TEMP'].dt.month == 7) & (df['DATA_PARSED_TEMP'].dt.year == 2026)]
    else: # Consolidado Ano 2026
        return df[df['DATA_PARSED_TEMP'].dt.year == 2026]

df_extrato_f = filter_dataframe_by_period(df_extrato, 'DATA')
df_var_f = filter_dataframe_by_period(df_var, 'Data de Pagamento', 'Vencimento')
df_fixas_f = filter_dataframe_by_period(df_fixas, 'Data de Pagamento', 'Vencimento')

# -----------------------------------------------------------------------------
# PROCESSAMENTO DOS VALORES REAIS DAS ABAS
# -----------------------------------------------------------------------------
receita_real = 0.0
if not df_extrato_f.empty:
    col_valor = [c for c in df_extrato_f.columns if 'BANCO' in c.upper() or 'VALOR' in c.upper()]
    if col_valor:
        vals = df_extrato_f[col_valor[0]].apply(parse_currency)
        receita_real = vals[vals > 0].sum()

custo_var_pago = 0.0
var_vencido = 0.0
if not df_var_f.empty and 'Valor' in df_var_f.columns:
    df_var_f['VALOR_CLEAN'] = df_var_f['Valor'].apply(parse_currency)
    if 'Status' in df_var_f.columns:
        custo_var_pago = df_var_f[df_var_f['Status'] == 'PAGO']['VALOR_CLEAN'].sum()
        var_vencido = df_var_f[df_var_f['Status'].isin(['VENCIDO', 'PENDENTE'])]['VALOR_CLEAN'].sum()

custo_fixo_pago = 0.0
fixo_vencido = 0.0
if not df_fixas_f.empty and 'Valor' in df_fixas_f.columns:
    df_fixas_f['VALOR_CLEAN'] = df_fixas_f['Valor'].apply(parse_currency)
    if 'Status' in df_fixas_f.columns:
        custo_fixo_pago = df_fixas_f[df_fixas_f['Status'] == 'PAGO']['VALOR_CLEAN'].sum()
        fixo_vencido = df_fixas_f[df_fixas_f['Status'].isin(['VENCIDO', 'PENDENTE'])]['VALOR_CLEAN'].sum()

resultado_liquido = receita_real - (custo_var_pago + custo_fixo_pago)
total_vencido_pendente = var_vencido + fixo_vencido

# -----------------------------------------------------------------------------
# PAINEL PRINCIPAL
# -----------------------------------------------------------------------------
st.title(f"📊 Gestão Financeira Real — {cliente_info['nome']}")
st.caption(f"Filtro Selecionado: **{periodo_selecionado}** | Leitura automática do Extrato, Contas Fixas e Variáveis")

# KPI Cards Reais
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
# AGENDA FINANCEIRA (ATRASADOS INCONDICIONAIS + SEMANA VIGENTE / CALENDÁRIO)
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

# Unificar pendências e vencidos
df_agenda_var = df_var[df_var['Status'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_var.empty and 'Status' in df_var.columns else pd.DataFrame()
df_agenda_fix = df_fixas[df_fixas['Status'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_fixas.empty and 'Status' in df_fixas.columns else pd.DataFrame()

df_agenda = pd.concat([df_agenda_var, df_agenda_fix], ignore_index=True)

if not df_agenda.empty and 'Vencimento' in df_agenda.columns:
    df_agenda['VENC_DT'] = parse_dates_robust(df_agenda['Vencimento'])
    
    cond_vencidos = (df_agenda['Status'] == 'VENCIDO')
    
    if modo_agenda == "Semana Atual Vigente":
        cond_datas = (df_agenda['VENC_DT'] >= pd.to_datetime(start_current_week)) & (df_agenda['VENC_DT'] <= pd.to_datetime(end_current_week))
    else:
        if isinstance(dates_selected, tuple) and len(dates_selected) == 2:
            cond_datas = (df_agenda['VENC_DT'] >= pd.to_datetime(dates_selected[0])) & (df_agenda['VENC_DT'] <= pd.to_datetime(dates_selected[1]))
        else:
            cond_datas = (df_agenda['VENC_DT'] >= pd.to_datetime(start_current_week)) & (df_agenda['VENC_DT'] <= pd.to_datetime(end_current_week))

    df_agenda_filtered = df_agenda[cond_vencidos | cond_datas].copy()
    
    if not df_agenda_filtered.empty:
        df_agenda_filtered['Valor (R$)'] = df_agenda_filtered['Valor'].apply(lambda x: format_brl(parse_currency(x)))
        cols_show = [c for c in ['Vencimento', 'Fornecedor', 'Descrição', 'Categoria', 'Valor (R$)', 'Status'] if c in df_agenda_filtered.columns]
        
        st.dataframe(
            df_agenda_filtered[cols_show].style.map(
                lambda v: 'color: red; font-weight: bold;' if v == 'VENCIDO' else 'color: orange; font-weight: bold;',
                subset=['Status']
            ),
            use_container_width=True
        )
        total_agenda = df_agenda_filtered['Valor'].apply(parse_currency).sum()
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
    if 'Valor' in df_var_display.columns:
        df_var_display['Valor (R$)'] = df_var_display['Valor'].apply(lambda x: format_brl(parse_currency(x)))
    st.dataframe(df_var_display, use_container_width=True)
else:
    st.info("Nenhum lançamento encontrado na aba CONTAS VARIAVEIS para este período.")
