import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Reportes de Prefectura CETIS 79 (Matutino)", layout="centered", page_icon="📋")

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_google_sheets():
    # Los secretos se leerán desde la configuración de Streamlit Cloud
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credenciales = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    cliente = gspread.authorize(credenciales)
    # ATENCIÓN: Conectando al Excel de la mañana
    hoja = cliente.open("Reportes_Prefectura_Matutino").sheet1
    return hoja

# --- CARGAR BASE DE MAESTROS ---
@st.cache_data
def cargar_maestros():
    # ATENCIÓN: Leyendo el CSV de la mañana
    return pd.read_csv("base_maestros_matutino.csv")

try:
    hoja_reportes = conectar_google_sheets()
    df_horarios = cargar_maestros()
except Exception as e:
    st.error(f"Error de conexión: Verifica que tu archivo en Drive se llame exactamente 'Reportes_Prefectura_Matutino' y esté compartido con el correo de servicio. Detalle: {e}")
    st.stop()

st.title("📋 Reportes de Incidencias Prefectura - Matutino")

dias_semana = {0: "LUNES", 1: "MARTES", 2: "MIERCOLES", 3: "JUEVES", 4: "VIERNES", 5: "SABADO", 6: "DOMINGO"}

# --- DATOS DEL PREFECTO ---
st.markdown("### Datos del Prefecto")
nombre_prefecto = st.text_input("Nombre del prefecto en turno:", placeholder="Ej. Juan Pérez")
st.divider()

# --- CAPTURA DE INCIDENCIA ---
st.header("Buscar y Capturar Incidencia")

fecha_seleccionada = st.date_input("Fecha de la incidencia")
dia_texto = dias_semana[fecha_seleccionada.weekday()]

if dia_texto in ["SABADO", "DOMINGO"]:
    st.warning("Seleccionaste un fin de semana. Elige un día de Lunes a Viernes.")
else:
    df_dia = df_horarios[df_horarios['DIA'] == dia_texto].copy()
    
    st.markdown("#### Filtros de Búsqueda")
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    st.markdown("#### Filtros de Búsqueda")
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    # 1. Selecciona Docente
    with col_filtro1:
        lista_docentes = ["Todos"] + sorted(df_dia['DOCENTE'].unique())
        filtro_docente = st.selectbox("Docente", lista_docentes)
    
    # 💥 LA MAGIA: Filtramos la base de datos inmediatamente después de elegir al docente
    if filtro_docente != "Todos":
        df_dia = df_dia[df_dia['DOCENTE'] == filtro_docente]
        
    # 2. Selecciona Grupo (Ahora solo muestra los grupos del docente elegido)
    with col_filtro2:
        lista_grupos = ["Todos"] + sorted(df_dia['GRADO_GRUPO'].unique())
        filtro_grupo = st.selectbox("Grupo", lista_grupos)

    # Filtramos la base de nuevo
    if filtro_grupo != "Todos":
        df_dia = df_dia[df_dia['GRADO_GRUPO'] == filtro_grupo]
        
    # 3. Selecciona Materia (Ahora solo muestra las materias de ese docente y grupo)
    with col_filtro3:
        lista_materias = ["Todas"] + sorted(df_dia['MATERIA'].unique())
        filtro_materia = st.selectbox("Materia", lista_materias)

    # Filtro final
    if filtro_materia != "Todas":
        df_dia = df_dia[df_dia['MATERIA'] == filtro_materia]

    st.markdown("#### Seleccionar Clase Afectada")
    if df_dia.empty:
        st.warning("No se encontraron clases con esos filtros en este día.")
    else:
        opciones_clases = []
        for idx, row in df_dia.iterrows():
            opciones_clases.append(f"{row['MODULO']} | Grupo: {row['GRADO_GRUPO']} | {row['DOCENTE']} | {row['MATERIA']}")
            
        clase_seleccionada = st.selectbox("Elige la clase donde ocurrió la incidencia:", opciones_clases)
        
        indice_elegido = opciones_clases.index(clase_seleccionada)
        datos_clase = df_dia.iloc[indice_elegido]
        
        col_inc1, col_inc2 = st.columns(2)
        with col_inc1:
            tipo_incidencia = st.radio("Tipo:", ["FALTA", "RETARDO"])
        with col_inc2:
            hora_retardo = ""
            if tipo_incidencia == "RETARDO":
                hora_retardo = st.text_input("Hora exacta del retardo (ej. 7:10)")
                
        # --- NUEVO CAMPO DE OBSERVACIONES ---
        observaciones = st.text_area("Observaciones (Opcional):", placeholder="Anota aquí cualquier detalle o justificación...")
                
        if st.button("🚀 Enviar a Google Drive", type="primary"):
            if not nombre_prefecto:
                st.error("⚠ Ingresa tu nombre en la parte superior.")
            else:
                grado = datos_clase['GRADO_GRUPO'].split('°')[0] if '°' in datos_clase['GRADO_GRUPO'] else ""
                grupo = datos_clase['GRADO_GRUPO'].split('°')[1].strip() if '°' in datos_clase['GRADO_GRUPO'] else datos_clase['GRADO_GRUPO']
                
                falta = "FALTA" if tipo_incidencia == "FALTA" else ""
                retardo = hora_retardo if tipo_incidencia == "RETARDO" else ""
                
                try:
                    # Inyectar directamente la fila en Google Sheets (Ahora con 10 columnas)
                    hoja_reportes.append_row([
                        fecha_seleccionada.strftime("%d/%m/%Y"),
                        dia_texto,
                        datos_clase['DOCENTE'],
                        datos_clase['MODULO'],
                        falta,
                        retardo,
                        grado,
                        grupo,
                        nombre_prefecto,
                        observaciones # <-- El nuevo dato que se manda a la columna J
                    ])
                    st.success("✅ ¡Incidencia registrada en la nube exitosamente!")
                except Exception as e:
                    st.error(f"Hubo un error al escribir en el Excel de Drive: {e}")
