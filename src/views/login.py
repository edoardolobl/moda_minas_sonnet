# src/views/login.py
import streamlit as st
from src.models import get_db
from src.controllers.auth import AuthController


def mostrar_pagina():
    """Exibe a página de login"""
    st.title("Sistema de Consignados")

    # Centraliza o formulário de login
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Login")

        # Formulário de login
        with st.form("login_form"):
            login = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")

            if submitted:
                if not login or not senha:
                    st.error("Por favor, preencha todos os campos")
                    return

                try:
                    # Tenta autenticar o usuário
                    db = next(get_db())
                    auth_controller = AuthController(db)
                    usuario = auth_controller.autenticar_usuario(login, senha)

                    if usuario:
                        # Atualiza o estado da sessão
                        st.session_state.autenticado = True
                        st.session_state.usuario_id = usuario.id
                        st.session_state.usuario_nome = usuario.nome
                        st.session_state.usuario_tipo = usuario.tipo.value
                        st.session_state.pagina_atual = 'dashboard'

                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos")

                except Exception as e:
                    st.error(f"Erro ao realizar login: {str(e)}")
                finally:
                    db.close()

        # Informações adicionais
        st.markdown("---")
        st.markdown("""
            Para suporte, entre em contato com o administrador do sistema.
        """)