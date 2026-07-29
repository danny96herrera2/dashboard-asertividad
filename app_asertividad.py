import streamlit as st
import pandas as pd
import plotly.express as px
import os
import tempfile

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

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

archivo_residente = None
if os.path.exists("base_datos.xlsx"):
    archivo_residente = "base_datos.xlsx"
elif os.path.exists("base_datos.csv"):
    archivo_residente = "base_datos.csv"

if archivo_residente is None:
    st.info("👋 **¡Bienvenido al sistema corporativo!**\n\nSube tu archivo consolidado a GitHub renombrado exactamente como **`base_datos.xlsx`**.")
    st.stop()

with st.spinner("🚀 Sincronizando Base de Datos..."):
    df, mensaje = cargar_y_procesar_base(archivo_residente)
    
if mensaje != "OK":
    st.error(mensaje)
    st.stop()

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
# 4. PANEL DE PONDERACIONES (PESOS) 
# ==========================================
st.sidebar.markdown("---")
st.sidebar.markdown("⚖️ **Ponderación de Asertividad**")
usar_pesos = st.sidebar.toggle("Activar Pesos Ponderados", value=True)

df_pesos_guardados = None
if usar_pesos:
    with st.expander("🛠️ Configuración de Pesos (%)", expanded=False):
        df_config_pesos = df_filtrado[['GRUPO', 'ACTIVIDAD']].drop_duplicates().reset_index(drop=True)
        if not df_config_pesos.empty:
            total_grupos = df_config_pesos['GRUPO'].nunique()
            df_config_pesos['Peso Grupo (%)'] = 100.0 / total_grupos if total_grupos > 0 else 100.0
            df_config_pesos['Peso Actividad (%)'] = df_config_pesos.groupby('GRUPO')['ACTIVIDAD'].transform(lambda x: 100.0 / len(x) if len(x) > 0 else 100.0)
            
            if os.path.exists("pesos.csv"):
                try:
                    df_pesos_csv = pd.read_csv("pesos.csv", sep=None, engine='python', encoding='utf-8-sig')
                    df_pesos_csv.columns = df_pesos_csv.columns.astype(str).str.strip().str.upper()
                    if 'GRUPO' in df_pesos_csv.columns:
                        cols_numericas = [c for c in df_pesos_csv.columns if c not in ['GRUPO', 'ACTIVIDAD'] and not c.startswith('UNNAMED')]
                        cols_peso = [c for c in cols_numericas if 'PESO' in c or '%' in c or 'VALOR' in c]
                        col_peso_csv = cols_peso[0] if cols_peso else cols_numericas[-1]
                        
                        df_pesos_csv[col_peso_csv] = df_pesos_csv[col_peso_csv].astype(str).str.replace(',', '.', regex=False).str.replace('%', '', regex=False).str.strip()
                        df_pesos_csv[col_peso_csv] = pd.to_numeric(df_pesos_csv[col_peso_csv], errors='coerce')
                        
                        def limpiar_texto(t):
                            if pd.isna(t) or str(t).strip().upper() in ['NAN', 'NONE', '']: return ""
                            t = str(t).strip().upper()
                            reemplazos = {'Á':'A', 'É':'E', 'Í':'I', 'Ó':'O', 'Ú':'U'}
                            for a, b in reemplazos.items(): t = t.replace(a, b)
                            return t

                        df_pesos_csv['G_CLN'] = df_pesos_csv['GRUPO'].apply(limpiar_texto)
                        df_pesos_csv['A_CLN'] = df_pesos_csv.get('ACTIVIDAD', pd.Series(dtype=str)).apply(limpiar_texto)
                        df_config_pesos['G_CLN'] = df_config_pesos['GRUPO'].apply(limpiar_texto)
                        df_config_pesos['A_CLN'] = df_config_pesos['ACTIVIDAD'].apply(limpiar_texto)

                        df_g_csv = df_pesos_csv[df_pesos_csv['A_CLN'] == '']
                        dict_g = dict(zip(df_g_csv['G_CLN'], df_g_csv[col_peso_csv]))
                        df_a_csv = df_pesos_csv[df_pesos_csv['A_CLN'] != '']
                        dict_a = dict(zip(df_a_csv['G_CLN'] + "||" + df_a_csv['A_CLN'], df_a_csv[col_peso_csv]))
                        
                        def cruzar_grupo(row):
                            g = row['G_CLN']
                            if g in dict_g: return dict_g[g]
                            for k, v in dict_g.items():
                                if k in g or g in k: return v
                            return row['Peso Grupo (%)']
                            
                        def cruzar_actividad(row):
                            g, a = row['G_CLN'], row['A_CLN']
                            k_exacta = f"{g}||{a}"
                            if k_exacta in dict_a: return dict_a[k_exacta]
                            for k, v in dict_a.items():
                                if g in k and (a in k or k in a): return v
                            return row['Peso Actividad (%)']

                        df_config_pesos['Peso Grupo (%)'] = df_config_pesos.apply(cruzar_grupo, axis=1)
                        df_config_pesos['Peso Actividad (%)'] = df_config_pesos.apply(cruzar_actividad, axis=1)
                        df_config_pesos = df_config_pesos.drop(columns=['G_CLN', 'A_CLN'])
                        
                except Exception:
                    pass
        df_pesos_guardados = st.data_editor(df_config_pesos, hide_index=True, use_container_width=True)

# ==========================================
# 5. MOTOR ESTADÍSTICO Y COLECCIÓN PARA PDF
# ==========================================
# Declaramos contenedores de memoria para el PDF
fig1 = None
texto_resumen = ""
val_txt_pre_ana = val_txt_con_pre = val_txt_con_ana = 0
reporte_grupos = []
reporte_actividades = []

colores_marca = {'Analizado': '#FFC112', 'Presupuesto': '#223983', 'Contratado': '#00A54C'}

if not df_filtrado.empty and col_valor in df_filtrado.columns:
    cols_agrupacion = [c for c in ['CIUDAD', 'PROYECTO', 'GRUPO', 'ACTIVIDAD'] if c in df.columns]
    cols_extras = [c for c in ['TIPO DE PROYECTO', 'CONTRATISTA/PROVEEDOR', 'ALCANCE', 'TRM(DIA DE CONTRATO /COTIZACION)'] if c in df_filtrado.columns]

    mask_ascensor = df_filtrado['GRUPO'].astype(str).str.upper().str.contains('ASCENSOR')
    df_asc = df_filtrado[mask_ascensor].copy()
    df_resto = df_filtrado[~mask_ascensor].copy()

    pivotes, desc_list = [], []

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
    
    # ==========================================
    # 6. CREACIÓN DE LAS PESTAÑAS Y TARJETAS
    # ==========================================
    tab_main, tab_grupos, tab_actividad, tab_audit = st.tabs(["📊 Dashboard Principal", "📁 Resumen por Grupo", "🛠️ Resumen por Actividad", "🚨 Auditoría"])

    with tab_main:
        if df_completos.empty:
            st.warning("⚠️ No hay ítems con el ciclo de 3 fases completado para los filtros seleccionados.")
        else:
            df_resumen = df_completos.groupby('PROYECTO')[['Analizado', 'Presupuestado', 'Contratado']].mean().reset_index()
            df_mostrar_resumen = df_resumen.rename(columns={'Analizado': 'Precio Analizado PYC', 'Presupuestado': 'Presupuesto', 'Contratado': 'Contratado'})
            
            for col in ['Precio Analizado PYC', 'Presupuesto', 'Contratado']:
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
                c = "#00A54C" if val < 0 else ("#e63946" if val > 0 else "#FFC112")
                return f"<div class='kpi-value' style='color:{c};'>{'+' if val>0 else ''}{val:.2f}%</div>"

            st.markdown("### 🏆 Indicadores de Variaciones")
            if usar_pesos and 'Peso Grupo (%)' in df_tab1.columns:
                k_w1, k_w2, k_w3 = st.columns(3)
                df_tab1['W_Ana_Pre'] = df_tab1['Δ Pre vs Ana'] * (df_tab1['Peso Grupo (%)']/100) * (df_tab1['Peso Actividad (%)']/100)
                df_tab1['W_Con_Pre'] = df_tab1['Δ Con vs Pre'] * (df_tab1['Peso Grupo (%)']/100) * (df_tab1['Peso Actividad (%)']/100)
                df_tab1['W_Con_Ana'] = df_tab1['Δ Con vs Ana'] * (df_tab1['Peso Grupo (%)']/100) * (df_tab1['Peso Actividad (%)']/100)
                
                v_pre_ana_w = df_tab1["W_Ana_Pre"].sum()
                v_con_pre_w = df_tab1["W_Con_Pre"].sum()
                v_con_ana_w = df_tab1["W_Con_Ana"].sum()

                k_w1.markdown(f'<div class="kpi-card border-purple"><div class="kpi-title">% Presupuesto vs Analizado (Ponderado)</div>{kpi(v_pre_ana_w)}</div>', unsafe_allow_html=True)
                k_w2.markdown(f'<div class="kpi-card border-purple"><div class="kpi-title">% Contratado vs Presupuesto (Ponderado)</div>{kpi(v_con_pre_w)}</div>', unsafe_allow_html=True)
                k_w3.markdown(f'<div class="kpi-card border-purple"><div class="kpi-title">% Contratado vs Analizado (Ponderado)</div>{kpi(v_con_ana_w)}</div>', unsafe_allow_html=True)
                
            prom_ana, prom_pre, prom_con = df_tab1['Analizado'].mean(), df_tab1['Presupuestado'].mean(), df_tab1['Contratado'].mean()
            v_pre_ana = ((prom_pre - prom_ana) / prom_ana) if prom_ana else 0
            v_con_pre = ((prom_con - prom_pre) / prom_pre) if prom_pre else 0
            v_con_ana = ((prom_con - prom_ana) / prom_ana) if prom_ana else 0

            st.markdown("---")
            val_txt_pre_ana = v_pre_ana_w if usar_pesos else v_pre_ana
            val_txt_con_pre = v_con_pre_w if usar_pesos else v_con_pre
            val_txt_con_ana = v_con_ana_w if usar_pesos else v_con_ana
            
            texto_resumen = f"En el análisis global, el indicador de Presupuesto vs Analizado muestra una variación del {val_txt_pre_ana*100:.2f}%. Por otro lado, la transición de Contratado vs Presupuesto refleja un impacto del {val_txt_con_pre*100:.2f}%. Finalmente, el desfase total (Contratado vs Analizado) se consolida en {val_txt_con_ana*100:.2f}%. Estos resultados indican una tendencia general {'favorable (ahorros)' if val_txt_con_ana < 0 else 'desfavorable (sobrecostos)'} frente a las estimaciones iniciales."
            
            st.info(f"📝 **Resumen Ejecutivo:**\n\n{texto_resumen}")
            st.markdown("---")

            st.markdown("### 📊 Promedios Globales (Sin Ponderar)")
            k1, k2, k3 = st.columns(3)
            k1.markdown(f'<div class="kpi-card border-blue"><div class="kpi-title">% Presupuesto vs Analizado</div>{kpi(v_pre_ana)}</div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="kpi-card border-green"><div class="kpi-title">% Contratado vs Presupuesto</div>{kpi(v_con_pre)}</div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kpi-card border-yellow"><div class="kpi-title">% Contratado vs Analizado</div>{kpi(v_con_ana)}</div>', unsafe_allow_html=True)

            st.subheader("📊 Comparativa Consolidada de Fases por Proyecto")
            df_graf = df_tab1.groupby('PROYECTO')[['Analizado', 'Presupuestado', 'Contratado']].mean().reset_index()
            df_graf = df_graf.rename(columns={'Presupuestado': 'Presupuesto'})
            df_melted = df_graf.melt(id_vars='PROYECTO', value_vars=['Analizado', 'Presupuesto', 'Contratado'], var_name='Fase', value_name='Valor Promedio')
            
            fig1 = px.bar(df_melted, x='PROYECTO', y='Valor Promedio', color='Fase', barmode='group', text='Valor Promedio', color_discrete_map=colores_marca)
            fig1.update_traces(texttemplate=f'<b>{simbolo_moneda} %{{y:,.0f}}</b>', textposition='inside', textangle=-90, insidetextanchor='middle', hovertemplate=f'<b>Proyecto:</b> %{{x}}<br><b>Fase:</b> %{{data.name}}<br><b>Valor:</b> {simbolo_moneda} %{{y:,.0f}}<extra></extra>')
            fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1, title=""), xaxis_title="", yaxis_title=f"Inversión Promedio ({simbolo_moneda})", margin=dict(t=50, l=0, r=0, b=0))
            fig1.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f2f6')
            st.plotly_chart(fig1, use_container_width=True)

            st.subheader("📋 Matriz Detallada")
            df_tab1['Δ Presup. vs Analiz. (%)'] = df_tab1['Δ Pre vs Ana'] * 100
            df_tab1['Δ Contrat. vs Presup. (%)'] = df_tab1['Δ Con vs Pre'] * 100
            df_tab1['Δ Contrat. vs Analiz. (%)'] = df_tab1['Δ Con vs Ana'] * 100

            def aplicar_color_semaforo(val):
                if pd.isna(val): return ''
                if val < 0: return 'background-color: #d4edda; color: #155724; font-weight: bold;'
                elif val > 0: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                else: return 'background-color: #fff3cd; color: #856404; font-weight: bold;'

            columnas_porcentaje = ['Δ Presup. vs Analiz. (%)', 'Δ Contrat. vs Presup. (%)', 'Δ Contrat. vs Analiz. (%)']
            formatos = {col: lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A" for col in columnas_porcentaje}
            
            for col in ['Analizado', 'Presupuestado', 'Contratado']:
                formatos[col] = lambda x: f"{simbolo_moneda}{x:,.0f}" if pd.notna(x) else "N/A"

            df_mostrar_det = df_tab1.rename(columns={'Analizado': 'Precio Analizado PYC', 'Presupuestado': 'Presupuesto', 'Contratado': 'Contratado'})
            formatos['Precio Analizado PYC'] = formatos.pop('Analizado')
            formatos['Presupuesto'] = formatos.pop('Presupuestado')
            formatos['Contratado'] = formatos.pop('Contratado')

            columnas_ordenadas = cols_agrupacion + ['Precio Analizado PYC', 'Presupuesto', 'Contratado'] + columnas_porcentaje + [c for c in cols_extras if c in df_mostrar_det.columns]
            
            if 'TRM(DIA DE CONTRATO /COTIZACION)' in columnas_ordenadas:
                formatos['TRM(DIA DE CONTRATO /COTIZACION)'] = lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A"

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
                c = "#00A54C" if val < 0 else ("#e63946" if val > 0 else "#FFC112")
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
                            df_graf_g = df_graf_g.rename(columns={'Presupuestado': 'Presupuesto'})
                            df_melt_g = df_graf_g.melt(id_vars='PROYECTO', value_vars=['Analizado', 'Presupuesto', 'Contratado'], var_name='Fase', value_name='Valor')
                            fig_g = px.bar(df_melt_g, x='PROYECTO', y='Valor', color='Fase', barmode='group', text='Valor', color_discrete_map=colores_marca)
                            fig_g.update_traces(texttemplate=f'<b>{simbolo_moneda} %{{y:,.0f}}</b>', textposition='inside', textangle=-90, insidetextanchor='middle')
                            fig_g.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=""), xaxis_title="", yaxis_title="", margin=dict(t=10, l=0, r=0, b=0))
                            fig_g.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f2f6', showticklabels=False)
                            st.plotly_chart(fig_g, use_container_width=True, key=f"graf_g_{grupo}_{i+j}")

                            # Guardamos en la memoria para el PDF
                            reporte_grupos.append({'nombre': grupo, 'pa': v_pre_ana, 'cp': v_con_pre, 'ca': v_con_ana, 'figura': fig_g})

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
                            df_graf_act = df_graf_act.rename(columns={'Presupuestado': 'Presupuesto'})
                            df_melt_act = df_graf_act.melt(id_vars='PROYECTO', value_vars=['Analizado', 'Presupuesto', 'Contratado'], var_name='Fase', value_name='Valor')
                            fig_a = px.bar(df_melt_act, x='PROYECTO', y='Valor', color='Fase', barmode='group', text='Valor', color_discrete_map=colores_marca)
                            fig_a.update_traces(texttemplate=f'<b>{simbolo_moneda} %{{y:,.0f}}</b>', textposition='inside', textangle=-90, insidetextanchor='middle')
                            fig_a.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=""), xaxis_title="", yaxis_title="", margin=dict(t=10, l=0, r=0, b=0))
                            fig_a.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f2f6', showticklabels=False)
                            st.plotly_chart(fig_a, use_container_width=True, key=f"graf_a_{actividad}_{i+j}")

                            # Guardamos en la memoria para el PDF
                            reporte_actividades.append({'nombre': actividad, 'pa': v_pre_ana, 'cp': v_con_pre, 'ca': v_con_ana, 'figura': fig_a})

    # ------------------------------------------
    # PESTAÑA 4: AUDITORÍA (INCOMPLETOS)
    # ------------------------------------------
    with tab_audit:
        st.subheader("🚨 Reporte de Registros Incompletos")
        if df_incompletos.empty:
            st.success("🎉 ¡Excelente! No hay registros con fases faltantes bajo estos filtros.")
        else:
            df_audit_mostrar = df_incompletos.rename(columns={'Analizado': 'Precio Analizado PYC', 'Presupuestado': 'Presupuesto', 'Contratado': 'Contratado'})
            formatos_audit = {col: lambda x: f"{simbolo_moneda}{x:,.0f}" if pd.notna(x) else "❌ FALTA" for col in ['Precio Analizado PYC', 'Presupuesto', 'Contratado']}
            def resaltar_faltantes(val): return 'background-color: #fee2e2; color: #b91c1c; font-weight:bold;' if pd.isna(val) else ''
            cols_audit_ord = cols_agrupacion + ['Precio Analizado PYC', 'Presupuesto', 'Contratado'] + [c for c in cols_extras if c in df_audit_mostrar.columns]
            st.dataframe(df_audit_mostrar[cols_audit_ord].style.map(resaltar_faltantes, subset=['Precio Analizado PYC', 'Presupuesto', 'Contratado']).format(formatos_audit), use_container_width=True, hide_index=True, height=500)

else:
    st.warning("⚠️ No existen registros numéricos válidos con la combinación de filtros seleccionada.")

# ==========================================
# 7. EXPORTACIÓN PDF MAESTRO (BARRA LATERAL)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.markdown("📄 **Exportar Reporte Completo a PDF**")

if FPDF is not None and fig1 is not None:
    def safe_txt(txt):
        return str(txt).encode('latin-1', 'replace').decode('latin-1')

    def f_pct(val):
        return f"{val:.2f}%" if pd.notna(val) else "N/A"

    def crear_pdf():
        pdf = FPDF()
        
        # --- SECCIÓN 1: PANEL GLOBAL ---
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Informe Ejecutivo de Asertividad de Precios", ln=True, align='C')
        pdf.ln(5)
        
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 7, safe_txt(texto_resumen))
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 12)
        tit_pesos = "Indicadores Globales (Ponderados):" if usar_pesos else "Indicadores Globales (Sin Ponderar):"
        pdf.cell(0, 10, tit_pesos, ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 8, f"   > % Presupuesto vs Analizado:     {val_txt_pre_ana*100:.2f}%", ln=True)
        pdf.cell(0, 8, f"   > % Contratado vs Presupuesto: {val_txt_con_pre*100:.2f}%", ln=True)
        pdf.cell(0, 8, f"   > % Contratado vs Analizado:     {val_txt_con_ana*100:.2f}%", ln=True)
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Comparativa Consolidada de Fases por Proyecto:", ln=True)
        pdf.ln(2)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
            fig1.write_image(tmp_img.name, format="png", engine="kaleido", width=900, height=450)
            pdf.image(tmp_img.name, x=10, w=190)

        # --- SECCIÓN 2: GRUPOS ---
        if reporte_grupos:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "RESUMEN DETALLADO POR GRUPO", ln=True, align='C')
            pdf.ln(5)
            for g in reporte_grupos:
                if pdf.get_y() > 220:  # Salto de página automático si no cabe
                    pdf.add_page()
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 8, safe_txt(f"GRUPO: {g['nombre']}"), ln=True)
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 5, f" % Presupuesto vs Analizado: {f_pct(g['pa'])}  |  % Contratado vs Presupuesto: {f_pct(g['cp'])}  |  % Contratado vs Analizado: {f_pct(g['ca'])}", ln=True)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_g:
                    g['figura'].write_image(tmp_g.name, format="png", engine="kaleido", width=800, height=300)
                    pdf.image(tmp_g.name, x=10, w=190)
                pdf.ln(8)

        # --- SECCIÓN 3: ACTIVIDADES ---
        if reporte_actividades:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "RESUMEN DETALLADO POR ACTIVIDAD", ln=True, align='C')
            pdf.ln(5)
            for a in reporte_actividades:
                if pdf.get_y() > 220:
                    pdf.add_page()
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 8, safe_txt(f"ACTIVIDAD: {a['nombre']}"), ln=True)
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 5, f" % Presupuesto vs Analizado: {f_pct(a['pa'])}  |  % Contratado vs Presupuesto: {f_pct(a['cp'])}  |  % Contratado vs Analizado: {f_pct(a['ca'])}", ln=True)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_a:
                    a['figura'].write_image(tmp_a.name, format="png", engine="kaleido", width=800, height=300)
                    pdf.image(tmp_a.name, x=10, w=190)
                pdf.ln(8)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            with open(tmp_pdf.name, "rb") as f:
                return f.read()
    
    # Generador con animacion de carga (spinner) porque Kaleido toma unos segundos en dibujar todas las graficas
    st.sidebar.markdown("*(Nota: Generar el PDF toma unos segundos porque procesa todas las pestañas simultáneamente).*")
    if st.sidebar.button("Generar Reporte Completo"):
        with st.sidebar.status("📸 Capturando todas las gráficas...", expanded=True) as status:
            try:
                pdf_bytes = crear_pdf()
                status.update(label="✅ ¡Reporte Listo!", state="complete", expanded=False)
                st.sidebar.download_button(label="📥 Clic aquí para Descargar", data=pdf_bytes, file_name="Reporte_Completo_Asertividad.pdf", mime="application/pdf")
            except Exception as e:
                status.update(label="❌ Error al generar", state="error")
                st.sidebar.error(f"Error técnico: {e}")
else:
    st.sidebar.info("Aplica filtros para activar la exportación.")
