# ==========================================
# 2. MOTOR DE DATOS AUTOMÁTICO CON CACHÉ
# ==========================================
@st.cache_data(show_spinner=False)
def cargar_y_procesar_base(ruta_archivo):
    if ruta_archivo.endswith('.csv'):
        try:
            df = pd.read_csv(ruta_archivo, encoding='utf-8-sig', sep=',')
        except:
            df = pd.read_csv(ruta_archivo, encoding='latin1', sep=';')
    else:
        df = pd.read_excel(ruta_archivo)
        
    df.columns = df.columns.astype(str).str.strip().str.upper()
    
    # --- MAGIA LIMPIADORA: Quitar espacios fantasmas y estandarizar mayúsculas ---
    for col_texto in ['CIUDAD', 'PROYECTO', 'GRUPO', 'ACTIVIDAD']:
        if col_texto in df.columns:
            df[col_texto] = df[col_texto].astype(str).str.strip().str.upper()
    
    if 'FASE DEL PRECIO' not in df.columns:
        return pd.DataFrame(), f"Error: No se encontró 'FASE DEL PRECIO'. Detectadas: {', '.join(df.columns)}"

    cols_dinero = ['VALOR EN PESOS COLOMBIANOS X PARADA', 'PRECIO USD(SOLO SUMINISTRO)']
    for c in cols_dinero:
        if c in df.columns:
            df[c] = df[c].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.replace(' ', '', regex=False).str.replace(r'[^\d\.-]', '', regex=True)
            df[c] = pd.to_numeric(df[c], errors='coerce')

    df['FASE DEL PRECIO'] = df['FASE DEL PRECIO'].fillna('').astype(str).str.strip().str.upper()
    df.loc[df['FASE DEL PRECIO'].str.contains('ANALIZADO', na=False), 'FASE DEL PRECIO'] = 'Analizado'
    df.loc[df['FASE DEL PRECIO'].str.contains('PRE-CONST', na=False) | df['FASE DEL PRECIO'].str.contains('PRECONST', na=False), 'FASE DEL PRECIO'] = 'Presupuestado'
    df.loc[df['FASE DEL PRECIO'].str.contains('CONSTRUCC', na=False) & ~df['FASE DEL PRECIO'].str.contains('PRE', na=False), 'FASE DEL PRECIO'] = 'Contratado'

    col_fecha = 'FECHA DE PRECIO(ADJUDICADO Y/O COTIZADO)'
    if col_fecha in df.columns:
        df['AÑO_FECHA'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.year
    else:
        df['AÑO_FECHA'] = None

    return df, "OK"
