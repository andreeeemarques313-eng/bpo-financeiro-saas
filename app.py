import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(
    page_title="Portal BPO Financeiro | Agenda & BI Reais",
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
    "cliente_tere": {
        "nome": "Fino House - Unidade Teresópolis",
        "sheet_id": "1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw"
    },
    "cliente_ob": {
        "nome": "Fino House - Unidade Minas Gerais",
        "sheet_id": "1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw"
    }
}

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
# SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 BPO Financeiro Real")
st.sidebar.markdown("---")

cliente_selected_key = st.sidebar.selectbox(
    "Unidade Selecionada:",
    options=list(CLIENT_DATABASE.keys()),
    format_func=lambda x: CLIENT_DATABASE[x]["nome"]
)

cliente_info = CLIENT_DATABASE[cliente_selected_key]
st.sidebar.success(f"Conectado: **{cliente_info['nome']}**")

# Carregar dados transacionais
df_extrato, df_var, df_fixas = load_operational_data(cliente_info['sheet_id'])

# Tratar valores numéricos das tabelas
if not df_var.empty and 'Valor' in df_var.columns:
    df_var['Valor_Float'] = df_var['Valor'].apply(clean_money)
    df_var['Valor (R$)'] = df_var['Valor_Float'].apply(format_brl)

if not df_fixas.empty and 'Valor' in df_fixas.columns:
    df_fixas['Valor_Float'] = df_fixas['Valor'].apply(clean_money)
    df_fixas['Valor (R$)'] = df_fixas['Valor_Float'].apply(format_brl)

# -----------------------------------------------------------------------------
# PROCESSAMENTO DE DADOS REAIS
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
st.title(f"📊 Gestão Financeira Reais — {cliente_info['nome']}")

# KPI Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Entradas Reais (Extrato)</div><div class="kpi-value">{format_brl(receita_real)}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #EF4444;"><div class="kpi-title">Saídas Variáveis Pagas</div><div class="kpi-value">{format_brl(custo_var_pago)}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #F59E0B;"><div class="kpi-title">Saídas Fixas Pagas</div><div class="kpi-value">{format_brl(custo_fixo_pago)}</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="kpi-card" style="border-left-color: {"#10B981" if resultado_liquido >= 0 else "#EF4444"};"><div class="kpi-title">Resultado de Caixa Real</div><div class="kpi-value">{format_brl(resultado_liquido)}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# AGENDA FINANCEIRA SEMANAL (VENCIDOS E PENDENTES A PAGAR)
# -----------------------------------------------------------------------------
st.subheader("📅 Agenda Financeira Semanal (Contas Vencidas e Pendentes a Pagar)")

# Unir vencidos e pendentes de variáveis e fixas
df_agenda_var = df_var[df_var['Status'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_var.empty and 'Status' in df_var.columns else pd.DataFrame()
df_agenda_fix = df_fixas[df_fixas['Status'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_fixas.empty and 'Status' in df_fixas.columns else pd.DataFrame()

df_agenda = pd.concat([df_agenda_var, df_agenda_fix], ignore_index=True)

if not df_agenda.empty:
    cols_display = [c for c in ['Vencimento', 'Fornecedor', 'Descrição', 'Categoria', 'Valor (R$)', 'Status'] if c in df_agenda.columns]
    
    # Exibição formatada
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
# TABELA COMPLETA DE LANÇAMENTOS
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 Gestão Detalhada de Lançamentos (Todas as Contas Variáveis)")

if not df_var.empty:
    cols_var_show = [c for c in ['Vencimento', 'Data de Pagamento', 'Fornecedor', 'Descrição', 'Categoria', 'Valor (R$)', 'Status', 'CONCILIATION BANCARIA'] if c in df_var.columns]
    if not cols_var_show:
        cols_var_show = [c for c in df_var.columns if c != 'Valor_Float']
    
    st.dataframe(df_var[cols_var_show], use_container_width=True)
else:
    st.info("Nenhum dado encontrado na aba CONTAS VARIAVEIS.")
