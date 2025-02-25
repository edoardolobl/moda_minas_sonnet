# src/views/estoque.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from src.models import get_db
from src.controllers.estoque import EstoqueController
from src.controllers.fornecedor import FornecedorController


def exportar_estoque_csv(produtos: list) -> str:
    """Formata os dados do estoque para CSV"""
    # Criar DataFrame com as colunas na ordem desejada
    df = pd.DataFrame({
        'Status': [p['status'] for p in produtos],
        'Referência': [p['referencia'] for p in produtos],
        'Descrição': [p['descricao'] for p in produtos],
        'Tamanho': [p['tamanho'] for p in produtos],
        'Quantidade': [p['quantidade_total'] for p in produtos],
        'Valor Unitário': [p['valor_unitario'] for p in produtos],
        'Fornecedor': [p['fornecedor'] for p in produtos],
        'Data Entrada': [p['data_entrada'] for p in produtos],
        'Dias em Estoque': [p['dias_em_estoque'] for p in produtos]
    })

    # Remover emojis do status
    df['Status'] = df['Status'].apply(lambda x: x.replace('✅', '').replace('⚡', '').replace('⚠️', '').strip())

    # Formatar valores monetários
    df['Valor Unitário'] = df['Valor Unitário'].apply(lambda x: f'R$ {x:.2f}'.replace('.', ','))

    # Exportar para CSV
    return df.to_csv(
        index=False,
        encoding='utf-8-sig',
        sep=',',  # Mudamos para vírgula que é mais padrão
        decimal=',',  # Usar vírgula como separador decimal
        float_format='%.2f'  # Formatar números com 2 casas decimais
    )




def mostrar_resumo_estoque():
    """Mostra cards com resumo do estoque"""
    try:
        db = next(get_db())
        estoque_controller = EstoqueController(db)

        stats = estoque_controller.analise_estoque_antiguidade()
        total_pecas = sum(faixa['total_pecas'] for faixa in stats.values())
        valor_total = sum(faixa['valor_total'] for faixa in stats.values())
        produtos_antigos = stats.get('mais_90_dias', {}).get('total_pecas', 0)

        # Cards em grid
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
                <div style='padding: 1rem; border-radius: 0.5rem; border: 1px solid #e0e0e0;'>
                    <h3 style='margin: 0; font-size: 1rem; color: #666;'>Total em Estoque</h3>
                    <p style='margin: 0; font-size: 1.5rem; font-weight: bold;'>
                        {} peças
                    </p>
                    <p style='margin: 0; color: #666;'>
                        R$ {:,.2f}
                    </p>
                </div>
            """.format(total_pecas, valor_total), unsafe_allow_html=True)

        with col2:
            st.markdown("""
                <div style='padding: 1rem; border-radius: 0.5rem; border: 1px solid #e0e0e0;'>
                    <h3 style='margin: 0; font-size: 1rem; color: #666;'>Produtos > 90 dias</h3>
                    <p style='margin: 0; font-size: 1.5rem; font-weight: bold; color: {};'>
                        {} peças
                    </p>
                    <p style='margin: 0; color: #666;'>
                        Atenção necessária
                    </p>
                </div>
            """.format('#ff4b4b' if produtos_antigos > 100 else '#333', produtos_antigos),
                        unsafe_allow_html=True)

        with col3:
            produtos_parados = len(estoque_controller.produtos_sem_movimento(30))
            st.markdown("""
                <div style='padding: 1rem; border-radius: 0.5rem; border: 1px solid #e0e0e0;'>
                    <h3 style='margin: 0; font-size: 1rem; color: #666;'>Sem Movimento</h3>
                    <p style='margin: 0; font-size: 1.5rem; font-weight: bold; color: {};'>
                        {} produtos
                    </p>
                    <p style='margin: 0; color: #666;'>
                        Últimos 30 dias
                    </p>
                </div>
            """.format('#ff4b4b' if produtos_parados > 50 else '#333', produtos_parados),
                        unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao carregar resumo: {str(e)}")
    finally:
        db.close()


def visualizar_estoque():
    """Visualização aprimorada do estoque"""
    try:
        db = next(get_db())
        estoque_controller = EstoqueController(db)
        fornecedor_controller = FornecedorController(db)

        # Layout dos filtros
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:
            fornecedores = [(f.id, f.nome) for f in fornecedor_controller.listar_fornecedores()]
            fornecedor = st.selectbox(
                "Fornecedor",
                options=[(None, "Todos")] + fornecedores,
                format_func=lambda x: x[1],
                key="filtro_fornecedor",
                help="Filtrar por fornecedor específico"
            )

        with col2:
            tamanhos = ["Todos", "P", "M", "G", "GG", "U"]
            tamanho = st.selectbox(
                "Tamanho",
                options=tamanhos,
                key="filtro_tamanho",
                help="Filtrar por tamanho específico"
            )

        with col3:
            status_options = [
                "Todos",
                "✅ Em Estoque",
                "⚡ Baixo Estoque",
                "⚠️ Sem Movimento"
            ]
            status = st.selectbox(
                "Status",
                options=status_options,
                key="filtro_status",
                help="Filtrar por status do produto"
            )

        with col4:
            ordem_options = {
                "Referência ↑": ("referencia", False),
                "Quantidade ↓": ("quantidade_total", True),
                "Valor ↓": ("valor_unitario", True),
                "Mais Antigos": ("dias_em_estoque", True),
            }
            ordenacao = st.selectbox(
                "Ordenar por",
                options=list(ordem_options.keys()),
                help="Escolha como ordenar os resultados"
            )

        # Obtém dados paginados
        page = st.session_state.get('pagina_estoque', 1)
        resultado = estoque_controller.visualizar_estoque_completo(page=page)

        if resultado['produtos']:
            # Aplicar filtros
            produtos_filtrados = resultado['produtos']

            if fornecedor and fornecedor[0]:
                produtos_filtrados = [p for p in produtos_filtrados
                                      if p['fornecedor'] == fornecedor[1]]

            if tamanho != "Todos":
                produtos_filtrados = [p for p in produtos_filtrados
                                      if p['tamanho'] == tamanho]

            if status != "Todos":
                # Mapeamento correto dos status
                status_map = {
                    "✅ Em Estoque": "✅ Em Estoque",
                    "⚡ Baixo Estoque": "⚡ Baixo Estoq",
                    "⚠️ Sem Movimento": "⚠️ Sem Movim"
                }
                produtos_filtrados = [p for p in produtos_filtrados
                                      if p['status'].strip() == status_map[status].strip()]

            # Ordenação
            campo, reverso = ordem_options[ordenacao]
            produtos_filtrados.sort(key=lambda x: x[campo], reverse=reverso)

            # Mostra tabela
            st.dataframe(
                produtos_filtrados,
                hide_index=True,
                column_config={
                    "status": st.column_config.TextColumn(
                        "Status",
                        help="Status atual do produto",
                        width="small"
                    ),
                    "referencia": st.column_config.TextColumn(
                        "Referência",
                        width="small"
                    ),
                    "descricao": st.column_config.TextColumn(
                        "Descrição",
                        width="medium"
                    ),
                    "tamanho": st.column_config.TextColumn(
                        "Tamanho",
                        width="small"
                    ),
                    "quantidade_total": st.column_config.NumberColumn(
                        "Qtd",
                        help="Quantidade total em estoque",
                        format="%d",
                        width="small"
                    ),
                    "valor_unitario": st.column_config.NumberColumn(
                        "Valor Unit.",
                        format="R$ %.2f",
                        width="small"
                    ),
                    "fornecedor": st.column_config.TextColumn(
                        "Fornecedor",
                        width="medium"
                    ),
                    "data_entrada": st.column_config.TextColumn(
                        "Data Entrada",
                        width="small"
                    ),
                    "dias_em_estoque": st.column_config.ProgressColumn(
                        "Tempo em Estoque",
                        help="Dias desde a entrada",
                        format="%d dias",
                        min_value=0,
                        max_value=90
                    )
                },
                use_container_width=True
            )

            # Paginação
            paginacao_container = st.container()
            with paginacao_container:
                col1, col2, col3, col4, col5 = st.columns([1, 3, 1, 3, 1])

                with col1:
                    if page > 1:
                        if st.button("⬅️", key="prev_page"):
                            st.session_state.pagina_estoque = page - 1
                            st.rerun()

                with col3:
                    st.markdown(f"<div style='text-align: center; padding: 0.5rem;'>"
                                f"Página {page} de {resultado['pages']}</div>",
                                unsafe_allow_html=True)

                with col5:
                    if page < resultado['pages']:
                        if st.button("➡️", key="next_page"):
                            st.session_state.pagina_estoque = page + 1
                            st.rerun()

            # Botão de exportação
            st.download_button(
                "📥 Exportar Dados",
                data=exportar_estoque_csv(produtos_filtrados),
                file_name=f"estoque_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                key='download-csv'
            )

        else:
            st.info("Nenhum produto em estoque")

    except Exception as e:
        st.error(f"Erro ao visualizar estoque: {str(e)}")
    finally:
        db.close()


def buscar_produtos():
    """Interface melhorada de busca de produtos"""
    st.markdown("### 🔍 Buscar Produtos")

    try:
        db = next(get_db())
        estoque_controller = EstoqueController(db)
        fornecedor_controller = FornecedorController(db)

        # Interface de busca principal
        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                termo_busca = st.text_input(
                    "Buscar por",
                    placeholder="Digite código, referência ou descrição...",
                    help="Busque por qualquer parte do código, referência ou descrição"
                )

            with col2:
                campo_busca = st.selectbox(
                    "Buscar em",
                    options=[
                        "Todos os campos",
                        "Código",
                        "Referência",
                        "Descrição"
                    ],
                    help="Escolha onde buscar o termo"
                )

        # Filtros adicionais
        with st.expander("➕ Filtros Adicionais", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                filtro_tamanho = st.multiselect(
                    "Tamanhos",
                    options=["P", "M", "G", "GG", "U"],
                    help="Selecione um ou mais tamanhos"
                )

            with col2:
                filtro_status = st.multiselect(
                    "Status",
                    options=[
                        "Em Estoque",
                        "Baixo Estoque",
                        "Sem Movimento"
                    ],
                    help="Selecione um ou mais status"
                )

            with col3:
                fornecedores = [(f.id, f.nome) for f in fornecedor_controller.listar_fornecedores()]
                filtro_fornecedor = st.selectbox(
                    "Fornecedor",
                    options=[(None, "Todos")] + fornecedores,
                    format_func=lambda x: x[1],
                    help="Selecione um fornecedor específico"
                )

        # Executa busca apenas se houver termo ou filtros
        if termo_busca or filtro_tamanho or filtro_status or (filtro_fornecedor and filtro_fornecedor[0]):
            # Obtém resultados
            resultados = estoque_controller.visualizar_estoque_completo(page=1, per_page=1000)['produtos']

            # Aplica filtros
            produtos_filtrados = resultados

            # Filtro por termo de busca
            if termo_busca:
                if campo_busca == "Código":
                    produtos_filtrados = [p for p in produtos_filtrados
                                          if termo_busca.lower() in p['referencia'].lower()]
                elif campo_busca == "Referência":
                    produtos_filtrados = [p for p in produtos_filtrados
                                          if termo_busca.lower() in p['referencia'].lower()]
                elif campo_busca == "Descrição":
                    produtos_filtrados = [p for p in produtos_filtrados
                                          if termo_busca.lower() in p['descricao'].lower()]
                else:  # Todos os campos
                    produtos_filtrados = [p for p in produtos_filtrados
                                          if termo_busca.lower() in p['referencia'].lower() or
                                          termo_busca.lower() in p['descricao'].lower()]

            # Aplica filtros adicionais
            if filtro_tamanho:
                produtos_filtrados = [p for p in produtos_filtrados
                                      if p['tamanho'] in filtro_tamanho]

            if filtro_status:
                status_map = {
                    "Em Estoque": "✅ Em Estoque",
                    "Baixo Estoque": "⚡ Baixo Estoq",
                    "Sem Movimento": "⚠️ Sem Movim"
                }
                status_filtrados = [status_map[s] for s in filtro_status]
                produtos_filtrados = [p for p in produtos_filtrados
                                      if p['status'] in status_filtrados]

            if filtro_fornecedor and filtro_fornecedor[0]:
                produtos_filtrados = [p for p in produtos_filtrados
                                      if p['fornecedor'] == filtro_fornecedor[1]]

            # Mostra resultados
            if produtos_filtrados:
                st.success(f"Encontrados {len(produtos_filtrados)} produtos")

                # Usa o mesmo formato de visualização da aba principal
                st.dataframe(
                    produtos_filtrados,
                    hide_index=True,
                    column_config={
                        "status": st.column_config.TextColumn(
                            "Status",
                            help="Status atual do produto",
                            width="small"
                        ),
                        "referencia": st.column_config.TextColumn(
                            "Referência",
                            width="small"
                        ),
                        "descricao": st.column_config.TextColumn(
                            "Descrição",
                            width="medium"
                        ),
                        "tamanho": st.column_config.TextColumn(
                            "Tamanho",
                            width="small"
                        ),
                        "quantidade_total": st.column_config.NumberColumn(
                            "Qtd",
                            help="Quantidade total em estoque",
                            format="%d",
                            width="small"
                        ),
                        "valor_unitario": st.column_config.NumberColumn(
                            "Valor Unit.",
                            format="R$ %.2f",
                            width="small"
                        ),
                        "fornecedor": st.column_config.TextColumn(
                            "Fornecedor",
                            width="medium"
                        ),
                        "data_entrada": st.column_config.TextColumn(
                            "Data Entrada",
                            width="small"
                        ),
                        "dias_em_estoque": st.column_config.ProgressColumn(
                            "Tempo em Estoque",
                            help="Dias desde a entrada",
                            format="%d dias",
                            min_value=0,
                            max_value=90
                        )
                    },
                    use_container_width=True
                )

                # Botão de exportação
                st.download_button(
                    "📥 Exportar Resultados",
                    data=exportar_estoque_csv(produtos_filtrados),
                    file_name=f"busca_estoque_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key='download-csv-busca'
                )
            else:
                st.info("Nenhum produto encontrado com os critérios informados")
        else:
            st.info("👆 Digite um termo de busca ou use os filtros acima")

    except Exception as e:
        st.error(f"Erro ao buscar produtos: {str(e)}")
    finally:
        db.close()


def mostrar_pagina():
    """Exibe a página de estoque"""
    st.title("Gestão de Estoque")

    # Resumo sempre visível
    mostrar_resumo_estoque()
    st.markdown("---")

    # Tabs reorganizadas
    tab_visualizacao, tab_busca = st.tabs([
        "📋 Visualização",
        "🔍 Busca"
    ])

    with tab_visualizacao:
        visualizar_estoque()

    with tab_busca:
        buscar_produtos()
