import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuração da página e tema visual do SaaS
st.set_page_config(
    page_title="Portal BPO Financeiro | Agenda & Analytics",
    page_icon="📊",
    layout="wide"
)

# Estilização CSS Customizada (Visual SaaS Moderno)
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
# MULTI-TENANT CONFIGURATION (Mapeamento das Unidades)
# -----------------------------------------------------------------------------
CLIENT_DATABASE = {
    "cliente_tere": {
        "nome": "Fino House - Unidade Teresópolis",
        "sheet_id": "1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw"
    },
    "cliente_ob": {
        "nome": "Fino House - Unidade Minas Gerais",
        "sheet_id": "1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw"
    }
}

# Funções auxiliares de limpeza e formatação monetária
def clean_money(val):
    if pd.isna(val): return 0.0
    val_str = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(val_str)
    except:
        return 0.0

def format_brl(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Carregamento dinâmico direto das abas operacionais do Google Sheets
@st.cache_data(ttl=120)
def load_operational_data(sheet_id):
    def get_df(sheet_name):
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
        try:
            df = pd.read_csv(url)
            df.columns = df.columns.str.strip()
            return df
        except:
            return pd.DataFrame()

    df_extrato = get_df("EXTRATO BANCARIO")
    df_var = get_df("CONTAS VARIAVEIS")
    df_fixas = get_df("CONTAS FIXAS")

    return df_extrato, df_var, df_fixas

# -----------------------------------------------------------------------------
# SIDEBAR - SELEÇÃO DE EMPRESA E REGRAS
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 BPO Financeiro SaaS")
st.sidebar.markdown("---")

cliente_selected_key = st.sidebar.selectbox(
    "Unidade Selecionada:",
    options=list(CLIENT_DATABASE.keys()),
    format_func=lambda x: CLIENT_DATABASE[x]["nome"]
)

cliente_info = CLIENT_DATABASE[cliente_selected_key]
st.sidebar.success(f"Conectado: **{cliente_info['nome']}**")

# Carregar dados reais das abas operacionais
df_extrato, df_var, df_fixas = load_operational_data(cliente_info['sheet_id'])

# Ajustar e formatar valores numéricos
if not df_var.empty and 'Valor' in df_var.columns:
    df_var['Valor_Float'] = df_var['Valor'].apply(clean_money)
    df_var['Valor (R$)'] = df_var['Valor_Float'].apply(format_brl)

if not df_fixas.empty and 'Valor' in df_fixas.columns:
    df_fixas['Valor_Float'] = df_fixas['Valor'].apply(clean_money)
    df_fixas['Valor (R$)'] = df_fixas['Valor_Float'].apply(format_brl)

# -----------------------------------------------------------------------------
# PROCESSAMENTO DOS INDICADORES REAIS DE CAIXA E DRE
# -----------------------------------------------------------------------------
receita_real = 0.0
if not df_extrato.empty:
    col_valor = [c for c in df_extrato.columns if 'VALOR' in c.upper() or 'BANCO' in c.upper()]
    if col_valor:
        receita_real = df_extrato[col_valor[0]].apply(clean_money).sum()

custo_var_pago = df_var[df_var['Status'] == 'PAGO']['Valor_Float'].sum() if not df_var.empty and 'Status' in df_var.columns else 0.0
custo_fixo_pago = df_fixas[df_fixas['Status'] == 'PAGO']['Valor_Float'].sum() if not df_fixas.empty and 'Status' in df_fixas.columns else 0.0

resultado_liquido = receita_real - (custo_var_pago + custo_fixo_pago)

# -----------------------------------------------------------------------------
# PAINEL PRINCIPAL
# -----------------------------------------------------------------------------
st.title(f"📊 Gestão Financeira Real — {cliente_info['nome']}")
st.caption("Dados calculados diretamente dos lançamentos das abas de Extrato, Contas Fixas e Contas Variáveis.")

# KPI Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Entradas (Extrato)</div><div class="kpi-value">{format_brl(receita_real)}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #EF4444;"><div class="kpi-title">Saídas Variáveis Pagas</div><div class="kpi-value">{format_brl(custo_var_pago)}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #F59E0B;"><div class="kpi-title">Saídas Fixas Pagas</div><div class="kpi-value">{format_brl(custo_fixo_pago)}</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="kpi-card" style="border-left-color: {"#10B981" if resultado_liquido >= 0 else "#EF4444"};"><div class="kpi-title">Resultado de Caixa Real</div><div class="kpi-value">{format_brl(resultado_liquido)}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# AGENDA FINANCEIRA SEMANAL (CONTAS VENCIDAS E PENDENTES A PAGAR)
# -----------------------------------------------------------------------------
st.subheader("📅 Agenda Financeira Semanal (Contas Vencidas e Pendentes a Pagar)")

df_agenda_var = df_var[df_var['Status'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_var.empty and 'Status' in df_var.columns else pd.DataFrame()
df_agenda_fix = df_fixas[df_fixas['Status'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_fixas.empty and 'Status' in df_fixas.columns else pd.DataFrame()

df_agenda = pd.concat([df_agenda_var, df_agenda_fix], ignore_index=True)

if not df_agenda.empty:
    cols_display = [c for c in ['Vencimento', 'Fornecedor', 'Descrição', 'Categoria', 'Valor (R$)', 'Status'] if c in df_agenda.columns]
    
    st.dataframe(
        df_agenda[cols_display].style.map(
            lambda v: 'color: red; font-weight: bold;' if v == 'VENCIDO' else 'color: orange; font-weight: bold;',
            subset=['Status']
        ),
        use_container_width=True
    )
    
    total_a_pagar = df_agenda['Valor_Float'].sum()
    st.error(f"⚠️ **Total de Compromissos Pendentes / Vencidos a Pagar:** {format_brl(total_a_pagar)}")
else:
    st.success("✅ **Nenhuma conta vencida ou pendente para esta semana.**")

# -----------------------------------------------------------------------------
# TABELA DETALHADA COMPLETA (FORMATADA EM MOEDA)
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 Gestão Detalhada de Lançamentos (Contas Variáveis)")

if not df_var.empty:
    cols_var_show = [c for c in ['Vencimento', 'Data de Pagamento', 'Fornecedor', 'Descrição', 'Categoria', 'Valor (R$)', 'Status', 'CONCILIAÇÃO BANCARIA'] if c in df_var.columns]
    if not cols_var_show:
        cols_var_show = [c for c in df_var.columns if c != 'Valor_Float']
    
    st.dataframe(df_var[cols_var_show], use_container_width=True)
else:
    st.info("Nenhum dado encontrado na aba CONTAS VARIAVEIS.")
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(
    page_title="Portal BPO Financeiro | Dados Operacionais Reais",
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
# FUNÇÕES DE LIMPEZA E FORMATAÇÃO DE MOEDA
# -----------------------------------------------------------------------------
def clean_money(val):
    if pd.isna(val): return 0.0
    val_str = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
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
        # Carrega Teresópolis e MG e unifica
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
# SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Painel de Dados Reais")
st.sidebar.markdown("---")

cliente_selected_key = st.sidebar.selectbox(
    "Unidade Selecionada:",
    options=list(CLIENT_DATABASE.keys()),
    format_func=lambda x: CLIENT_DATABASE[x]["nome"]
)

cliente_info = CLIENT_DATABASE[cliente_selected_key]
st.sidebar.success(f"Conectado: **{cliente_info['nome']}**")

# Carregar Dados Reais das 3 Abas Transacionais
df_extrato, df_var, df_fixas = load_operational_data(cliente_info['sheet_id'])

# -----------------------------------------------------------------------------
# PROCESSAMENTO DE VALORES REAIS
# -----------------------------------------------------------------------------
# 1. Receita (Extrato)
receita_real = 0.0
if not df_extrato.empty:
    col_valor = [c for c in df_extrato.columns if 'VALOR' in c.upper() or 'BANCO' in c.upper()]
    if col_valor:
        receita_real = df_extrato[col_valor[0]].apply(clean_money).sum()

# 2. Custos Variáveis / CMV (Contas Variáveis)
custo_var_pago = 0.0
var_vencido = 0.0
if not df_var.empty and 'Valor' in df_var.columns:
    df_var['VALOR_CLEAN'] = df_var['Valor'].apply(clean_money)
    if 'Status' in df_var.columns:
        custo_var_pago = df_var[df_var['Status'] == 'PAGO']['VALOR_CLEAN'].sum()
        var_vencido = df_var[df_var['Status'].isin(['VENCIDO', 'PENDENTE'])]['VALOR_CLEAN'].sum()

# 3. Custos Fixos (Contas Fixas)
custo_fixo_pago = 0.0
fixo_vencido = 0.0
if not df_fixas.empty and 'Valor' in df_fixas.columns:
    df_fixas['VALOR_CLEAN'] = df_fixas['Valor'].apply(clean_money)
    if 'Status' in df_fixas.columns:
        custo_fixo_pago = df_fixas[df_fixas['Status'] == 'PAGO']['VALOR_CLEAN'].sum()
        fixo_vencido = df_fixas[df_fixas['Status'].isin(['VENCIDO', 'PENDENTE'])]['VALOR_CLEAN'].sum()

# Cálculos Consolidados de DRE Real
resultado_liquido = receita_real - (custo_var_pago + custo_fixo_pago)
total_vencido_pendente = var_vencido + fixo_vencido

# -----------------------------------------------------------------------------
# PAINEL PRINCIPAL
# -----------------------------------------------------------------------------
st.title(f"📊 DRE e Caixa Real — {cliente_info['nome']}")
st.caption("Métricas calculadas exclusivamente com base em lançamentos de Extrato, Contas Fixas e Contas Variáveis.")

# KPI Cards Reais
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Entradas (Extrato)</div>
            <div class="kpi-value">{format_brl(receita_real)}</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #EF4444;">
            <div class="kpi-title">Contas Variáveis Pagas</div>
            <div class="kpi-value">{format_brl(custo_var_pago)}</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #F59E0B;">
            <div class="kpi-title">Contas Fixas Pagas</div>
            <div class="kpi-value">{format_brl(custo_fixo_pago)}</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color: {'#10B981' if resultado_liquido >= 0 else '#EF4444'};">
            <div class="kpi-title">Resultado de Caixa Real</div>
            <div class="kpi-value">{format_brl(resultado_liquido)}</div>
        </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #DC2626;">
            <div class="kpi-title">Total Pendente / Vencido</div>
            <div class="kpi-value">{format_brl(total_vencido_pendente)}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# AGENDA FINANCEIRA SEMANAL (VENCIDOS E PENDENTES A PAGAR)
# -----------------------------------------------------------------------------
st.subheader("📅 Agenda Financeira Semanal (Contas Vencidas e Pendentes a Pagar)")

df_agenda_var = df_var[df_var['Status'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_var.empty and 'Status' in df_var.columns else pd.DataFrame()
df_agenda_fix = df_fixas[df_fixas['Status'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_fixas.empty and 'Status' in df_fixas.columns else pd.DataFrame()

df_agenda = pd.concat([df_agenda_var, df_agenda_fix], ignore_index=True)

if not df_agenda.empty:
    if 'VALOR_CLEAN' in df_agenda.columns:
        df_agenda['Valor Exibição'] = df_agenda['VALOR_CLEAN'].apply(format_brl)
    elif 'Valor' in df_agenda.columns:
        df_agenda['Valor Exibição'] = df_agenda['Valor'].apply(lambda x: format_brl(clean_money(x)))

    cols_agenda_show = [c for c in ['Vencimento', 'Fornecedor', 'Descrição', 'Categoria', 'Valor Exibição', 'Status'] if c in df_agenda.columns]
    
    st.dataframe(
        df_agenda[cols_agenda_show].style.map(
            lambda v: 'color: red; font-weight: bold;' if v == 'VENCIDO' else 'color: orange; font-weight: bold;',
            subset=['Status']
        ),
        use_container_width=True
    )
    st.error(f"⚠️ **Total da Agenda a Pagar:** {format_brl(total_vencido_pendente)}")
else:
    st.success("✅ **Nenhuma conta vencida ou pendente identificada nesta seleção.**")

st.markdown("<br>", unsafe_allow_html=True)

# Visualização de Gráficos Reais
g_col1, g_col2 = st.columns([6, 4])

with g_col1:
    st.subheader("📈 Resultado Financeiro Real (Fluxo de Entrada x Saída)")
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

# Tabela Operacional de Lançamentos
st.markdown("---")
st.subheader("📋 Lançamentos de Contas Variáveis (Tabela Real)")

if not df_var.empty:
    df_var_display = df_var.copy()
    if 'VALOR_CLEAN' in df_var_display.columns:
        df_var_display['Valor (R$)'] = df_var_display['VALOR_CLEAN'].apply(format_brl)
        cols_to_drop = [c for c in ['VALOR_CLEAN', 'Valor'] if c in df_var_display.columns]
        df_var_display = df_var_display.drop(columns=cols_to_drop)
    st.dataframe(df_var_display, use_container_width=True)
else:
    st.info("Nenhum lançamento encontrado na aba CONTAS VARIAVEIS.")
