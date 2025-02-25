# src/controllers/venda.py
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Venda, ItemVenda, Produto, LogAcao, TipoAcao, FormaPagamento, StatusVenda
from .produto import ProdutoController


class VendaController:
    def __init__(self, db: Session):
        self.db = db
        self.produto_controller = ProdutoController(db)

    def iniciar_venda(self,
                      usuario_id: int,
                      cliente_nome: str,
                      cliente_cpf: Optional[str] = None) -> Venda:
        """
        Inicia uma nova venda
        """
        try:
            venda = Venda(
                usuario_id=usuario_id,
                cliente_nome=cliente_nome,
                cliente_cpf=cliente_cpf,
                valor_total=0,
                status=StatusVenda.FINALIZADA
            )

            self.db.add(venda)
            self.db.flush()  # Para obter o ID da venda

            # Registra no log
            log = LogAcao(
                usuario_id=usuario_id,
                tipo_acao=TipoAcao.VENDA,
                descricao=f"Início de venda para cliente: {cliente_nome}",
                tabela_afetada="vendas",
                referencia_id=venda.id
            )
            self.db.add(log)

            self.db.commit()
            return venda

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao iniciar venda: {str(e)}")

    def adicionar_item(self,
                       venda_id: int,
                       referencia: str,
                       tamanho: str,
                       quantidade: int,
                       usuario_id: int) -> List[ItemVenda]:
        """
        Adiciona um item à venda usando a lógica FIFO
        """
        try:
            # Calcula quais produtos serão usados (FIFO)
            produtos_venda = self.produto_controller.calcular_produtos_venda_fifo(
                referencia=referencia,
                tamanho=tamanho,
                quantidade_desejada=quantidade
            )

            if not produtos_venda:
                raise ValueError("Produtos insuficientes em estoque")

            itens_venda = []
            for produto_info in produtos_venda:
                item = ItemVenda(
                    venda_id=venda_id,
                    produto_id=produto_info['produto_id'],
                    quantidade=produto_info['quantidade'],
                    valor_unitario=produto_info['valor_unitario'],
                    nota_entrada_id=produto_info['nota_entrada_id']
                )
                self.db.add(item)
                itens_venda.append(item)

            # Atualiza o estoque
            self.produto_controller.atualizar_estoque_venda(produtos_venda, usuario_id)

            # Atualiza o valor total da venda
            self.atualizar_valor_total(venda_id)

            self.db.commit()
            return itens_venda

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao adicionar item: {str(e)}")

    def atualizar_valor_total(self, venda_id: int):
        """
        Atualiza o valor total da venda
        """
        try:
            total = self.db.query(
                func.sum(ItemVenda.quantidade * ItemVenda.valor_unitario)
            ).filter(
                ItemVenda.venda_id == venda_id
            ).scalar() or 0

            venda = self.db.query(Venda).filter(Venda.id == venda_id).first()
            venda.valor_total = total

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao atualizar valor total: {str(e)}")

    def finalizar_venda(self,
                        venda_id: int,
                        forma_pagamento: FormaPagamento,
                        usuario_id: int) -> Venda:
        """
        Finaliza a venda com a forma de pagamento
        """
        try:
            venda = self.db.query(Venda).filter(Venda.id == venda_id).first()
            if not venda:
                raise ValueError("Venda não encontrada")

            # Verifica se há itens na venda
            itens = self.db.query(ItemVenda).filter(
                ItemVenda.venda_id == venda_id
            ).all()
            if not itens:
                raise ValueError("Não é possível finalizar uma venda sem itens")

            venda.forma_pagamento = forma_pagamento

            # Registra no log
            log = LogAcao(
                usuario_id=usuario_id,
                tipo_acao=TipoAcao.VENDA,
                descricao=f"Finalização de venda - Valor: R${venda.valor_total:.2f}",
                tabela_afetada="vendas",
                referencia_id=venda.id
            )
            self.db.add(log)

            self.db.commit()
            return venda

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao finalizar venda: {str(e)}")

    def cancelar_venda(self, venda_id: int, usuario_id: int) -> bool:
        """
        Cancela uma venda e estorna os produtos para o estoque
        """
        try:
            venda = self.db.query(Venda).filter(Venda.id == venda_id).first()
            if not venda:
                raise ValueError("Venda não encontrada")

            # Estorna os produtos para o estoque
            itens = self.db.query(ItemVenda).filter(
                ItemVenda.venda_id == venda_id
            ).all()

            for item in itens:
                produto = self.db.query(Produto).filter(
                    Produto.id == item.produto_id
                ).first()

                produto.quantidade_atual += item.quantidade
                produto.status = StatusProduto.EM_ESTOQUE

            venda.status = StatusVenda.CANCELADA

            # Registra no log
            log = LogAcao(
                usuario_id=usuario_id,
                tipo_acao=TipoAcao.VENDA,
                descricao=f"Cancelamento de venda - ID: {venda_id}",
                tabela_afetada="vendas",
                referencia_id=venda.id
            )
            self.db.add(log)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao cancelar venda: {str(e)}")

    def buscar_venda(self, venda_id: int) -> Optional[Dict]:
        """
        Busca uma venda com seus itens
        """
        try:
            venda = self.db.query(Venda).filter(Venda.id == venda_id).first()
            if not venda:
                return None

            itens = self.db.query(ItemVenda).filter(
                ItemVenda.venda_id == venda_id
            ).all()

            return {
                "venda": venda,
                "itens": itens
            }

        except Exception as e:
            raise Exception(f"Erro ao buscar venda: {str(e)}")

    def relatorio_vendas_periodo(self,
                                 data_inicio: datetime,
                                 data_fim: datetime) -> List[Dict]:
        """
        Gera relatório de vendas por período
        """
        try:
            vendas = self.db.query(Venda).filter(
                Venda.data_hora >= data_inicio,
                Venda.data_hora <= data_fim,
                Venda.status == StatusVenda.FINALIZADA
            ).all()

            relatorio = []
            for venda in vendas:
                itens = self.db.query(ItemVenda).filter(
                    ItemVenda.venda_id == venda.id
                ).all()

                relatorio.append({
                    "id": venda.id,
                    "data_hora": venda.data_hora,
                    "cliente_nome": venda.cliente_nome,
                    "valor_total": float(venda.valor_total),
                    "forma_pagamento": venda.forma_pagamento.value,
                    "quantidade_itens": len(itens)
                })

            return relatorio

        except Exception as e:
            raise Exception(f"Erro ao gerar relatório: {str(e)}")

    def resumo_vendas_dia(self, data: datetime) -> Dict:
        """
        Retorna resumo das vendas do dia
        """
        try:
            inicio_dia = data.replace(hour=0, minute=0, second=0, microsecond=0)
            fim_dia = data.replace(hour=23, minute=59, second=59, microsecond=999999)

            total_vendas = self.db.query(func.count(Venda.id)).filter(
                Venda.data_hora.between(inicio_dia, fim_dia),
                Venda.status == StatusVenda.FINALIZADA
            ).scalar()

            valor_total = self.db.query(func.sum(Venda.valor_total)).filter(
                Venda.data_hora.between(inicio_dia, fim_dia),
                Venda.status == StatusVenda.FINALIZADA
            ).scalar() or 0

            vendas_por_pagamento = self.db.query(
                Venda.forma_pagamento,
                func.count(Venda.id),
                func.sum(Venda.valor_total)
            ).filter(
                Venda.data_hora.between(inicio_dia, fim_dia),
                Venda.status == StatusVenda.FINALIZADA
            ).group_by(Venda.forma_pagamento).all()

            return {
                "total_vendas": total_vendas,
                "valor_total": float(valor_total),
                "vendas_por_pagamento": [
                    {
                        "forma": forma.value,
                        "quantidade": quantidade,
                        "valor_total": float(valor)
                    }
                    for forma, quantidade, valor in vendas_por_pagamento
                ]
            }

        except Exception as e:
            raise Exception(f"Erro ao gerar resumo do dia: {str(e)}")