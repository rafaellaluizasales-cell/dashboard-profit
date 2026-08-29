import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import plotly.graph_objects as go
from utils.data_loader import fetch_real_ohlc
import datetime
import yfinance as yf
import numpy as np
from utils.components import section_header, status_badge, glass_card

@st.cache_data(ttl=3600)
def get_batch_market_data(proxies_to_fetch):
    """Fetches markert data for multiple symbols in one go with caching."""
    results = {}
    for sym, d_range in proxies_to_fetch.items():
        p_start = d_range['start'].replace(hour=0, minute=0, second=0) - datetime.timedelta(days=1)
        p_end = d_range['end'].replace(hour=23, minute=59, second=59) + datetime.timedelta(days=1)
        
        try:
            df = yf.download(sym, start=p_start, end=p_end, interval='5m', progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [str(c[0]) for c in df.columns]
                results[sym] = df
            else:
                results[sym] = pd.DataFrame()
        except:
            results[sym] = pd.DataFrame()
    return results

def render(df, df_raw, mask_val):
    # Calculate performance metrics
    total_pnl = df['Res_Numeric'].sum()
    gross_profit = df[df['Res_Numeric'] > 0]['Res_Numeric'].sum()
    gross_loss = df[df['Res_Numeric'] < 0]['Res_Numeric'].sum()
    num_trades = len(df)
    win_rate = (len(df[df['Res_Numeric'] > 0]) / num_trades * 100) if num_trades > 0 else 0
    
    section_header("Performance do Dia", icon="⚡")

    # Define colors and strings for the header
    c_res = "#00fa9a" if total_pnl >= 0 else "#ff4d4d"
    s_res_liq = mask_val(total_pnl) if isinstance(mask_val(total_pnl), str) else f"R$ {total_pnl:,.2f}"
    s_ops = f"{num_trades}"
    s_win = f"{win_rate:.1f}%"
    s_lucro = mask_val(gross_profit) if isinstance(mask_val(gross_profit), str) else f"R$ {gross_profit:,.2f}"
    s_prej = mask_val(gross_loss) if isinstance(mask_val(gross_loss), str) else f"R$ {gross_loss:,.2f}"
    
    # Premium Header Container
    st.markdown(f"""
    <div class="glass-card" style="padding: 15px; margin-bottom: 25px; border-left: 5px solid {c_res};">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
            <div>
                <label class="glass-label">Resultado Líquido</label>
                <div class="glass-value" style="color: {c_res}; font-size: 2.2em;">{s_res_liq}</div>
            </div>
            <div style="display: flex; gap: 30px;">
                <div>
                    <label class="glass-label">Operações</label>
                    <div style="font-size: 1.2em; font-weight: 700;">{s_ops}</div>
                </div>
                <div>
                    <label class="glass-label">Taxa de Acerto</label>
                    <div style="font-size: 1.2em; font-weight: 700; color: #00fa9a;">{s_win}</div>
                </div>
                <div>
                    <label class="glass-label">Lucro Bruto</label>
                    <div style="font-size: 1.2em; font-weight: 700; color: #00fa9a;">{s_lucro}</div>
                </div>
                <div>
                    <label class="glass-label">Prejuízo Bruto</label>
                    <div style="font-size: 1.2em; font-weight: 700; color: #ff6b6b;">{s_prej}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- RECENT OPERATIONS CARDS (Horizontal Layout) ---
    if not df.empty:
        st.markdown("### 🎯 Foco Principal: Operações Recentes (5m)")
        
        # Sort by Date desc
        sorted_df = df.sort_values('Abertura_Dt', ascending=False)
        
        # --- BATCH DATA FETCHING PER SYMBOL ---
        proxies_to_fetch = {}
        for _, row in sorted_df.iterrows():
            sym = "^BVSP" if "WIN" in str(row['Ativo']).upper() else "USDBRL=X"
            if sym not in proxies_to_fetch:
                proxies_to_fetch[sym] = {'start': row['Abertura_Dt'], 'end': row.get('Fechamento_Dt', row['Abertura_Dt'])}
            else:
                proxies_to_fetch[sym]['start'] = min(proxies_to_fetch[sym]['start'], row['Abertura_Dt'])
                proxies_to_fetch[sym]['end'] = max(proxies_to_fetch[sym]['end'], row.get('Fechamento_Dt', row['Abertura_Dt']))

        # Use the cached batch fetcher
        proxy_data = get_batch_market_data(proxies_to_fetch)

        # Render cards
        for idx, row in sorted_df.iterrows():
            # Auto-expand only first 5
            is_expanded = (idx < 5)
            
            title_ativo = mask_val(row['Ativo'], "text")
            side = str(row.get('Lado', 'C')).strip().upper()
            badge_var = "success" if side == 'C' else "danger"
            badge_text = "COMPRA" if side == 'C' else "VENDA"
            
            with st.expander(f"{title_ativo} | {mask_val(row['Abertura'], 'time')} | Resultado: {mask_val(row.get('Res. Operação', row.get('Res. Intervalo Bruto', 0)))}", expanded=is_expanded):
                col1, col2, col3 = st.columns([1.5, 3, 2.5])
                
                with col1:
                    st.markdown(status_badge(badge_text, badge_var), unsafe_allow_html=True)
                    st.metric("Ativo", row['Ativo'])
                    st.write(f"**Qtd:** {row['Qtd']}")
                    st.caption(f"📅 {row['Abertura']}")
                
                with col2:
                    symbol_proxy = "^BVSP" if "WIN" in str(row['Ativo']).upper() else "USDBRL=X"
                    st.write(f"**Gráfico 5m ({symbol_proxy})**")
                    
                    side = str(row.get('Lado', 'C')).strip().upper()
                    
                    def get_price(p_col_numeric, p_col_raw):
                        val = row.get(p_col_numeric, row.get(p_col_raw, 0))
                        if isinstance(val, str):
                             val = val.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
                             try: val = float(val)
                             except: val = 0
                        return val

                    p_compra = get_price('Preço Compra Numeric', 'Preço Compra')
                    p_venda = get_price('Preço Venda Numeric', 'Preço Venda')
                    p_medio = get_price('Médio Numeric', 'Médio')
                    
                    # Robust assignment
                    if side == 'C':
                        entry_px = p_compra if p_compra > 0 else p_medio
                        exit_px = p_venda
                    else:
                        entry_px = p_venda if p_venda > 0 else p_medio
                        exit_px = p_compra

                    # Fallback: Calculate missing price from P&L if necessary
                    res_bruto = row.get('Res_Numeric', 0)
                    qtd = max(1, int(row.get('Qtd_Clean', 1)))
                    
                    # Multipliers: WIN/IND = 0.2, WDO/DOL = 10/50
                    mult = 0.2 if 'W' in str(row['Ativo']).upper() or 'I' in str(row['Ativo']).upper() else 1.0
                    if 'WDO' in str(row['Ativo']).upper() or 'DOL' in str(row['Ativo']).upper():
                        mult = 10.0 if 'WDO' in str(row['Ativo']).upper() else 50.0

                    if entry_px > 0 and (exit_px == 0 or abs(exit_px - entry_px) > entry_px * 0.1):
                        # If exit_px is 0 or suspiciously far, derive it
                        # Res = (Exit - Entry) * Qtd * Mult (for Long)
                        # Res = (Entry - Exit) * Qtd * Mult (for Short)
                        points = res_bruto / (qtd * mult)
                        exit_px = entry_px + points if side == 'C' else entry_px - points
                    
                    exit_dt = row.get('Fechamento_Dt', row['Abertura_Dt'])
                    
                    # Pass the pre-fetched data
                    df_symbol = proxy_data.get(symbol_proxy, pd.DataFrame())
                    fig = render_daytrade_sparkline(
                        df_symbol, 
                        row['Abertura_Dt'], 
                        exit_dt, 
                        entry_px, 
                        exit_px, 
                        side
                    )
                    st.plotly_chart(fig, config={'displayModeBar': False}, use_container_width=True, key=f"dt_card_chart_{idx}")
                
                with col3:
                    st.write("**📊 Detalhes da Execução:**")
                    st.write(f"- **Preço Médio:** {row.get('Médio', 'N/A')}")
                    st.write(f"- **Resultado Bruto:** {row.get('Res. Intervalo Bruto', 'N/A')}")
                    res_val = row.get('Res_Numeric', 0)
                    res_color = "green" if res_val > 0 else "red" if res_val < 0 else "gray"
                    st.markdown(f"- **P/L Final:** :{res_color}[{row.get('Res. Operação', row.get('Res. Intervalo Bruto', 0))}]")
                    st.write(f"- **Tempo:** {row.get('Tempo Operação', 'N/A')}")

    # --- DATAFRAME ---
    target_cols = [
        'Ativo', 'Abertura', 'Fechamento', 'Tempo Operação', 
        'Pattern_View', 'Tipo de Ordem', # Manual Classifications
        'Qtd', 'Lado', # Combined
        'Preço Compra', 'Preço Venda', 'Preço de Mercado', 
        'MEP', 'MEN', 
        'Ag. Compra', 'Ag. Venda', 'Médio', 
        'Res. Intervalo Bruto', 'Res. Intervalo (%)', 
        'Número Operação', 'Res. Operação', 'Res. Operação (%)', 
        'Drawdown', 'Ganho Max.', 'Perda Max.', 'TET', 'Total'
    ]
    
    if not df.empty:
        df_show = df.copy()
        
        # Create Qtd Display Column
        def fmt_qtd(row):
            q = int(row.get('Qtd_Clean', 0))
            l = str(row.get('Lado', '')).strip()
            prefix = "-" if l == 'V' else ""
            return f"{prefix}{q} {l}"
        
        df_show['Qtd'] = df_show.apply(fmt_qtd, axis=1)
        
        # Ensure we have the list
        cols_to_show = [c for c in target_cols if c in df_show.columns]
        
        # Sort by Date desc
        df_show = df_show.sort_values('Abertura_Dt', ascending=False)
        
        # Styling
        s = df_show[cols_to_show].style
        
        # 1. Colors
        color_cols = [
            'MEP', 'MEN', 'Res. Intervalo Bruto', 'Res. Operação', 
            'Drawdown', 'Ganho Max.', 'Perda Max.', 'TET', 'Total', 'Res. Intervalo (%)', 'Res. Operação (%)'
        ]
        valid_color_cols = [c for c in color_cols if c in cols_to_show]
        
        def color_val(v):
            if st.session_state.get("hide_values", False): return ""
            if pd.isna(v) or v == '': return ''
            s_v = str(v).strip().replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
            try:
                val = float(s_v)
                if val == 0: return 'color: #888;' # Grey for zero
                return 'color: #00fa9a;' if val > 0 else 'color: #ff4d4d;'
            except:
                return ''
        
        s.map(color_val, subset=valid_color_cols)
        
        # 2. Qtd Styling
        def style_qtd(v):
            if pd.isna(v): return ''
            s_v = str(v)
            if 'V' in s_v: return 'color: #ff4d4d; font-weight: bold;' 
            if 'C' in s_v: return 'color: #00fa9a; font-weight: bold;'
            return ''
            
        if 'Qtd' in cols_to_show:
            s.map(style_qtd, subset=['Qtd'])

        # Masking the dataframe values
        for c in valid_color_cols:
            df_show[c] = df_show[c].apply(lambda x: mask_val(x))
        df_show['Ativo'] = df_show['Ativo'].apply(lambda x: mask_val(x, "text"))
        if 'Abertura' in df_show.columns:
            df_show['Abertura'] = df_show['Abertura'].apply(lambda x: mask_val(x, "time"))
        if 'Fechamento' in df_show.columns:
            df_show['Fechamento'] = df_show['Fechamento'].apply(lambda x: mask_val(x, "time"))

        st.dataframe(
            s,
            use_container_width=True,
            height=600
        )

def render_daytrade_sparkline(full_df, entry_dt, exit_dt, entry_px, exit_px, side):
    """Generates a 5m candlestick chart aligned with entry price, handling TZ gaps."""
    try:
        if full_df is None or full_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="Sem dados de mercado (5m)", showarrow=False, font=dict(size=10, color="gray"))
            return fig

        # --- TIMEZONE & SLICING LOGIC ---
        # 1. Normalize market data to naive local (BRT is typically UTC-3)
        # yfinance index usually comes in UTC
        working_df = full_df.copy()
        if working_df.index.tz is not None:
            # Convert to Brazil/Sao_Paulo then strip TZ to match Excel/CSV dates
            working_df.index = working_df.index.tz_convert('America/Sao_Paulo').tz_localize(None)
        
        # 2. Slice with a wider window to ensure we catch the data
        # Increase window to 2 hours before/after to be safe
        start_range = entry_dt - datetime.timedelta(hours=2)
        end_range = exit_dt + datetime.timedelta(hours=2)
        
        df = working_df.loc[start_range:end_range].copy()

        # 3. Fallback: If still empty, try to find the 20 closest candles to entry_dt
        if df.empty:
            iloc_idx = working_df.index.get_indexer([entry_dt], method='nearest')[0]
            start_iloc = max(0, iloc_idx - 10)
            end_iloc = min(len(working_df), iloc_idx + 10)
            df = working_df.iloc[start_iloc:end_iloc].copy()

        if df.empty:
            fig = go.Figure()
            fig.add_annotation(text="Aguardando dados intraday...", showarrow=False, font=dict(size=10, color="gray"))
            return fig
            
        # --- ALIGNMENT LOGIC ---
        try:
            closest_idx = df.index.get_indexer([entry_dt], method='nearest')[0]
            market_at_entry = df['Close'].iloc[closest_idx]
            offset = entry_px - market_at_entry
        except:
            offset = 0

        # Apply offset to all OHLC data
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = df[col] + offset
        
        df['EMA20'] = df['Close'].ewm(span=20, adjust=True).mean()
        
        color_up = '#00fa9a'
        color_down = '#ff4d4d'
        
        fig = go.Figure(data=[
            go.Candlestick(
                x=df.index,
                open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing=dict(line=dict(color=color_up), fillcolor=color_up),
                decreasing=dict(line=dict(color=color_down), fillcolor=color_down),
                whiskerwidth=0.3,
                name="Preço"
            )
        ])
        
        # Add EMA Segments
        for i in range(1, len(df)):
            seg_color = color_up if df['Close'].iloc[i] > df['EMA20'].iloc[i] else color_down
            fig.add_trace(go.Scatter(
                x=df.index[i-1:i+1], y=df['EMA20'].iloc[i-1:i+1],
                mode='lines', line=dict(color=seg_color, width=1.5), showlegend=False
            ))
            
        # --- ENTRY/EXIT MARKERS (Precision Arrows) ---
        # We use annotations to ensure the arrow tip points EXACTLY to the price.
        # side 'C': Entry is BUY (Arrow points UP), Exit is SELL (Arrow points DOWN)
        # side 'V': Entry is SELL (Arrow points DOWN), Exit is BUY (Arrow points UP)
        
        # Entry Arrow (Tiny horizontal)
        e_color = "#00fa9a" if side == 'C' else "#ff4d4d"
        
        fig.add_annotation(
            x=entry_dt, y=entry_px,
            text="", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5, arrowcolor=e_color,
            ax=-15, ay=0, axref='pixel', ayref='pixel', hovertext=f"Entrada: {entry_px:,.2f}"
        )
        
        # Exit Arrow (Tiny horizontal)
        ex_color = "#ffcc00"
        
        fig.add_annotation(
            x=exit_dt, y=exit_px,
            text="", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5, arrowcolor=ex_color,
            ax=15, ay=0, axref='pixel', ayref='pixel', hovertext=f"Saída: {exit_px:,.2f}"
        )
        
        # Connect with dashed line
        fig.add_trace(go.Scatter(
            x=[entry_dt, exit_dt], y=[entry_px, exit_px],
            mode='lines',
            line=dict(color="rgba(255,255,255,0.4)", width=1, dash="dot"),
            showlegend=False, hoverinfo='skip'
        ))
        
        # Dynamic Zoom
        y_min = min(df['Low'].min(), entry_px, exit_px) * 0.9997
        y_max = max(df['High'].max(), entry_px, exit_px) * 1.0003

        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(visible=False), 
            yaxis=dict(
                visible=True, showticklabels=True, tickfont=dict(size=8, color="gray"), side="right",
                range=[y_min, y_max]
            ),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis_rangeslider_visible=False, height=220
        )
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erro visual: {str(e)}", showarrow=False, font=dict(size=10, color="red"))
        return fig
