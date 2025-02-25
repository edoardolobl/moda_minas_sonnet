# src/models/nota.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

import enum


class StatusNota(enum.Enum):
    ATIVA = "ativa"
    FINALIZADA = "finalizada"
    DEVOLVIDA = "devolvida"


class NotaEntrada(Base):
    __tablename__ = "notas_entrada"

    id = Column(Integer, primary_key=True, index=True)
    numero_nota = Column(String(50), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=False)
    data_emissao = Column(DateTime(timezone=True), nullable=False)
    data_registro = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(StatusNota), default=StatusNota.ATIVA, nullable=False)
    usuario_registro_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    observacoes = Column(String(500))

    # Relacionamentos
    fornecedor = relationship("Fornecedor", back_populates="notas_entrada")
    usuario_registro = relationship("Usuario")
    produtos = relationship("Produto", back_populates="nota_entrada")

    # Índice composto para buscas eficientes
    __table_args__ = (
        # Criando índice composto para fornecedor_id e numero_nota
        # Útil para consultas que filtram por fornecedor e número da nota
        Index('idx_fornecedor_numero_nota', 'fornecedor_id', 'numero_nota'),
    )

    def __repr__(self):
        return f"<NotaEntrada(id={self.id}, numero_nota={self.numero_nota}, fornecedor_id={self.fornecedor_id})>"