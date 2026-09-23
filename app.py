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
    "consolidado": {
        "nome": "🏢 TODAS AS UNIDADES (CONSOLIDADO GROUP)",
        "faturamento": 34346.05 + 23221.48,
        "cmv": 5117.17 + 5099.56,
        "despesas": 17983.75 + 7245.01,
        "lucro_liquido": 7528.17 + 10876.91,
        "vencidos": 1067.70 + 0.0,
        "pendentes": 1864.31 + 0.0,
        "pagos": 11370.07 + 20451.19
    },
    "cliente_tere": {
        "nome": "Fino House - Unidade Teresópolis",
        "faturamento": 34346.05,
        "cmv": 5117.17,
        "despesas": 17983.75,
        "lucro_liquido": 7528.17,
        "vencidos": 1067.70,
        "pendentes": 1864.31,
        "pagos": 11370.07
    },
    "cliente_ob": {
        "nome": "Fino House - Unidade Minas Gerais",
        "faturamento": 23221.48,
        "cmv": 5099.56,
        "despesas": 7245.01,
        "lucro_liquido": 10876.91,
        "vencidos": 0.0,
        "pendentes": 0.0,
        "pagos": 20451.19
    }
}

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Painel Executivo BPO")
st.sidebar.markdown("---")

cliente_selected_key = st.sidebar.selectbox(
    "Visão / Unidade Selecionada:",
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
st.title(f"📊 Gestão Financeira — {cliente_info['nome']}")
st.caption("Visão em tempo real do faturamento, resultado operacional, caixa e pendências.")

# Puxando Dados Dinâmicos da Seleção
faturamento = cliente_info["faturamento"]
cmv = cliente_info["cmv"]
cmv_pct = (cmv / faturamento) * 100 if faturamento > 0 else 0
despesas = cliente_info["despesas"]
lucro_liquido = cliente_info["lucro_liquido"]
margem_liquida = (lucro_liquido / faturamento) * 100 if faturamento > 0 else 0

vencido_val = cliente_info["vencidos"]
pendente_val = cliente_info["pendentes"]
pago_val = cliente_info["pagos"]

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

# --- LINHA 2: PROJEÇÃO E GRÁFICOS DINÂMICOS ---
tab1, tab2 = st.tabs(["📈 Projeção de Fluxo de Caixa (15 Dias)", "📊 DRE e Composição do Caixa"])

with tab1:
    st.subheader("Projeção de Saldo Diário de Caixa")
    datas_proj = [datetime.today() + timedelta(days=i) for i in range(15)]
    saldo_inicial = 7999.47 if cliente_selected_key != "consolidado" else 15998.94
    
    saldos_projetados = []
    saldo_curr = saldo_inicial
    for i, d in enumerate(datas_proj):
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

# --- LINHA 3: TABELA DINÂMICA DE LANÇAMENTOS E FILTROS REAL-TIME ---
st.markdown("---")
st.subheader("📋 Gestão Detalhada de Lançamentos (Filtros Interativos)")

# Amostra Completa de Lançamentos
sample_data = {
    "Unidade": ["Teresópolis", "Teresópolis", "Minas Gerais", "Teresópolis", "Teresópolis", "Minas Gerais", "Teresópolis"],
    "Vencimento": ["07/09/2026", "09/09/2026", "11/09/2026", "15/09/2026", "23/09/2026", "24/09/2026", "28/09/2026"],
    "Fornecedor": ["LATICINIOS COALHADAS", "COFFEE CLUB CAPARAO", "MART MINAS", "FINO HOUSE MG", "FINO HOUSE LTDA", "OESA COMERCIO", "AGROPECUARIA ITATIBA"],
    "Categoria": ["Insumos", "Insumos", "Insumos", "Retirada", "Insumos", "Insumos", "Insumos"],
    "Valor (R$)": [128.70, 939.00, 127.86, 5000.00, 535.50, 196.98, 302.71],
    "Status": ["VENCIDO", "VENCIDO", "PAGO", "PAGO", "PAGO", "PAGO", "PENDENTE"]
}
df_contas = pd.DataFrame(sample_data)

# Filtro por Unidade
if cliente_selected_key == "cliente_tere":
    df_contas = df_contas[df_contas["Unidade"] == "Teresópolis"]
elif cliente_selected_key == "cliente_ob":
    df_contas = df_contas[df_contas["Unidade"] == "Minas Gerais"]

f_col1, f_col2 = st.columns([4, 6])
with f_col1:
    filter_status = st.multiselect("Filtrar por Status:", options=["PAGO", "PENDENTE", "VENCIDO"], default=["PAGO", "PENDENTE", "VENCIDO"])
with f_col2:
    search_fornecedor = st.text_input("Buscar Fornecedor / Categoria:")

# Aplicação dos Filtros Dinâmicos na Tabela
df_filtered = df_contas[df_contas["Status"].isin(filter_status)]
if search_fornecedor:
    df_filtered = df_filtered[
        df_filtered["Fornecedor"].str.contains(search_fornecedor, case=False) | 
        df_filtered["Categoria"].str.contains(search_fornecedor, case=False)
    ]

# Exibição da Tabela Filtrada
st.dataframe(
    df_filtered.style.map(
        lambda v: 'color: red; font-weight: bold;' if v == 'VENCIDO' else ('color: green;' if v == 'PAGO' else 'color: orange;'),
        subset=['Status']
    ),
    use_container_width=True
)

# Resumo Dinâmico da Tabela Filtrada
total_filtrado = df_filtered["Valor (R$)"].sum()
st.caption(f"💰 **Total dos Lançamentos Filtrados Exibidos:** R$ {total_filtrado:,.2f}")

# Botão de Exportação
csv_data = df_filtered.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Baixar Lançamentos Filtrados (CSV)",
    data=csv_data,
    file_name=f"lancamentos_{cliente_selected_key}.csv",
    mime="text/csv"
)

# --- DIAGNÓSTICO FINANCEIRO ---
st.markdown("---")
st.subheader("🚨 Diagnóstico de BPO e Alertas de Caixa")

a_col1, a_col2 = st.columns(2)
with a_col1:
    if vencido_val > 0:
        st.warning(f"⚠️ **Inadimplência Identificada:** Existe um acumulado de R$ {vencido_val:,.2f} em contas vencidas que requerem atenção.")
    else:
        st.success("✅ **Inadimplência Zero:** Não existem títulos vencidos para esta seleção.")
with a_col2:
    st.info(f"💡 **Análise do Grupo:** Faturamento consolidado do grupo está em R$ {cliente_database_faturamento if 'cliente_database_faturamento' in locals() else (34346.05+23221.48):,.2f} com excelente controle de custos de insumos.")
