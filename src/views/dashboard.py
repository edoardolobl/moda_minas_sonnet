# src/views/dashboard.py
import streamlit as st
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from src.models import get_db
from src.controllers.venda import VendaController
from src.controllers.estoque import EstoqueController
from src.controllers.fornecedor import FornecedorController


def formatar_valor(valor: float) -> str:
    """Formata valores monetários"""
    return f"R$ {valor:,.2f}"


def formatar_percentual(valor: float) -> str:
    """Formata valores percentuais"""
    return f"{valor:.1f}%"


def mostrar_kpis():
    """Exibe os KPIs principais em um layout responsivo"""
    try:
        db = next(get_db())
        venda_controller = VendaController(db)
        estoque_controller = EstoqueController(db)

        # Obtém dados
        resumo_vendas = venda_controller.resumo_vendas_dia(datetime.now())
        stats_estoque = estoque_controller.analise_estoque_antiguidade()

        # Primeira linha de KPIs
        with st.container():
            col1, col2 = st.columns(2)

            # KPI de Vendas
            with col1:
                st.markdown("### 💰 Vendas do Dia")
                valor_vendas = resumo_vendas.get('valor_total', 0)
                qtd_vendas = resumo_vendas.get('total_vendas', 0)

                # Calcula variação com dia anterior (exemplo)
                # TODO: Implementar lógica real de comparação
                variacao = 5.2  # Exemplo

                st.metric(
                    label="Total de Vendas",
                    value=formatar_valor(valor_vendas),
                    delta=formatar_percentual(variacao),
                    help="Comparação com o dia anterior"
                )
                st.caption(f"Total de {qtd_vendas} vendas realizadas hoje")

            # KPI de Estoque
            with col2:
                st.markdown("### 📦 Situação do Estoque")
                total_pecas = sum(faixa['total_pecas'] for faixa in stats_estoque.values())
                valor_total = sum(faixa['valor_total'] for faixa in stats_estoque.values())

                st.metric(
                    label="Valor em Estoque",
                    value=formatar_valor(valor_total),
                    delta=f"{total_pecas} peças",
                    help="Total de peças e valor em estoque"
                )

        # Segunda linha de KPIs
        with st.container():
            col3, col4 = st.columns(2)

            # KPI de Produtos Antigos
            with col3:
                st.markdown("### ⚠️ Atenção")
                produtos_antigos = stats_estoque.get('mais_90_dias', {})
                valor_antigos = produtos_antigos.get('valor_total', 0)
                qtd_antigos = produtos_antigos.get('total_pecas', 0)

                st.metric(
                    label="Produtos > 90 dias",
                    value=f"{qtd_antigos} peças",
                    delta=formatar_valor(valor_antigos),
                    delta_color="inverse",
                    help="Produtos em estoque há mais de 90 dias"
                )

            # KPI de Giro de Estoque
            with col4:
                st.markdown("### 🔄 Giro de Estoque")
                produtos_parados = len(estoque_controller.produtos_sem_movimento(30))

                st.metric(
                    label="Produtos sem Movimento",
                    value=f"{produtos_parados} itens",
                    delta="30 dias",
                    delta_color="inverse",
                    help="Produtos sem movimentação nos últimos 30 dias"
                )

    except Exception as e:
        st.error(f"Erro ao carregar KPIs: {str(e)}")
    finally:
        db.close()


def mostrar_grafico_vendas():
    """Exibe gráfico de vendas com Plotly"""
    try:
        db = next(get_db())
        venda_controller = VendaController(db)

        # Controle do período
        st.markdown("### 📊 Análise de Vendas")
        periodos = {
            "Últimos 7 dias": 7,
            "Últimos 15 dias": 15,
            "Últimos 30 dias": 30
        }
        periodo_selecionado = st.selectbox(
            "Período",
            options=list(periodos.keys()),
            index=0
        )

        dias = periodos[periodo_selecionado]
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=dias)

        vendas = venda_controller.relatorio_vendas_periodo(data_inicio, data_fim)

        if vendas:
            # Prepara dados
            datas = [venda['data_hora'].strftime('%d/%m') for venda in vendas]
            valores = [venda['valor_total'] for venda in vendas]

            # Cria gráfico com Plotly
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=datas,
                y=valores,
                mode='lines+markers',
                name='Vendas',
                line=dict(color='#2E86C1', width=2),
                marker=dict(size=8),
                hovertemplate="Data: %{x}<br>" +
                              "Valor: R$ %{y:.2f}<br>" +
                              "<extra></extra>"
            ))

            # Layout
            fig.update_layout(
                margin=dict(l=0, r=0, t=30, b=0),
                height=400,
                hovermode='x unified',
                xaxis_title="Data",
                yaxis_title="Valor (R$)",
                yaxis_tickformat=",.2f",
                yaxis_tickprefix="R$ "
            )

            st.plotly_chart(fig, use_container_width=True)

            # Resumo do período
            total_periodo = sum(valores)
            media_diaria = total_periodo / len(valores)

            col1, col2 = st.columns(2)
            col1.metric("Total no Período", formatar_valor(total_periodo))
            col2.metric("Média Diária", formatar_valor(media_diaria))

        else:
            st.info("Sem dados de vendas para o período selecionado")

    except Exception as e:
        st.error(f"Erro ao carregar gráfico de vendas: {str(e)}")
    finally:
        db.close()


def mostrar_analise_estoque():
    """Exibe análise do estoque com gráfico e tabela"""
    try:
        db = next(get_db())
        estoque_controller = EstoqueController(db)

        st.markdown("### 📈 Análise de Estoque por Fornecedor")

        analise = estoque_controller.analise_estoque_fornecedor()
        if analise:
            # Criar gráfico de barras
            dados_grafico = {
                'Fornecedor': [item['fornecedor'] for item in analise],
                'Valor Total': [item['valor_total'] for item in analise],
                'Total Peças': [item['total_pecas'] for item in analise]
            }

            fig = px.bar(
                dados_grafico,
                x='Fornecedor',
                y='Valor Total',
                text='Total Peças',
                title='Distribuição de Estoque por Fornecedor',
                labels={'Valor Total': 'Valor em Estoque (R$)'},
                height=400
            )

            fig.update_traces(
                texttemplate='%{text} peças',
                textposition='outside'
            )

            fig.update_layout(
                margin=dict(l=0, r=0, t=30, b=0),
                yaxis_tickformat=",.2f",
                yaxis_tickprefix="R$ "
            )

            st.plotly_chart(fig, use_container_width=True)

            # Tabela com dados detalhados
            with st.expander("Ver Detalhes"):
                st.dataframe(
                    analise,
                    hide_index=True,
                    column_config={
                        "fornecedor": st.column_config.TextColumn("Fornecedor"),
                        "total_produtos": st.column_config.NumberColumn(
                            "Produtos",
                            help="Número de produtos diferentes"
                        ),
                        "total_pecas": st.column_config.NumberColumn(
                            "Total Peças",
                            help="Quantidade total de peças"
                        ),
                        "valor_total": st.column_config.NumberColumn(
                            "Valor Total",
                            help="Valor total em estoque",
                            format="R$ %.2f"
                        )
                    }
                )
        else:
            st.info("Sem dados de estoque para exibir")

    except Exception as e:
        st.error(f"Erro ao carregar análise de estoque: {str(e)}")
    finally:
        db.close()


def mostrar_analise_detalhada():
    """Exibe análises detalhadas para usuários master"""
    st.markdown("### 📊 Análise Detalhada")

    try:
        db = next(get_db())
        estoque_controller = EstoqueController(db)

        # Análise por antiguidade em gráfico de pizza
        analise = estoque_controller.analise_estoque_antiguidade()

        if analise:
            labels = [
                "Até 30 dias",
                "30-60 dias",
                "60-90 dias",
                "Mais de 90 dias"
            ]

            valores = [
                analise['ate_30_dias']['valor_total'],
                analise['30_60_dias']['valor_total'],
                analise['60_90_dias']['valor_total'],
                analise['mais_90_dias']['valor_total']
            ]

            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=valores,
                hole=.3,
                hovertemplate="Período: %{label}<br>" +
                              "Valor: R$ %{value:.2f}<br>" +
                              "<extra></extra>"
            )])

            fig.update_layout(
                title="Distribuição do Valor em Estoque por Antiguidade",
                margin=dict(l=0, r=0, t=30, b=0),
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

            # Tabela detalhada
            dados_tabela = []
            for periodo, dados in analise.items():
                dados_tabela.append({
                    "Período": periodo.replace("_", " ").title(),
                    "Total Produtos": dados['total_produtos'],
                    "Total Peças": dados['total_pecas'],
                    "Valor Total": formatar_valor(dados['valor_total'])
                })

            st.dataframe(
                dados_tabela,
                hide_index=True,
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Erro ao carregar análise detalhada: {str(e)}")
    finally:
        db.close()


def mostrar_pagina():
    """Exibe a página do dashboard"""
    st.title("Dashboard")

    # Layout principal em containers
    with st.container():
        mostrar_kpis()

    st.markdown("---")

    # Gráficos principais
    col1, col2 = st.columns([3, 2])

    with col1:
        mostrar_grafico_vendas()

    with col2:
        mostrar_analise_estoque()

    # Análises detalhadas para usuários master
    if st.session_state.usuario_tipo == 'master':
        st.markdown("---")
        mostrar_analise_detalhada()