import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Marcador de Albaranes", layout="wide")

# --- Funciones auxiliares ---
def normalizar_codigo(texto: str) -> str:
    if pd.isna(texto):
        return ""
    texto = str(texto).upper().strip()
    return re.sub(r"\s+", "", texto)

def guardar_historial(prev):
    st.session_state.historial.append(prev)

def aplicar_codigo(codigo: str, anotacion: str = ""):
    codigo = normalizar_codigo(codigo)
    if not (4 <= len(codigo) <= 14):
        return f"❌ El código '{codigo}' no es válido (debe tener entre 4 y 14 caracteres)."

    mask = st.session_state.df["Nº"].astype(str).str.upper().str.contains(codigo, na=False)

    if not mask.any():
        return f"⚠️ Ningún albarán encontrado para '{codigo}'."

    prev = st.session_state.df.loc[mask, "Marcado"].copy()
    guardar_historial(prev)

    if anotacion:
        st.session_state.df.loc[mask, "Marcado"] = anotacion
        return f"✅ Código '{codigo}' → anotación '{anotacion}' aplicada en {mask.sum()} albaranes."
    else:
        st.session_state.df.loc[mask, "Marcado"] = "✔️"
        return f"✅ Código '{codigo}' marcado en {mask.sum()} albaranes."

def deshacer():
    if st.session_state.historial:
        ultimo = st.session_state.historial.pop()
        st.session_state.df.loc[ultimo.index, "Marcado"] = ultimo
        st.success("↩️ Última acción deshecha.")

def procesar_codigo_callback():
    codigo = st.session_state.codigo_input
    anotacion_manual = st.session_state.anotacion_input.strip()
    anotacion_predef = st.session_state.anotacion_predef.strip()

    # Prioridad: manual > predefinida
    if anotacion_manual:
        anotacion = anotacion_manual
    else:
        anotacion = anotacion_predef

    if codigo.strip():
        st.session_state.last_result = aplicar_codigo(codigo, anotacion)

        # Limpiar inputs tras procesar
        st.session_state.codigo_input = ""
        st.session_state.anotacion_input = ""
        st.session_state.anotacion_predef = ""


# --- Layout principal ---
st.title("📑 Marcador de Albaranes")

uploaded_file = st.file_uploader("📤 Sube tu archivo Excel", type=["xlsx"])

if uploaded_file:
    if "df" not in st.session_state:
        df = pd.read_excel(uploaded_file)

        # --- Forzar formato de fecha sin hora ---
        if "Fecha envio" in df.columns:
            df["Fecha envio"] = pd.to_datetime(df["Fecha envio"], errors="coerce")
            df["Fecha envio"] = df["Fecha envio"].dt.strftime("%d/%m/%Y")

        # --- Crear columna Marcado ---
        if "Marcado" not in df.columns:
            if "Nº" in df.columns:
                pos = df.columns.get_loc("Nº") + 1
                df.insert(pos, "Marcado", "")
            else:
                df["Marcado"] = ""

        st.session_state.df = df.copy()
        st.session_state.historial = []
        st.session_state.codigo_input = ""
        st.session_state.anotacion_input = ""
        st.session_state.anotacion_predef = ""
    else:
        df = st.session_state.df

    col1, col2 = st.columns([2, 1])

    with col1:
        # --- Formulario individual ---
        with st.form("entrada_form"):
            codigo_input = st.text_input(
                "✏️ Escribe un código (4 a 14 caracteres)",
                key="codigo_input",
                placeholder="Pulsa ENTER o Procesar"
            )

            col_ani1, col_ani2 = st.columns([2, 1])
            with col_ani1:
                anotacion_input = st.text_input("📝 Anotación manual", key="anotacion_input")
            with col_ani2:
                anotacion_predef = st.selectbox(
                    "⚡ Rápida",
                    ["", "ANULADO", "COBRADO", "TRANSFER", "TPV FISICO", "DUPLICADO", "COMERCIAL"],
                    key="anotacion_predef"
                )

            st.form_submit_button("Procesar", on_click=procesar_codigo_callback)

        # --- Procesar lista de códigos ---
        with st.expander("📋 Pegar varios códigos a la vez"):
            lista_codigos = st.text_area("Introduce códigos separados por saltos de línea")
            anotacion_lista = st.selectbox(
                "📝 Anotación (opcional, se aplicará a todos)",
                ["", "ANULADO", "COBRADO", "TRANSFER", "TPV FISICO", "DUPLICADO", "COMERCIAL"],
                key="anotacion_lista"
            )
            if st.button("Procesar lista"):
                resultados = []
                beep_needed = False
                for c in lista_codigos.splitlines():
                    if c.strip():
                        r = aplicar_codigo(c.strip(), anotacion_lista)
                        resultados.append(r)
                        if r.startswith("⚠️") or r.startswith("❌"):
                            beep_needed = True
                st.session_state.last_result = "\n".join(resultados)
                if beep_needed:
                    st.markdown(
                        """
                        <audio autoplay>
                            <source src="data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YYQAAAAA" type="audio/wav">
                        </audio>
                        """,
                        unsafe_allow_html=True
                    )

        # --- Quitar marcado ---
        with st.expander("❌ Quitar marcado manualmente"):
            codigo_borrar = st.text_input("Código a desmarcar", key="codigo_borrar")
            if st.button("Quitar marcado"):
                if codigo_borrar.strip():
                    mask = st.session_state.df["Nº"].astype(str).str.upper().str.contains(codigo_borrar.strip().upper(), na=False)
                    if mask.any():
                        st.session_state.df.loc[mask, "Marcado"] = ""
                        st.success(f"✅ Marcado eliminado en {mask.sum()} albarán(es) con código '{codigo_borrar}'.")
                    else:
                        st.warning("⚠️ No se encontró ningún albarán con ese código.")

        # --- Deshacer ---
        st.button("↩️ Deshacer último cambio", on_click=deshacer)

        # --- Mostrar resultados con beep ---
        beep_html = """
        <audio autoplay>
            <source src="data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YYQAAAAA" type="audio/wav">
        </audio>
        """

        if "last_result" in st.session_state:
            beep_needed = False
            for line in st.session_state.last_result.split("\n"):
                if line.startswith("❌"):
                    st.error(line)
                elif line.startswith("⚠️"):
                    st.warning(line)
                    beep_needed = True
                else:
                    st.success(line)
            if beep_needed:
                st.markdown(beep_html, unsafe_allow_html=True)

    with col2:
        total = len(df)
        marcados = (df["Marcado"] == "✔️").sum()
        anotados = df["Marcado"].apply(lambda x: x not in ["", "✔️"]).sum()

        st.subheader("📊 Resumen")
        st.metric("Total", total)
        st.metric("✔️ Marcados", marcados)
        st.metric("📝 Con anotación", anotados)

    # --- Tabla ---
    st.markdown("### 📋 Vista de la tabla")
    filtro = st.text_input("🔍 Buscar en la tabla (Nº o anotación)")
    if filtro:
        filtrado = df[
            df["Nº"].astype(str).str.contains(filtro, na=False, case=False) |
            df["Marcado"].astype(str).str.contains(filtro, na=False, case=False)
        ]
        st.dataframe(filtrado, use_container_width=True, height=700)
    else:
        st.dataframe(df, use_container_width=True, height=700)

    # --- Exportar Excel / CSV ---
    nombre_archivo = st.text_input("📌 Nombre del archivo final (sin extensión)", value="albaranes_marcados")

    output_xlsx = BytesIO()
    df.to_excel(output_xlsx, index=False)
    output_xlsx.seek(0)

    st.download_button("💾 Descargar Excel modificado", data=output_xlsx,
                       file_name=f"{nombre_archivo}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    output_csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📄 Descargar CSV modificado", data=output_csv,
                       file_name=f"{nombre_archivo}.csv", mime="text/csv")

# --- Marca de agua ---
st.markdown(
    """
    <div style='position:fixed; bottom:8px; right:12px; opacity:0.4; font-size:12px; color:gray;'>
        Hecho por Álvaro Montero
    </div>
    """,
    unsafe_allow_html=True
)
