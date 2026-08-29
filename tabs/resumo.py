import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from utils.components import glass_card, section_header, status_badge

def render(df, metrics, mask_val):
    if df.empty:
        st.info("Sem dados para exibir no momento.")
        return

    # Unpack metrics
    total_pnl = metrics['total_pnl']
    gross_profit = metrics['gross_profit']
    gross_loss = metrics['gross_loss']
    num_trades = metrics['num_trades']
    win_rate = metrics['win_rate']
    profit_factor = metrics['profit_factor']
    avg_pnl = metrics['avg_pnl']
    avg_win = metrics['avg_win']
    avg_loss = metrics['avg_loss']
    payoff = metrics['payoff']
    max_win = metrics['max_win']
    max_loss = metrics['max_loss']
    max_w_streak = metrics['max_w_streak']
    max_l_streak = metrics['max_l_streak']
    max_dd = metrics['max_dd']

    # --- MONTHLY PROFIT GAUGE DATA ---
    today = datetime.date.today()
    this_month_mask = (df['Date'].apply(lambda x: x.year) == today.year) & (df['Date'].apply(lambda x: x.month) == today.month)
    df_month = df[this_month_mask]
    
    monthly_net = df_month['Res_Numeric'].sum()
    monthly_gross = df_month[df_month['Res_Numeric'] > 0]['Res_Numeric'].sum()

    # --- TAB: RESUMO (Premium Glassmorphism Layout) ---
    section_header("Visão Geral", icon="📈")

    # Top Headline Stats
    h1, h2, h3 = st.columns([1, 1, 1])
    with h2: 
        lbl_col = "profit-val" if total_pnl >= 0 else "loss-val"
        display_pnl = mask_val(total_pnl)
        if isinstance(display_pnl, (int, float)):
            display_pnl = f"R$ {display_pnl:,.2f}"
            
        st.markdown(glass_card(
            "Resultado Total", 
            display_pnl, 
            label_class=lbl_col,
            extra_style="text-align: center; font-size: 2.2em;"
        ), unsafe_allow_html=True)

    # Monthly Gauge Row
    st.markdown("---")
    g1, g2, g3 = st.columns([1, 2, 1])
    with g2:
        if not df_month.empty:
            # Masking for gauge
            display_net = mask_val(monthly_net)
            display_title = "Lucro Real vs Rendimento (Mês)" if not st.session_state["hide_values"] else "Performance Mensal"
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = monthly_net if not st.session_state["hide_values"] else 0,
                title = {'text': display_title, 'font': {'size': 18, 'color': '#00aaff'}},
                number = {'prefix': "R$ ", 'font': {'size': 20}, 'valueformat': ",.2f"} if not st.session_state["hide_values"] else {'valueformat': ""},
                gauge = {
                    'axis': {'range': [None, max(monthly_gross, 2000)], 'tickwidth': 1, 'tickcolor': "#444"},
                    'bar': {'color': "#00fa9a" if monthly_net >= 0 else "#ff4d4d"},
                    'bgcolor': "#1e1e1e",
                    'borderwidth': 2,
                    'bordercolor': "#444",
                    'steps': [
                        {'range': [0, monthly_gross], 'color': 'rgba(0, 250, 154, 0.1)'}
                    ],
                    'threshold': {
                        'line': {'color': "white", 'width': 4},
                        'thickness': 0.75,
                        'value': monthly_gross
                    }
                }
            ))
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font={'color': "white", 'family': "Arial"},
                height=250,
                margin=dict(l=20, r=20, t=50, b=20)
            )
            
            if st.session_state["hide_values"]:
                fig.add_annotation(text="VALORES OCULTOS", x=0.5, y=0.4, showarrow=False, font=dict(size=20, color="gray"))

            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Aguardando operações este mês para o medidor.")

    st.markdown("---")

    # Grid Layout Section
    section_header("Estatísticas Detalhadas", icon="📊")
    
    def grid_row(label, value, value_class="", extra_style=""):
        return f"""
        <div class='grid-row'>
            <span class='grid-label'>{label}</span>
            <span class='grid-value {value_class}' style='{extra_style}'>{mask_val(value) if "R$" in str(value) else value}</span>
        </div>
        """

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<div class='grid-header' style='font-size: 1.1em; color: #00aaff; border-bottom: 2px solid #00aaff; padding-bottom: 5px; margin-bottom: 15px;'>Estatísticas Principais</div>", unsafe_allow_html=True)
        st.markdown(grid_row("Lucro Bruto", f"R$ {gross_profit:,.2f}", "profit-val"), unsafe_allow_html=True)
        st.markdown(grid_row("Prejuízo Bruto", f"R$ {gross_loss:,.2f}", "loss-val"), unsafe_allow_html=True)
        st.markdown(grid_row("Fator de Lucro", f"{profit_factor:.2f}"), unsafe_allow_html=True)
        st.markdown(grid_row("Total de Trades", f"{num_trades}"), unsafe_allow_html=True)
        st.markdown(grid_row("Taxa de Acerto", f"{win_rate:.2f}%", "profit-val", extra_style="color:#00fa9a !important;"), unsafe_allow_html=True)
        
        # Gestão Matemática Insight
        if win_rate > 0:
            min_payoff = (100 - win_rate) / win_rate
            st.markdown(f"""
            <div style="background: rgba(0, 250, 154, 0.05); border: 1px solid rgba(0, 250, 154, 0.1); border-radius: 4px; padding: 12px; margin-top: 15px;">
                <div style="color: #00fa9a; font-size: 0.8em; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; letter-spacing: 0.5px;">Gestão Matemática</div>
                <div style="color: #ccc; font-size: 0.9em; line-height: 1.4;">
                    Para sua taxa de <b>{win_rate:.1f}%</b>, o Payoff mínimo é de <b>{min_payoff:.2f}x</b>.<br><br>
                    <span style="color: #888; font-size: 0.85em;">Benchmarks de Sobrevivência:</span><br>
                    • Alvos <b>2:1</b> exigem <b>33.3%</b> de acerto.<br>
                    • Alvos <b>3:1</b> exigem <b>25.0%</b> de acerto.
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<div class='grid-header' style='font-size: 1.1em; color: #00aaff; border-bottom: 2px solid #00aaff; padding-bottom: 5px; margin-bottom: 15px;'>Médias</div>", unsafe_allow_html=True)
        st.markdown(grid_row("Média Lucro/Prejuízo", f"R$ {avg_pnl:,.2f}", "profit-val" if avg_pnl > 0 else "loss-val"), unsafe_allow_html=True)
        st.markdown(grid_row("Média de Ganho", f"R$ {avg_win:,.2f}", "profit-val"), unsafe_allow_html=True)
        st.markdown(grid_row("Média de Perda", f"R$ {avg_loss:,.2f}", "loss-val"), unsafe_allow_html=True)
        st.markdown(grid_row("Payoff", f"{payoff:.2f}"), unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<div class='grid-header' style='font-size: 1.1em; color: #00aaff; border-bottom: 2px solid #00aaff; padding-bottom: 5px; margin-bottom: 15px;'>Extremos</div>", unsafe_allow_html=True)
        st.markdown(grid_row("Maior Ganho", f"R$ {max_win:,.2f}", "profit-val"), unsafe_allow_html=True)
        st.markdown(grid_row("Maior Perda", f"R$ {max_loss:,.2f}", "loss-val"), unsafe_allow_html=True)
        st.markdown(grid_row("Drawdown Máximo", f"R$ {max_dd:,.2f}", "loss-val"), unsafe_allow_html=True)
        st.markdown(grid_row("Seq. Vencedora", f"{max_w_streak}", "profit-val"), unsafe_allow_html=True)
        st.markdown(grid_row("Seq. Perdedora", f"{max_l_streak}", "loss-val"), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<div class='grid-header' style='font-size: 1.1em; color: #ffaa00; border-bottom: 2px solid #ffaa00; padding-bottom: 5px; margin-bottom: 15px;'>Monitor Comportamental</div>", unsafe_allow_html=True)
        
        # New Metrics
        num_violinadas = metrics.get('num_violinadas', 0)
        potencial_perdido = metrics.get('potencial_perdido', 0)
        streak = metrics.get('discipline_streak', 0)

        st.markdown(grid_row("Violinadas no BE", f"{num_violinadas}", "loss-val" if num_violinadas > 0 else ""), unsafe_allow_html=True)
        st.markdown(grid_row("Lucro Deixado (BE)", f"R$ {potencial_perdido:,.2f}", "loss-val" if potencial_perdido > 0 else ""), unsafe_allow_html=True)
        st.markdown(grid_row("Trades sem Fading", f"{streak} 🔥", "profit-val" if streak > 5 else ""), unsafe_allow_html=True)
        
        if num_violinadas > 0:
            st.markdown(f"""
            <div style="background: rgba(255, 170, 0, 0.05); border: 1px solid rgba(255, 170, 0, 0.1); border-radius: 4px; padding: 10px; margin-top: 10px;">
                <div style="color: #ffaa00; font-size: 0.75em; font-weight: bold; text-transform: uppercase; margin-bottom: 3px;">Alerta de Gestão</div>
                <div style="color: #ccc; font-size: 0.85em; line-height: 1.3;">
                    Você foi tirado de <b>{num_violinadas}</b> trades no zero que acabaram pagando o alvo. 
                    Isso custou <b>R$ {potencial_perdido:,.2f}</b> teóricos.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # --- PROJETO 5M CONSOLIDADO (era 1R=1000 / jun–ago 2026) ---
    import os
    import json

    p5_path = os.path.join("data", "projeto_5m_resumo.json")
    if os.path.exists(p5_path):
        try:
            with open(p5_path, "r", encoding="utf-8") as f:
                p5 = json.load(f)
            h = p5.get("headline", {})
            d = p5.get("direction", {})
            td = p5.get("tipo_labeled", {})
            hr = p5.get("horario", {})
            proto = p5.get("protocolo", {})
            as_of = p5.get("as_of", "")

            st.markdown("---")
            section_header("Projeto 5M — Consolidado", icon="🎯")
            st.caption(
                f"Atualizado em {as_of} · {p5.get('era', '')} · "
                "fonte: OPERAÇÕES_DAY_TRADE + sim 2:1 (N=Sim intacto)"
            )

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(
                    glass_card("Realizado (era)", f"{h.get('realizado_r', 0):+.1f}R",
                               label_class="loss-val" if h.get("realizado_r", 0) < 0 else "profit-val"),
                    unsafe_allow_html=True,
                )
            with k2:
                st.markdown(
                    glass_card("Se OCO 2:1", f"{h.get('sim_2r_r', 0):+.0f}R", label_class="profit-val"),
                    unsafe_allow_html=True,
                )
            with k3:
                st.markdown(
                    glass_card("Gap (mão de alface)", f"+{h.get('gap_r', 0):.0f}R", label_class="loss-val"),
                    unsafe_allow_html=True,
                )
            with k4:
                st.markdown(
                    glass_card("W32 real / sim", f"{h.get('w32_real_r', 0):+.1f}R / +{h.get('w32_sim_r', 0):.0f}R"),
                    unsafe_allow_html=True,
                )

            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown(
                    "<div class='grid-header' style='font-size: 1.05em; color: #00aaff; "
                    "border-bottom: 2px solid #00aaff; padding-bottom: 5px; margin-bottom: 12px;'>"
                    "Expectancy & WR</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    grid_row("WR realizado", f"{h.get('wr_realizado_pct', 0):.1f}%"),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    grid_row("WR sim decisivas", f"{h.get('wr_sim_decisivas_pct', 0):.1f}%", "profit-val"),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    grid_row("E[R] realizado", f"{h.get('e_r_realizado', 0):+.2f}R", "loss-val"),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    grid_row("E[R] sim 2:1", f"{h.get('e_r_sim', 0):+.2f}R", "profit-val"),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    grid_row("BE WR @ 2:1", f"{h.get('be_wr_2r_pct', 33.3):.1f}%"),
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

            with m2:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown(
                    "<div class='grid-header' style='font-size: 1.05em; color: #00aaff; "
                    "border-bottom: 2px solid #00aaff; padding-bottom: 5px; margin-bottom: 12px;'>"
                    "Direção vs Setup Real</div>",
                    unsafe_allow_html=True,
                )
                cr = d.get("com_real", {})
                ctr = d.get("contra_real", {})
                soft = d.get("soft_ok_bo_canal", {})
                st.markdown(
                    grid_row(
                        "COM Real (viés)",
                        f"{cr.get('pnl_r', 0):+.1f}R · WR {cr.get('wr_pct', 0):.0f}% · n={cr.get('n', 0)}",
                        "profit-val",
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    grid_row(
                        "CONTRA Real",
                        f"{ctr.get('pnl_r', 0):+.1f}R · WR {ctr.get('wr_pct', 0):.0f}% · n={ctr.get('n', 0)}",
                        "loss-val",
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    grid_row(
                        "BO≈Canal (mesmo viés)",
                        f"{soft.get('pnl_r', 0):+.1f}R · WR {soft.get('wr_pct', 0):.0f}%",
                        "profit-val",
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='color:#888;font-size:0.8em;margin-top:8px;line-height:1.35;'>"
                    f"{d.get('note', '')}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

            with m3:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown(
                    "<div class='grid-header' style='font-size: 1.05em; color: #00aaff; "
                    "border-bottom: 2px solid #00aaff; padding-bottom: 5px; margin-bottom: 12px;'>"
                    "Tipo A–D (rotulados)</div>",
                    unsafe_allow_html=True,
                )
                for t in ("A", "B", "C", "D"):
                    info = td.get(t, {})
                    cls = "profit-val" if info.get("pnl_r", 0) > 0 else ("loss-val" if info.get("pnl_r", 0) < 0 else "")
                    st.markdown(
                        grid_row(
                            f"Tipo {t}",
                            f"{info.get('pnl_r', 0):+.1f}R · n={info.get('n', 0)}",
                            cls,
                        ),
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f"<div style='color:#888;font-size:0.8em;margin-top:8px;'>{td.get('note', '')}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

            p1, p2 = st.columns(2)
            with p1:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown(
                    "<div class='grid-header' style='font-size: 1.05em; color: #ffaa00; "
                    "border-bottom: 2px solid #ffaa00; padding-bottom: 5px; margin-bottom: 12px;'>"
                    "Protocolo & horário</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    grid_row("OCO", proto.get("oco", "−1R / +2R")),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    grid_row("Dia / Semana", f"{proto.get('r_day', -2)}R dia · piso {proto.get('r_week_floor', -4)}R · alvo +{proto.get('r_week_target', 5)}R"),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='color:#ccc;font-size:0.9em;line-height:1.4;margin-top:8px;'>"
                    f"<b>Horário:</b> {hr.get('insight', '')}<br>"
                    f"<span style='color:#888'>{hr.get('note', '')}</span></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

            with p2:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown(
                    "<div class='grid-header' style='font-size: 1.05em; color: #00fa9a; "
                    "border-bottom: 2px solid #00fa9a; padding-bottom: 5px; margin-bottom: 12px;'>"
                    "Plano — próximas semanas</div>",
                    unsafe_allow_html=True,
                )
                weeks = p5.get("plano_proximas_semanas", [])
                bullets = "".join(f"<li style='margin-bottom:6px;'>{x}</li>" for x in weeks)
                st.markdown(
                    f"<ul style='color:#ccc;font-size:0.9em;line-height:1.35;padding-left:18px;margin:0;'>{bullets}</ul>",
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("Plano — próximos meses"):
                months = p5.get("plano_proximos_meses", [])
                for x in months:
                    st.markdown(f"- {x}")
                errs = p5.get("tipo_d_patterns", {}).get("main_errors", [])
                if errs:
                    st.markdown("**Erros Tipo D (evitar):**")
                    for e in errs:
                        st.markdown(f"- {e}")
        except Exception as e:
            st.caption(f"Projeto 5M consolidado indisponível: {e}")

    # --- LATEST REPORT HIGHLIGHT ---
    reports_path = os.path.join("data", "relatorios.json")
    if os.path.exists(reports_path):
        try:
            with open(reports_path, 'r', encoding='utf-8') as f:
                reports = json.load(f)
            if reports:
                latest = reports[-1]
                st.markdown("---")
                c_rep1, c_rep2 = st.columns([7, 3])
                with c_rep1:
                    st.subheader(f"📑 Último Relatório: {latest['title']}")
                    st.caption(f"Publicado em: {latest['date']}")
                with c_rep2:
                    if st.button("Ler Relatório Completo 📝", use_container_width=True):
                        st.session_state.selected_main_tab = "📝 Relatórios"
                        st.rerun()
                
                # Show first few lines of content in an expander or block
                preview = latest['content'].split('\n')[:5]
                st.markdown('\n'.join(preview) + "...")
        except:
            pass
