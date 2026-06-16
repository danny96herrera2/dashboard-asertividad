import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ==========================================
# 1. CONFIGURACIÓN Y ESTÉTICA DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Dashboard Asertividad", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .kpi-card { 
        background-color: white; padding: 24px; border-radius: 16px; 
        box-shadow: 0 4px 20px rgba(0,0,0,0.03); margin-bottom: 20px; text-align: center; transition: transform 0.2s ease;
    }
    .kpi-card:hover { transform: translateY(-5px); }
    .kpi-title { font-size: 13px; color: #8a98ac; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;}
    .kpi-value { font-size: 34px; font-weight: 800; margin: 5px 0; letter-spacing: -0.5px;}
    .border-blue { border-left: 6px solid #223983; }   
    .border-green { border-left: 6px solid #00A54C; }  
    .border-yellow { border-left: 6px solid #FFC112; } 
    .border-purple { border-left: 6px solid #6f42c1; } 
    
    .act-card {
        background-color: white; border: 1px solid #e0e5ec; border-radius: 8px; padding: 15px; margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .act-title { font-size: 16px; font-weight: 800; color: #1d3557; text-transform: uppercase; margin-bottom: 10px; border-bottom: 2px solid #f0f2f6; padding-bottom: 5px;}
    .mini-kpi-container { display: flex; justify-content: space-between; margin-bottom: 10px; }
    .mini-kpi { border: 1px solid #e0e5ec; padding: 10px; width: 32%; text-align: center; border-radius: 5px; }
    .mini-kpi-val { font-size: 22px; font-weight: 800; }
    .mini-kpi-lbl { font-size: 10px; color: #6c757d; font-weight: bold; text-transform: uppercase; margin-top: 5px;}
    </style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard Corporativo de Asertividad de Precios")
st.markdown("---")

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

# ==========================================
# 3. DETECCIÓN AUTOMÁTICA DEL ARCHIVO RESIDENTE
# ==========================================
archivo_residente = None
if os.path.exists("base_datos.xlsx"):
    archivo_residente = "base_datos.xlsx"
elif os.path.exists("base_datos.csv"):
    archivo_residente = "base_datos.csv"

if archivo_residente is None:
    st.info("👋 **¡Bienvenido al sistema corporativo!**\n\nPara activar el Dashboard, sube tu archivo consolidado a GitHub renombrado exactamente como **`base_datos.xlsx`**.")
    st.stop()

with st.spinner("🚀 Sincronizando Base de Datos de Producción..."):
    df, mensaje = cargar_y_procesar_base(archivo_residente)
    
if mensaje != "OK":
    st.error(mensaje)
    st.stop()

# ==========================================
# 4. FILTROS EN CASCADA GLOBAL
# ==========================================
st.sidebar.header("🔍 Panel de Filtros Globales")

años_construccion = sorted([int(x) for x in df[(df['FASE DEL PRECIO'] == 'Contratado') & (df['AÑO_FECHA'].notna())]['AÑO_FECHA'].unique()])
año_seleccionado = st.sidebar.multiselect("📅 Año de Construcción", options=años_construccion, help="Filtra proyectos construidos este año y trae su historial previo.")

df_base = df.copy()
if año_seleccionado:
    proyectos_del_año = df[(df['FASE DEL PRECIO'] == 'Contratado') & (df['AÑO_FECHA'].isin(año_seleccionado))]['PROYECTO'].unique()
    df_base = df_base[df_base['PROYECTO'].isin(proyectos_del_año)]

lista_ciudades = sorted([str(x) for x in df_base.get('CIUDAD', pd.Series(dtype=str)).dropna().unique()])
ciudad = st.sidebar.multiselect("📍 Filtrar por Ciudad", options=lista_ciudades)
df_f1 = df_base[df_base.get('CIUDAD', pd.Series(dtype=str)).astype(str).isin(ciudad)] if ciudad else df_base

lista_grupos = sorted([str(x) for x in df_f1.get('GRUPO', pd.Series(dtype=str)).dropna().unique()])
grupo = st.sidebar.multiselect("📁 Filtrar por Grupo", options=lista_grupos)
df_f2 = df_f1[df_f1.get('GRUPO', pd.Series(dtype=str)).astype(str).isin(grupo)] if grupo else df_f1

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

# ==========================================
# 5. PANEL DE PONDERACIONES (PESOS) CON AUTOCARGA
# ==========================================
st.sidebar.markdown("---")
st.sidebar.markdown("⚖️ **Ponderación de Asertividad**")
usar_pesos = st.sidebar.toggle("Activar Pesos Ponderados", value=True)

df_pesos_guardados = None
if usar_pesos:
    with st.expander("🛠️ Panel de Configuración de Pesos (%)", expanded=True):
        st.markdown("Valores cargados desde el archivo de configuración:")
        df_config_pesos = df_filtrado[['GRUPO', 'ACTIVIDAD']].drop_duplicates().reset_index(drop=True)
        
        if not df_config_pesos.empty:
            total_grupos = df_config_pesos['GRUPO'].nunique()
            df_config_pesos['Peso Grupo (%)'] = 100.0 / total_grupos if total_grupos > 0 else 100.0
            df_config_pesos['Peso Actividad (%)'] = df_config_pesos.groupby('GRUPO')['ACTIVIDAD'].transform(lambda x: 100.0 / len(x) if len(x) > 0 else 100.0)
            
            if os.path.exists("pesos.csv"):
                try:
                    # Forzamos detección automática de comas o punto y coma
                    df_pesos_csv = pd.read_csv("pesos.csv", sep=None, engine='python', encoding='utf-8-sig')
                    df_pesos_csv.columns = df_pesos_csv.columns.astype(str).str.strip().str.upper()
                    
                    # Buscamos la columna numérica (la que no sea GRUPO ni ACTIVIDAD)
                    col_peso_csv = [c for c in df_pesos_csv.columns if c not in ['GRUPO', 'ACTIVIDAD'] and not c.startswith('UNNAMED')][0]
                    
                    # Limpieza absoluta de textos (quitar espacios, acentos ocultos y pasar a mayúsculas)
                    df_pesos_csv['GRUPO_CLEAN'] = df_pesos_csv['GRUPO'].astype(str).str.strip().str.upper().str.replace(r'[ÁÉÍÓÚ]', 'X', regex=True)
                    df_pesos_csv['ACTIVIDAD_CLEAN'] = df_pesos_csv['ACTIVIDAD'].fillna('').astype(str).str.strip().str.upper()
                    
                    # Separamos diccionarios de Grupos y Actividades
                    df_grupos_csv = df_pesos_csv[df_pesos_csv['ACTIVIDAD_CLEAN'].isin(['', 'NAN', 'NONE'])]
                    dict_grupos = dict(zip(df_grupos_csv['GRUPO_CLEAN'], pd.to_numeric(df_grupos_csv[col_peso_csv], errors='coerce').fillna(0)))
                    
                    df_act_csv = df_pesos_csv[~df_pesos_csv['ACTIVIDAD_CLEAN'].isin(['', 'NAN', 'NONE'])]
                    dict_act = dict(zip(df_act_csv['GRUPO_CLEAN'] + "||" + df_act_csv['ACTIVIDAD_CLEAN'], pd.to_numeric(df_act_csv[col_peso_csv], errors='coerce').fillna(0)))
                    
                    def mapear_grupo(g):
                        g_clean = str(g).strip().upper()
                        # Búsqueda exacta o parcial
                        if g_clean in dict_grupos:
                            return dict_grupos[g_clean]
                        for k, v in dict_grupos.items():
                            if k in g_clean or g_clean in k:
                                return v
                        return 100.0 / total_grupos if total_grupos > 0 else 100.0
                        
                    def mapear_actividad(row):
                        g_clean = str(row['GRUPO']).strip().upper()
                        a_clean = str(row['ACTIVIDAD']).strip().upper()
                        k_exacta = g_clean + "||" + a_clean
                        
                        if k_exacta in dict_act:
                            return dict_act[k_exacta]
                        # Búsqueda flexible por aproximación si el Excel cambió una letra
                        for k, v in dict_act.items():
                            if g_clean in k and (a_clean in k or k in a_clean):
                                return v
                        t_act = len(df_config_pesos[df_config_pesos['GRUPO'] == row['GRUPO']])
                        return 100.0 / t_act if t_act > 0 else 100.0

                    df_config_pesos['Peso Grupo (%)'] = df_config_pesos['GRUPO'].apply(mapear_grupo)
                    df_config_pesos['Peso Actividad (%)'] = df_config_pesos.apply(mapear_actividad, axis=1)
                    st.sidebar.success("✅ 'pesos.csv' cargado exitosamente")
                    
                except Exception as e:
                    st.sidebar.error(f"❌ Error al procesar pesos.csv: {e}")
            else:
                st.sidebar.warning("⚠️ Archivo 'pesos.csv' no encontrado en GitHub.")

        df_pesos_guardados = st.data_editor(df_config_pesos, hide_index=True, use_container_width=True)


# ==========================================
# 6. MOTOR ESTADÍSTICO Y EXCEPCIÓN ASCENSORES
# ==========================================
if not df_filtrado.empty and col_valor in df_filtrado.columns:
    cols_agrupacion = [c for c in ['CIUDAD', 'PROYECTO', 'GRUPO', 'ACTIVIDAD'] if c in df.columns]
    cols_extras = [c for c in ['TIPO DE PROYECTO', 'CONTRATISTA/PROVEEDOR', 'ALCANCE', 'TRM(DIA DE CONTRATO /COTIZACION)'] if c in df_filtrado.columns]

    mask_ascensor = df_filtrado['GRUPO'].astype(str).str.upper().str.contains('ASCENSOR')
    df_asc = df_filtrado[mask_ascensor].copy()
    df_resto = df_filtrado[~mask_ascensor].copy()

    pivotes = []
    desc_list = []

    if not df_resto.empty:
        piv_resto = df_resto.pivot_table(index=cols_agrupacion, columns='FASE DEL PRECIO', values=col_valor, aggfunc='mean').reset_index()
        pivotes.append(piv_resto)
        
        desc_resto = df_resto[df_resto['FASE DEL PRECIO'] == 'Contratado'].drop_duplicates(subset=cols_agrupacion)[cols_agrupacion + cols_extras]
        desc_list.append(desc_resto)
        
    if not df_asc.empty:
        df_asc['ACTIVIDAD'] = 'ASCENSOR (SUMA SUMINISTRO + INSTALACIÓN)'
        piv_asc = df_asc.pivot_table(index=cols_agrupacion, columns='FASE DEL PRECIO', values=col_valor, aggfunc='sum').reset_index()
        pivotes.append(piv_asc)

        desc_asc = df_asc[df_asc['FASE DEL PRECIO'] == 'Contratado'].drop_duplicates(subset=cols_agrupacion)[cols_agrupacion + cols_extras]
        desc_list.append(desc_asc)

    df_pivot = pd.concat(pivotes, ignore_index=True)
    df_desc_final = pd.concat(desc_list, ignore_index=True) if desc_list else pd.DataFrame()

    for fase in ['Analizado', 'Presupuestado', 'Contratado']:
        if fase not in df_pivot.columns: df_pivot[fase] = float('nan')

    if not df_desc_final.empty:
        df_pivot = pd.merge(df_pivot, df_desc_final, on=cols_agrupacion, how='left')

    df_completos = df_pivot.dropna(subset=['Analizado', 'Presupuestado', 'Contratado']).copy()
    df_incompletos = df_pivot[df_pivot[['Analizado', 'Presupuestado', 'Contratado']].isna().any(axis=1)].copy()
    
    if usar_pesos and df_pesos_guardados is not None:
        df_completos = pd.merge(df_completos, df_pesos_guardados, on=['GRUPO', 'ACTIVIDAD'], how='left')
        df_completos['Peso Grupo (%)'] = df_completos['Peso Grupo (%)'].fillna(0)
        df_completos['Peso Actividad (%)'] = df_completos['Peso Actividad (%)'].fillna(0)
    
    colores_marca = {'Analizado': '#FFC112', 'Presupuestado': '#223983', 'Contratado': '#00A54C'}

    # ==========================================
    # 7. CREACIÓN DE LAS 4 PESTAÑAS
    # ==========================================
    tab_main, tab_grupos, tab_actividad, tab_audit = st.tabs(["📊 Dashboard Principal", "📁 Resumen por Grupo", "🛠️ Resumen por Actividad", "🚨 Auditoría"])

    # ------------------------------------------
    # PESTAÑA 1: DASHBOARD DE PROYECTOS
    # ------------------------------------------
    with tab_main:
        if df_completos.empty:
            st.warning("⚠️ No hay ítems con el ciclo de 3 fases completado para los filtros seleccionados.")
        else:
            st.subheader("🖱️ Panel de Control por Proyecto")
            df_resumen = df_completos.groupby('PROYECTO')[['Analizado', 'Presupuestado', 'Contratado']].mean().reset_index()
            df_mostrar_resumen = df_resumen.rename(columns={'Analizado': 'Precio Analizado PYC', 'Presupuestado': 'Pre-Construcción', 'Contratado': 'Construcción'})
            
            for col in ['Precio Analizado PYC', 'Pre-Construcción', 'Construcción']:
                df_mostrar_resumen[col] = df_mostrar_resumen[col].apply(lambda x: f"{simbolo_moneda}{x:,.0f}")

            try:
                evento = st.dataframe(df_mostrar_resumen, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row")
                proyectos_sel = df_mostrar_resumen.iloc[evento.selection.rows]['PROYECTO'].tolist() if evento.selection.rows else []
            except:
                st.dataframe(df_mostrar_resumen, use_container_width=True, hide_index=True)
                proyectos_sel = []

            df_tab1 = df_completos[df_completos['PROYECTO'].isin(proyectos_sel)].copy() if proyectos_sel else df_completos.copy()

            df_tab1['Δ Pre vs Ana'] = ((df_tab1['Presupuestado'] - df_tab1['Analizado']) / df_tab1['Analizado'])
            df_tab1['Δ Con vs Pre'] = ((df_tab1['Contratado'] - df_tab1['Presupuestado']) / df_tab1['Presupuestado'])
            df_tab1['Δ Con vs Ana'] = ((df_tab1['Contratado'] - df_tab1['Analizado']) / df_tab1['Analizado'])

            def kpi(val):
                if pd.isna(val): return "<div class='kpi-value' style='color:#8a98ac;'>N/A</div>"
                val = val * 100
                c = "#00A54C" if abs(val) <= 5 else ("#FFC112" if abs(val) <= 15 else "#e63946") 
                return f"<div class='kpi-value' style='color:{c};'>{'+' if val>0 else ''}{val:.2f}%</div>"

            if usar_pesos and 'Peso Grupo (%)' in df_tab1.columns:
                st.markdown("### 🏆 Asertividad Global Ponderada (Var * %Grupo * %Actividad)")
                k_w1, k_w2, k_w3 = st.columns(3)
                
                df_tab1['W_Ana_Pre'] = df_tab1['Δ Pre vs Ana'] * (df_tab1['Peso Grupo (%)']/100) * (df_tab1['Peso Actividad (%)']/100)
                df_tab1['W_Con_Pre'] = df_tab1['Δ Con vs Pre'] * (df_tab1['Peso Grupo (%)']/100) * (df_tab1['Peso Actividad (%)']/100)
                df_tab1['W_Con_Ana'] = df_tab1['Δ Con vs Ana'] * (df_tab1['Peso Grupo (%)']/100) * (df_tab1['Peso Actividad (%)']/100)
                
                k_w1.markdown(f'<div class="kpi-card border-purple"><div class="kpi-title">Planeación Ponderada</div>{kpi(df_tab1["W_Ana_Pre"].sum())}</div>', unsafe_allow_html=True)
                k_w2.markdown(f'<div class="kpi-card border-purple"><div class="kpi-title">Financiero Ponderado</div>{kpi(df_tab1["W_Con_Pre"].sum())}</div>', unsafe_allow_html=True)
                k_w3.markdown(f'<div class="kpi-card border-purple"><div class="kpi-title">Efectividad Ponderada</div>{kpi(df_tab1["W_Con_Ana"].sum())}</div>', unsafe_allow_html=True)
                st.markdown("---")

            prom_ana, prom_pre, prom_con = df_tab1['Analizado'].mean(), df_tab1['Presupuestado'].mean(), df_tab1['Contratado'].mean()
            v_pre_ana = ((prom_pre - prom_ana) / prom_ana) if prom_ana else None
            v_con_pre = ((prom_con - prom_pre) / prom_pre) if prom_pre else None
            v_con_ana = ((prom_con - prom_ana) / prom_ana) if prom_ana else None

            st.markdown("### Promedios Globales (Sin Ponderar)")
            k1, k2, k3 = st.columns(3)
            k1.markdown(f'<div class="kpi-card border-blue"><div class="kpi-title">Planeación (Pre-Const. vs Analizado)</div>{kpi(v_pre_ana)}</div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="kpi-card border-green"><div class="kpi-title">Financiero (Construcción vs Pre-Const.)</div>{kpi(v_con_pre)}</div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kpi-card border-yellow"><div class="kpi-title">Efectividad Total (Const. vs Analizado)</div>{kpi(v_con_ana)}</div>', unsafe_allow_html=True)

            st.subheader("📊 Comparativa Consolidada de Fases por Proyecto")
            df_graf = df_tab1.groupby('PROYECTO')[['Analizado', 'Presupuestado', 'Contratado']].mean().reset_index()
            df_melted = df_graf.melt(id_vars='PROYECTO', value_vars=['Analizado', 'Presupuestado', 'Contratado'], var_name='Fase', value_name='Valor Promedio')
            
            fig1 = px.bar(df_melted, x='PROYECTO', y='Valor Promedio', color='Fase', barmode='group', text='Valor Promedio', color_discrete_map=colores_marca)
            fig1.update_traces(texttemplate=f'<b>{simbolo_moneda} %{{y:,.0f}}</b>', textposition='inside', textangle=-90, insidetextanchor='middle', hovertemplate=f'<b>Proyecto:</b> %{{x}}<br><b>Fase:</b> %{{data.name}}<br><b>Valor:</b> {simbolo_moneda} %{{y:,.0f}}<extra></extra>')
            fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1, title=""), xaxis_title="", yaxis_title=f"Inversión Promedio ({simbolo_moneda})", margin=dict(t=50, l=0, r=0, b=0), font=dict(family="Segoe UI", size=13, color="#4a5568"), uniformtext_minsize=10, uniformtext_mode='hide')
            fig1.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f2f6')
            fig1.update_xaxes(showgrid=False)
            st.plotly_chart(fig1, use_container_width=True)

            st.subheader("📋 Matriz Detallada")
            df_tab1['Δ Presup. vs Analiz. (%)'] = df_tab1['Δ Pre vs Ana'] * 100
            df_tab1['Δ Contrat. vs Presup. (%)'] = df_tab1['Δ Con vs Pre'] * 100
            df_tab1['Δ Contrat. vs Analiz. (%)'] = df_tab1['Δ Con vs Ana'] * 100

            def aplicar_color_semaforo(val):
                if pd.isna(val): return ''
                if -5 <= val <= 5: return 'background-color: #d4edda; color: #155724; font-weight: bold;'
                elif -15 <= val < -5 or 5 < val <= 15: return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
                else: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'

            columnas_porcentaje = ['Δ Presup. vs Analiz. (%)', 'Δ Contrat. vs Presup. (%)', 'Δ Contrat. vs Analiz. (%)']
            formatos = {col: lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A" for col in columnas_porcentaje}
            
            for col in ['Analizado', 'Presupuestado', 'Contratado']:
                formatos[col] = lambda x: f"{simbolo_moneda}{x:,.0f}" if pd.notna(x) else "N/A"

            df_mostrar_det = df_tab1.rename(columns={'Analizado': 'Precio Analizado PYC', 'Presupuestado': 'Pre-Construcción', 'Contratado': 'Construcción'})
            formatos['Precio Analizado PYC'] = formatos.pop('Analizado')
            formatos['Pre-Construcción'] = formatos.pop('Presupuestado')
            formatos['Construcción'] = formatos.pop('Contratado')

            columnas_ordenadas = cols_agrupacion + ['Precio Analizado PYC', 'Pre-Construcción', 'Construcción'] + columnas_porcentaje + [c for c in cols_extras if c in df_mostrar_det.columns]
            st.dataframe(df_mostrar_det[columnas_ordenadas].style.map(aplicar_color_semaforo, subset=columnas_porcentaje).format(formatos), use_container_width=True, hide_index=True, height=450)

    # ------------------------------------------
    # PESTAÑA 2: RESUMEN POR GRUPO 
    # ------------------------------------------
    with tab_grupos:
        st.markdown("### 📁 Fichas Técnicas por GRUPO")
        if not df_completos.empty and 'GRUPO' in df_completos.columns:
            grupos_unicos = sorted(df_completos['GRUPO'].dropna().unique())
            
            def mini_kpi(val):
                if pd.isna(val): return "<span style='color:#6c757d;'>N/A</span>"
                c = "#00A54C" if abs(val) <= 5 else ("#FFC112" if abs(val) <= 15 else "#e63946")
                return f"<span style='color:{c};'>{'+' if val>0 else ''}{val:.2f}%</span>"

            for i in range(0, len(grupos_unicos), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(grupos_unicos):
                        grupo = grupos_unicos[i + j]
                        df_grp = df_completos[df_completos['GRUPO'] == grupo]
                        with cols[j]:
                            p_ana, p_pre, p_con = df_grp['Analizado'].mean(), df_grp['Presupuestado'].mean(), df_grp['Contratado'].mean()
                            v_pre_ana = ((p_pre - p_ana) / p_ana * 100) if p_ana else float('nan')
                            v_con_pre = ((p_con - p_pre) / p_pre * 100) if p_pre else float('nan')
                            v_con_ana = ((p_con - p_ana) / p_ana * 100) if p_ana else float('nan')
                            
                            html_tarjeta = f"""<div class="act-card"><div class="act-title">{grupo}</div><div class="mini-kpi-container">
                                    <div class="mini-kpi"><div class="mini-kpi-val">{mini_kpi(v_pre_ana)}</div><div class="mini-kpi-lbl">% Presupuesto vs Analizado</div></div>
                                    <div class="mini-kpi"><div class="mini-kpi-val">{mini_kpi(v_con_pre)}</div><div class="mini-kpi-lbl">% Contratado vs Presupuesto</div></div>
                                    <div class="mini-kpi"><div class="mini-kpi-val">{mini_kpi(v_con_ana)}</div><div class="mini-kpi-lbl">% Contratado vs Analizado</div></div>
                                </div></div>"""
                            st.markdown(html_tarjeta, unsafe_allow_html=True)
                            
                            df_graf_g = df_grp.groupby('PROYECTO')[['Analizado', 'Presupuestado', 'Contratado']].mean().reset_index()
                            df_melt_g = df_graf_g.melt(id_vars='PROYECTO', value_vars=['Analizado', 'Presupuestado', 'Contratado'], var_name='Fase', value_name='Valor')
                            fig = px.bar(df_melt_g, x='PROYECTO', y='Valor', color='Fase', barmode='group', color_discrete_map=colores_marca)
                            fig.update_traces(hovertemplate=f'<b>Proyecto:</b> %{{x}}<br><b>Fase:</b> %{{data.name}}<br><b>Valor:</b> {simbolo_moneda} %{{y:,.0f}}<extra></extra>')
                            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=""), xaxis_title="PROYECTO", yaxis_title="", margin=dict(t=10, l=0, r=0, b=0), font=dict(family="Segoe UI", size=11, color="#4a5568"))
                            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f2f6', showticklabels=False)
                            fig.update_xaxes(showgrid=False)
                            st.plotly_chart(fig, use_container_width=True, key=f"graf_g_{grupo}_{i+j}")

    # ------------------------------------------
    # PESTAÑA 3: RESUMEN POR ACTIVIDAD
    # ------------------------------------------
    with tab_actividad:
        st.markdown("### 🛠️ Fichas Técnicas por ACTIVIDAD")
        if not df_completos.empty and 'ACTIVIDAD' in df_completos.columns:
            actividades_unicas = sorted(df_completos['ACTIVIDAD'].dropna().unique())

            for i in range(0, len(actividades_unicas), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(actividades_unicas):
                        actividad = actividades_unicas[i + j]
                        df_act = df_completos[df_completos['ACTIVIDAD'] == actividad]
                        with cols[j]:
                            p_ana, p_pre, p_con = df_act['Analizado'].mean(), df_act['Presupuestado'].mean(), df_act['Contratado'].mean()
                            v_pre_ana = ((p_pre - p_ana) / p_ana * 100) if p_ana else float('nan')
                            v_con_pre = ((p_con - p_pre) / p_pre * 100) if p_pre else float('nan')
                            v_con_ana = ((p_con - p_ana) / p_ana * 100) if p_ana else float('nan')
                            
                            html_tarjeta = f"""<div class="act-card"><div class="act-title">{actividad}</div><div class="mini-kpi-container">
                                    <div class="mini-kpi"><div class="mini-kpi-val">{mini_kpi(v_pre_ana)}</div><div class="mini-kpi-lbl">% Presupuesto vs Analizado</div></div>
                                    <div class="mini-kpi"><div class="mini-kpi-val">{mini_kpi(v_con_pre)}</div><div class="mini-kpi-lbl">% Contratado vs Presupuesto</div></div>
                                    <div class="mini-kpi"><div class="mini-kpi-val">{mini_kpi(v_con_ana)}</div><div class="mini-kpi-lbl">% Contratado vs Analizado</div></div>
                                </div></div>"""
                            st.markdown(html_tarjeta, unsafe_allow_html=True)
                            
                            df_graf_act = df_act.groupby('PROYECTO')[['Analizado', 'Presupuestado', 'Contratado']].mean().reset_index()
                            df_melt_act = df_graf_act.melt(id_vars='PROYECTO', value_vars=['Analizado', 'Presupuestado', 'Contratado'], var_name='Fase', value_name='Valor')
                            fig2 = px.bar(df_melt_act, x='PROYECTO', y='Valor', color='Fase', barmode='group', color_discrete_map=colores_marca)
                            fig2.update_traces(hovertemplate=f'<b>Proyecto:</b> %{{x}}<br><b>Fase:</b> %{{data.name}}<br><b>Valor:</b> {simbolo_moneda} %{{y:,.0f}}<extra></extra>')
                            fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=""), xaxis_title="PROYECTO", yaxis_title="", margin=dict(t=10, l=0, r=0, b=0), font=dict(family="Segoe UI", size=11, color="#4a5568"))
                            fig2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f2f6', showticklabels=False)
                            fig2.update_xaxes(showgrid=False)
                            st.plotly_chart(fig2, use_container_width=True, key=f"graf_a_{actividad}_{i+j}")

    # ------------------------------------------
    # PESTAÑA 4: AUDITORÍA (INCOMPLETOS)
    # ------------------------------------------
    with tab_audit:
        st.subheader("🚨 Reporte de Registros Incompletos")
        if df_incompletos.empty:
            st.success("🎉 ¡Excelente! No hay registros con fases faltantes bajo estos filtros.")
        else:
            st.markdown("Los siguientes registros tienen al menos una fase sin precio asociado en el Excel.")
            df_audit_mostrar = df_incompletos.rename(columns={'Analizado': 'Precio Analizado PYC', 'Presupuestado': 'Pre-Construcción', 'Contratado': 'Construcción'})
            formatos_audit = {col: lambda x: f"{simbolo_moneda}{x:,.0f}" if pd.notna(x) else "❌ FALTA" for col in ['Precio Analizado PYC', 'Pre-Construcción', 'Construcción']}
            def resaltar_faltantes(val): return 'background-color: #fee2e2; color: #b91c1c; font-weight:bold;' if pd.isna(val) else ''
            cols_audit_ord = cols_agrupacion + ['Precio Analizado PYC', 'Pre-Construcción', 'Construcción'] + [c for c in cols_extras if c in df_audit_mostrar.columns]
            st.dataframe(df_audit_mostrar[cols_audit_ord].style.map(resaltar_faltantes, subset=['Precio Analizado PYC', 'Pre-Construcción', 'Construcción']).format(formatos_audit), use_container_width=True, hide_index=True, height=500)
else:
    st.warning("⚠️ No existen registros numéricos válidos con la combinación de filtros seleccionada.")
