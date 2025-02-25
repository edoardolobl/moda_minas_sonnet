# src/controllers/estoque.py
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from ..models import Produto, NotaEntrada, Fornecedor, StatusProduto


class EstoqueController:
    def __init__(self, db: Session):
        self.db = db

    def visualizar_estoque_completo(self, page: int = 1, per_page: int = 50) -> Dict:
        """
        Retorna visão paginada do estoque completo com produtos agrupados
        """
        try:
            # Query base para produtos agrupados
            query = (
                self.db.query(
                    Produto.referencia,
                    Produto.descricao,
                    Produto.tamanho,
                    func.sum(Produto.quantidade_atual).label('quantidade_total'),
                    func.avg(Produto.valor_unitario).label('valor_unitario_medio'),
                    Fornecedor.nome.label('fornecedor_nome'),
                    func.min(NotaEntrada.data_emissao).label('primeira_entrada'),
                    func.max(NotaEntrada.data_emissao).label('ultima_entrada')
                )
                .join(NotaEntrada, Produto.nota_entrada_id == NotaEntrada.id)
                .join(Fornecedor, NotaEntrada.fornecedor_id == Fornecedor.id)
                .filter(Produto.status == StatusProduto.EM_ESTOQUE)
                .group_by(
                    Produto.referencia,
                    Produto.descricao,
                    Produto.tamanho,
                    Fornecedor.nome
                )
            )

            # Contagem total para paginação
            total = query.count()

            # Query para os dados da página atual
            produtos = (
                query.order_by(Produto.referencia)
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )

            # Calcula dias em estoque e status para cada grupo
            hoje = datetime.now()
            dados_produtos = []

            for produto in produtos:
                # Calcula dias desde a primeira entrada
                dias_em_estoque = (hoje - produto.primeira_entrada).days

                # Determina o status do produto
                if dias_em_estoque > 90:  # Mais de 90 dias = Sem Movimento
                    status = "⚠️ Sem Movim"
                elif produto.quantidade_total <= 3:  # 3 ou menos = Baixo Estoque
                    status = "⚡ Baixo Estoq"
                else:
                    status = "✅ Em Estoque"

                dados_produtos.append({
                    "status": status,
                    "referencia": produto.referencia,
                    "descricao": produto.descricao,
                    "tamanho": produto.tamanho,
                    "quantidade_total": produto.quantidade_total,
                    "valor_unitario": float(produto.valor_unitario_medio),
                    "fornecedor": produto.fornecedor_nome,
                    "data_entrada": produto.primeira_entrada.strftime("%d/%m/%Y"),
                    "dias_em_estoque": dias_em_estoque
                })

            return {
                "produtos": dados_produtos,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
                "current_page": page
            }

        except Exception as e:
            raise Exception(f"Erro ao visualizar estoque: {str(e)}")

    def buscar_estoque(self,
                       termo: str,
                       filtro: str = "referencia") -> List[Dict]:
        """
        Busca produtos no estoque por diferentes critérios
        """
        try:
            query = self.db.query(
                Produto,
                NotaEntrada.numero_nota,
                Fornecedor.nome.label('fornecedor_nome')
            ).join(
                NotaEntrada, Produto.nota_entrada_id == NotaEntrada.id
            ).join(
                Fornecedor, NotaEntrada.fornecedor_id == Fornecedor.id
            ).filter(
                Produto.status == StatusProduto.EM_ESTOQUE
            )

            # Aplicar filtro de busca
            if filtro == "referencia":
                query = query.filter(Produto.referencia.ilike(f"%{termo}%"))
            elif filtro == "descricao":
                query = query.filter(Produto.descricao.ilike(f"%{termo}%"))
            elif filtro == "codigo_barras":
                query = query.filter(Produto.codigo_barras == termo)
            elif filtro == "fornecedor":
                query = query.filter(Fornecedor.nome.ilike(f"%{termo}%"))

            resultados = []
            for produto, numero_nota, fornecedor_nome in query.all():
                resultados.append({
                    "id": produto.id,
                    "codigo_barras": produto.codigo_barras,
                    "referencia": produto.referencia,
                    "descricao": produto.descricao,
                    "tamanho": produto.tamanho,
                    "quantidade_atual": produto.quantidade_atual,
                    "valor_unitario": float(produto.valor_unitario),
                    "nota_entrada": numero_nota,
                    "fornecedor": fornecedor_nome
                })

            return resultados

        except Exception as e:
            raise Exception(f"Erro ao buscar estoque: {str(e)}")

    def analise_estoque_fornecedor(self, fornecedor_id: Optional[int] = None) -> List[Dict]:
        """
        Análise do estoque por fornecedor
        """
        try:
            query = self.db.query(
                Fornecedor.nome,
                func.count(Produto.id).label('total_produtos'),
                func.sum(Produto.quantidade_atual).label('total_pecas'),
                func.sum(Produto.quantidade_atual * Produto.valor_unitario).label('valor_total')
            ).join(
                NotaEntrada, Fornecedor.id == NotaEntrada.fornecedor_id
            ).join(
                Produto, NotaEntrada.id == Produto.nota_entrada_id
            ).filter(
                Produto.status == StatusProduto.EM_ESTOQUE
            ).group_by(
                Fornecedor.id, Fornecedor.nome
            )

            if fornecedor_id:
                query = query.filter(Fornecedor.id == fornecedor_id)

            resultados = []
            for nome, total_produtos, total_pecas, valor_total in query.all():
                resultados.append({
                    "fornecedor": nome,
                    "total_produtos": total_produtos,
                    "total_pecas": total_pecas or 0,
                    "valor_total": float(valor_total or 0)
                })

            return resultados

        except Exception as e:
            raise Exception(f"Erro ao analisar estoque por fornecedor: {str(e)}")

    def analise_estoque_antiguidade(self) -> Dict:
        """
        Análise do estoque por antiguidade dos produtos
        """
        try:
            hoje = datetime.now()
            faixas = {
                "ate_30_dias": (hoje - timedelta(days=30), hoje),
                "30_60_dias": (hoje - timedelta(days=60), hoje - timedelta(days=30)),
                "60_90_dias": (hoje - timedelta(days=90), hoje - timedelta(days=60)),
                "mais_90_dias": (None, hoje - timedelta(days=90))
            }

            resultado = {}
            for faixa, (data_inicio, data_fim) in faixas.items():
                query = self.db.query(
                    func.count(Produto.id).label('total_produtos'),
                    func.sum(Produto.quantidade_atual).label('total_pecas'),
                    func.sum(Produto.quantidade_atual * Produto.valor_unitario).label('valor_total')
                ).join(
                    NotaEntrada, Produto.nota_entrada_id == NotaEntrada.id
                ).filter(
                    Produto.status == StatusProduto.EM_ESTOQUE
                )

                if data_inicio:
                    query = query.filter(NotaEntrada.data_emissao >= data_inicio)
                if data_fim:
                    query = query.filter(NotaEntrada.data_emissao < data_fim)

                total_produtos, total_pecas, valor_total = query.first()

                resultado[faixa] = {
                    "total_produtos": total_produtos or 0,
                    "total_pecas": total_pecas or 0,
                    "valor_total": float(valor_total or 0)
                }

            return resultado

        except Exception as e:
            raise Exception(f"Erro ao analisar estoque por antiguidade: {str(e)}")

    def produtos_sem_movimento(self, dias: int = 30) -> List[Dict]:
        """
        Lista produtos sem movimentação no período especificado
        """
        try:
            data_limite = datetime.now() - timedelta(days=dias)

            produtos = self.db.query(
                Produto,
                NotaEntrada.numero_nota,
                Fornecedor.nome.label('fornecedor_nome')
            ).join(
                NotaEntrada, Produto.nota_entrada_id == NotaEntrada.id
            ).join(
                Fornecedor, NotaEntrada.fornecedor_id == Fornecedor.id
            ).filter(
                Produto.status == StatusProduto.EM_ESTOQUE,
                NotaEntrada.data_emissao < data_limite
            ).all()

            return [{
                "id": p.id,
                "codigo_barras": p.codigo_barras,
                "referencia": p.referencia,
                "descricao": p.descricao,
                "tamanho": p.tamanho,
                "quantidade_atual": p.quantidade_atual,
                "valor_unitario": float(p.valor_unitario),
                "nota_entrada": nota,
                "fornecedor": fornecedor,
                "dias_sem_movimento": (datetime.now() - p.data_registro).days
            } for p, nota, fornecedor in produtos]

        except Exception as e:
            raise Exception(f"Erro ao listar produtos sem movimento: {str(e)}")