# src/models/produto.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Numeric, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

import enum


class StatusProduto(enum.Enum):
    EM_ESTOQUE = "em_estoque"
    VENDIDO = "vendido"
    DEVOLVIDO = "devolvido"


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    codigo_barras = Column(String(50), unique=True, nullable=False, index=True)
    nota_entrada_id = Column(Integer, ForeignKey("notas_entrada.id"), nullable=False)
    referencia = Column(String(50), nullable=False)
    descricao = Column(String(200), nullable=False)
    tamanho = Column(String(10), nullable=False)
    valor_unitario = Column(Numeric(10, 2), nullable=False)
    quantidade_inicial = Column(Integer, nullable=False)
    quantidade_atual = Column(Integer, nullable=False)
    status = Column(Enum(StatusProduto), default=StatusProduto.EM_ESTOQUE, nullable=False)
    data_registro = Column(DateTime(timezone=True), server_default=func.now())
    usuario_registro_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    # Relacionamentos
    nota_entrada = relationship("NotaEntrada", back_populates="produtos")
    usuario_registro = relationship("Usuario")
    itens_venda = relationship("ItemVenda", back_populates="produto")

    # Índices compostos
    __table_args__ = (
        Index('idx_nota_status', 'nota_entrada_id', 'status'),
        Index('idx_produto_busca', 'referencia', 'descricao', 'tamanho'),
    )

    def __repr__(self):
        return f"<Produto(id={self.id}, codigo_barras={self.codigo_barras}, referencia={self.referencia})>"

    def atualizar_quantidade(self, quantidade_vendida):
        """Atualiza a quantidade do produto após uma venda"""
        if quantidade_vendida <= self.quantidade_atual:
            self.quantidade_atual -= quantidade_vendida
            if self.quantidade_atual == 0:
                self.status = StatusProduto.VENDIDO
            return True
        return False