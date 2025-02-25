# src/models/log.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

import enum


class TipoAcao(enum.Enum):
    INSERCAO_ITEM = "insercao_item"
    VENDA = "venda"
    DEVOLUCAO = "devolucao"
    LOGIN = "login"
    ALTERACAO_PRODUTO = "alteracao_produto"
    ALTERACAO_USUARIO = "alteracao_usuario"


class LogAcao(Base):
    __tablename__ = "log_acoes"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    data_hora = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    tipo_acao = Column(Enum(TipoAcao), nullable=False)
    descricao = Column(String(500), nullable=False)
    referencia_id = Column(Integer)  # ID do registro afetado
    tabela_afetada = Column(String(50))  # Nome da tabela afetada

    # Relacionamento com usuário
    usuario = relationship("Usuario")

    def __repr__(self):
        return f"<LogAcao(id={self.id}, usuario_id={self.usuario_id}, tipo_acao={self.tipo_acao})>"