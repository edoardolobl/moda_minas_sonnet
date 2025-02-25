# src/views/fornecedores.py
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from src.models import get_db
from src.controllers.fornecedor import FornecedorController
from src.controllers.nota_entrada import NotaEntradaController
from src.utils.pdf_generator import gerar_pdf_nota
import time


def mostrar_resumo_fornecedores():
    """Mostra cards com resumo dos fornecedores"""
    try:
        db = next(get_db())
        fornecedor_controller = FornecedorController(db)

        fornecedores = fornecedor_controller.listar_fornecedores(apenas_ativos=False)  # Mudança aqui
        total_fornecedores = len(fornecedores)
        fornecedores_ativos = len([f for f in fornecedores if f.ativo])

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
                <div style='padding: 1rem; border-radius: 0.5rem; border: 1px solid #e0e0e0;'>
                    <h3 style='margin: 0; font-size: 1rem; color: #666;'>Total de Fornecedores</h3>
                    <p style='margin: 0; font-size: 1.5rem; font-weight: bold;'>{}</p>
                    <p style='margin: 0; color: #666;'>cadastrados no sistema</p>
                </div>
            """.format(total_fornecedores), unsafe_allow_html=True)

        with col2:
            st.markdown("""
                <div style='padding: 1rem; border-radius: 0.5rem; border: 1px solid #e0e0e0;'>
                    <h3 style='margin: 0; font-size: 1rem; color: #666;'>Fornecedores Ativos</h3>
                    <p style='margin: 0; font-size: 1.5rem; font-weight: bold;'>{}</p>
                    <p style='margin: 0; color: #666;'>em operação</p>
                </div>
            """.format(fornecedores_ativos), unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erro ao carregar resumo: {str(e)}")
    finally:
        db.close()


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ com máscara"""
    cnpj = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj


def cadastrar_fornecedor():
    """Interface para cadastro de fornecedor"""
    st.markdown("### 📝 Novo Fornecedor")

    with st.form("form_fornecedor", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome do Fornecedor")
            cnpj = st.text_input("CNPJ", help="Digite apenas números")
            if cnpj:
                cnpj = formatar_cnpj(cnpj)
                st.text(f"CNPJ formatado: {cnpj}")

        with col2:
            telefone = st.text_input("Telefone")
            email = st.text_input("E-mail")

        submitted = st.form_submit_button("Cadastrar", use_container_width=True)

        if submitted:
            if not nome or not cnpj:
                st.error("Nome e CNPJ são obrigatórios")
                return

            try:
                db = next(get_db())
                fornecedor_controller = FornecedorController(db)

                if not fornecedor_controller.validar_cnpj(cnpj):
                    st.error("CNPJ inválido")
                    return

                fornecedor = fornecedor_controller.criar_fornecedor(
                    nome=nome,
                    cnpj=cnpj,
                    telefone=telefone,
                    email=email,
                    usuario_id=st.session_state.usuario_id
                )

                if fornecedor:
                    st.success("✅ Fornecedor cadastrado com sucesso!")
                    time.sleep(1)  # Pequena pausa para o usuário ver a mensagem
                    st.rerun()  # Recarrega a página para mostrar a lista atualizada
                    return True

            except Exception as e:
                st.error(f"Erro ao cadastrar fornecedor: {str(e)}")
            finally:
                db.close()

            return False


def listar_fornecedores():
    """Lista fornecedores com linhas customizadas"""
    try:
        db = next(get_db())
        fornecedor_controller = FornecedorController(db)

        # Filtros
        col1, col2 = st.columns([3, 1])
        with col1:
            busca = st.text_input("🔍 Buscar fornecedor", placeholder="Nome ou CNPJ...")
        with col2:
            mostrar_inativos = st.checkbox("Mostrar inativos", key="show_inactive")

        # Busca todos os fornecedores
        fornecedores = fornecedor_controller.listar_fornecedores(apenas_ativos=False)

        if fornecedores:
            # Aplica filtros
            if not mostrar_inativos:
                fornecedores = [f for f in fornecedores if f.ativo]
            if busca:
                fornecedores = [f for f in fornecedores if
                                busca.lower() in f.nome.lower() or
                                busca in f.cnpj]

            # Cabeçalho
            st.markdown("---")
            header = st.columns([1, 3, 2.5, 2, 2.5, 1])
            header[0].write("Status")
            header[1].write("Nome")
            header[2].write("CNPJ")
            header[3].write("Telefone")
            header[4].write("Email")
            header[5].write("Ação")
            st.markdown("---")

            # Lista de fornecedores
            for f in fornecedores:
                cols = st.columns([1, 3, 2.5, 2, 2.5, 1])

                # Status com tooltip
                status_emoji = "🟢" if f.ativo else "🔴"
                status_text = "Ativo" if f.ativo else "Inativo"
                cols[0].markdown(f"""
                    <div title="{status_text}">{status_emoji}</div>
                """, unsafe_allow_html=True)

                # Dados
                cols[1].write(f.nome)
                cols[2].write(formatar_cnpj(f.cnpj))
                cols[3].write(f.telefone or "-")
                cols[4].write(f.email or "-")

                # Botão de ação com confirmação
                acao = "Desativar" if f.ativo else "Ativar"
                icone = "❌" if f.ativo else "✅"
                if cols[5].button(
                        icone,
                        key=f"btn_{f.id}",
                        help=f"Clique para {acao.lower()} o fornecedor"
                ):
                    # Modal de confirmação
                    modal_key = f"modal_{f.id}"
                    with st.expander(f"Confirmar {acao}", expanded=True):
                        st.write(f"""
                            **{acao} fornecedor?**  
                            Nome: {f.nome}  
                            CNPJ: {formatar_cnpj(f.cnpj)}
                        """)
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Confirmar", key=f"confirm_{f.id}", type="primary"):
                                try:
                                    if fornecedor_controller.alterar_status_fornecedor(
                                            fornecedor_id=f.id,
                                            ativo=not f.ativo,
                                            usuario_id=st.session_state.usuario_id
                                    ):
                                        novo_status = "ativado" if not f.ativo else "desativado"
                                        st.success(f"Fornecedor {f.nome} {novo_status} com sucesso!")
                                        time.sleep(1)
                                        st.rerun()
                                except Exception as e:
                                    st.error(str(e))
                        with col2:
                            if st.button("Cancelar", key=f"cancel_{f.id}"):
                                st.rerun()

                st.markdown("---")  # Linha separadora entre fornecedores

        else:
            st.info("Nenhum fornecedor cadastrado")

    except Exception as e:
        st.error(f"Erro ao listar fornecedores: {str(e)}")
    finally:
        db.close()


def visualizar_notas_entrada():
    """Interface independente para visualização de notas"""
    st.markdown("### 📋 Notas de Entrada")

    try:
        db = next(get_db())
        nota_controller = NotaEntradaController(db)
        fornecedor_controller = FornecedorController(db)

        # Filtros
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            fornecedores = [(f.id, f.nome) for f in fornecedor_controller.listar_fornecedores()]
            fornecedor = st.selectbox(
                "Fornecedor",
                options=[(None, "Todos")] + fornecedores,
                format_func=lambda x: x[1]
            )
            fornecedor_id = fornecedor[0] if fornecedor else None

        with col2:
            numero_nota = st.text_input("Número da Nota", placeholder="Buscar por número...")

        with col3:
            periodo = st.selectbox(
                "Período",
                options=["Últimos 30 dias", "Últimos 90 dias", "Este ano", "Todos"]
            )

        # Define datas baseado no período
        data_fim = datetime.now()
        if periodo == "Últimos 30 dias":
            data_inicio = data_fim - timedelta(days=30)
        elif periodo == "Últimos 90 dias":
            data_inicio = data_fim - timedelta(days=90)
        elif periodo == "Este ano":
            data_inicio = datetime(data_fim.year, 1, 1)
        else:
            data_inicio = datetime(2000, 1, 1)

        # Busca notas
        notas = nota_controller.buscar_notas_por_periodo(
            data_inicio=data_inicio,
            data_fim=data_fim,
            fornecedor_id=fornecedor_id
        )

        # Filtra por número se especificado
        if numero_nota:
            notas = [n for n in notas if numero_nota in n.numero_nota]

        if notas:
            # Cabeçalho
            st.markdown("---")
            header = st.columns([1.5, 1.5, 2, 1, 1.5, 1, 1])
            header[0].write("Data")
            header[1].write("Número")
            header[2].write("Fornecedor")
            header[3].write("Produtos")
            header[4].write("Valor Total")
            header[5].write("Status")
            header[6].write("Ações")
            st.markdown("---")

            # Lista de notas
            for nota in notas:
                cols = st.columns([1.5, 1.5, 2, 1, 1.5, 1, 1])

                # Data
                cols[0].write(nota.data_emissao.strftime("%d/%m/%Y"))

                # Número da nota
                cols[1].write(nota.numero_nota)

                # Fornecedor
                cols[2].write(nota.fornecedor.nome)

                # Quantidade de produtos
                total_produtos = len(nota.produtos)
                cols[3].write(f"{total_produtos} {'item' if total_produtos == 1 else 'itens'}")

                # Valor total
                valor_total = sum(p.valor_unitario * p.quantidade_inicial for p in nota.produtos)
                cols[4].write(f"R$ {float(valor_total):,.2f}")

                # Status com ícone
                status_icons = {
                    'ativa': '📝',
                    'finalizada': '✅',
                    'devolvida': '↩️'
                }
                status_icon = status_icons.get(nota.status.value, '❓')
                cols[5].write(f"{status_icon}")

                # Botão de download
                if cols[6].button(
                        "📥",
                        key=f"download_{nota.id}",
                        help="Baixar nota de entrada"
                ):
                    try:
                        # Gera o PDF
                        pdf_buffer = gerar_pdf_nota(nota, nota_controller)

                        # Oferece o download
                        nome_arquivo = f"nota_{nota.numero_nota}_{nota.data_emissao.strftime('%Y%m%d')}.pdf"
                        st.download_button(
                            label="📄 Download PDF",
                            data=pdf_buffer,
                            file_name=nome_arquivo,
                            mime="application/pdf",
                            key=f"pdf_{nota.id}"
                        )

                        st.success("PDF gerado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {str(e)}")

                st.markdown("---")

        else:
            st.info("Nenhuma nota encontrada com os filtros selecionados")

    except Exception as e:
        st.error(f"Erro ao visualizar notas: {str(e)}")
    finally:
        db.close()


def mostrar_pagina():
    """Exibe a página de fornecedores"""
    st.title("Gestão de Fornecedores")

    # Resumo sempre visível
    mostrar_resumo_fornecedores()
    st.markdown("---")

    # Tabs
    tab_cadastro, tab_notas = st.tabs([
        "📝 Cadastro",
        "📋 Notas de Entrada"
    ])

    with tab_cadastro:
        if st.session_state.usuario_tipo == 'master':
            if cadastrar_fornecedor():
                st.rerun()

        st.markdown("---")
        listar_fornecedores()

    with tab_notas:
        visualizar_notas_entrada()