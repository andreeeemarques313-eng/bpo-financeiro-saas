import streamlit as st
import pandas as pd
import requests
import urllib.parse
import re
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO VISUAL ENTERPRISE (SEM RETICÊNCIAS)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Portal BPO Financeiro | Grupo Fiño House",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS responsiva sem corte por reticências
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .kpi-card {
        background-color: #ffffff;
        padding: 16px 14px;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #0052CC;
        margin-bottom: 12px;
        min-height: 110px;
    }
    .kpi-title { 
        font-size: 11px; 
        color: #5E6C84; 
        font-weight: 700; 
        text-transform: uppercase; 
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .kpi-value { 
        font-size: clamp(15px, 1.2vw, 21px) !important; 
        color: #172B4D; 
        font-weight: 800; 
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }
    .kpi-sub { 
        font-size: 11px; 
        color: #7A869A; 
        margin-top: 4px;
        white-space: nowrap;
    }
    </style>
""", unsafe_allow_html=True)

CLIENTES = {
    "Tere": {
        "nome": "Fiño House - Teresópolis (RJ)", 
        "id": "1hmByjAyoXmw-nH_nGB4gzCWFTYogXw-BkiPBcMhEfqw"
    },
    "OB": {
        "nome": "Fiño House - Minas Gerais (OB)", 
        "id": "1xgmgbzffKULhJI6HInEn-uzagRcqSR0A_0HXq53omsw"
    }
}

# -----------------------------------------------------------------------------
# 2. CONVERSÃO MONETÁRIA E PARSERS DE DADOS
# -----------------------------------------------------------------------------
def clean_currency(val):
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace('R$', '').replace(' ', '')
    if not s or s in ['-', '#REF!', '#N/A', 'nan', 'None']:
        return 0.0
    if '(' in s and ')' in s:
        s = '-' + s.replace('(', '').replace(')', '')
    if '.' in s and ',' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except:
        return 0.0

def format_brl(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_dates_robust(series):
    if series is None or series.empty:
        return pd.Series(dtype='datetime64[ns]')
    s = series.astype(str).str.strip().replace({'nan': None, 'None': None, '': None, 'NaT': None})
    try:
        return pd.to_datetime(s, format='mixed', dayfirst=True, errors='coerce')
    except:
        return pd.to_datetime(s, dayfirst=True, errors='coerce')

def match_col(df, candidates):
    if df.empty: return None
    cols_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        clean = cand.strip().lower()
        if clean in cols_map: return cols_map[clean]
    return None

# -----------------------------------------------------------------------------
# 3. VALIDAÇÃO ESTRUTURAL DE ESQUEMA DAS TABELAS
# -----------------------------------------------------------------------------
def is_valid_extrato(df):
    if df.empty or len(df.columns) < 2: return False
    cols = [str(c).strip().upper() for c in df.columns]
    if 'INDICADOR' in cols: return False
    return any('DATA' in c for c in cols) and (any('VALOR' in c for c in cols) or any('BANCO' in c for c in cols))

def is_valid_contas_var(df):
    if df.empty or len(df.columns) < 3: return False
    cols = [str(c).strip().upper() for c in df.columns]
    if 'INDICADOR' in cols: return False
    has_venc = any('VENCIMENTO' in c for c in cols) or any('PAGAMENTO' in c for c in cols)
    has_val = any('VALOR' in c for c in cols)
    return has_venc and has_val

def is_valid_contas_fix(df):
    if df.empty or len(df.columns) < 3: return False
    cols = [str(c).strip().upper() for c in df.columns]
    if 'INDICADOR' in cols: return False
    has_venc = any('VENCIMENTO' in c for c in cols) or any('PAGAMENTO' in c for c in cols)
    has_val = any('VALOR' in c for c in cols)
    return has_venc and has_val

# -----------------------------------------------------------------------------
# 4. MOTOR AVANÇADO DE EXTRAÇÃO POR GID E MULTI-VARREDURA
# -----------------------------------------------------------------------------
@st.cache_data(ttl=10, show_spinner=False)
def discover_all_gids(sheet_id):
    """Extrai os GIDs de todas as abas tratando tags internas <span> e estruturas JSON."""
    gids = {}
    for u in [
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/htmlview",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    ]:
        try:
            r = requests.get(u, timeout=6, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                # 1. Busca por tags de botão de aba com limpeza interna de HTML
                for gid, content in re.findall(r'id=["\']sheet-button-([0-9]+)["\'][^>]*>(.*?)</li>', r.text, re.DOTALL):
                    title_clean = re.sub(r'<[^>]+>', '', content).strip()
                    if title_clean:
                        gids[title_clean.upper()] = gid
                # 2. Busca por JSON incorporado
                for m in re.finditer(r'["\']?sheetId["\']?\s*:\s*([0-9]+)[^}]+?["\']?title["\']?\s*:\s*["\']([^"\']+)["\']', r.text):
                    gids[m.group(2).strip().upper()] = m.group(1).strip()
                for m in re.finditer(r'["\']?title["\']?\s*:\s*["\']([^"\']+)["\'][^}]+?["\']?sheetId["\']?\s*:\s*([0-9]+)', r.text):
                    gids[m.group(1).strip().upper()] = m.group(2).strip()
                if len(gids) >= 3:
                    break
        except Exception:
            continue
    return gids

@st.cache_data(ttl=10, show_spinner=False)
def download_tab_guaranteed(sheet_id, target_kind, candidate_names, discovered_gids, manual_gid=""):
    validator = is_valid_extrato if target_kind == "extrato" else (is_valid_contas_var if target_kind == "variaveis" else is_valid_contas_fix)

    # Prioridade 0: GID Manual fornecido na barra lateral
    if manual_gid and manual_gid.strip().isdigit():
        url_manual = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={manual_gid.strip()}"
        try:
            df = pd.read_csv(url_manual)
            if validator(df):
                df.columns = [str(c).strip() for c in df.columns]
                return df, f"GID Manual ({manual_gid.strip()})"
        except Exception:
            pass

    # Prioridade 1: GIDs mapeados na inspeção HTML/JSON
    for title_upper, gid in discovered_gids.items():
        match = False
        if target_kind == "extrato" and "EXTRATO" in title_upper: match = True
        elif target_kind == "variaveis" and ("VARIA" in title_upper or "VARIÁ" in title_upper): match = True
        elif target_kind == "fixas" and "FIXA" in title_upper: match = True

        if match:
            url_gid = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"
            try:
                df = pd.read_csv(url_gid)
                if validator(df):
                    df.columns = [str(c).strip() for c in df.columns]
                    return df, f"GID Automático ({gid})"
            except Exception:
                pass

    # Prioridade 2: Variações textuais completas (com e sem espaços finais)
    for name in candidate_names:
        for enc in [urllib.parse.quote(name), urllib.parse.quote_plus(name), name]:
            for url_pattern in [
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={enc}",
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={enc}"
            ]:
                try:
                    df = pd.read_csv(url_pattern)
                    if validator(df):
                        df.columns = [str(c).strip() for c in df.columns]
                        return df, f"Aba ('{name.strip()}')"
                except Exception:
                    continue

    # Prioridade 3: Varredura sequencial direta de GIDs comuns (0 a 15)
    for test_gid in range(0, 16):
        url_scan = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={test_gid}"
        try:
            df = pd.read_csv(url_scan)
            if validator(df):
                df.columns = [str(c).strip() for c in df.columns]
                return df, f"Varredura GID ({test_gid})"
        except Exception:
            continue

    return pd.DataFrame(), None

def load_data_pipeline(sheet_id, manual_var_gid=""):
    gids = discover_all_gids(sheet_id)

    ext_names = [
        "EXTRATO BANCARIO", "EXTRATO", "EXTRATO BANCÁRIO", "Extrato Bancario", "EXTRATO BANCARIO "
    ]
    # Lista ampliada com espaços no final para contornar qualquer formatação no Sheets
    var_names = [
        "CONTAS VARIAVEIS", "CONTAS VARIAVEIS ", "CONTAS VARIAVEIS  ", " CONTAS VARIAVEIS",
        "CONTAS VARIÁVEIS", "CONTAS VARIÁVEIS ", "VARIAVEIS", "VARIÁVEIS", "VARIAVEIS ",
        "Contas Variaveis", "Contas Variáveis", "Contas Variaveis "
    ]
    fix_names = [
        "CONTAS FIXAS", "CONTAS FIXAS ", "FIXAS", "Contas Fixas", "Contas Fixas "
    ]

    df_ext, m_e = download_tab_guaranteed(sheet_id, "extrato", ext_names, gids)
    df_var, m_v = download_tab_guaranteed(sheet_id, "variaveis", var_names, gids, manual_var_gid)
    df_fix, m_f = download_tab_guaranteed(sheet_id, "fixas", fix_names, gids)

    return {
        "extrato": df_ext,
        "variaveis": df_var,
        "fixas": df_fix,
        "status": {
            "extrato": (not df_ext.empty, m_e, len(df_ext)),
            "variaveis": (not df_var.empty, m_v, len(df_var)),
            "fixas": (not df_fix.empty, m_f, len(df_fix))
        }
    }

# -----------------------------------------------------------------------------
# 5. CONTROLES LATERAIS E MONITORAMENTO
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Painel BPO Financeiro")
st.sidebar.caption("Alex — Diretor de Tecnologia (CTO)")
st.sidebar.markdown("---")

unidade_chave = st.sidebar.selectbox("Unidade:", list(CLIENTES.keys()), format_func=lambda x: CLIENTES[x]["nome"])
periodo_filtro = st.sidebar.selectbox("Competência:", ["Agosto/2026", "Setembro/2026", "CONSOLIDADO DO ANO (2026)"])

# Campo opcional para garantir conexão manual se desejado
manual_var_gid = st.sidebar.text_input(
    "GID Contas Variáveis (Opcional):", 
    value="", 
    help="Se a aba não for localizada automaticamente, insira o número do gid presente na URL do navegador quando estiver na aba."
)

if st.sidebar.button("🔄 Sincronizar Base de Dados"):
    st.cache_data.clear()
    st.rerun()

dados = load_data_pipeline(CLIENTES[unidade_chave]["id"], manual_var_gid)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📡 Conexão de Dados")
st_ext_ok, st_ext_mod, st_ext_rows = dados["status"]["extrato"]
st_var_ok, st_var_mod, st_var_rows = dados["status"]["variaveis"]
st_fix_ok, st_fix_mod, st_fix_rows = dados["status"]["fixas"]

st.sidebar.markdown(f"{'🟢' if st_ext_ok else '🔴'} **Extrato:** {st_ext_rows} reg ({st_ext_mod or 'Não localizado'})")
st.sidebar.markdown(f"{'🟢' if st_var_ok else '🔴'} **Variáveis:** {st_var_rows} reg ({st_var_mod or 'Não localizado'})")
st.sidebar.markdown(f"{'🟢' if st_fix_ok else '🔴'} **Fixas:** {st_fix_rows} reg ({st_fix_mod or 'Não localizado'})")

target_month = 8 if "Agosto" in periodo_filtro else (9 if "Setembro" in periodo_filtro else None)

df_ext = dados["extrato"]
df_var = dados["variaveis"]
df_fix = dados["fixas"]

# -----------------------------------------------------------------------------
# 6. REGRAS 1 & 2: EXTRATO (ENTRADAS) E CONTAS (SAÍDAS DA COMPETÊNCIA)
# -----------------------------------------------------------------------------

# REGRA 1: ENTRADAS EXCLUSIVAS DA ABA EXTRATO BANCÁRIO
receita_extrato, saidas_extrato = 0.0, 0.0
df_ext_filtro = pd.DataFrame()

if not df_ext.empty:
    c_dt_e = match_col(df_ext, ['DATA', 'DATA ', 'DATA DO LANÇAMENTO'])
    c_val_e = match_col(df_ext, ['VALOR', 'VALOR (R$)', 'BANCO'])
    if c_dt_e and c_val_e:
        dt_s = parse_dates_robust(df_ext[c_dt_e])
        df_ext['VALOR_NUM'] = df_ext[c_val_e].apply(clean_currency)
        df_ext['DT_S'] = dt_s
        cond = (dt_s.dt.month == target_month) & (dt_s.dt.year == 2026) if target_month else (dt_s.dt.year == 2026)
        df_ext_filtro = df_ext[cond].copy()
        if not df_ext_filtro.empty:
            receita_extrato = df_ext_filtro[df_ext_filtro['VALOR_NUM'] > 0]['VALOR_NUM'].sum()
            saidas_extrato = df_ext_filtro[df_ext_filtro['VALOR_NUM'] < 0]['VALOR_NUM'].sum()

# REGRA 2: SAÍDAS FIXAS E VARIÁVEIS SOMENTE DA COMPETÊNCIA
def process_contas_competencia(df):
    if df.empty: return 0.0, 0.0, 0.0, pd.DataFrame()
    c_comp = match_col(df, ['Competência', 'Competencia'])
    c_pag = match_col(df, ['Data de Pagamento', 'Pagamento'])
    c_venc = match_col(df, ['Vencimento', 'Data de Vencimento', 'Data'])
    c_val = match_col(df, ['Valor', 'Valor (R$)'])
    c_st = match_col(df, ['Status', 'Situação'])
    
    if c_val and c_st:
        s_comp = parse_dates_robust(df[c_comp]) if c_comp else pd.Series(index=df.index, dtype='datetime64[ns]')
        s_pag = parse_dates_robust(df[c_pag]) if c_pag else pd.Series(index=df.index, dtype='datetime64[ns]')
        s_venc = parse_dates_robust(df[c_venc]) if c_venc else pd.Series(index=df.index, dtype='datetime64[ns]')
        
        # Prioriza Competência; se vazia, utiliza Pagamento ou Vencimento
        df['DT_REF'] = s_comp.fillna(s_pag).fillna(s_venc)
        df['VALOR_NUM'] = df[c_val].apply(clean_currency)
        df['ST_UP'] = df[c_st].astype(str).str.strip().str.upper()
        
        cond = (df['DT_REF'].dt.month == target_month) & (df['DT_REF'].dt.year == 2026) if target_month else (df['DT_REF'].dt.year == 2026)
        df_f = df[cond].copy()
        
        pago = df_f[df_f['ST_UP'] == 'PAGO']['VALOR_NUM'].sum()
        vencido = df_f[df_f['ST_UP'] == 'VENCIDO']['VALOR_NUM'].sum()
        a_vencer = df_f[df_f['ST_UP'] == 'PENDENTE']['VALOR_NUM'].sum()
        
        return pago, vencido, a_vencer, df_f
    return 0.0, 0.0, 0.0, pd.DataFrame()

var_pago, var_venc, var_pend, df_var_f = process_contas_competencia(df_var)
fix_pago, fix_venc, fix_pend, df_fix_f = process_contas_competencia(df_fix)

saldo_caixa_real = receita_extrato + saidas_extrato

# Total de pendências (Vencidas + A Vencer)
total_vencido_mes = var_venc + fix_venc
total_a_vencer_mes = var_pend + fix_pend
total_pendente_mes = total_vencido_mes + total_a_vencer_mes

# -----------------------------------------------------------------------------
# 7. DASHBOARD EXECUTIVO: KPI CARDS
# -----------------------------------------------------------------------------
st.title(f"📊 Painel Executivo BPO Financeiro — {CLIENTES[unidade_chave]['nome']}")
st.caption(f"Competência: **{periodo_filtro}** | Monitorização Automatizada em Tempo Real")

c1, c2, c3, c4, c5 = st.columns(5)
with c1: 
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Entradas (Extrato)</div><div class="kpi-value">{format_brl(receita_extrato)}</div><div class="kpi-sub">Total Recebido</div></div>', unsafe_allow_html=True)
with c2: 
    st.markdown(f'<div class="kpi-card" style="border-left-color: #FF5630;"><div class="kpi-title">Variáveis Pagas</div><div class="kpi-value">{format_brl(var_pago)}</div><div class="kpi-sub">Insumos & Fornecedores</div></div>', unsafe_allow_html=True)
with c3: 
    st.markdown(f'<div class="kpi-card" style="border-left-color: #FFAB00;"><div class="kpi-title">Fixas Pagas</div><div class="kpi-value">{format_brl(fix_pago)}</div><div class="kpi-sub">Estrutura Operacional</div></div>', unsafe_allow_html=True)
with c4: 
    cor_caixa = "#36B37E" if saldo_caixa_real >= 0 else "#FF5630"
    st.markdown(f'<div class="kpi-card" style="border-left-color: {cor_caixa};"><div class="kpi-title">Resultado de Caixa</div><div class="kpi-value">{format_brl(saldo_caixa_real)}</div><div class="kpi-sub">Entradas − Saídas Extrato</div></div>', unsafe_allow_html=True)
with c5: 
    sub_pend = f"{format_brl(total_vencido_mes)} Vencidas | {format_brl(total_a_vencer_mes)} A Vencer" if total_pendente_mes > 0 else "Nenhuma Pendência"
    st.markdown(f'<div class="kpi-card" style="border-left-color: #6554C0;"><div class="kpi-title">Contas Pendentes</div><div class="kpi-value">{format_brl(total_pendente_mes)}</div><div class="kpi-sub">{sub_pend}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 8. REGRA 3: AGENDA FINANCEIRA DINÂMICA (SEMANA VIGENTE SEGUNDA A DOMINGO)
# -----------------------------------------------------------------------------
st.subheader("📅 Agenda Financeira Vigente — Previsão Semanal (Segunda a Domingo)")

hoje = datetime.today()
segunda = hoje - timedelta(days=hoje.weekday())
domingo = segunda + timedelta(days=6)

ag1, ag2 = st.columns([4, 6])
with ag1:
    modo_ag = st.radio("Período da Agenda:", ["Semana Vigente (Seg a Dom)", "Intervalo Personalizado"], horizontal=True)
with ag2:
    if modo_ag == "Intervalo Personalizado":
        datas_sel = st.date_input("Intervalo de Vencimento:", value=(segunda.date(), domingo.date()))
    else:
        st.info(f"📆 **Semana Vigente:** Segunda-feira ({segunda.strftime('%d/%m/%Y')}) até Domingo ({domingo.strftime('%d/%m/%Y')})")

def extrair_pendencias(df, tipo):
    if df.empty: return pd.DataFrame()
    c_venc = match_col(df, ['Vencimento', 'Data de Vencimento', 'Data'])
    c_val = match_col(df, ['Valor', 'Valor (R$)'])
    c_st = match_col(df, ['Status', 'Situação'])
    c_forn = match_col(df, ['Fornecedor', 'Razão Social', 'Beneficiário'])
    c_desc = match_col(df, ['Descrição', 'Descricao', 'Item'])
    c_cat = match_col(df, ['Categoria'])
    
    if c_venc and c_val and c_st:
        df_temp = df.copy()
        df_temp['VALOR_NUM'] = df_temp[c_val].apply(clean_currency)
        df_temp['VENC_DT'] = parse_dates_robust(df_temp[c_venc])
        df_temp['STATUS_UP'] = df_temp[c_st].astype(str).str.strip().str.upper()
        
        # Filtra títulos não liquidados (PENDENTE ou VENCIDO)
        pendentes = df_temp[df_temp['STATUS_UP'].isin(['PENDENTE', 'VENCIDO'])].copy()
        pendentes['Tipo de Despesa'] = tipo
        pendentes['Fornecedor_Display'] = pendentes[c_forn] if c_forn else '-'
        pendentes['Descricao_Display'] = pendentes[c_desc] if c_desc else '-'
        pendentes['Categoria_Display'] = pendentes[c_cat] if c_cat else '-'
        return pendentes
    return pd.DataFrame()

pend_var = extrair_pendencias(df_var, "Variável")
pend_fix = extrair_pendencias(df_fix, "Fixa")

df_agenda_dinamica = pd.concat([pend_var, pend_fix], ignore_index=True)

if not df_agenda_dinamica.empty:
    cond_vencido = (df_agenda_dinamica['STATUS_UP'] == 'VENCIDO')
    
    if modo_ag == "Semana Vigente (Seg a Dom)":
        cond_data = (df_agenda_dinamica['VENC_DT'] >= pd.to_datetime(segunda.date())) & (df_agenda_dinamica['VENC_DT'] <= pd.to_datetime(domingo.date()))
    else:
        if isinstance(datas_sel, tuple) and len(datas_sel) == 2:
            cond_data = (df_agenda_dinamica['VENC_DT'] >= pd.to_datetime(datas_sel[0])) & (df_agenda_dinamica['VENC_DT'] <= pd.to_datetime(datas_sel[1]))
        else:
            cond_data = (df_agenda_dinamica['VENC_DT'] >= pd.to_datetime(segunda.date())) & (df_agenda_dinamica['VENC_DT'] <= pd.to_datetime(domingo.date()))
            
    df_agenda_view = df_agenda_dinamica[cond_vencido | cond_data].copy()
    
    if not df_agenda_view.empty:
        df_agenda_view['Valor Formatado'] = df_agenda_view['VALOR_NUM'].apply(format_brl)
        df_agenda_view['Data Vencimento'] = df_agenda_view['VENC_DT'].dt.strftime('%d/%m/%Y')
        
        cols_grid = ['Data Vencimento', 'Tipo de Despesa', 'Fornecedor_Display', 'Descricao_Display', 'Categoria_Display', 'Valor Formatado', 'STATUS_UP']
        col_rename = {
            'Data Vencimento': 'Vencimento',
            'Tipo de Despesa': 'Tipo',
            'Fornecedor_Display': 'Fornecedor',
            'Descricao_Display': 'Descrição',
            'Categoria_Display': 'Categoria',
            'Valor Formatado': 'Valor (R$)',
            'STATUS_UP': 'Status'
        }
        
        st.dataframe(
            df_agenda_view[cols_grid].rename(columns=col_rename).sort_values(by='Vencimento'),
            use_container_width=True
        )
        total_previsto = df_agenda_view['VALOR_NUM'].sum()
        st.error(f"💸 **Total de Pagamentos da Semana / Atrasados:** {format_brl(total_previsto)}")
    else:
        st.success("✅ Nenhum pagamento pendente registrado para a semana atual.")
else:
    st.success("✅ Nenhuma conta a pagar pendente encontrada no sistema.")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 9. DEMONSTRATIVO VISUAL GERENCIAL DE FLUXO DE CAIXA
# -----------------------------------------------------------------------------
st.subheader("📈 Demonstrativo Gerencial do Período")
g1, g2 = st.columns([6, 4])

with g1:
    fig_bar = go.Figure(go.Bar(
        x=['Entradas Extrato', 'Saídas Extrato', 'Variáveis Pagas', 'Fixas Pagas', 'Resultado de Caixa'],
        y=[receita_extrato, abs(saidas_extrato), var_pago, fix_pago, saldo_caixa_real],
        marker_color=['#0052CC', '#172B4D', '#FF5630', '#FFAB00', cor_caixa],
        text=[format_brl(v) for v in [receita_extrato, abs(saidas_extrato), var_pago, fix_pago, saldo_caixa_real]],
        textposition='auto'
    ))
    fig_bar.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20), title="Visão Comparativa do Período (R$)")
    st.plotly_chart(fig_bar, use_container_width=True)

with g2:
    if (var_pago + fix_pago) > 0:
        fig_pie = px.pie(
            names=['Contas Variáveis', 'Contas Fixas'],
            values=[var_pago, fix_pago],
            color_discrete_sequence=['#FF5630', '#FFAB00'],
            hole=0.4,
            title="Distribuição de Saídas Realizadas"
        )
        fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")
st.subheader("📋 Tabela Operacional de Lançamentos (Variáveis da Competência)")
if not df_var_f.empty:
    df_var_view = df_var_f.copy()
    c_v_show = match_col(df_var_view, ['Valor', 'Valor (R$)'])
    if c_v_show:
        df_var_view['Valor (R$)'] = df_var_view[c_v_show].apply(clean_currency).apply(format_brl)
    drop_cols = [c for c in ['DT_REF', 'VALOR_NUM', 'ST_UP'] if c in df_var_view.columns]
    st.dataframe(df_var_view.drop(columns=drop_cols), use_container_width=True)
else:
    st.info("Nenhum lançamento de contas variáveis registrado para o filtro ativo.")
