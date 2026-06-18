import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title="Sistema de Manobras",
    page_icon="⚡",
    layout="wide"
)

BANCO = "Banco_Manobras.xlsx"


# =========================
# CARREGAR BANCO
# =========================
def carregar_banco():

    if Path(BANCO).exists():

        df = pd.read_excel(BANCO)

        if "DataMan" in df.columns:
            df["DataMan"] = pd.to_datetime(df["DataMan"], errors="coerce")

        return df

    return pd.DataFrame(columns=[
        "Manobra",
        "DataMan",
        "TipoMan",
        "DescServicos",
        "Recursos",
        "Gerencia",
        "Polo",
        "DataImportacao"
    ])


# =========================
# SALVAR BANCO
# =========================
def salvar_banco(df):
    df.to_excel(BANCO, index=False)


# =========================
# EXPORTAR EXCEL
# =========================
def exportar_excel(df):

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    return output.getvalue()


# =========================
# UI
# =========================
st.title("⚡ Sistema de Consulta de Manobras")

st.subheader("📥 Importar Relatório Diário")

arquivo = st.file_uploader(
    "Selecione o arquivo recebido por e-mail",
    type=["xlsx"]
)

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

        df_novo["DataMan"] = pd.to_datetime(df_novo["DataMan"], errors="coerce")
        df_novo["DataImportacao"] = datetime.now()

        banco = carregar_banco()

        banco = pd.concat([banco, df_novo], ignore_index=True)

        banco.drop_duplicates(subset=["Manobra"], keep="last", inplace=True)

        salvar_banco(banco)

        st.success(f"{len(df_novo)} registros importados com sucesso.")

    except Exception as erro:
        st.error(f"Erro ao importar arquivo: {erro}")


# =========================
# CARREGAR DADOS
# =========================
df = carregar_banco()

st.divider()

# =========================
# FILTROS
# =========================
st.subheader("🔎 Consulta de Manobras")

col1, col2 = st.columns(2)

with col1:
    manobra = st.text_input("Número da Manobra")

with col2:
    texto = st.text_input("Texto em DescServicos")

col1, col2 = st.columns(2)

gerencias = ["Todas"]
if len(df):
    gerencias += sorted(df["Gerencia"].dropna().astype(str).unique())

with col1:
    gerencia = st.selectbox("Gerência", gerencias)

polos = ["Todos"]
if len(df):
    polos += sorted(df["Polo"].dropna().astype(str).unique())

with col2:
    polo = st.selectbox("Polo", polos)

# =========================
# PERÍODO
# =========================
st.markdown("### 📅 Período da Manobra")

if len(df) and "DataMan" in df.columns and df["DataMan"].notna().any():
    data_min = df["DataMan"].min().date()
    data_max = df["DataMan"].max().date()
else:
    hoje = datetime.today().date()
    data_min = hoje
    data_max = hoje

periodo = st.date_input(
    "Selecione o período",
    value=(data_min, data_max)
)

# =========================
# FILTRO
# =========================
resultado = df.copy()

if manobra:
    resultado = resultado[
        resultado["Manobra"].astype(str).str.contains(manobra, case=False, na=False)
    ]

if texto:
    resultado = resultado[
        resultado["DescServicos"].astype(str).str.contains(texto, case=False, na=False)
    ]

if gerencia != "Todas":
    resultado = resultado[resultado["Gerencia"].astype(str) == gerencia]

if polo != "Todos":
    resultado = resultado[resultado["Polo"].astype(str) == polo]

if len(periodo) == 2 and "DataMan" in resultado.columns:
    data_inicio = pd.Timestamp(periodo[0])
    data_fim = pd.Timestamp(periodo[1])

    resultado = resultado[
        (resultado["DataMan"] >= data_inicio) &
        (resultado["DataMan"] <= data_fim)
    ]

# =========================
# MÉTRICAS (DINÂMICAS)
# =========================
df_metric = resultado.copy()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total de Manobras", len(df_metric))

with col2:
    qtd_gerencias = (
        df_metric["Gerencia"].dropna().nunique()
        if len(df_metric)
        else 0
    )

    st.metric("Gerências", qtd_gerencias)

with col3:
    hoje = pd.Timestamp.today().date()

    qtd_hoje = 0
    if len(df_metric) and "DataMan" in df_metric.columns:
        qtd_hoje = len(df_metric[df_metric["DataMan"].dt.date == hoje])

    st.metric("Manobras Hoje", qtd_hoje)

with col4:
    qtd_complexas = 0

    if len(df_metric) and "TipoMan" in df_metric.columns:
        qtd_complexas = len(
            df_metric[
                df_metric["TipoMan"].astype(str).str.upper() == "COMPLEXA"
            ]
        )

    st.metric("🚨 Complexas", qtd_complexas)

# =========================
# ORGANIZAÇÃO
# =========================
resultado = resultado.sort_values(by="DataMan", ascending=False)

resultado_exibicao = resultado.copy()

# Destaque de manobras complexas
if "TipoMan" in resultado_exibicao.columns:

    resultado_exibicao["Manobra"] = resultado_exibicao.apply(
        lambda x: f"🚨 {x['Manobra']}"
        if str(x["TipoMan"]).strip().upper() == "COMPLEXA"
        else str(x["Manobra"]),
        axis=1
    )

# Formatação de data
if "DataMan" in resultado_exibicao.columns:
    resultado_exibicao["DataMan"] = resultado_exibicao["DataMan"].dt.strftime("%d/%m/%Y")

# Remove colunas técnicas
resultado_exibicao = resultado_exibicao.drop(
    columns=["TipoMan"],
    errors="ignore"
)

# =========================
# RESULTADO
# =========================
st.divider()

st.subheader(f"📋 Resultado ({len(resultado)} registros)")

st.dataframe(
    resultado_exibicao,
    use_container_width=True,
    height=650
)

# =========================
# EXPORTAÇÃO
# =========================
arquivo_excel = exportar_excel(resultado)

st.download_button(
    label="📤 Exportar Resultado",
    data=arquivo_excel,
    file_name="resultado_manobras.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.divider()

st.caption("Sistema de Consulta de Manobras - Versão 1.1")
