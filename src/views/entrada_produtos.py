# src/views/entrada_produtos.py
import time
import streamlit as st
from datetime import datetime
import pandas as pd
from src.models import get_db
from src.controllers.fornecedor import FornecedorController
from src.controllers.nota_entrada import NotaEntradaController
from src.views.fornecedores import formatar_cnpj
from src.utils.pdf_generator import gerar_pdf_nota


def selecionar_fornecedor():
    """Interface melhorada para seleção do fornecedor"""
    st.subheader("1. Selecionar Fornecedor")

    try:
        db = next(get_db())
        fornecedor_controller = FornecedorController(db)

        fornecedores = fornecedor_controller.listar_fornecedores()
        if not fornecedores:
            st.warning("⚠️ Nenhum fornecedor cadastrado")
            if st.button("📝 Cadastrar Novo Fornecedor", type="primary"):
                st.session_state.pagina_atual = 'fornecedores'
                st.rerun()
            return None

        # Container para seleção
        with st.container():
            # Seletor com busca
            opcoes_fornecedor = [(None, "Selecione um fornecedor...")] + [
                (f.id, f"{f.nome} ({formatar_cnpj(f.cnpj)})")
                for f in fornecedores
            ]

            fornecedor = st.selectbox(
                "Fornecedor",
                options=opcoes_fornecedor,
                format_func=lambda x: x[1],
                key="select_fornecedor",
                help="Selecione o fornecedor para entrada de produtos"
            )

            if fornecedor and fornecedor[0]:
                # Mostra informações do fornecedor selecionado
                fornec = fornecedor_controller.buscar_fornecedor(fornecedor[0])

                st.success("✅ Fornecedor selecionado")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"""
                        **Fornecedor:** {fornec.nome}  
                        **CNPJ:** {formatar_cnpj(fornec.cnpj)}  
                    """)

                with col2:
                    st.markdown(f"""
                        **Telefone:** {fornec.telefone or '-'}  
                        **Email:** {fornec.email or '-'}  
                    """)

                if st.button("🔄 Trocar Fornecedor"):
                    st.session_state.fornecedor_selecionado = None
                    st.session_state.nota_atual = None
                    st.rerun()

                return fornecedor[0]

        return None

    except Exception as e:
        st.error(f"Erro ao carregar fornecedores: {str(e)}")
        return None
    finally:
        db.close()


def gerenciar_nota_entrada(fornecedor_id: int):
    """Interface melhorada para criação/seleção de nota"""
    st.subheader("2. Nota de Entrada")

    try:
        db = next(get_db())
        nota_controller = NotaEntradaController(db)

        # Busca notas ativas do fornecedor
        notas_ativas = nota_controller.buscar_notas_por_periodo(
            data_inicio=datetime(2000, 1, 1),
            data_fim=datetime.now(),
            fornecedor_id=fornecedor_id
        )

        # Filtra apenas notas ativas
        notas_ativas = [n for n in notas_ativas if n.status.value == 'ativa']

        # Tabs para separar criar nova nota e selecionar existente
        tab_nova, tab_existente = st.tabs([
            "📝 Nova Nota",
            "📋 Notas Existentes" if notas_ativas else "📋 Sem Notas Ativas"
        ])

        with tab_nova:
            with st.form("form_nota_entrada", clear_on_submit=True):
                st.markdown("### Nova Nota de Entrada")

                col1, col2 = st.columns(2)
                with col1:
                    numero_nota = st.text_input(
                        "Número da Nota",
                        help="Número/identificador único da nota fiscal"
                    )
                    data_emissao = st.date_input(
                        "Data de Emissão",
                        help="Data de emissão da nota fiscal"
                    )

                with col2:
                    observacoes = st.text_area(
                        "Observações",
                        help="Observações adicionais sobre a nota",
                        height=100
                    )

                if st.form_submit_button("✨ Criar Nota", use_container_width=True):
                    if not numero_nota or not data_emissao:
                        st.error("Número da nota e data são obrigatórios")
                        return None

                    try:
                        nota = nota_controller.criar_nota_entrada(
                            numero_nota=numero_nota,
                            fornecedor_id=fornecedor_id,
                            data_emissao=datetime.combine(data_emissao, datetime.min.time()),
                            usuario_id=st.session_state.usuario_id,
                            observacoes=observacoes
                        )

                        if nota:
                            st.success("✅ Nota criada com sucesso!")
                            time.sleep(1)
                            return nota.id

                    except Exception as e:
                        st.error(f"Erro ao criar nota: {str(e)}")

        with tab_existente:
            if notas_ativas:
                st.markdown("### Selecione uma Nota Ativa")

                # Prepara dados para mostrar
                dados_notas = []
                for nota in notas_ativas:
                    total_itens = len(nota.produtos)
                    valor_total = sum(p.quantidade_atual * p.valor_unitario for p in nota.produtos)

                    dados_notas.append({
                        "Número": nota.numero_nota,
                        "Data": nota.data_emissao.strftime("%d/%m/%Y"),
                        "Itens": f"{total_itens} produtos",
                        "Valor": f"R$ {float(valor_total):,.2f}",
                        "ID": nota.id
                    })

                # Mostra notas em formato de cards clicáveis
                for nota in dados_notas:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                        col1.write(f"**Nota:** {nota['Número']}")
                        col2.write(f"**Data:** {nota['Data']}")
                        col3.write(f"**{nota['Itens']}**")

                        if col4.button("📝", key=f"select_nota_{nota['ID']}", help="Selecionar esta nota"):
                            return nota['ID']

                        st.markdown("---")
            else:
                st.info("Não há notas ativas para este fornecedor")

        return None

    except Exception as e:
        st.error(f"Erro ao gerenciar nota: {str(e)}")
        return None
    finally:
        db.close()


def adicionar_produtos_manual(nota_id: int):
    """Interface melhorada para adicionar produtos manualmente"""
    st.subheader("3. Adicionar Produtos")

    with st.form("form_produto", clear_on_submit=True):
        st.markdown("### 📝 Entrada Manual")

        # Primeira linha de campos
        col1, col2 = st.columns(2)
        with col1:
            codigo_barras = st.text_input(
                "Código de Barras",
                help="Código de barras único do produto",
                placeholder="Digite ou escaneie o código"
            )

        with col2:
            referencia = st.text_input(
                "Referência",
                help="Código de referência do produto",
                placeholder="Ex: REF-001"
            )

        # Segunda linha de campos
        col1, col2 = st.columns(2)
        with col1:
            descricao = st.text_input(
                "Descrição",
                help="Descrição detalhada do produto",
                placeholder="Ex: Camiseta Manga Curta"
            )

        with col2:
            tamanho = st.selectbox(
                "Tamanho",
                options=["P", "M", "G", "GG", "U"],
                help="Tamanho do produto"
            )

        # Terceira linha de campos
        col1, col2 = st.columns(2)
        with col1:
            valor_unitario = st.number_input(
                "Valor Unitário (R$)",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                help="Valor unitário do produto"
            )

        with col2:
            quantidade = st.number_input(
                "Quantidade",
                min_value=1,
                step=1,
                help="Quantidade de peças"
            )

        # Botão de submissão
        if st.form_submit_button("➕ Adicionar Produto", use_container_width=True):
            if not all([codigo_barras, referencia, descricao]):
                st.error("Código de barras, referência e descrição são obrigatórios")
                return False

            try:
                db = next(get_db())
                nota_controller = NotaEntradaController(db)

                produto = nota_controller.adicionar_produto(
                    nota_id=nota_id,
                    codigo_barras=codigo_barras,
                    referencia=referencia,
                    descricao=descricao,
                    tamanho=tamanho,
                    valor_unitario=valor_unitario,
                    quantidade=quantidade,
                    usuario_id=st.session_state.usuario_id
                )

                if produto:
                    st.success("✅ Produto adicionado com sucesso!")
                    return True

            except Exception as e:
                st.error(f"Erro ao adicionar produto: {str(e)}")
            finally:
                db.close()

    return False


def adicionar_produtos_excel(nota_id: int):
    """Interface melhorada para importar produtos via Excel/CSV"""
    st.markdown("### 📎 Importar Excel/CSV")

    # Instruções de importação
    with st.expander("ℹ️ Instruções de Importação", expanded=False):
        st.markdown("""
            #### Formato esperado do arquivo:
            O arquivo Excel/CSV deve conter as seguintes colunas:
            - `codigo_barras`: Código de barras único do produto
            - `referencia`: Código de referência do produto
            - `descricao`: Descrição do produto
            - `tamanho`: Tamanho (P, M, G, GG, U)
            - `valor_unitario`: Valor unitário do produto
            - `quantidade`: Quantidade de peças

            #### Exemplo:
            | codigo_barras | referencia | descricao | tamanho | valor_unitario | quantidade |
            |--------------|------------|-----------|----------|----------------|------------|
            | 789123456789 | REF-001    | Camiseta  | M       | 29.90          | 10         |
        """)

    uploaded_file = st.file_uploader(
        "Escolha o arquivo",
        type=['csv', 'xlsx'],
        help="Selecione um arquivo Excel (.xlsx) ou CSV"
    )

    if uploaded_file:
        try:
            # Lê o arquivo
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            # Verifica colunas necessárias
            colunas_necessarias = [
                'codigo_barras', 'referencia', 'descricao',
                'tamanho', 'valor_unitario', 'quantidade'
            ]

            colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]
            if colunas_faltantes:
                st.error(f"Colunas faltantes no arquivo: {', '.join(colunas_faltantes)}")
                return

            # Preview dos dados
            st.markdown("### Preview dos dados")
            st.dataframe(
                df.head(),
                column_config={
                    "valor_unitario": st.column_config.NumberColumn(
                        "Valor Unitário",
                        format="R$ %.2f"
                    )
                }
            )

            # Resumo da importação
            total_produtos = len(df)
            total_pecas = df['quantidade'].sum()
            valor_total = (df['valor_unitario'] * df['quantidade']).sum()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Produtos", str(total_produtos))
            col2.metric("Total de Peças", str(total_pecas))
            col3.metric("Valor Total", f"R$ {valor_total:,.2f}")

            # Botão de confirmação
            if st.button("✨ Confirmar Importação", type="primary", use_container_width=True):
                db = next(get_db())
                nota_controller = NotaEntradaController(db)

                with st.spinner("Importando produtos..."):
                    produtos_adicionados = 0
                    erros = []

                    # Barra de progresso
                    progress_bar = st.progress(0)
                    total = len(df)

                    for idx, row in df.iterrows():
                        try:
                            produto = nota_controller.adicionar_produto(
                                nota_id=nota_id,
                                codigo_barras=str(row['codigo_barras']),
                                referencia=str(row['referencia']),
                                descricao=str(row['descricao']),
                                tamanho=str(row['tamanho']),
                                valor_unitario=float(row['valor_unitario']),
                                quantidade=int(row['quantidade']),
                                usuario_id=st.session_state.usuario_id
                            )
                            if produto:
                                produtos_adicionados += 1
                        except Exception as e:
                            erros.append(f"Erro na linha {idx + 2}: {str(e)}")

                        # Atualiza barra de progresso
                        progress_bar.progress((idx + 1) / total)

                    # Resultado da importação
                    if produtos_adicionados > 0:
                        st.success(f"✅ {produtos_adicionados} produtos importados com sucesso!")

                    if erros:
                        with st.expander("⚠️ Erros na importação", expanded=True):
                            for erro in erros:
                                st.error(erro)

        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()


def mostrar_produtos_nota(nota_id: int):
    """Visualização melhorada dos produtos na nota"""
    try:
        db = next(get_db())
        nota_controller = NotaEntradaController(db)

        produtos = nota_controller.listar_produtos_nota(nota_id)

        if produtos:
            st.markdown("### 📋 Produtos na Nota")

            # Filtro de busca
            busca = st.text_input(
                "🔍 Buscar produto",
                placeholder="Buscar por código, referência ou descrição..."
            )

            # Filtra produtos se houver busca
            if busca:
                produtos = [p for p in produtos if
                            busca.lower() in p.codigo_barras.lower() or
                            busca.lower() in p.referencia.lower() or
                            busca.lower() in p.descricao.lower()]

            # Dados para a tabela
            dados_tabela = []
            total_valor = 0
            total_pecas = 0

            for produto in produtos:
                valor_total = produto.quantidade_atual * produto.valor_unitario
                total_valor += valor_total
                total_pecas += produto.quantidade_atual

                dados_tabela.append({
                    "Código": produto.codigo_barras,
                    "Referência": produto.referencia,
                    "Descrição": produto.descricao,
                    "Tamanho": produto.tamanho,
                    "Qtd.": produto.quantidade_atual,
                    "Valor Unit.": float(produto.valor_unitario),
                    "Total": float(valor_total)
                })

            # Mostra tabela com produtos
            st.dataframe(
                dados_tabela,
                hide_index=True,
                column_config={
                    "Valor Unit.": st.column_config.NumberColumn(
                        "Valor Unit.",
                        format="R$ %.2f",
                        width="medium"
                    ),
                    "Total": st.column_config.NumberColumn(
                        "Total",
                        format="R$ %.2f",
                        width="medium"
                    )
                },
                use_container_width=True
            )

            # Resumo e totais
            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Total de Produtos",
                str(len(produtos)),
                help="Número de produtos diferentes"
            )

            col2.metric(
                "Total de Peças",
                str(total_pecas),
                help="Quantidade total de peças"
            )

            col3.metric(
                "Valor Total",
                f"R$ {float(total_valor):,.2f}",
                help="Valor total da nota"
            )

    except Exception as e:
        st.error(f"Erro ao listar produtos: {str(e)}")
    finally:
        db.close()


def finalizar_nota(nota_id: int):
    """Interface para finalização da nota"""
    st.markdown("### ✨ Finalizar Nota de Entrada")

    try:
        db = next(get_db())
        nota_controller = NotaEntradaController(db)

        nota = nota_controller.buscar_nota(nota_id)
        if not nota:
            st.error("Nota não encontrada")
            return False

        # Confirmação com resumo
        with st.expander("📝 Resumo da Nota", expanded=True):
            # Informações da nota
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                    **Número da Nota:** {nota.numero_nota}  
                    **Data de Emissão:** {nota.data_emissao.strftime('%d/%m/%Y')}  
                    **Fornecedor:** {nota.fornecedor.nome}
                """)

            with col2:
                st.markdown(f"""
                    **CNPJ:** {formatar_cnpj(nota.fornecedor.cnpj)}  
                    **Data de Registro:** {nota.data_registro.strftime('%d/%m/%Y %H:%M')}  
                    **Registrado por:** {nota.usuario_registro.nome}
                """)

            # Totais
            total_produtos = len(nota.produtos)
            total_pecas = sum(p.quantidade_atual for p in nota.produtos)
            valor_total = sum(p.quantidade_atual * p.valor_unitario for p in nota.produtos)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Produtos", str(total_produtos))
            col2.metric("Total de Peças", str(total_pecas))
            col3.metric("Valor Total", f"R$ {float(valor_total):,.2f}")

        # Botões de ação
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Confirmar e Finalizar", type="primary", use_container_width=True):
                try:
                    if nota_controller.finalizar_nota(nota_id, st.session_state.usuario_id):
                        return True
                except Exception as e:
                    st.error(f"Erro ao finalizar nota: {str(e)}")

        with col2:
            if st.button("❌ Cancelar", type="secondary", use_container_width=True):
                st.session_state.nota_atual = None
                st.rerun()

        return False

    except Exception as e:
        st.error(f"Erro ao finalizar nota: {str(e)}")
        return False
    finally:
        db.close()


def mostrar_pagina():
    """Exibe a página de entrada de produtos"""
    st.title("Entrada de Produtos")

    # Inicializa estados da sessão
    if 'fornecedor_selecionado' not in st.session_state:
        st.session_state.fornecedor_selecionado = None
    if 'nota_atual' not in st.session_state:
        st.session_state.nota_atual = None
    if 'nota_finalizada' not in st.session_state:
        st.session_state.nota_finalizada = False

    # Progresso visual do processo
    if st.session_state.nota_atual:
        progress = 3
    elif st.session_state.fornecedor_selecionado:
        progress = 2
    else:
        progress = 1

    # Barra de progresso
    st.progress(progress / 3)

    # Se a nota foi finalizada, mantem o estado até o usuário decidir o que fazer
    if st.session_state.nota_finalizada and st.session_state.nota_atual:
        # Busca a nota para gerar o PDF
        db = next(get_db())
        nota_controller = NotaEntradaController(db)
        nota = nota_controller.buscar_nota(st.session_state.nota_atual)

        if nota:
            st.success("✅ Nota finalizada com sucesso!")
            st.markdown("### 📋 Ações Disponíveis")

            # Download do PDF
            pdf_buffer = gerar_pdf_nota(nota, nota_controller)
            st.download_button(
                label="📥 Download PDF da Nota",
                data=pdf_buffer,
                file_name=f"nota_{nota.numero_nota}_{nota.data_emissao.strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            # Botão para nova entrada
            if st.button("➕ Iniciar Nova Entrada", type="primary", use_container_width=True):
                st.session_state.fornecedor_selecionado = None
                st.session_state.nota_atual = None
                st.session_state.nota_finalizada = False
                st.rerun()

        db.close()
        return

    # Fluxo normal quando não tem nota finalizada
    if not st.session_state.fornecedor_selecionado:
        fornecedor_id = selecionar_fornecedor()
        if fornecedor_id:
            st.session_state.fornecedor_selecionado = fornecedor_id
            st.rerun()

    # Gerenciar nota
    elif not st.session_state.nota_atual:
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Voltar"):
                st.session_state.fornecedor_selecionado = None
                st.rerun()

        with col2:
            nota_id = gerenciar_nota_entrada(st.session_state.fornecedor_selecionado)
            if nota_id:
                st.session_state.nota_atual = nota_id
                st.rerun()

    # Adicionar produtos
    else:
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Voltar"):
                st.session_state.nota_atual = None
                st.rerun()

        with col2:
            # Tabs para diferentes métodos de entrada
            tab1, tab2 = st.tabs(["📝 Entrada Manual", "📎 Importar Excel/CSV"])

            with tab1:
                adicionar_produtos_manual(st.session_state.nota_atual)

            with tab2:
                adicionar_produtos_excel(st.session_state.nota_atual)

            # Mostra produtos já adicionados
            st.markdown("---")
            mostrar_produtos_nota(st.session_state.nota_atual)

            # Opção para finalizar nota
            st.markdown("---")
            if finalizar_nota(st.session_state.nota_atual):
                st.session_state.nota_finalizada = True
                st.rerun()