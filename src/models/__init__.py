# src/models/__init__.py
from .base import Base, engine, get_db
from .usuario import Usuario, TipoUsuario
from .log import LogAcao, TipoAcao
from .fornecedor import Fornecedor
from .nota import NotaEntrada, StatusNota
from .produto import Produto, StatusProduto
from .venda import Venda, ItemVenda, FormaPagamento, StatusVenda

# Lista de todos os modelos para facilitar a criação das tabelas
all_models = [
    Usuario,
    LogAcao,
    Fornecedor,
    NotaEntrada,
    Produto,
    Venda,
    ItemVenda
]

# Função para criar todas as tabelas
def create_tables():
    Base.metadata.create_all(bind=engine)

# Função para dropar todas as tabelas (útil para testes e reset)
def drop_tables():
    Base.metadata.drop_all(bind=engine)