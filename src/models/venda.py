# src/models/venda.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Numeric, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

import enum


class FormaPagamento(enum.Enum):
    DINHEIRO = "dinheiro"
    CARTAO_CREDITO = "cartao_credito"
    CARTAO_DEBITO = "cartao_debito"
    PIX = "pix"


class StatusVenda(enum.Enum):
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"


class Venda(Base):
    __tablename__ = "vendas"

    id = Column(Integer, primary_key=True, index=True)
    data_hora = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cliente_nome = Column(String(100), nullable=False)
    cliente_cpf = Column(String(11))
    valor_total = Column(Numeric(10, 2), nullable=False)
    forma_pagamento = Column(Enum(FormaPagamento), nullable=False)
    status = Column(Enum(StatusVenda), default=StatusVenda.FINALIZADA, nullable=False)
    observacoes = Column(String(500))

    # Relacionamentos
    usuario = relationship("Usuario")
    itens = relationship("ItemVenda", back_populates="venda")

    def __repr__(self):
        return f"<Venda(id={self.id}, cliente={self.cliente_nome}, valor_total={self.valor_total})>"


class ItemVenda(Base):
    __tablename__ = "itens_venda"

    id = Column(Integer, primary_key=True, index=True)
    venda_id = Column(Integer, ForeignKey("vendas.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    valor_unitario = Column(Numeric(10, 2), nullable=False)
    nota_entrada_id = Column(Integer, ForeignKey("notas_entrada.id"), nullable=False)

    # Relacionamentos
    venda = relationship("Venda", back_populates="itens")
    produto = relationship("Produto", back_populates="itens_venda")
    nota_entrada = relationship("NotaEntrada")

    # Índice composto para consultas FIFO
    __table_args__ = (
        Index('idx_item_venda_nota', 'nota_entrada_id', 'produto_id'),
    )

    def __repr__(self):
        return f"<ItemVenda(id={self.id}, venda_id={self.venda_id}, produto_id={self.produto_id})>"

    @property
    def valor_total(self):
        """Calcula o valor total do item"""
        return self.quantidade * self.valor_unitario