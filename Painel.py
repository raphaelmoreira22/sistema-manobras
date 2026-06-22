import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase_client import supabase

st.set_page_config(
    page_title="Sistema de Manobras",
    page_icon="⚡",
    layout="wide"
)

# =========================
# NORMALIZAÇÃO PADRÃO
# =========================
def normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip().str.lower()

    rename_map = {
        "manobra": "manobra",
        "dataman": "dataman",
        "tipoman": "tipoman",
        "descservicos": "descservicos",
        "recursos": "recursos",
        "gerencia": "gerencia",
        "polo": "polo",
        "dataimportacao": "dataimportacao"
    }

    df = df.rename(columns=rename_map)

    if "dataman" in df.columns:
        df["dataman"] = df["dataman"].dt.strftime("%Y-%m-%d %H:%M:%S")

    if "dataimportacao" in df.columns:
        df["dataimportacao"] = df["dataimportacao"].dt.strftime("%Y-%m-%d %H:%M:%S")

    return df


# =========================
# SUPABASE - CARREGAR
# =========================
@st.cache_data(ttl=60)
def carregar_banco():
   
    try:
        response = supabase.table("manobras").select("*").execute()
        df = pd.DataFrame(response.data)

        if df.empty:
            return pd.DataFrame()

        return normalizar_df(df)

    except Exception as e:
        st.error(f"Erro ao carregar Supabase: {e}")
        return pd.DataFrame()


# =========================
# SUPABASE - UPSERT (EVITA DUPLICAÇÃO)
# =========================
def salvar_no_supabase(df: pd.DataFrame):
    if df.empty:
        return

    df = normalizar_df(df)

    registros = df.to_dict(orient="records")

    supabase.table("manobras").upsert(
        registros,
        on_conflict="manobra"
    ).execute()


# =========================
# EXPORT EXCEL
# =========================
def exportar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# =========================
# UI
# =========================
st.title("⚡ Sistema de Manobras")

st.subheader("📥 Importar relatório Excel")

arquivo = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"])


# =========================
# IMPORTAÇÃO
# =========================
if arquivo:

    try:
        df_novo = pd.read_excel(
            arquivo,
            sheet_name="qryExportRegistrosDetalhadosRDM"
        )

        df_novo = df_novo[[
            "Manobra",
            "DataMan",
            "TipoMan",
            "DescServicos",
            "Recursos",
            "Gerencia",
            "Polo"
        ]].copy()

        df_novo["DataImportacao"] = datetime.now()

        df_novo = normalizar_df(df_novo)

        salvar_no_supabase(df_novo)
        st.cache_data.clear()
        st.success(f"{len(df_novo)} registros enviados ao Supabase.")

    except Exception as e:
        st.error(f"Erro na importação: {e}")


# =========================
# CARREGAR DADOS
# =========================
df = carregar_banco()

st.divider()

st.subheader("🔎 Consulta")

# =========================
# FILTROS
# =========================
col1, col2 = st.columns(2)

with col1:
    filtro_manobra = st.text_input("Manobra")

with col2:
    filtro_texto = st.text_input("Descrição")


col1, col2 = st.columns(2)

gerencias = ["Todas"]
if not df.empty and "gerencia" in df.columns:
    gerencias += sorted(df["gerencia"].dropna().unique())

polos = ["Todos"]
if not df.empty and "polo" in df.columns:
    polos += sorted(df["polo"].dropna().unique())

with col1:
    gerencia = st.selectbox("Gerência", gerencias)

with col2:
    polo = st.selectbox("Polo", polos)


# =========================
# PERÍODO
# =========================
st.markdown("### 📅 Período")

if not df.empty and "dataman" in df.columns and df["dataman"].notna().any():
    data_min = df["dataman"].min().date()
    data_max = df["dataman"].max().date()
else:
    hoje = datetime.today().date()
    data_min = hoje
    data_max = hoje

periodo = st.date_input("Selecione o período", value=(data_min, data_max))


# =========================
# FILTRO
# =========================
resultado = df.copy()

if not resultado.empty:

    if filtro_manobra:
        resultado = resultado[
            resultado["manobra"].astype(str).str.contains(filtro_manobra, case=False, na=False)
        ]

    if filtro_texto:
        resultado = resultado[
            resultado["descservicos"].astype(str).str.contains(filtro_texto, case=False, na=False)
        ]

    if gerencia != "Todas":
        resultado = resultado[resultado["gerencia"] == gerencia]

    if polo != "Todos":
        resultado = resultado[resultado["polo"] == polo]

    if isinstance(periodo, tuple) and len(periodo) == 2:
        ini = pd.Timestamp(periodo[0])
        fim = pd.Timestamp(periodo[1])

        resultado = resultado[
            (resultado["dataman"] >= ini) &
            (resultado["dataman"] <= fim)
        ]


# =========================
# MÉTRICAS
# =========================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total", len(resultado))

with col2:
    st.metric("Gerências", resultado["gerencia"].nunique() if not resultado.empty else 0)

with col3:
    hoje = pd.Timestamp.today().date()
    qtd_hoje = len(resultado[resultado["dataman"].dt.date == hoje]) if not resultado.empty else 0
    st.metric("Hoje", qtd_hoje)

with col4:
    qtd_complexas = len(
        resultado[resultado["tipoman"].astype(str).str.upper() == "COMPLEXA"]
    ) if not resultado.empty else 0

    st.metric("🚨 Complexas", qtd_complexas)


# =========================
# EXIBIÇÃO
# =========================
if "dataman" in resultado.columns:
    resultado = resultado.sort_values("dataman", ascending=False)
else:
    st.error(f"Coluna 'dataman' não encontrada. Colunas disponíveis: {resultado.columns.tolist()}")

exibir = resultado.copy()

if not exibir.empty:

    exibir["manobra"] = exibir.apply(
        lambda x: f"🚨 {x['manobra']}" if str(x.get("tipoman", "")).upper() == "COMPLEXA" else x["manobra"],
        axis=1
    )

    exibir["dataman"] = pd.to_datetime(exibir["dataman"]).dt.strftime("%d/%m/%Y")

st.divider()

st.subheader(f"📋 Resultado ({len(resultado)})")

st.dataframe(exibir, use_container_width=True, height=650)


# =========================
# EXPORTAÇÃO
# =========================
arquivo_excel = exportar_excel(resultado)

st.download_button(
    "📤 Exportar",
    data=arquivo_excel,
    file_name="manobras.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.divider()

st.caption("Sistema de Manobras - Supabase (Stable v1)")
