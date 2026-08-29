import streamlit as st
import json
import os


def render():
    st.title("Relatorios de Performance")
    st.markdown("---")

    reports_path = os.path.join("data", "relatorios.json")

    if not os.path.exists(reports_path):
        st.warning("Nenhum relatorio encontrado em data/relatorios.json.")
        return

    try:
        with open(reports_path, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar relatorios: {e}")
        return

    if not reports:
        st.info("A fileira de relatorios esta vazia.")
        return

    # Newest first; unique labels (id + title + date) avoid selectbox collisions
    reports_display = list(reversed(reports))
    options = []
    for i, r in enumerate(reports_display):
        rid = r.get("id", i)
        title = str(r.get("title", "Sem titulo")).strip()
        date = str(r.get("date", "")).strip()
        options.append(f"[{rid}] {title} ({date})")

    # Prefer current weekly report if present
    default_idx = 0
    for i, opt in enumerate(options):
        if "W32" in opt or "03/08 a 07/08" in opt:
            default_idx = i
            break

    q = st.text_input("Buscar relatorio", placeholder="Ex.: W32, semanal, julho...")
    filtered_idx = list(range(len(options)))
    if q.strip():
        q_low = q.strip().lower()
        filtered_idx = [i for i, opt in enumerate(options) if q_low in opt.lower()]
        if not filtered_idx:
            st.warning("Nenhum relatorio corresponde a busca.")
            return

    filtered_options = [options[i] for i in filtered_idx]
    # Keep W32 as default when visible
    try:
        select_default = filtered_options.index(options[default_idx])
    except ValueError:
        select_default = 0

    selected_option = st.selectbox(
        "Selecione o Relatorio:",
        filtered_options,
        index=min(select_default, len(filtered_options) - 1),
        key="relatorio_select",
    )
    selected_global_idx = options.index(selected_option)
    report = reports_display[selected_global_idx]

    st.markdown(f"### {report.get('title', '')}")
    st.caption(f"Data: {report.get('date', '')}")
    st.markdown("---")

    content = report.get("content") or "_Relatorio sem conteudo._"
    try:
        st.markdown(content)
    except Exception as e:
        st.error(f"Falha ao renderizar markdown: {e}")
        st.code(content, language="markdown")

    st.markdown("---")

    with st.expander("Exportar para Substack"):
        st.write("Copie o codigo abaixo e cole no seu post do Substack:")
        substack_md = f"""# {report.get('title', '')}
> Data: {report.get('date', '')}

{content}

---
*Analise gerada automaticamente pelo Dashboard de Performance.*
"""
        st.code(substack_md, language="markdown")

    st.info("Este relatorio e fixo e nao e afetado pelos filtros de data globais do dashboard.")
