import streamlit as st
import pandas as pd
import requests
import urllib.parse
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE INTERFACE E ENGENHARIA DE SOFTWARE (Padrão Enterprise)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Portal BPO Financeiro | Fiño House",
    page_icon="📊",
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
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #0052CC;
        margin-bottom: 15px;
    }
    .kpi-title { font-size: 12px; color: #5E6C84; font-weight: 700; text-transform: uppercase; }
    .kpi-value { font-size: 26px; color: #172B4D; font-weight: 800; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. MOTOR DE INTEGRAÇÃO (GOOGLE SHEETS API v4)
# -----------------------------------------------------------------------------
# Unidades mapeadas
CLIENTES = {
    "Tere": {"nome": "Fiño House - Teresópolis", "id": "1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw"},
    "OB": {"nome": "Fiño House - Minas Gerais", "id": "1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw"}
}

def normalizar_colunas(df):
    """Remove espaços invisíveis, acentos e deixa tudo em maiúsculo para blindar a leitura."""
    if df.empty: return df
    df.columns = df.columns.str.strip().str.upper()
    df.columns = df.columns.str.replace('Á', 'A').str.replace('É', 'E').str.replace('Í', 'I').str.replace('Ó', 'O').str.replace('Ú', 'U')
    return df

@st.cache_data(ttl=30, show_spinner=False)
def extrair_dados_api(sheet_id, sheet_name, api_key):
    """Extrai os dados da API Oficial do Google usando a chave fornecida."""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{urllib.parse.quote(sheet_name)}?key={api_key}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            dados = res.json().get('values', [])
            if len(dados) > 1:
                df = pd.DataFrame(dados[1:], columns=dados[0])
                return normalizar_colunas(df)
        return pd.DataFrame() # Retorna vazio se der erro
    except:
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# 3. TRATAMENTO DE DADOS (PARSERS ROBUSTOS)
# -----------------------------------------------------------------------------
def limpar_moeda(valor):
    if pd.isna(valor): return 0.0
    v_str = str(valor).replace('R$', '').replace(' ', '').strip()
    if not v_str or v_str in ['-', '#REF!', '#N/A']: return 0.0
    if '(' in v_str and ')' in v_str: # Formato contábil negativo
        v_str = '-' + v_str.replace('(', '').replace(')', '')
    if ',' in v_str and '.' in v_str:
        v_str = v_str.replace('.', '').replace(',', '.')
    elif ',' in v_str:
        v_str = v_str.replace(',', '.')
    try: return float(v_str)
    except: return 0.0

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def converter_datas(serie):
    return pd.to_datetime(serie.astype(str).str.strip(), errors='coerce', dayfirst=True)

# -----------------------------------------------------------------------------
# 4. BARRA LATERAL E AUTENTICAÇÃO
# -----------------------------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2942/2942269.png", width=50)
st.sidebar.title("Configuração BPO")

# Para não travar no GitHub, pedimos a chave na tela (seguro e imune a bloqueios)
api_key_input = st.sidebar.text_input("🔑 Chave API do Google (Obrigatório)", type="password", help="Cole sua chave API do Google Cloud aqui.")

st.sidebar.markdown("---")
unidade_selecionada = st.sidebar.selectbox("🏢 Unidade:", list(CLIENTES.keys()), format_func=lambda x: CLIENTES[x]['nome'])
mes_filtro = st.sidebar.selectbox("📅 Competência:", ["Agosto/2026", "Setembro/2026", "Geral (2026)"])

if st.sidebar.button("🔄 Sincronizar Base de Dados"):
    st.cache_data.clear()

if not api_key_input:
    st.warning("⚠️ **Sistema Bloqueado:** Insira a sua Chave de API do Google no menu lateral esquerdo para conectar ao banco de dados.")
    st.stop()

# -----------------------------------------------------------------------------
# 5. EXECUÇÃO DO MOTOR DE DADOS
# -----------------------------------------------------------------------------
id_planilha = CLIENTES[unidade_selecionada]['id']

with st.spinner("Conectando ao Google Sheets via API..."):
    # Lê as abas testando com e sem acento
    df_ext = extrair_dados_api(id_planilha, "EXTRATO BANCÁRIO", api_key_input)
    if df_ext.empty: df_ext = extrair_dados_api(id_planilha, "EXTRATO BANCARIO", api_key_input)
    
    df_var = extrair_dados_api(id_planilha, "CONTAS VARIÁVEIS", api_key_input)
    if df_var.empty: df_var = extrair_dados_api(id_planilha, "CONTAS VARIAVEIS", api_key_input)
    
    df_fix = extrair_dados_api(id_planilha, "CONTAS FIXAS", api_key_input)

if df_ext.empty and df_var.empty and df_fix.empty:
    st.error("❌ Erro de Conexão: A API rejeitou o acesso ou a planilha está vazia. Verifique se a chave API está correta e se a planilha possui os nomes corretos nas abas.")
    st.stop()

# Mapeamento do mês
mes_target = 8 if "Agosto" in mes_filtro else (9 if "Setembro" in mes_filtro else None)

# --- PROCESSAMENTO EXTRATO ---
entradas_reais, saidas_extrato = 0.0, 0.0
df_ext_tabela = pd.DataFrame()

if not df_ext.empty and 'DATA' in df_ext.columns and 'VALOR' in df_ext.columns:
    df_ext['DATA_FORMATADA'] = converter_datas(df_ext['DATA'])
    df_ext['VALOR_NUM'] = df_ext['VALOR'].apply(limpar_moeda)
    
    df_ext_filtro = df_ext[df_ext['DATA_FORMATADA'].dt.month == mes_target] if mes_target else df_ext
    df_ext_tabela = df_ext_filtro.copy()
    
    entradas_reais = df_ext_filtro[df_ext_filtro['VALOR_NUM'] > 0]['VALOR_NUM'].sum()
    saidas_extrato = df_ext_filtro[df_ext_filtro['VALOR_NUM'] < 0]['VALOR_NUM'].sum()

# --- PROCESSAMENTO CONTAS VARIÁVEIS E FIXAS ---
def processar_contas(df):
    pago, pendente = 0.0, 0.0
    if df.empty: return 0.0, 0.0, pd.DataFrame()
    
    # Procura as colunas padronizadas
    col_pag = 'DATA DE PAGAMENTO' if 'DATA DE PAGAMENTO' in df.columns else 'PAGAMENTO'
    col_venc = 'VENCIMENTO' if 'VENCIMENTO' in df.columns else 'DATA'
    col_valor = 'VALOR' if 'VALOR' in df.columns else 'VALOR (R$)'
    col_status = 'STATUS' if 'STATUS' in df.columns else 'SITUAÇÃO'
    
    if col_valor in df.columns and col_status in df.columns:
        dt_pag = converter_datas(df.get(col_pag, pd.Series()))
        dt_venc = converter_datas(df.get(col_venc, pd.Series()))
        df['DATA_REFERENCIA'] = dt_pag.fillna(dt_venc)
        df['VALOR_NUM'] = df[col_valor].apply(limpar_moeda)
        df['STATUS_UPPER'] = df[col_status].astype(str).str.strip().str.upper()
        
        df_filtro = df[df['DATA_REFERENCIA'].dt.month == mes_target] if mes_target else df
        
        pago = df_filtro[df_filtro['STATUS_UPPER'] == 'PAGO']['VALOR_NUM'].sum()
        pendente = df_filtro[df_filtro['STATUS_UPPER'].isin(['VENCIDO', 'PENDENTE'])]['VALOR_NUM'].sum()
        
        return pago, pendente, df_filtro
    return 0.0, 0.0, pd.DataFrame()

var_pago, var_pendente, df_var_tabela = processar_contas(df_var)
fix_pago, fix_pendente, df_fix_tabela = processar_contas(df_fix)

caixa_liquido = entradas_reais + saidas_extrato # Saídas são negativas
total_pendente_geral = var_pendente + fix_pendente

# -----------------------------------------------------------------------------
# 6. RENDERIZAÇÃO DO DASHBOARD (UI)
# -----------------------------------------------------------------------------
st.title("Painel de Controle BPO Financeiro")
st.markdown(f"**Unidade:** {CLIENTES[unidade_selecionada]['nome']} | **Competência:** {mes_filtro}")

# CARDS PRINCIPAIS
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Receita (Extrato)</div><div class="kpi-value">{formatar_moeda(entradas_reais)}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="kpi-card" style="border-left-color: #FF5630;"><div class="kpi-title">Variáveis Pagas</div><div class="kpi-value">{formatar_moeda(var_pago)}</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="kpi-card" style="border-left-color: #FFAB00;"><div class="kpi-title">Fixas Pagas</div><div class="kpi-value">{formatar_moeda(fix_pago)}</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="kpi-card" style="border-left-color: {"#36B37E" if caixa_liquido >= 0 else "#FF5630"};"><div class="kpi-title">Caixa Líquido</div><div class="kpi-value">{formatar_moeda(caixa_liquido)}</div></div>', unsafe_allow_html=True)
with c5: st.markdown(f'<div class="kpi-card" style="border-left-color: #6554C0;"><div class="kpi-title">Pendências (A Pagar)</div><div class="kpi-value">{formatar_moeda(total_pendente_geral)}</div></div>', unsafe_allow_html=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# 7. AGENDA FINANCEIRA (Segunda a Domingo Vigente)
# -----------------------------------------------------------------------------
st.subheader("📅 Agenda Financeira (Semana Vigente)")

hoje = datetime.today()
segunda = hoje - timedelta(days=hoje.weekday())
domingo = segunda + timedelta(days=6)
st.caption(f"Período: Segunda-feira ({segunda.strftime('%d/%m/%Y')}) até Domingo ({domingo.strftime('%d/%m/%Y')})")

# Consolida todas as contas Pendentes/Vencidas
df_agenda_var = df_var[df_var['STATUS_UPPER'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_var.empty and 'STATUS_UPPER' in df_var.columns else pd.DataFrame()
df_agenda_fix = df_fix[df_fix['STATUS_UPPER'].isin(['VENCIDO', 'PENDENTE'])].copy() if not df_fix.empty and 'STATUS_UPPER' in df_fix.columns else pd.DataFrame()

df_agenda_geral = pd.concat([df_agenda_var, df_agenda_fix], ignore_index=True)

if not df_agenda_geral.empty and 'VENCIMENTO' in df_agenda_geral.columns:
    df_agenda_geral['VENC_DT'] = converter_datas(df_agenda_geral['VENCIMENTO'])
    
    # Filtra: Ou está vencido (atrasado) OU o vencimento cai nesta semana vigente
    filtro_agenda = (df_agenda_geral['STATUS_UPPER'] == 'VENCIDO') | ((df_agenda_geral['VENC_DT'] >= pd.to_datetime(segunda.date())) & (df_agenda_geral['VENC_DT'] <= pd.to_datetime(domingo.date())))
    
    df_exibir = df_agenda_geral[filtro_agenda].copy()
    
    if not df_exibir.empty:
        df_exibir['Valor Formatado'] = df_exibir['VALOR_NUM'].apply(formatar_moeda)
        colunas_exibir = [c for c in ['VENCIMENTO', 'FORNECEDOR', 'DESCRIÇÃO', 'CATEGORIA', 'Valor Formatado', 'STATUS'] if c in df_exibir.columns]
        
        st.dataframe(df_exibir[colunas_exibir].sort_values(by='VENCIMENTO'), use_container_width=True)
        total_semana = df_exibir['VALOR_NUM'].sum()
        st.error(f"💸 **Fluxo de Saída Necessário para a Semana:** {formatar_moeda(total_semana)}")
    else:
        st.success("✅ Tudo limpo! Nenhum compromisso previsto para a semana atual.")
else:
    st.info("Nenhuma conta a pagar registrada no sistema.")

st.markdown("---")

# -----------------------------------------------------------------------------
# 8. GRÁFICOS GERENCIAIS E TABELA OPERACIONAL
# -----------------------------------------------------------------------------
st.subheader("📈 Demonstrativo Gerencial Visual")
g1, g2 = st.columns([6, 4])

with g1:
    fig_bar = go.Figure(go.Bar(
        x=['Entradas Reais', 'Saídas Bancárias', 'Despesas Variáveis', 'Despesas Fixas', 'Caixa Líquido'],
        y=[entradas_reais, abs(saidas_extrato), var_pago, fix_pago, caixa_liquido],
        marker_color=['#0052CC', '#172B4D', '#FF5630', '#FFAB00', '#36B37E' if caixa_liquido >= 0 else '#FF5630'],
        text=[formatar_moeda(v) for v in [entradas_reais, abs(saidas_extrato), var_pago, fix_pago, caixa_liquido]],
        textposition='auto'
    ))
    fig_bar.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20), title="Fluxo Comparativo do Período (R$)")
    st.plotly_chart(fig_bar, use_container_width=True)

with g2:
    if (var_pago + fix_pago) > 0:
        fig_pie = px.pie(
            names=['Custos Variáveis', 'Custos Fixos'],
            values=[var_pago, fix_pago],
            color_discrete_sequence=['#FF5630', '#FFAB00'],
            hole=0.4,
            title="Distribuição de Saídas"
        )
        fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")
st.subheader("📋 Base Operacional (Variáveis do Período)")
if not df_var_tabela.empty:
    df_tela = df_var_tabela.copy()
    if 'VALOR_NUM' in df_tela.columns:
        df_tela['VALOR'] = df_tela['VALOR_NUM'].apply(formatar_moeda)
        # Limpa colunas auxiliares
        colunas_remover = [c for c in ['DATA_REFERENCIA', 'VALOR_NUM', 'STATUS_UPPER'] if c in df_tela.columns]
        df_tela = df_tela.drop(columns=colunas_remover)
    st.dataframe(df_tela, use_container_width=True)
else:
    st.info("Não há dados operacionais variáveis filtrados para este período.")
