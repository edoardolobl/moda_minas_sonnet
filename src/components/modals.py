import streamlit as st


def show_confirmation_modal(
        title: str,
        message: str,
        on_confirm: callable,
        on_cancel: callable = None,
        confirm_text: str = "✅ Sim, prosseguir",
        cancel_text: str = "❌ Não, continuar"
) -> bool:
    """
    Modal reutilizável para confirmações

    Args:
        title: Título do modal
        message: Mensagem principal
        on_confirm: Função a ser executada na confirmação
        on_cancel: Função a ser executada no cancelamento (opcional)
        confirm_text: Texto do botão de confirmação
        cancel_text: Texto do botão de cancelamento

    Returns:
        bool: True se confirmado, False se cancelado
    """

    # Estilo do modal
    st.markdown("""
        <style>
            .warning-modal {
                background-color: #262730;
                padding: 20px;
                border-radius: 10px;
                border: 1px solid #FF4B4B;
                margin: 10px 0;
            }
        </style>
    """, unsafe_allow_html=True)

    # Layout do modal com colunas para centralização
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
            <div class="warning-modal">
                <h2>⚠️ {title}</h2>
                <p>{message}</p>
            </div>
        """, unsafe_allow_html=True)

        # Botões de ação
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button(confirm_text, type="primary", use_container_width=True):
                if on_confirm:
                    on_confirm()
                return True

        with col_btn2:
            if st.button(cancel_text, type="secondary", use_container_width=True):
                if on_cancel:
                    on_cancel()
                return False

    return False