# src/models/usuario.py
from sqlalchemy import Column, Integer, String, Enum, Boolean, DateTime
from sqlalchemy.sql import func
from .base import Base

import enum


class TipoUsuario(enum.Enum):
    MASTER = "master"
    ATENDENTE = "atendente"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    login = Column(String(50), unique=True, nullable=False, index=True)
    senha_hash = Column(String(100), nullable=False)
    tipo = Column(Enum(TipoUsuario), nullable=False)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Usuario(id={self.id}, nome={self.nome}, login={self.login}, tipo={self.tipo})>"