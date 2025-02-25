# main.py
import streamlit as st
from src.models import get_db
from src.controllers.auth import AuthController
from src.views import login, dashboard, vendas, estoque, fornecedores, relatorios, devolucoes, entrada_produtos
from src.components.modals import show_confirmation_modal
from src.utils.state_handlers import has_unsaved_entrada_produtos, limpar_estado_entrada_produtos


def configurar_pagina():
    """Configura as características básicas da página"""
    st.set_page_config(
        page_title="Sistema de Consignados",
        page_icon="👕",
        layout="wide",
        initial_sidebar_state="expanded"
    )


def inicializar_estado():
    """Inicializa variáveis de estado da sessão"""
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    if 'usuario_id' not in st.session_state:
        st.session_state.usuario_id = None
    if 'usuario_nome' not in st.session_state:
        st.session_state.usuario_nome = None
    if 'usuario_tipo' not in st.session_state:
        st.session_state.usuario_tipo = None
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = 'login'


def mostrar_menu():
    """Exibe o menu de navegação lateral"""
    # Controle do modal
    if 'show_modal' not in st.session_state:
        st.session_state.show_modal = False
    if 'target_page' not in st.session_state:
        st.session_state.target_page = None
    if 'modal_action' not in st.session_state:
        st.session_state.modal_action = None

    with st.sidebar:
        st.title("Menu Principal")
        st.markdown(f"Bem-vindo, {st.session_state.usuario_nome}!")

        # Menu principal
        menu_options = {
            "Dashboard": "dashboard",
            "Fornecedores": "fornecedores",
            "Entrada de Produtos": "entrada_produtos",
            "Estoque": "estoque",
            "Vendas": "vendas"
        }

        # Opções adicionais para usuário master
        if st.session_state.usuario_tipo == 'master':
            menu_options.update({
                "Devoluções": "devolucoes",
                "Relatórios": "relatorios",
                "Usuários": "usuarios"
            })

        for nome, pagina in menu_options.items():
            if st.sidebar.button(nome):
                # Verifica se está saindo da página de entrada de produtos
                if (st.session_state.pagina_atual == 'entrada_produtos' and
                        pagina != 'entrada_produtos' and
                        has_unsaved_entrada_produtos()):
                    st.session_state.show_modal = True
                    st.session_state.target_page = pagina
                    st.session_state.modal_action = 'navigate'
                    st.rerun()
                else:
                    # Se está indo para entrada de produtos, garante estado limpo
                    if pagina == 'entrada_produtos':
                        limpar_estado_entrada_produtos()
                    st.session_state.pagina_atual = pagina
                    st.rerun()

        # Botão de logout
        if st.sidebar.button("Sair"):
            if (st.session_state.pagina_atual == 'entrada_produtos' and
                    has_unsaved_entrada_produtos()):
                st.session_state.show_modal = True
                st.session_state.target_page = 'logout'
                st.session_state.modal_action = 'logout'
                st.rerun()
            else:
                st.session_state.autenticado = False
                st.session_state.usuario_id = None
                st.session_state.usuario_nome = None
                st.session_state.usuario_tipo = None
                st.session_state.pagina_atual = 'login'
                limpar_estado_entrada_produtos()
                st.rerun()

    # Modal fora do sidebar
    if st.session_state.show_modal:
        def on_confirm():
            if st.session_state.modal_action == 'logout':
                st.session_state.autenticado = False
                st.session_state.usuario_id = None
                st.session_state.usuario_nome = None
                st.session_state.usuario_tipo = None
                st.session_state.pagina_atual = 'login'
            else:
                st.session_state.pagina_atual = st.session_state.target_page

            limpar_estado_entrada_produtos()
            st.session_state.show_modal = False
            st.session_state.target_page = None
            st.session_state.modal_action = None
            st.rerun()

        def on_cancel():
            st.session_state.show_modal = False
            st.session_state.target_page = None
            st.session_state.modal_action = None
            st.rerun()

        result = show_confirmation_modal(
            "Atenção!",
            "Existem dados não salvos. Se sair agora, todas as informações serão perdidas.",
            on_confirm=on_confirm,
            on_cancel=on_cancel
        )


def main():
    """Função principal do aplicativo"""
    configurar_pagina()
    inicializar_estado()

    # Roteamento básico
    if not st.session_state.autenticado:
        login.mostrar_pagina()
    else:
        mostrar_menu()

        # Roteamento das páginas
        if st.session_state.pagina_atual == 'dashboard':
            dashboard.mostrar_pagina()
        elif st.session_state.pagina_atual == 'vendas':
            vendas.mostrar_pagina()
        elif st.session_state.pagina_atual == 'estoque':
            estoque.mostrar_pagina()
        elif st.session_state.pagina_atual == 'fornecedores':
            fornecedores.mostrar_pagina()
        elif st.session_state.pagina_atual == 'relatorios':
            relatorios.mostrar_pagina()
        elif st.session_state.pagina_atual == 'devolucoes':
            devolucoes.mostrar_pagina()
        elif st.session_state.pagina_atual == 'entrada_produtos':
            entrada_produtos.mostrar_pagina()


if __name__ == "__main__":
    main()