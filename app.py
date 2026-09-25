import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuração da página e layout
st.set_page_config(
    page_title="Portal BPO Financeiro | Grupo Fiño House",
    page_icon="📊",
    layout="wide"
)

# Estilização CSS customizada
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

# Base de Dados das Unidades
CLIENT_DATABASE = {
    "cliente_tere": {
        "nome": "Fiño House - Unidade Teresópolis (RJ)",
        "sheet_id": "1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw"
    },
    "cliente_ob": {
        "nome": "Fiño House - Unidade Minas Gerais (OB)",
        "sheet_id": "1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw"
    },
    "consolidado": {
        "nome": "🏢 CONSOLIDADO (GRUPO FIÑO HOUSE)",
        "sheet_id": "CONSOLIDADO"
    }
}

# Conversor de moeda seguro
def parse_currency(val):
    if pd.isna(val): return 0.0
    s = str(val).strip().replace('R$', '').replace(' ', '').replace('(', '-').replace(')', '').strip()
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
    return pd.to_datetime(series.astype(str).str.strip(), errors='coerce')

def find_column(df, possible_names):
    if df.empty: return None
    cols_clean = {str(c).strip().lower(): c for c in df.columns}
    for name in possible_names:
        name_clean = name.strip().lower()
        if name_clean in cols_clean:
            return cols_clean[name_clean]
    return None

# Carregamento seguro com encode de URL
@st.cache_data(ttl=1)
def load_operational_data(sheet_id):
    def get_df_safe(s_id, sheet_names):
        for s_name in sheet_names:
            encoded_name = urllib.parse.quote(s_name)
            url = f"https://docs.google.com/spreadsheets/d/{s_id}/export?format=csv&sheet={encoded_name}"
            try:
                df = pd.read_csv(url)
                if not df.empty and len(df.columns) > 1:
                    df.columns = [str(c).strip() for c in df.columns]
                    return df.reset_index(drop=True)
            except Exception:
                continue
        return pd.DataFrame()

    if sheet_id == "CONSOLIDADO":
        e1, v1, f1 = load_operational_data("1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw")
        e2, v2, f2 = load_operational_data("1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw")
        df_ext = pd.concat([e1, e2], ignore_index=True).reset_index(drop=True) if not e1.empty or not e2.empty else pd.DataFrame()
        df_v = pd.concat([v1, v2], ignore_index=True).reset_index(drop=True) if not v1.empty or not v2.empty else pd.DataFrame()
        df_f = pd.concat([f1, f2], ignore_index=True).reset_index(drop=True) if not f1.empty or not f2.empty else pd.DataFrame()
        return df_ext, df_v, df_f
    else:
        df_ext = get_df_safe(sheet_id, ["EXTRATO BANCÁRIO", "EXTRATO BANCARIO", "EXTRATO"])
        df_v = get_df_safe(sheet_id, ["CONTAS VARIÁVEIS", "CONTAS VARIAVEIS", "VARIAVEIS"])
        df_f = get_df_safe(sheet_id, ["CONTAS FIXAS", "FIXAS"])
        return df_ext, df_v, df_f

# Painel e Filtros
st.sidebar.title("🏢 Portal BPO Financeiro")
st.sidebar.markdown("---")

cliente_selected_key = st.sidebar.selectbox(
    "Unidade Selecionada:",
    options=list(CLIENT_DATABASE.keys()),
    format_func=lambda x: CLIENT_DATABASE[x]["nome"]
)

cliente_info = CLIENT_DATABASE[cliente_selected_key]
st.sidebar.success(f"Conectado: **{cliente_info['nome']}**")

periodo_opcoes = ["Agosto/2026", "Setembro/2026", "CONSOLIDADO DO ANO (2026)"]
periodo_selecionado = st.sidebar.selectbox("Competência:", periodo_opcoes)

df_extrato, df_var, df_fixas = load_operational_data(cliente_info['sheet_id'])

target_month = 8 if "Agosto" in periodo_selecionado else (9 if "Setembro" in periodo_selecionado else None)

# Extrato Bancário
df_extrato_f = pd.DataFrame()
receita_real = 0.0
saidas_extrato = 0.0

if not df_extrato.empty:
    col_date_ext = find_column(df_extrato, ['DATA', 'DATA ', 'DATA DO LANÇAMENTO'])
    col_val_ext = find_column(df_extrato, ['VALOR', 'VALOR (R$)', 'BANCO'])
    
    if col_date_ext and col_val_ext:
        dt_ext_series = parse_any_date(df_extrato[col_date_ext])
        df_extrato['DT_PARSED'] = dt_ext_series
        df_extrato['VALOR_CLEAN'] = df_extrato[col_val_ext].apply(parse_currency)
        
        if target_month:
            df_extrato_f = df_extrato[(dt_ext_series.dt.month == target_month) & (dt_ext_series.dt.year == 2026)].copy()
        else:
            df_extrato_f = df_extrato[dt_ext_series.dt.year == 2026].copy()

        if not df_extrato_f.empty:
            receita_real = df_extrato_f[df_extrato_f['VALOR_CLEAN'] > 0]['VALOR_CLEAN'].sum()
            saidas_extrato = df_extrato_f[df_extrato_f['VALOR_CLEAN'] < 0]['VALOR_CLEAN'].sum()

# Contas Variáveis
df_var_f = pd.DataFrame()
custo_var_pago = 0.0
var_vencido = 0.0

if not df_var.empty:
    col_pag = find_column(df_var, ['Data de Pagamento'])
    col_venc = find_column(df_var, ['Vencimento'])
    
    s_pag = parse_any_date(df_var[col_pag]) if col_pag else pd.Series(index=df_var.index, dtype='datetime64[ns]')
    s_venc = parse_any_date(df_var[col_venc]) if col_venc else pd.Series(index=df_var.index, dtype='datetime64[ns]')
    
    dt_final_var = s_pag.fillna(s_venc)
    df_var['DT_PARSED'] = dt_final_var

    if target_month:
        df_var_f = df_var[(dt_final_var.dt.month == target_month) & (dt_final_var.dt.year == 2026)].copy()
    else:
        df_var_f = df_var[dt_final_var.dt.year == 2026].copy()

    if not df_var_f.empty:
        col_val_var = find_column(df_var_f, ['Valor', 'Valor (R$)'])
        col_status_var = find_column(df_var_f, ['Status'])
        if col_val_var:
            df_var_f['VALOR_CLEAN'] = df_var_f[col_val_var].apply(parse_currency)
            if col_status_var:
                custo_var_pago = df_var_f[df_var_f[col_status_var].astype(str).str.strip().str.upper() == 'PAGO']['VALOR_CLEAN'].sum()
                var_vencido = df_var_f[df_var_f[col_status_var].astype(str).str.strip().str.upper().isin(['VENCIDO', 'PENDENTE'])]['VALOR_CLEAN'].sum()

# Contas Fixas
df_fixas_f = pd.DataFrame()
custo_fixo_pago = 0.0
fixo_vencido = 0.0

if not df_fixas.empty:
    col_pag_f = find_column(df_fixas, ['Data de Pagamento'])
    col_venc_f = find_column(df_fixas, ['Vencimento'])
    
    s_pag_f = parse_any_date(df_fixas[col_pag_f]) if col_pag_f else pd.Series(index=df_fixas.index, dtype='datetime64[ns]')
    s_venc_f = parse_any_date(df_fixas[col_venc_f]) if col_venc_f else pd.Series(index=df_fixas.index, dtype='datetime64[ns]')
    
    dt_final_fix = s_pag_f.fillna(s_venc_f)
    df_fixas['DT_PARSED'] = dt_final_fix

    if target_month:
        df_fixas_f = df_fixas[(dt_final_fix.dt.month == target_month) & (dt_final_fix.dt.year == 2026)].copy()
    else:
        df_fixas_f = df_fixas[dt_final_fix.dt.year == 2026].copy()

    if not df_fixas_f.empty:
        col_val_fix = find_column(df_fixas_f, ['Valor', 'Valor (R$)'])
        col_status_fix = find_column(df_fixas_f, ['Status'])
        if col_val_fix:
            df_fixas_f['VALOR_CLEAN'] = df_fixas_f[col_val_fix].apply(parse_currency)
            if col_status_fix:
                custo_fixo_pago = df_fixas_f[df_fixas_f[col_status_fix].astype(str).str.strip().str.upper() == 'PAGO']['VALOR_CLEAN'].sum()
                fixo_vencido = df_fixas_f[df_fixas_f[col_status_fix].astype(str).str.strip().str.upper().isin(['VENCIDO', 'PENDENTE'])]['VALOR_CLEAN'].sum()

resultado_caixa = receita_real + saidas_extrato # Saídas são negativas
total_pendente = var_vencido + fixo_vencido

# Exibição do Dashboard
st.title(f"📊 Painel Executivo BPO Financeiro — {cliente_info['nome']}")
st.caption(f"Filtro Ativo: **{periodo_selecionado}** | Sincronizado")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Entradas (Extrato)</div><div class="kpi-value">{format_brl(receita_real)}</div></div>', unsafe_allow_html=True)
with kpi2:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #EF4444;"><div class="kpi-title">Variáveis Pagas</div><div class="kpi-value">{format_brl(custo_var_pago)}</div></div>', unsafe_allow_html=True)
with kpi3:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #F59E0B;"><div class="kpi-title">Fixas Pagas</div><div class="kpi-value">{format_brl(custo_fixo_pago)}</div></div>', unsafe_allow_html=True)
with kpi4:
    st.markdown(f'<div class="kpi-card" style="border-left-color: {"#10B981" if resultado_caixa >= 0 else "#EF4444"};"><div class="kpi-title">Resultado de Caixa</div><div class="kpi-value">{format_brl(resultado_caixa)}</div></div>', unsafe_allow_html=True)
with kpi5:
    st.markdown(f'<div class="kpi-card" style="border-left-color: #DC2626;"><div class="kpi-title">Contas Pendentes/Vencidas</div><div class="kpi-value">{format_brl(total_pendente)}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Agenda Financeira
st.subheader("📅 Agenda Financeira e Previsão de Pagamentos")
ag_col1, ag_col2 = st.columns([4, 6])
today = datetime.today()
start_week = today - timedelta(days=today.weekday())
end_week = start_week + timedelta(days=6)

with ag_col1:
    modo_agenda = st.radio("Modo de Visualização:", options=["Semana Atual Vigente", "Período Personalizado"], horizontal=True)

with ag_col2:
    if modo_agenda == "Período Personalizado":
        dates_selected = st.date_input("Intervalo de Vencimento:", value=(start_week.date(), end_week.date()))
    else:
        st.info(f"📆 **Semana Vigente:** {start_week.strftime('%d/%m/%Y')} até {end_week.strftime('%d/%m/%Y')}")

col_status_v = find_column(df_var, ['Status'])
col_status_f = find_column(df_fixas, ['Status'])

df_ag_v = df_var[df_var[col_status_v].astype(str).str.strip().str.upper().isin(['VENCIDO', 'PENDENTE'])].copy() if not df_var.empty and col_status_v else pd.DataFrame()
df_ag_f = df_fixas[df_fixas[col_status_f].astype(str).str.strip().str.upper().isin(['VENCIDO', 'PENDENTE'])].copy() if not df_fixas.empty and col_status_f else pd.DataFrame()

df_ag_all = pd.concat([df_ag_v, df_ag_f], ignore_index=True)

col_venc_all = find_column(df_ag_all, ['Vencimento', 'Data de Pagamento'])
col_stat_all = find_column(df_ag_all, ['Status'])

if not df_ag_all.empty and col_venc_all:
    df_ag_all['VENC_DT'] = parse_any_date(df_ag_all[col_venc_all])
    cond_venc = (df_ag_all[col_stat_all].astype(str).str.strip().str.upper() == 'VENCIDO') if col_stat_all else False
    
    if modo_agenda == "Semana Atual Vigente":
        cond_dt = (df_ag_all['VENC_DT'] >= pd.to_datetime(start_week)) & (df_ag_all['VENC_DT'] <= pd.to_datetime(end_week))
    else:
        if isinstance(dates_selected, tuple) and len(dates_selected) == 2:
            cond_dt = (df_ag_all['VENC_DT'] >= pd.to_datetime(dates_selected[0])) & (df_ag_all['VENC_DT'] <= pd.to_datetime(dates_selected[1]))
        else:
            cond_dt = (df_ag_all['VENC_DT'] >= pd.to_datetime(start_week)) & (df_ag_all['VENC_DT'] <= pd.to_datetime(end_week))

    df_ag_filt = df_ag_all[cond_venc | cond_dt].copy()
    col_val_ag = find_column(df_ag_filt, ['Valor', 'Valor (R$)'])
    
    if not df_ag_filt.empty and col_val_ag:
        df_ag_filt['Valor Exibição'] = df_ag_filt[col_val_ag].apply(lambda x: format_brl(parse_currency(x)))
        show_cols = [c for c in ['Vencimento', 'Fornecedor', 'Descrição', 'Categoria', 'Valor Exibição', 'Status'] if c in df_ag_filt.columns]
        st.dataframe(df_ag_filt[show_cols], use_container_width=True)
        tot_ag = df_ag_filt[col_val_ag].apply(parse_currency).sum()
        st.error(f"⚠️ **Total da Agenda no Período:** {format_brl(tot_ag)}")
    else:
        st.success("✅ **Nenhum compromisso pendente no período selecionado.**")
else:
    st.success("✅ **Sem pendências financeiras registradas.**")

st.markdown("<br>", unsafe_allow_html=True)

# Gráficos de Fluxo
st.subheader("📈 Demonstrativo de Fluxo do Período")
g1, g2 = st.columns([6, 4])

with g1:
    fig_bar = go.Figure(go.Bar(
        x=['Entradas', 'Saídas Extrato', 'Saídas Variáveis', 'Saídas Fixas', 'Resultado Caixa'],
        y=[receita_real, abs(saidas_extrato), custo_var_pago, custo_fixo_pago, resultado_caixa],
        marker_color=['#1E3A8A', '#DC2626', '#EF4444', '#F59E0B', '#10B981' if resultado_caixa >= 0 else '#DC2626'],
        text=[format_brl(v) for v in [receita_real, abs(saidas_extrato), custo_var_pago, custo_fixo_pago, resultado_caixa]],
        textposition='auto'
    ))
    fig_bar.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
    st.plotly_chart(fig_bar, use_container_width=True)

with g2:
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
st.subheader("📋 Tabela Operacional de Lançamentos")
if not df_var_f.empty:
    df_var_disp = df_var_f.copy()
    c_v = find_column(df_var_disp, ['Valor', 'Valor (R$)'])
    if c_v:
        df_var_disp['Valor (R$)'] = df_var_disp[c_v].apply(lambda x: format_brl(parse_currency(x)))
    st.dataframe(df_var_disp, use_container_width=True)
else:
    st.info("Nenhum lançamento variável para o período selecionado.")
