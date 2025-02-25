# src/controllers/nota_entrada.py
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models import NotaEntrada, Fornecedor, Produto, LogAcao, TipoAcao, StatusNota, StatusProduto


class NotaEntradaController:
    def __init__(self, db: Session):
        self.db = db

    def criar_nota_entrada(self,
                           numero_nota: str,
                           fornecedor_id: int,
                           data_emissao: datetime,
                           usuario_id: int,
                           observacoes: str = None) -> Optional[NotaEntrada]:
        """
        Cria uma nova nota de entrada
        """
        try:
            # Verifica se o fornecedor existe e está ativo
            fornecedor = self.db.query(Fornecedor).filter(
                Fornecedor.id == fornecedor_id,
                Fornecedor.ativo == True
            ).first()

            if not fornecedor:
                raise ValueError("Fornecedor não encontrado ou inativo")

            # Verifica se já existe nota com mesmo número para este fornecedor
            nota_existente = self.db.query(NotaEntrada).filter(
                NotaEntrada.numero_nota == numero_nota,
                NotaEntrada.fornecedor_id == fornecedor_id
            ).first()

            if nota_existente:
                raise ValueError("Já existe uma nota com este número para este fornecedor")

            # Cria a nota
            nota = NotaEntrada(
                numero_nota=numero_nota,
                fornecedor_id=fornecedor_id,
                data_emissao=data_emissao,
                usuario_registro_id=usuario_id,
                observacoes=observacoes,
                status=StatusNota.ATIVA
            )

            self.db.add(nota)
            self.db.flush()  # Para obter o ID da nota

            # Registra no log
            log = LogAcao(
                usuario_id=usuario_id,
                tipo_acao=TipoAcao.INSERCAO_ITEM,
                descricao=f"Criação de nota de entrada: {numero_nota} - Fornecedor: {fornecedor.nome}",
                tabela_afetada="notas_entrada",
                referencia_id=nota.id
            )
            self.db.add(log)

            self.db.commit()
            return nota

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao criar nota de entrada: {str(e)}")

    def adicionar_produto(self,
                          nota_id: int,
                          codigo_barras: str,
                          referencia: str,
                          descricao: str,
                          tamanho: str,
                          valor_unitario: float,
                          quantidade: int,
                          usuario_id: int) -> Optional[Produto]:
        """
        Adiciona um produto à nota de entrada
        """
        try:
            # Verifica se a nota existe e está ativa
            nota = self.db.query(NotaEntrada).filter(
                NotaEntrada.id == nota_id,
                NotaEntrada.status == StatusNota.ATIVA
            ).first()

            if not nota:
                raise ValueError("Nota de entrada não encontrada ou não está ativa")

            # Verifica se o código de barras já existe
            produto_existente = self.db.query(Produto).filter(
                Produto.codigo_barras == codigo_barras
            ).first()

            if produto_existente:
                raise ValueError("Código de barras já cadastrado no sistema")

            # Cria o produto
            produto = Produto(
                nota_entrada_id=nota_id,
                codigo_barras=codigo_barras,
                referencia=referencia,
                descricao=descricao,
                tamanho=tamanho,
                valor_unitario=valor_unitario,
                quantidade_inicial=quantidade,
                quantidade_atual=quantidade,
                status=StatusProduto.EM_ESTOQUE,
                usuario_registro_id=usuario_id
            )

            self.db.add(produto)
            self.db.flush()

            # Registra no log
            log = LogAcao(
                usuario_id=usuario_id,
                tipo_acao=TipoAcao.INSERCAO_ITEM,
                descricao=f"Produto adicionado à nota {nota.numero_nota}: {descricao}",
                tabela_afetada="produtos",
                referencia_id=produto.id
            )
            self.db.add(log)

            self.db.commit()
            return produto

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao adicionar produto: {str(e)}")

    def finalizar_nota(self, nota_id: int, usuario_id: int) -> bool:
        """
        Finaliza uma nota de entrada, impedindo novas alterações
        """
        try:
            nota = self.db.query(NotaEntrada).filter(
                NotaEntrada.id == nota_id,
                NotaEntrada.status == StatusNota.ATIVA
            ).first()

            if not nota:
                raise ValueError("Nota não encontrada ou não está ativa")

            # Verifica se há produtos na nota
            produtos = self.db.query(Produto).filter(
                Produto.nota_entrada_id == nota_id
            ).all()

            if not produtos:
                raise ValueError("Não é possível finalizar uma nota sem produtos")

            nota.status = StatusNota.FINALIZADA

            # Registra no log
            log = LogAcao(
                usuario_id=usuario_id,
                tipo_acao=TipoAcao.ALTERACAO_USUARIO,
                descricao=f"Finalização da nota de entrada: {nota.numero_nota}",
                tabela_afetada="notas_entrada",
                referencia_id=nota.id
            )
            self.db.add(log)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao finalizar nota: {str(e)}")

    def buscar_nota(self, nota_id: int) -> Optional[NotaEntrada]:
        """
        Busca uma nota de entrada pelo ID
        """
        try:
            return self.db.query(NotaEntrada).filter(
                NotaEntrada.id == nota_id
            ).first()
        except Exception as e:
            raise Exception(f"Erro ao buscar nota: {str(e)}")

    def listar_produtos_nota(self, nota_id: int) -> List[Produto]:
        """
        Lista todos os produtos de uma nota
        """
        try:
            return self.db.query(Produto).filter(
                Produto.nota_entrada_id == nota_id
            ).all()
        except Exception as e:
            raise Exception(f"Erro ao listar produtos da nota: {str(e)}")

    def buscar_notas_por_periodo(self,
                                 data_inicio: datetime,
                                 data_fim: datetime,
                                 fornecedor_id: Optional[int] = None) -> List[NotaEntrada]:
        """
        Busca notas de entrada por período e opcionalmente por fornecedor
        """
        try:
            query = self.db.query(NotaEntrada).filter(
                NotaEntrada.data_emissao >= data_inicio,
                NotaEntrada.data_emissao <= data_fim
            )

            if fornecedor_id:
                query = query.filter(NotaEntrada.fornecedor_id == fornecedor_id)

            return query.order_by(NotaEntrada.data_emissao.desc()).all()
        except Exception as e:
            raise Exception(f"Erro ao buscar notas por período: {str(e)}")

    def buscar_notas_para_devolucao(self, fornecedor_id: int) -> List[NotaEntrada]:
        """
        Busca notas finalizadas com produtos em estoque para possível devolução
        """
        try:
            # Busca notas que tenham pelo menos um produto em estoque
            notas = self.db.query(NotaEntrada).join(
                Produto, NotaEntrada.id == Produto.nota_entrada_id
            ).filter(
                NotaEntrada.fornecedor_id == fornecedor_id,
                NotaEntrada.status == StatusNota.FINALIZADA,
                Produto.status == StatusProduto.EM_ESTOQUE,
                Produto.quantidade_atual > 0
            ).distinct().all()

            return notas
        except Exception as e:
            raise Exception(f"Erro ao buscar notas para devolução: {str(e)}")