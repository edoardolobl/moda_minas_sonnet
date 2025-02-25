# src/views/devolucoes.py
import streamlit as st
from datetime import datetime
from src.models import get_db
from src.controllers.nota_entrada import NotaEntradaController
from src.controllers.produto import ProdutoController
from src.controllers.fornecedor import FornecedorController


def selecionar_fornecedor():
    """Interface para seleção do fornecedor"""
    try:
        db = next(get_db())
        fornecedor_controller = FornecedorController(db)

        fornecedores = fornecedor_controller.listar_fornecedores()
        if not fornecedores:
            st.warning("Nenhum fornecedor cadastrado")
            return None

        fornecedor = st.selectbox(
            "Selecione o Fornecedor",
            options=[(f.id, f.nome) for f in fornecedores],
            format_func=lambda x: x[1]
        )

        return fornecedor[0] if fornecedor else None

    except Exception as e:
        st.error(f"Erro ao carregar fornecedores: {str(e)}")
        return None
    finally:
        db.close()


def listar_notas_devolucao(fornecedor_id: int):
    """Lista notas disponíveis para devolução"""
    try:
        db = next(get_db())
        nota_controller = NotaEntradaController(db)

        notas = nota_controller.buscar_notas_para_devolucao(fornecedor_id)
        if not notas:
            st.info("Não há notas disponíveis para devolução")
            return None

        nota_selecionada = st.selectbox(
            "Selecione a Nota de Entrada",
            options=[(n.id, f"{n.numero_nota} - {n.data_emissao.strftime('%d/%m/%Y')}")
                     for n in notas],
            format_func=lambda x: x[1]
        )

        return nota_selecionada[0] if nota_selecionada else None

    except Exception as e:
        st.error(f"Erro ao carregar notas: {str(e)}")
        return None
    finally:
        db.close()


def mostrar_produtos_nota(nota_id: int):
    """Mostra produtos disponíveis para devolução de uma nota"""
    try:
        db = next(get_db())
        produto_controller = ProdutoController(db)

        # Prepara lista de produtos para devolução
        produtos = produto_controller.preparar_devolucao(nota_id)

        if not produtos:
            st.warning("Não há produtos disponíveis para devolução nesta nota")
            return None

        st.subheader("Produtos Disponíveis para Devolução")

        # Lista de produtos para devolução
        produtos_devolver = []
        for produto in produtos:
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"""
                    **{produto['referencia']} - {produto['descricao']}**  
                    Tamanho: {produto['tamanho']} | 
                    Disponível: {produto['quantidade_disponivel']} | 
                    Valor: R$ {produto['valor_unitario']:.2f}
                """)

            with col2:
                qtd_devolver = st.number_input(
                    "Quantidade",
                    min_value=0,
                    max_value=produto['quantidade_disponivel'],
                    value=0,
                    key=f"qtd_{produto['produto_id']}"
                )

                if qtd_devolver > 0:
                    produtos_devolver.append({
                        'produto_id': produto['produto_id'],
                        'quantidade': qtd_devolver,
                        'referencia': produto['referencia'],
                        'descricao': produto['descricao'],
                        'valor_unitario': produto['valor_unitario']
                    })

        return produtos_devolver if produtos_devolver else None

    except Exception as e:
        st.error(f"Erro ao carregar produtos: {str(e)}")
        return None
    finally:
        db.close()


def processar_devolucao(nota_id: int, produtos: list):
    """Processa a devolução dos produtos selecionados"""
    try:
        db = next(get_db())
        produto_controller = ProdutoController(db)

        # Calcula totais para o resumo
        total_pecas = sum(p['quantidade'] for p in produtos)
        total_valor = sum(p['quantidade'] * p['valor_unitario'] for p in produtos)

        # Mostra resumo da devolução
        st.subheader("Resumo da Devolução")
        st.write(f"Total de Peças: {total_pecas}")
        st.write(f"Valor Total: R$ {total_valor:.2f}")

        # Lista itens
        st.write("Itens para devolução:")
        for item in produtos:
            st.write(f"""
                - {item['referencia']} - {item['descricao']}  
                  Quantidade: {item['quantidade']} | 
                  Valor Unit.: R$ {item['valor_unitario']:.2f} | 
                  Total: R$ {item['quantidade'] * item['valor_unitario']:.2f}
            """)

        if st.button("Confirmar Devolução"):
            # Processa a devolução
            if produto_controller.processar_devolucao(produtos, st.session_state.usuario_id):
                st.success("Devolução processada com sucesso!")

                # Gera protocolo de devolução
                protocolo = f"""
                PROTOCOLO DE DEVOLUÇÃO
                Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                Nota: {nota_id}
                Total de Peças: {total_pecas}
                Valor Total: R$ {total_valor:.2f}

                Itens Devolvidos:
                """

                for item in produtos:
                    protocolo += f"""
                    - {item['referencia']} - {item['descricao']}
                      Quantidade: {item['quantidade']}
                      Valor Unit.: R$ {item['valor_unitario']:.2f}
                      Total: R$ {item['quantidade'] * item['valor_unitario']:.2f}
                    """

                # Oferece download do protocolo
                st.download_button(
                    label="📥 Download Protocolo",
                    data=protocolo,
                    file_name=f"protocolo_devolucao_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )

                # Limpa estado para nova devolução
                st.session_state.nota_selecionada = None
                st.session_state.produtos_devolucao = None
                return True

        return False

    except Exception as e:
        st.error(f"Erro ao processar devolução: {str(e)}")
        return False
    finally:
        db.close()


def mostrar_pagina():
    """Exibe a página de devoluções"""
    st.title("Devoluções")

    # Verifica permissão
    if st.session_state.usuario_tipo != 'master':
        st.error("Acesso não autorizado")
        return

    # Inicializa estados
    if 'nota_selecionada' not in st.session_state:
        st.session_state.nota_selecionada = None
    if 'produtos_devolucao' not in st.session_state:
        st.session_state.produtos_devolucao = None

    # Fluxo de devolução
    fornecedor_id = selecionar_fornecedor()

    if fornecedor_id:
        if not st.session_state.nota_selecionada:
            nota_id = listar_notas_devolucao(fornecedor_id)
            if nota_id:
                st.session_state.nota_selecionada = nota_id
                st.rerun()

        if st.session_state.nota_selecionada and not st.session_state.produtos_devolucao:
            produtos = mostrar_produtos_nota(st.session_state.nota_selecionada)
            if produtos:
                st.session_state.produtos_devolucao = produtos
                st.rerun()

        if st.session_state.produtos_devolucao:
            if processar_devolucao(
                    st.session_state.nota_selecionada,
                    st.session_state.produtos_devolucao
            ):
                st.rerun()