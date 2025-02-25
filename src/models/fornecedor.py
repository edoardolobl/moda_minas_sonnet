# src/models/fornecedor.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    cnpj = Column(String(14), unique=True, nullable=False, index=True)
    telefone = Column(String(20))
    email = Column(String(100))
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    notas_entrada = relationship("NotaEntrada", back_populates="fornecedor")

    def __repr__(self):
        return f"<Fornecedor(id={self.id}, nome={self.nome}, cnpj={self.cnpj})>"