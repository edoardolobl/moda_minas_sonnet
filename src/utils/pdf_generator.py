from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def gerar_pdf_nota(nota, nota_controller):
    """
    Gera PDF para uma nota de entrada
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=inch / 2,
        leftMargin=inch / 2,
        topMargin=inch / 2,
        bottomMargin=inch / 2
    )

    # Lista para elementos do PDF
    elementos = []
    styles = getSampleStyleSheet()

    # Estilos personalizados
    styles.add(ParagraphStyle(
        name='NotaTitulo',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    ))
    styles.add(ParagraphStyle(
        name='NotaSubTitulo',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20
    ))

    # Título
    elementos.append(Paragraph("NOTA DE ENTRADA", styles['NotaTitulo']))

    # Informações da Nota
    elementos.append(Paragraph("Informações Gerais", styles['NotaSubTitulo']))
    info_nota = [
        ["Número da Nota:", nota.numero_nota],
        ["Data de Emissão:", nota.data_emissao.strftime("%d/%m/%Y")],
        ["Data de Registro:", nota.data_registro.strftime("%d/%m/%Y %H:%M")],
        ["Status:", nota.status.value.title()]
    ]
    tabela_info = Table(info_nota, colWidths=[2 * inch, 4 * inch])
    tabela_info.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    elementos.append(tabela_info)
    elementos.append(Spacer(1, 20))

    # Informações do Fornecedor
    elementos.append(Paragraph("Dados do Fornecedor", styles['NotaSubTitulo']))
    info_fornecedor = [
        ["Nome:", nota.fornecedor.nome],
        ["CNPJ:", nota.fornecedor.cnpj],
        ["Telefone:", nota.fornecedor.telefone or "-"],
        ["Email:", nota.fornecedor.email or "-"]
    ]
    tabela_fornecedor = Table(info_fornecedor, colWidths=[2 * inch, 4 * inch])
    tabela_fornecedor.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    elementos.append(tabela_fornecedor)
    elementos.append(Spacer(1, 20))

    # Lista de Produtos
    elementos.append(Paragraph("Produtos", styles['NotaSubTitulo']))
    cabecalho = ["Código", "Referência", "Descrição", "Tam.", "Qtd.", "Valor Unit.", "Total"]
    dados_produtos = [cabecalho]

    total_geral = 0
    total_pecas = 0

    for produto in nota.produtos:
        valor_total = produto.quantidade_inicial * produto.valor_unitario
        total_geral += valor_total
        total_pecas += produto.quantidade_inicial

        dados_produtos.append([
            produto.codigo_barras,
            produto.referencia,
            produto.descricao,
            produto.tamanho,
            str(produto.quantidade_inicial),
            f"R$ {float(produto.valor_unitario):.2f}",
            f"R$ {float(valor_total):.2f}"
        ])

    # Adiciona totais
    dados_produtos.append(["", "", "", "", f"Total: {total_pecas}", "", f"R$ {float(total_geral):.2f}"])

    tabela_produtos = Table(dados_produtos, repeatRows=1)
    tabela_produtos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabela_produtos)
    elementos.append(Spacer(1, 20))

    # Observações (se houver)
    if nota.observacoes:
        elementos.append(Paragraph("Observações:", styles['NotaSubTitulo']))
        elementos.append(Paragraph(nota.observacoes, styles['Normal']))

    # Rodapé com informações de registro
    elementos.append(Spacer(1, 40))
    elementos.append(Paragraph(
        f"Registrado por: {nota.usuario_registro.nome}",
        styles['Normal']
    ))
    elementos.append(Paragraph(
        f"Documento gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        styles['Normal']
    ))

    # Gera o PDF
    doc.build(elementos)
    buffer.seek(0)
    return buffer