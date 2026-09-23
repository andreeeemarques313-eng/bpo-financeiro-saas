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
    .kpi-title { font-size: 13px; color: #6B7280; font-weight: 600; text-transform: uppercase; }
    .kpi-value { font-size: 22px; color: #111827; font-weight: bold; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MAPEAMENTO DE UNIDADES / CLIENTES
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
def load_sheet_csv(sheet_id, sheet_name="CONTAS VARIAVEIS"):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        return None

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Painel Executivo BPO")
st.sidebar.markdown("---")

cliente_selected_key = st.sidebar.selectbox(
    "Unidade Selecionada:",
    options=list(CLIENT_DATABASE.keys()),
    format_func=lambda x: CLIENT_DATABASE[x]["nome"]
)

cliente_info = CLIENT_DATABASE[cliente_selected_key]
st.sidebar.success(f"Conectado: **{cliente_info['nome']}**")

st.sidebar.markdown("### 🔍 Filtros Gerais")
mes_selecionado = st.sidebar.selectbox("Competência:", ["Setembro/2026", "Agosto/2026", "Julho/2026"])

# -----------------------------------------------------------------------------
# PAINEL PRINCIPAL
# -----------------------------------------------------------------------------
st.title(f"📊 Gestão Financeira Avançada — {cliente_info['nome']}")
st.caption("Acompanhamento de DRE, Fluxo de Caixa Projetado, Destaques de CMV e Controle de Vencimentos.")

# Dados Base das Unidades
faturamento = 34346.05 if cliente_selected_key == "cliente_tere" else 23221.48
cmv = 5117.17 if cliente_selected_key == "cliente_tere" else 5099.56
cmv_pct = (cmv / faturamento) * 100
despesas = 17983.75 if cliente_selected_key == "cliente_tere" else 7245.01
lucro_liquido = 7528.17 if cliente_selected_key == "cliente_tere" else 10876.91
margem_liquida = (lucro_liquido / faturamento) * 100

vencido_val = 1067.70
pendente_val = 1864.31
pago_val = 11370.07

# --- LINHA 1: KPIS PRINCIPAIS ---
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
            <div class="kpi-value">R$ {cmv:,.2f} <span style="font-size:13px;color:#EF4444;">({cmv_pct:.1f}%)</span></div>
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

# --- LINHA 2: PROJEÇÃO DE FLUXO DE CAIXA E DRE ---
tab1, tab2 = st.tabs(["📈 Projeção de Fluxo de Caixa (15/30 Dias)", "📊 DRE e Composição da Operação"])

with tab1:
    st.subheader("Projeção de Saldo Diário de Caixa")
    
    # Gerando datas projetadas a partir de hoje
    datas_proj = [datetime.today() + timedelta(days=i) for i in range(15)]
    saldo_inicial = 7999.47
    
    # Simulação de variações de caixa baseadas nos compromissos agendados
    saldos_projetados = []
    saldo_curr = saldo_inicial
    for i, d in enumerate(datas_proj):
        # saídas simulação
        saida = 300 if i % 3 == 0 else (500 if i % 5 == 0 else 50)
        entrada = 1200 if i % 4 == 0 else 200
        saldo_curr += (entrada - saida)
        saldos_projetados.append(saldo_curr)

    df_proj = pd.DataFrame({"Data": datas_proj, "Saldo Projetado (R$)": saldos_projetados})
    
    fig_proj = px.line(
        df_proj, 
        x="Data", 
        y="Saldo Projetado (R$)", 
        markers=True,
        line_shape="spline",
        title="Evolução Prevista do Saldo Acumulado em Conta"
    )
    fig_proj.update_traces(line_color="#1E3A8A", line_width=3)
    fig_proj.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Limite Crítico de Caixa")
    st.plotly_chart(fig_proj, use_container_width=True)

with tab2:
    g_col1, g_col2 = st.columns([6, 4])
    
    with g_col1:
        st.subheader("DRE Operacional Sintética")
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
        st.subheader("Status de Pagamentos")
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

# --- LINHA 3: TABELA FILTRÁVEL E EXPORTAÇÃO ---
st.markdown("---")
st.subheader("📋 Gestão Detalhada de Lançamentos (Filtros Interativos)")

# Amostra de Dados do Lançamento
sample_data = {
    "Vencimento": ["07/09/2026", "09/09/2026", "11/09/2026", "15/09/2026", "23/09/2026", "24/09/2026"],
    "Fornecedor": ["LATICINIOS COALHADAS", "COFFEE CLUB CAPARAO", "MART MINAS", "FINO HOUSE MG", "FINO HOUSE LTDA", "AGROPECUARIA ITATIBA"],
    "Categoria": ["Insumos", "Insumos", "Insumos", "Retirada", "Insumos", "Insumos"],
    "Valor (R$)": [128.70, 939.00, 127.86, 5000.00, 535.50, 302.71],
    "Status": ["VENCIDO", "VENCIDO", "PAGO", "PAGO", "PAGO", "PENDENTE"],
    "Conciliação": ["NÃO CONCILIADO", "CONCILIADO", "CONCILIADO", "NÃO CONCILIADO", "NÃO CONCILIADO", "NÃO CONCILIADO"]
}
df_contas = pd.DataFrame(sample_data)

f_col1, f_col2, f_col3 = st.columns([3, 3, 4])
with f_col1:
    filter_status = st.multiselect("Filtrar por Status:", options=["PAGO", "PENDENTE", "VENCIDO"], default=["PAGO", "PENDENTE", "VENCIDO"])
with f_col2:
    search_fornecedor = st.text_input("Buscar Fornecedor:")

# Aplicando Filtros Dinâmicos
df_filtered = df_contas[df_contas["Status"].isin(filter_status)]
if search_fornecedor:
    df_filtered = df_filtered[df_filtered["Fornecedor"].str.contains(search_fornecedor, case=False)]

st.dataframe(
    df_filtered.style.map(
        lambda v: 'color: red; font-weight: bold;' if v == 'VENCIDO' else ('color: green;' if v == 'PAGO' else 'color: orange;'),
        subset=['Status']
    ),
    use_container_width=True
)

# Botão de Exportação de Excel/CSV
csv_data = df_filtered.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Baixar Tabela Filtrada (CSV)",
    data=csv_data,
    file_name=f"lancamentos_bpo_{cliente_selected_key}.csv",
    mime="text/csv"
)

# --- ALERTAS E DIAGNÓSTICO FINANCEIRO ---
st.markdown("---")
st.subheader("🚨 Diagnóstico de BPO e Alertas de Caixa")

a_col1, a_col2 = st.columns(2)
with a_col1:
    st.warning("⚠️ **Inadimplência Identificada:** Títulos vencidos na ordem de R$ 1.067,70 requerem atenção para evitar juros e corte de fornecedores.")
with a_col2:
    st.info("💡 **Análise de Margem (Marcos | CFO):** A margem de insumos (CMV) em 14,9% na unidade Teresópolis e ~21,9% na unidade MG demonstra excelente poder de compra e baixo desperdício.")
