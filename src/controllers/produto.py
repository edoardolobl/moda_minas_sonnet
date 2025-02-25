# src/controllers/produto.py
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from ..models import Produto, NotaEntrada, StatusProduto, LogAcao, TipoAcao

class ProdutoController:
    def __init__(self, db: Session):
        self.db = db

    def buscar_produto_codigo_barras(self, codigo_barras: str) -> Optional[Produto]:
        """
        Busca um produto pelo código de barras
        """
        try:
            return self.db.query(Produto).filter(
                Produto.codigo_barras == codigo_barras,
                Produto.status == StatusProduto.EM_ESTOQUE
            ).first()
        except Exception as e:
            raise Exception(f"Erro ao buscar produto: {str(e)}")

    def buscar_produtos_disponiveis(self,
                                  referencia: Optional[str] = None,
                                  descricao: Optional[str] = None,
                                  tamanho: Optional[str] = None) -> List[Produto]:
        """
        Busca produtos disponíveis em estoque com filtros opcionais
        """
        try:
            query = self.db.query(Produto).filter(
                Produto.status == StatusProduto.EM_ESTOQUE,
                Produto.quantidade_atual > 0
            )

            if referencia:
                query = query.filter(Produto.referencia.ilike(f"%{referencia}%"))
            if descricao:
                query = query.filter(Produto.descricao.ilike(f"%{descricao}%"))
            if tamanho:
                query = query.filter(Produto.tamanho == tamanho)

            return query.order_by(Produto.data_registro).all()
        except Exception as e:
            raise Exception(f"Erro ao buscar produtos disponíveis: {str(e)}")

    def calcular_produtos_venda_fifo(self,
                                   referencia: str,
                                   tamanho: str,
                                   quantidade_desejada: int) -> List[Dict]:
        """
        Calcula quais produtos devem ser vendidos seguindo a lógica FIFO
        Retorna lista de produtos com suas respectivas quantidades para venda
        """
        try:
            # Busca produtos disponíveis ordenados por data de entrada (FIFO)
            produtos = self.db.query(Produto).join(
                NotaEntrada, Produto.nota_entrada_id == NotaEntrada.id
            ).filter(
                Produto.referencia == referencia,
                Produto.tamanho == tamanho,
                Produto.status == StatusProduto.EM_ESTOQUE,
                Produto.quantidade_atual > 0
            ).order_by(
                NotaEntrada.data_emissao,
                Produto.data_registro
            ).all()

            if not produtos:
                return []

            produtos_venda = []
            quantidade_restante = quantidade_desejada

            for produto in produtos:
                if quantidade_restante <= 0:
                    break

                quantidade_disponivel = produto.quantidade_atual
                quantidade_usar = min(quantidade_disponivel, quantidade_restante)

                produtos_venda.append({
                    'produto_id': produto.id,
                    'codigo_barras': produto.codigo_barras,
                    'valor_unitario': produto.valor_unitario,
                    'quantidade': quantidade_usar,
                    'nota_entrada_id': produto.nota_entrada_id
                })

                quantidade_restante -= quantidade_usar

            # Se não conseguiu atingir a quantidade desejada, retorna vazio
            if quantidade_restante > 0:
                return []

            return produtos_venda
        except Exception as e:
            raise Exception(f"Erro ao calcular produtos para venda: {str(e)}")

    def atualizar_estoque_venda(self,
                               produtos_venda: List[Dict],
                               usuario_id: int) -> bool:
        """
        Atualiza o estoque após uma venda
        """
        try:
            for item in produtos_venda:
                produto = self.db.query(Produto).filter(
                    Produto.id == item['produto_id']
                ).first()

                if not produto:
                    raise ValueError(f"Produto não encontrado: {item['produto_id']}")

                # Atualiza quantidade
                nova_quantidade = produto.quantidade_atual - item['quantidade']
                if nova_quantidade < 0:
                    raise ValueError(f"Quantidade insuficiente para o produto: {produto.codigo_barras}")

                produto.quantidade_atual = nova_quantidade

                # Atualiza status se necessário
                if nova_quantidade == 0:
                    produto.status = StatusProduto.VENDIDO

                # Registra no log
                log = LogAcao(
                    usuario_id=usuario_id,
                    tipo_acao=TipoAcao.VENDA,
                    descricao=f"Venda de {item['quantidade']} unidades do produto {produto.codigo_barras}",
                    tabela_afetada="produtos",
                    referencia_id=produto.id
                )
                self.db.add(log)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao atualizar estoque: {str(e)}")

    def obter_estatisticas_estoque(self) -> Dict:
        """
        Retorna estatísticas gerais do estoque
        """
        try:
            total_produtos = self.db.query(Produto).filter(
                Produto.status == StatusProduto.EM_ESTOQUE
            ).count()

            valor_total = self.db.query(
                func.sum(Produto.valor_unitario * Produto.quantidade_atual)
            ).filter(
                Produto.status == StatusProduto.EM_ESTOQUE
            ).scalar() or 0

            produtos_zerados = self.db.query(Produto).filter(
                Produto.status == StatusProduto.EM_ESTOQUE,
                Produto.quantidade_atual == 0
            ).count()

            return {
                "total_produtos": total_produtos,
                "valor_total_estoque": float(valor_total),
                "produtos_zerados": produtos_zerados
            }
        except Exception as e:
            raise Exception(f"Erro ao obter estatísticas: {str(e)}")

    def preparar_devolucao(self, nota_id: int) -> List[Dict]:
        """
        Prepara lista de produtos disponíveis para devolução de uma nota
        """
        try:
            produtos = self.db.query(Produto).filter(
                Produto.nota_entrada_id == nota_id,
                Produto.status == StatusProduto.EM_ESTOQUE,
                Produto.quantidade_atual > 0
            ).all()

            return [
                {
                    "produto_id": p.id,
                    "codigo_barras": p.codigo_barras,
                    "referencia": p.referencia,
                    "descricao": p.descricao,
                    "tamanho": p.tamanho,
                    "quantidade_disponivel": p.quantidade_atual,
                    "valor_unitario": p.valor_unitario
                }
                for p in produtos
            ]
        except Exception as e:
            raise Exception(f"Erro ao preparar devolução: {str(e)}")

    def processar_devolucao(self,
                           produtos_devolucao: List[Dict],
                           usuario_id: int) -> bool:
        """
        Processa a devolução de produtos
        """
        try:
            for item in produtos_devolucao:
                produto = self.db.query(Produto).filter(
                    Produto.id == item['produto_id'],
                    Produto.status == StatusProduto.EM_ESTOQUE
                ).first()

                if not produto:
                    raise ValueError(f"Produto não encontrado ou não disponível: {item['produto_id']}")

                if item['quantidade'] > produto.quantidade_atual:
                    raise ValueError(f"Quantidade para devolução maior que disponível: {produto.codigo_barras}")

                produto.quantidade_atual -= item['quantidade']
                if produto.quantidade_atual == 0:
                    produto.status = StatusProduto.DEVOLVIDO

                # Registra no log
                log = LogAcao(
                    usuario_id=usuario_id,
                    tipo_acao=TipoAcao.DEVOLUCAO,
                    descricao=f"Devolução de {item['quantidade']} unidades do produto {produto.codigo_barras}",
                    tabela_afetada="produtos",
                    referencia_id=produto.id
                )
                self.db.add(log)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao processar devolução: {str(e)}")