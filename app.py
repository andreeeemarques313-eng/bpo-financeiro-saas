import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(
    page_title="Portal BPO Financeiro | Gestão & Analytics",
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
        "nome": "🏢 TODAS AS UNIDADES (CONSOLIDADO)",
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
# FUNÇÕES DE TRATAMENTO DE MOEDA E DATAS
# -----------------------------------------------------------------------------
def parse_currency(val):
    if pd.isna(val): return 0.0
    val_str = str(val).strip().replace('R$', '').strip()
    if not val_str: return 0.0
    
    if ',' in val_str and '.' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try:
        return float(val_str)
    except:
        return 0.0

def format_brl(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data(ttl=120)
def load_operational_data(sheet_id):
    def get_df(s_id, sheet_name):
        url = f"https://docs.google.com/spreadsheets/d/{s_id}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
        try:
            df = pd.read_csv(url)
            df.columns = df.columns.str.strip()
            return df
        except:
            return pd.DataFrame()

    if sheet_id == "CONSOLIDADO":
        e1, v1, f1 = load_operational_data("1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw")
        e2, v2, f2 = load_operational_data("1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw")
        df_extrato = pd.concat([e1, e2], ignore_index=True) if not e1.empty or not e2.empty else pd.DataFrame()
        df_var = pd.concat([v1, v2], ignore_index=True) if not v1.empty or not v2.empty else pd.DataFrame()
        df_fixas = pd.concat([f1, f2], ignore_index=True) if not f1.empty or not f2.empty else pd.DataFrame()
        return df_extrato, df_var, df_fixas
    else:
        df_extrato = get_df(sheet_id, "EXTRATO BANCARIO")
        df_var = get_df(sheet_id, "CONTAS VARIAVEIS")
        df_fixas = get_df(sheet_id, "CONTAS FIXAS")
        return df_extrato, df_var, df_fixas

# -----------------------------------------------------------------------------
# SIDEBAR - SELEÇÃO E FILTROS
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

# Filtro de Período
st.sidebar.markdown("### 🔍 Período da Análise")
periodo_opcoes = ["Setembro/2026", "Agosto/2026", "Julho/2026", "CONSOLIDADO DO ANO (2026)"]
periodo_selecionado = st.sidebar.selectbox("Competência / Filtro:", periodo_opcoes)

# Carregar Dados Reais das 3 Abas
df_extrato, df_var, df_fixas = load_operational_data(cliente_info['sheet_id'])

# -----------------------------------------------------------------------------
# FILTRAGEM POR DATA / PERÍODO
# -----------------------------------------------------------------------------
def filter_by_period(df, date_col):
    if df.empty or date_col not in df.columns:
        return df
    
    df['DATA_PARSED'] = pd.to_datetime(df[date_col], errors='coerce')
    
    if periodo_selecionado == "Setembro/2026":
        return df[(df['DATA_PARSED'].dt.month == 9) & (df['DATA_PARSED'].dt.year == 2026)]
    elif periodo_selecionado == "Agosto/2026":
        return df[(df['DATA_PARSED'].dt.month == 8) & (df['DATA_PARSED'].dt.year == 2026)]
    elif periodo_selecionado == "Julho/2026":
        return df[(df['DATA_PARSED'].dt.month == 7) & (df['DATA_PARSED'].dt.year == 2026)]
    else: # Consolidado Ano 2026
        return df[df['DATA_PARSED'].dt.year == 2026]

df_extrato_f = filter_by_period(df_extrato, 'DATA')
df_var_f = filter_by_period(df_var, 'Vencimento')
df_fixas_f = filter_by_period(df_fixas, 'Vencimento')

# -----------------------------------------------------------------------------
# PROCESSAMENTO DE VALORES REAIS (CRÉDITOS DO EXTRATO)
# -----------------------------------------------------------------------------
receita_real = 0.0
if not df_extrato_f.empty:
    col_valor = [c for c in df_extrato_f.columns if 'VALOR' in c.upper() or 'BANCO' in c.upper()]
    if col_valor:
        vals = df_extrato_f[col_valor[0]].apply(parse_currency)
        # Considera apenas ENTRADAS REAIS (créditos > 0)
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
st.title(f"📊 DRE e Caixa Real — {cliente_info['nome']}")
st.caption(f"Exibindo dados reais para o período: **{periodo_selecionado}**")

# KPI Cards Reais
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Entradas Reais (Créditos Extrato)</div><div class="kpi-value">{format_brl(receita_real)}</div></div>', unsafe_allow_html=True)
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
# AGENDA FINANCEIRA SEMANAL ROTATIVA (SÓ COMPROMISSOS DA SEMANA VIGENTE)
# -----------------------------------------------------------------------------
st.subheader("📅 Agenda Financeira Semanal (A Pagar na Semana Vigente)")

today = datetime.today()
# Calculando o início e fim da semana vigente (ex: 7 dias a partir de hoje ou do ciclo atual)
start_week = today - timedelta(days=today.weekday())
end_week = start_week + timedelta(days=6)

df_agenda_var = df_var[df_var['Status'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_var.empty and 'Status' in df_var.columns else pd.DataFrame()
df_agenda_fix = df_fixas[df_fixas['Status'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_fixas.empty and 'Status' in df_fixas.columns else pd.DataFrame()

df_agenda = pd.concat([df_agenda_var, df_agenda_fix], ignore_index=True)

if not df_agenda.empty and 'Vencimento' in df_agenda.columns:
    df_agenda['VENC_DT'] = pd.to_datetime(df_agenda['Vencimento'], errors='coerce')
    # Filtrar apenas o que vence no ciclo da semana vigente (ou que já venceu)
    df_agenda_semana = df_agenda[(df_agenda['VENC_DT'] <= end_week) | (df_agenda['Status'] == 'VENCIDO')]
    
    if not df_agenda_semana.empty:
        df_agenda_semana['Valor (R$)'] = df_agenda_semana['Valor'].apply(lambda x: format_brl(parse_currency(x)))
        cols_agenda = [c for c in ['Vencimento', 'Fornecedor', 'Descrição', 'Categoria', 'Valor (R$)', 'Status'] if c in df_agenda_semana.columns]
        
        st.dataframe(
            df_agenda_semana[cols_agenda].style.map(
                lambda v: 'color: red; font-weight: bold;' if v == 'VENCIDO' else 'color: orange; font-weight: bold;',
                subset=['Status']
            ),
            use_container_width=True
        )
        total_semana = df_agenda_semana['Valor'].apply(parse_currency).sum()
        st.error(f"⚠️ **Total de Compromissos a Pagar na Semana Vigente ({start_week.strftime('%d/%m')} a {end_week.strftime('%d/%m')}):** {format_brl(total_semana)}")
    else:
        st.success("✅ **Nenhuma conta vencida ou com vencimento para esta semana.**")
else:
    st.success("✅ **Nenhuma conta vencida ou pendente identificada.**")

st.markdown("<br>", unsafe_allow_html=True)

# Visualização de Gráficos Reais
g_col1, g_col2 = st.columns([6, 4])

with g_col1:
    st.subheader("📈 Resultado Financeiro Real (Fluxo do Período)")
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
    st.subheader("💳 Distribuição de Saídas Efetivadas")
    if (custo_var_pago + custo_fixo_pago) > 0:
        fig_pie = px.pie(
            names=['Contas Variáveis', 'Contas Fixas'],
            values=[custo_var_pago, custo_fixo_pago],
            color_discrete_sequence=['#EF4444', '#F59E0B'],
            hole=0.5
        )
        fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

# Tabela Operacional
st.markdown("---")
st.subheader("📋 Lançamentos de Contas Variáveis (Tabela Real do Período)")

if not df_var_f.empty:
    df_var_display = df_var_f.copy()
    if 'Valor' in df_var_display.columns:
        df_var_display['Valor (R$)'] = df_var_display['Valor'].apply(lambda x: format_brl(parse_currency(x)))
    st.dataframe(df_var_display, use_container_width=True)
else:
    st.info("Nenhum lançamento encontrado na aba CONTAS VARIAVEIS para este período.")
