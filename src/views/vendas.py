# src/views/vendas.py
import streamlit as st
from datetime import datetime
from src.models import get_db, FormaPagamento
from src.controllers.venda import VendaController
from src.controllers.produto import ProdutoController


def inicializar_estado_venda():
    """Inicializa ou reseta o estado da venda atual"""
    if 'venda_atual' not in st.session_state:
        st.session_state.venda_atual = None
    if 'itens_venda' not in st.session_state:
        st.session_state.itens_venda = []
    if 'total_venda' not in st.session_state:
        st.session_state.total_venda = 0.0


def nova_venda():
    """Interface para criar uma nova venda"""
    st.subheader("Nova Venda")

    # Dados do cliente
    with st.form("form_cliente"):
        col1, col2 = st.columns(2)
        with col1:
            cliente_nome = st.text_input("Nome do Cliente")
        with col2:
            cliente_cpf = st.text_input("CPF (opcional)", key="cpf_cliente")

        if st.form_submit_button("Iniciar Venda"):
            if not cliente_nome:
                st.error("Nome do cliente é obrigatório")
                return

            try:
                db = next(get_db())
                venda_controller = VendaController(db)

                # Cria nova venda
                venda = venda_controller.iniciar_venda(
                    usuario_id=st.session_state.usuario_id,
                    cliente_nome=cliente_nome,
                    cliente_cpf=cliente_cpf
                )

                st.session_state.venda_atual = venda
                st.success("Venda iniciada com sucesso!")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao iniciar venda: {str(e)}")
            finally:
                db.close()


def adicionar_item():
    """Interface para adicionar itens à venda"""
    st.subheader("Adicionar Item")

    with st.form("form_item"):
        col1, col2, col3 = st.columns(3)

        with col1:
            referencia = st.text_input("Referência do Produto")
        with col2:
            tamanho = st.selectbox("Tamanho", ["P", "M", "G", "GG", "U"])
        with col3:
            quantidade = st.number_input("Quantidade", min_value=1, value=1)

        if st.form_submit_button("Adicionar Item"):
            try:
                db = next(get_db())
                venda_controller = VendaController(db)

                # Adiciona item usando FIFO
                itens = venda_controller.adicionar_item(
                    venda_id=st.session_state.venda_atual.id,
                    referencia=referencia,
                    tamanho=tamanho,
                    quantidade=quantidade,
                    usuario_id=st.session_state.usuario_id
                )

                if itens:
                    st.session_state.itens_venda.extend(itens)
                    st.success("Item adicionado com sucesso!")
                    # Atualiza total
                    st.session_state.total_venda = sum(
                        item.valor_total for item in st.session_state.itens_venda
                    )
                    st.rerun()

            except Exception as e:
                st.error(f"Erro ao adicionar item: {str(e)}")
            finally:
                db.close()


def mostrar_itens_venda():
    """Exibe os itens da venda atual"""
    if st.session_state.itens_venda:
        st.subheader("Itens da Venda")

        # Cria tabela de itens
        dados_tabela = []
        for item in st.session_state.itens_venda:
            dados_tabela.append({
                "Referência": item.produto.referencia,
                "Descrição": item.produto.descricao,
                "Tamanho": item.produto.tamanho,
                "Quantidade": item.quantidade,
                "Valor Unit.": f"R$ {float(item.valor_unitario):,.2f}",
                "Total": f"R$ {float(item.valor_total):,.2f}"
            })

        st.dataframe(
            dados_tabela,
            hide_index=True,
            use_container_width=True
        )

        # Mostra total
        st.markdown(f"**Total da Venda:** R$ {st.session_state.total_venda:,.2f}")


def finalizar_venda():
    """Interface para finalizar a venda"""
    st.subheader("Finalizar Venda")

    with st.form("form_finalizar"):
        forma_pagamento = st.selectbox(
            "Forma de Pagamento",
            options=[fp.value for fp in FormaPagamento]
        )

        if st.form_submit_button("Finalizar Venda"):
            try:
                db = next(get_db())
                venda_controller = VendaController(db)

                # Finaliza a venda
                venda = venda_controller.finalizar_venda(
                    venda_id=st.session_state.venda_atual.id,
                    forma_pagamento=FormaPagamento(forma_pagamento),
                    usuario_id=st.session_state.usuario_id
                )

                if venda:
                    st.success("Venda finalizada com sucesso!")
                    # Reset do estado
                    st.session_state.venda_atual = None
                    st.session_state.itens_venda = []
                    st.session_state.total_venda = 0.0
                    st.rerun()

            except Exception as e:
                st.error(f"Erro ao finalizar venda: {str(e)}")
            finally:
                db.close()


def consultar_vendas():
    """Interface para consultar vendas anteriores"""
    with st.expander("Consultar Vendas"):
        try:
            db = next(get_db())
            venda_controller = VendaController(db)

            col1, col2 = st.columns(2)
            with col1:
                data_inicio = st.date_input("Data Início")
            with col2:
                data_fim = st.date_input("Data Fim")

            if st.button("Consultar"):
                vendas = venda_controller.relatorio_vendas_periodo(
                    data_inicio=datetime.combine(data_inicio, datetime.min.time()),
                    data_fim=datetime.combine(data_fim, datetime.max.time())
                )

                if vendas:
                    st.dataframe(vendas, hide_index=True)
                else:
                    st.info("Nenhuma venda encontrada no período")

        except Exception as e:
            st.error(f"Erro ao consultar vendas: {str(e)}")
        finally:
            db.close()


def mostrar_pagina():
    """Exibe a página de vendas"""
    st.title("Vendas")

    # Inicializa estado
    inicializar_estado_venda()

    # Layout principal
    if not st.session_state.venda_atual:
        nova_venda()
        consultar_vendas()
    else:
        # Venda em andamento
        adicionar_item()
        mostrar_itens_venda()

        if st.session_state.itens_venda:
            finalizar_venda()

            # Botão para cancelar venda
            if st.button("Cancelar Venda", type="secondary"):
                st.session_state.venda_atual = None
                st.session_state.itens_venda = []
                st.session_state.total_venda = 0.0
                st.rerun()