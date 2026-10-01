# ==========================================
# 3. FILTROS EN CASCADA GLOBAL
# ==========================================
st.sidebar.header("🔍 Panel de Filtros Globales")

años_construccion = sorted([int(x) for x in df[(df['FASE DEL PRECIO'] == 'Contratado') & (df['AÑO_FECHA'].notna())]['AÑO_FECHA'].unique()])
año_seleccionado = st.sidebar.multiselect("📅 Año de Construcción", options=años_construccion, help="Filtra estrictamente las actividades que fueron contratadas en este año.")

df_base = df.copy()
if año_seleccionado:
    df_contratados = df[(df['FASE DEL PRECIO'] == 'Contratado') & (df['AÑO_FECHA'].isin(año_seleccionado))]
    df_contratados['LLAVE_AÑO'] = df_contratados['PROYECTO'].astype(str) + "||" + df_contratados['GRUPO'].astype(str) + "||" + df_contratados['ACTIVIDAD'].astype(str)
    llaves_validas = df_contratados['LLAVE_AÑO'].unique()
    
    df_base['LLAVE_AÑO'] = df_base['PROYECTO'].astype(str) + "||" + df_base['GRUPO'].astype(str) + "||" + df_base['ACTIVIDAD'].astype(str)
    df_base = df_base[df_base['LLAVE_AÑO'].isin(llaves_validas)].drop(columns=['LLAVE_AÑO'])

lista_ciudades = sorted([str(x) for x in df_base.get('CIUDAD', pd.Series(dtype=str)).dropna().unique()])
ciudad = st.sidebar.multiselect("📍 Filtrar por Ciudad", options=lista_ciudades)
df_f1 = df_base[df_base.get('CIUDAD', pd.Series(dtype=str)).astype(str).isin(ciudad)] if ciudad else df_base

# NUEVO FILTRO: PROYECTO
lista_proyectos = sorted([str(x) for x in df_f1.get('PROYECTO', pd.Series(dtype=str)).dropna().unique()])
proyecto_sel = st.sidebar.multiselect("🏢 Filtrar por Proyecto", options=lista_proyectos)
df_f1_5 = df_f1[df_f1.get('PROYECTO', pd.Series(dtype=str)).astype(str).isin(proyecto_sel)] if proyecto_sel else df_f1

lista_grupos = sorted([str(x) for x in df_f1_5.get('GRUPO', pd.Series(dtype=str)).dropna().unique()])
grupo = st.sidebar.multiselect("📁 Filtrar por Grupo", options=lista_grupos)
df_f2 = df_f1_5[df_f1_5.get('GRUPO', pd.Series(dtype=str)).astype(str).isin(grupo)] if grupo else df_f1_5

lista_actividades = sorted([str(x) for x in df_f2.get('ACTIVIDAD', pd.Series(dtype=str)).dropna().unique()])
actividad = st.sidebar.multiselect("🛠️ Filtrar por Actividad", options=lista_actividades)
df_f3 = df_f2[df_f2.get('ACTIVIDAD', pd.Series(dtype=str)).astype(str).isin(actividad)] if actividad else df_f2

if 'CONTRATISTA/PROVEEDOR' in df_f3.columns:
    lista_contratistas = sorted([str(x) for x in df_f3['CONTRATISTA/PROVEEDOR'].dropna().unique() if str(x).strip() != ''])
    contratista = st.sidebar.multiselect("👷 Filtrar por Contratista/Proveedor", options=lista_contratistas)
    
    if contratista:
        mask_contratista = df_f3['CONTRATISTA/PROVEEDOR'].astype(str).isin(contratista)
        df_f3_temp = df_f3.copy()
        df_f3_temp['KEY_FILTRO'] = df_f3_temp['PROYECTO'].astype(str) + "||" + df_f3_temp['ACTIVIDAD'].astype(str)
        keys_validas = df_f3_temp[mask_contratista]['KEY_FILTRO'].unique()
        df_filtrado = df_f3_temp[df_f3_temp['KEY_FILTRO'].isin(keys_validas)].drop(columns=['KEY_FILTRO'])
    else:
        df_filtrado = df_f3
else:
    df_filtrado = df_f3

es_ascensor = df_filtrado.get('GRUPO', pd.Series(dtype=str)).astype(str).str.upper().str.contains('ASCENSOR').any()
col_valor = 'VALOR EN PESOS COLOMBIANOS X PARADA'
simbolo_moneda = "$"

if es_ascensor:
    st.sidebar.markdown("---")
    st.sidebar.markdown("⚙️ **Configuración Especial: Ascensores**")
    tipo_moneda = st.sidebar.radio("💵 Moneda de Análisis:", ["Pesos Colombianos (COP)", "Dólares (USD)"])
    if tipo_moneda == "Dólares (USD)":
        col_valor = 'PRECIO USD(SOLO SUMINISTRO)'
        simbolo_moneda = "USD $"
