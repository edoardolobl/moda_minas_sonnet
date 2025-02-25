import streamlit as st


def has_unsaved_entrada_produtos() -> bool:
    """Verifica se há dados não salvos na entrada de produtos"""
    if not hasattr(st.session_state, 'fornecedor_selecionado'):
        return False

    if not st.session_state.fornecedor_selecionado:
        return False

    if hasattr(st.session_state, 'nota_atual') and st.session_state.nota_atual:
        return True

    return False


def limpar_estado_entrada_produtos():
    """Limpa completamente os estados da entrada de produtos"""
    if hasattr(st.session_state, 'fornecedor_selecionado'):
        del st.session_state.fornecedor_selecionado
    if hasattr(st.session_state, 'nota_atual'):
        del st.session_state.nota_atual
    if hasattr(st.session_state, 'show_modal'):
        del st.session_state.show_modal
    if hasattr(st.session_state, 'target_page'):
        del st.session_state.target_page
    if hasattr(st.session_state, 'modal_action'):
        del st.session_state.modal_action