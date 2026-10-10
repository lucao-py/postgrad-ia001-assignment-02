"""Detecta apenas a mudança entre layout compacto e amplo por sessão."""

import streamlit as st


_viewport = st.components.v2.component(
    "dashboard_viewport",
    js="""
    export default function({setStateValue}) {
        const media = window.matchMedia("(max-width: 1023px)");
        const update = () => setStateValue("compact", media.matches);
        update();
        media.addEventListener("change", update);
        return () => media.removeEventListener("change", update);
    }
    """,
)


def tela_compacta():
    # O primeiro desenho já cabe no celular; só há rerun ao cruzar o breakpoint.
    with st.container(key="viewport"):
        result = _viewport(
            key="dashboard_viewport", height=0,
            default={"compact": True}, on_compact_change=lambda: None,
        )
    return result.compact
