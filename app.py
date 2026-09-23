import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página e tema visual do SaaS
st.set_page_config(
    page_title="Portal BPO Financeiro | Dashboard SaaS",
    page_icon="📊",
    layout="wide"
)

# Estilização CSS Customizada (Visual SaaS Moderno)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .kpi-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #1E3A8A;
        margin-bottom: 10px;
    }
    .kpi-title { font-size: 14px; color: #6B7280; font-weight: 600; text-transform: uppercase; }
    .kpi-value { font-size: 24px; color: #111827; font-weight: bold; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MULTI-TENANT CONFIGURATION (Mapeamento dos Clientes)
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

# -----------------------------------------------------------------------------
# CARREGAMENTO DE DADOS VIA GOOGLE SHEETS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_sheet_csv(sheet_id, sheet_name="RESUMO MENSAL"):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
    try:
        return pd.read_csv(url)
    except Exception as e:
        return None

# -----------------------------------------------------------------------------
# SIDEBAR: AUTENTICAÇÃO E SELEÇÃO DE CLIENTE
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 BPO Financeiro SaaS")
st.sidebar.markdown("---")

cliente_selected_key = st.sidebar.selectbox(
    "Empresa / Cliente Selecionado:",
    options=list(CLIENT_DATABASE.keys()),
    format_func=lambda x: CLIENT_DATABASE[x]["nome"]
)

cliente_info = CLIENT_DATABASE[cliente_selected_key]
st.sidebar.success(f"Conectado: **{cliente_info['nome']}**")

st.sidebar.markdown("### 🔍 Filtros")
mes_selecionado = st.sidebar.selectbox("Competência:", ["Setembro/2026", "Agosto/2026", "Julho/2026"])

# -----------------------------------------------------------------------------
# DASHBOARD PRINCIPAL
# -----------------------------------------------------------------------------
st.title(f"📊 Painel de Gestão Financeira — {cliente_info['nome']}")
st.caption("Visão em tempo real do faturamento, resultado operacional, caixa e pendências.")

# Métrica Padrão
faturamento = 34346.05 if cliente_selected_key == "cliente_tere" else 23221.48
cmv = 5117.17 if cliente_selected_key == "cliente_tere" else 5099.56
cmv_pct = (cmv / faturamento) * 100
despesas = 17983.75 if cliente_selected_key == "cliente_tere" else 7245.01
lucro_liquido = 7528.17 if cliente_selected_key == "cliente_tere" else 10876.91
margem_liquida = (lucro_liquido / faturamento) * 100

vencido_val = 1067.70
pendente_val = 1864.31
pago_val = 11370.07

# KPI Cards
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Faturamento Bruto</div>
            <div class="kpi-value">R$ {faturamento:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #EF4444;">
            <div class="kpi-title">CMV Total</div>
            <div class="kpi-value">R$ {cmv:,.2f} <span style="font-size:14px;color:#EF4444;">({cmv_pct:.1f}%)</span></div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #F59E0B;">
            <div class="kpi-title">Despesas Operacionais</div>
            <div class="kpi-value">R$ {despesas:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #10B981;">
            <div class="kpi-title">Lucro Líquido Real</div>
            <div class="kpi-value">R$ {lucro_liquido:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #6366F1;">
            <div class="kpi-title">Margem Líquida</div>
            <div class="kpi-value">{margem_liquida:.1f}%</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Gráficos
g_col1, g_col2 = st.columns([6, 4])

with g_col1:
    st.subheader("📈 DRE Sintética e Resultado Operacional")
    dre_categories = ['Faturamento Bruto', 'CMV (Insumos)', 'Despesas Operacionais', 'Lucro Líquido']
    dre_values = [faturamento, -cmv, -despesas, lucro_liquido]
    colors = ['#1E3A8A', '#EF4444', '#F59E0B', '#10B981']
    
    fig_dre = go.Figure(go.Bar(
        x=dre_categories,
        y=dre_values,
        marker_color=colors,
        text=[f"R$ {v:,.2f}" for v in dre_values],
        textposition='auto'
    ))
    fig_dre.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
    st.plotly_chart(fig_dre, use_container_width=True)

with g_col2:
    st.subheader("💳 Distribuição de Status do Caixa")
    labels_status = ['Pagos', 'Pendentes', 'Vencidos']
    values_status = [pago_val, pendente_val, vencido_val]
    colors_status = ['#10B981', '#F59E0B', '#EF4444']
    
    fig_pie = px.pie(
        names=labels_status,
        values=values_status,
        color_discrete_sequence=colors_status,
        hole=0.5
    )
    fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
    st.plotly_chart(fig_pie, use_container_width=True)

# Alertas
st.markdown("---")
st.subheader("🚨 Alertas e Recomendações de BPO")
st.warning("⚠️ **Atenção Inadimplência:** Existem contas pendentes/vencidas que precisam de atenção da gestão.")
st.info("💡 **Eficiência CMV:** Margem mantida em patamar saudável para o segmento.")
