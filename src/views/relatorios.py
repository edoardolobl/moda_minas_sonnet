# src/views/relatorios.py
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from src.models import get_db
from src.controllers.venda import VendaController
from src.controllers.estoque import EstoqueController
from src.controllers.nota_entrada import NotaEntradaController
from src.controllers.fornecedor import FornecedorController


def gerar_pdf(dados: list, titulo: str, colunas: list) -> BytesIO:
    """Gera um PDF com os dados fornecidos"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []

    # Estilos
    styles = getSampleStyleSheet()
    elementos.append(Paragraph(titulo, styles['Heading1']))
    elementos.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))

    # Criação da tabela
    tabela_dados = [colunas]  # Cabeçalho
    tabela_dados.extend(dados)  # Dados

    tabela = Table(tabela_dados)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elementos.append(tabela)
    doc.build(elementos)
    buffer.seek(0)
    return buffer


def relatorio_vendas():
    """Interface para relatório de vendas"""
    st.subheader("Relatório de Vendas")

    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data Início")
    with col2:
        data_fim = st.date_input("Data Fim")

    if st.button("Gerar Relatório de Vendas"):
        try:
            db = next(get_db())
            venda_controller = VendaController(db)

            vendas = venda_controller.relatorio_vendas_periodo(
                data_inicio=datetime.combine(data_inicio, datetime.min.time()),
                data_fim=datetime.combine(data_fim, datetime.max.time())
            )

            if vendas:
                # Preparar dados para PDF
                dados_pdf = [
                    [
                        str(v['id']),
                        v['data_hora'].strftime('%d/%m/%Y %H:%M'),
                        v['cliente_nome'],
                        f"R$ {v['valor_total']:,.2f}",
                        v['forma_pagamento'],
                        str(v['quantidade_itens'])
                    ] for v in vendas
                ]

                colunas = ['ID', 'Data/Hora', 'Cliente', 'Valor Total', 'Pagamento', 'Qtd. Itens']

                # Gerar PDF
                pdf = gerar_pdf(
                    dados_pdf,
                    f"Relatório de Vendas - {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
                    colunas
                )

                # Download do PDF
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf,
                    file_name=f"vendas_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

                # Mostrar resumo
                total_vendas = sum(v['valor_total'] for v in vendas)
                qtd_vendas = len(vendas)
                ticket_medio = total_vendas / qtd_vendas if qtd_vendas > 0 else 0

                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Vendas", f"R$ {total_vendas:,.2f}")
                col2.metric("Quantidade de Vendas", str(qtd_vendas))
                col3.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")

            else:
                st.info("Nenhuma venda encontrada no período")

        except Exception as e:
            st.error(f"Erro ao gerar relatório: {str(e)}")
        finally:
            db.close()


def relatorio_estoque():
    """Interface para relatório de estoque"""
    st.subheader("Relatório de Estoque")

    try:
        db = next(get_db())
        estoque_controller = EstoqueController(db)

        # Filtros
        fornecedor_id = st.selectbox(
            "Fornecedor",
            options=[None] + [(f.id, f.nome) for f in FornecedorController(db).listar_fornecedores()],
            format_func=lambda x: "Todos" if x is None else x[1]
        )

        if st.button("Gerar Relatório de Estoque"):
            if fornecedor_id:
                fornecedor_id = fornecedor_id[0]

            analise = estoque_controller.analise_estoque_fornecedor(fornecedor_id)

            if analise:
                # Preparar dados para PDF
                dados_pdf = [
                    [
                        item['fornecedor'],
                        str(item['total_produtos']),
                        str(item['total_pecas']),
                        f"R$ {item['valor_total']:,.2f}"
                    ] for item in analise
                ]

                colunas = ['Fornecedor', 'Total Produtos', 'Total Peças', 'Valor Total']

                # Gerar PDF
                pdf = gerar_pdf(
                    dados_pdf,
                    "Relatório de Estoque",
                    colunas
                )

                # Download do PDF
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf,
                    file_name=f"estoque_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

                # Mostrar dados em tabela
                st.dataframe(
                    analise,
                    hide_index=True,
                    column_config={
                        "valor_total": st.column_config.NumberColumn(
                            "Valor Total",
                            format="R$ %.2f"
                        )
                    }
                )
            else:
                st.info("Nenhum dado de estoque encontrado")

    except Exception as e:
        st.error(f"Erro ao gerar relatório: {str(e)}")
    finally:
        db.close()


def relatorio_devolucoes():
    """Interface para relatório de devoluções"""
    st.subheader("Relatório de Devoluções")

    try:
        db = next(get_db())
        estoque_controller = EstoqueController(db)

        # Filtros
        col1, col2 = st.columns(2)

        with col1:
            data_inicio = st.date_input("Data Início", key="dev_inicio")
        with col2:
            data_fim = st.date_input("Data Fim", key="dev_fim")

        fornecedor_id = st.selectbox(
            "Fornecedor",
            options=[None] + [(f.id, f.nome) for f in FornecedorController(db).listar_fornecedores()],
            format_func=lambda x: "Todos" if x is None else x[1],
            key="dev_fornecedor"
        )

        if st.button("Gerar Relatório de Devoluções"):
            # TODO: Implementar lógica de relatório de devoluções
            st.info("Funcionalidade em desenvolvimento")

    except Exception as e:
        st.error(f"Erro ao gerar relatório: {str(e)}")
    finally:
        db.close()


def mostrar_pagina():
    """Exibe a página de relatórios"""
    st.title("Relatórios")

    # Verifica permissão
    if st.session_state.usuario_tipo != 'master':
        st.error("Acesso não autorizado")
        return

    # Tabs para diferentes tipos de relatório
    tab_vendas, tab_estoque, tab_devolucoes = st.tabs([
        "💰 Vendas",
        "📦 Estoque",
        "↩️ Devoluções"
    ])

    with tab_vendas:
        relatorio_vendas()

    with tab_estoque:
        relatorio_estoque()

    with tab_devolucoes:
        relatorio_devolucoes()