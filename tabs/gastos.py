import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

SHEET_ID = "14iTFjqHSKFPdLT9rieop6lFozA9ZkC_zYmfjjjV7HlU"
CREDS_FILE = r"G:\Meu Drive\Antigravity\Bitcoin\certs\google_creds.json"

def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Priority for st.secrets (Streamlit Cloud)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Fallback for local file (Development)
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
        
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_planning():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("Planejamento")
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_data(sheet_name):
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet(sheet_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if 'Data' in df.columns:
            df['Data_Full'] = pd.to_datetime(df['Data'], errors='coerce')
        if 'Valor' in df.columns:
            df['Valor'] = pd.to_numeric(df['Valor'].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip(), errors='coerce').fillna(0)
        return df
    except Exception:
        return pd.DataFrame()

def render(mask_val_func):
    st.header("🛒 Controle de Gastos & Planejamento")
    
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheets = [ws.title for ws in spreadsheet.worksheets() if ws.title != "Planejamento"]
        
        # Filtros na parte superior
        c1, c2 = st.columns([1, 2])
        with c1:
            selected_month = st.selectbox("Selecione o Lançamento", options=worksheets, index=len(worksheets)-1)
        
        if selected_month:
            df = load_data(selected_month)
            df_plan = load_planning()
            
            if df.empty:
                st.warning(f"A aba '{selected_month}' está vazia.")
            else:
                # Sidebar de filtros
                with st.sidebar:
                    st.divider()
                    st.subheader("🔍 Filtros de Gastos")
                    
                    if 'Data_Full' in df.columns:
                        min_date = df['Data_Full'].min().date()
                        max_date = df['Data_Full'].max().date()
                        date_range = st.date_input("Intervalo", [min_date, max_date], min_value=min_date, max_value=max_date)
                        
                        if isinstance(date_range, list) and len(date_range) == 2:
                            df = df[(df['Data_Full'].dt.date >= date_range[0]) & (df['Data_Full'].dt.date <= date_range[1])]
                        elif isinstance(date_range, datetime.date):
                             df = df[df['Data_Full'].dt.date == date_range]

                    col_filter_user = st.multiselect("Usuário", options=df['Usuário'].unique(), default=df['Usuário'].unique())
                    col_filter_cat = st.multiselect("Categoria", options=df['Categoria'].unique(), default=df['Categoria'].unique())
                    col_filter_pay = st.multiselect("Forma de Pagamento", options=df['Pagamento'].unique(), default=df['Pagamento'].unique())
                
                # Aplicar filtros
                df_filtered = df[
                    (df['Usuário'].isin(col_filter_user)) & 
                    (df['Categoria'].isin(col_filter_cat)) & 
                    (df['Pagamento'].isin(col_filter_pay))
                ].copy()

                # Métricas
                m1, m2, m3 = st.columns(3)
                total_real = df_filtered['Valor'].sum()
                
                # Cálculo de Meta Total (soma das metas das categorias filtradas)
                total_meta = 0
                if not df_plan.empty:
                    # Garantir que metas são numéricas
                    df_plan['Gasto Máximo Mensal'] = pd.to_numeric(df_plan['Gasto Máximo Mensal'], errors='coerce')
                    total_meta = df_plan[df_plan['Categoria'].isin(col_filter_cat)]['Gasto Máximo Mensal'].sum()

                m1.metric("Realizado", mask_val_func(total_real), delta=f"{((total_real/total_meta)-1)*100:.1f}% da meta" if total_meta > 0 else None, delta_color="inverse")
                m2.metric("Planejado (Meta)", mask_val_func(total_meta))
                m3.metric("Saldo do Orçamento", mask_val_func(total_meta - total_real) if total_meta > 0 else "N/A")

                st.divider()

                # Gráficos
                g1, g2 = st.columns(2)
                
                with g1:
                    # Comparação Meta vs Real por Categoria
                    if not df_plan.empty:
                        real_by_cat = df_filtered.groupby('Categoria')['Valor'].sum().reset_index()
                        comp_df = pd.merge(df_plan, real_by_cat, on='Categoria', how='left').fillna(0)
                        comp_df = comp_df[comp_df['Categoria'].isin(col_filter_cat)]
                        
                        # Melt para gráfico de barras agrupadas
                        plot_df = comp_df.melt(id_vars='Categoria', value_vars=['Gasto Máximo Mensal', 'Valor'], 
                                             var_name='Tipo', value_name='Total')
                        plot_df['Tipo'] = plot_df['Tipo'].replace({'Gasto Máximo Mensal': 'Meta', 'Valor': 'Realizado'})
                        
                        fig_comp = px.bar(plot_df, x='Categoria', y='Total', color='Tipo', barmode='group',
                                        title="Meta vs Realizado por Categoria", color_discrete_map={'Meta': '#636EFA', 'Realizado': '#EF553B'})
                        st.plotly_chart(fig_comp, use_container_width=True)
                    else:
                        st.info("Cadastre metas na aba 'Planejamento' para ver a comparação.")
                
                with g2:
                    if selected_month == "Consolidado" and 'Mês_Ref' in df_filtered.columns:
                        month_evo = df_filtered.groupby('Mês_Ref')['Valor'].sum().reset_index()
                        fig_evo = px.bar(month_evo, x='Mês_Ref', y='Valor', title="Evolução Mensal", color='Mês_Ref')
                        st.plotly_chart(fig_evo, use_container_width=True)
                    else:
                        fig_cat = px.pie(df_filtered, values='Valor', names='Categoria', title="Divisão das Despesas Reais", hole=0.4)
                        st.plotly_chart(fig_cat, use_container_width=True)

                # Tabela
                st.subheader("📋 Detalhamento dos Registros")
                show_cols = ["Dia", "Hora", "Usuário", "Descrição", "Categoria", "Prioridade", "Pagamento", "Valor"]
                if "Mês_Ref" in df_filtered.columns: show_cols.append("Mês_Ref")
                st.dataframe(df_filtered[show_cols].sort_index(ascending=False), use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao carregar aba de gastos: {e}")

    except Exception as e:
        st.error(f"Erro ao carregar aba de gastos: {e}")
