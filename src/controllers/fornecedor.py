# src/controllers/fornecedor.py
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models import Fornecedor, LogAcao, TipoAcao, NotaEntrada, StatusNota


class FornecedorController:
    def __init__(self, db: Session):
        self.db = db

    def criar_fornecedor(self, nome: str, cnpj: str, telefone: str,
                         email: str, usuario_id: int) -> Optional[Fornecedor]:
        """
        Cria um novo fornecedor
        Retorna o fornecedor criado ou None em caso de erro
        """
        try:
            # Verifica se já existe fornecedor com mesmo CNPJ
            if self.db.query(Fornecedor).filter(Fornecedor.cnpj == cnpj).first():
                raise ValueError("CNPJ já cadastrado no sistema")

            # Cria o fornecedor
            fornecedor = Fornecedor(
                nome=nome,
                cnpj=cnpj,
                telefone=telefone,
                email=email,
                ativo=True
            )
            self.db.add(fornecedor)
            self.db.flush()  # Para obter o ID do fornecedor

            # Registra a criação no log
            log = LogAcao(
                usuario_id=usuario_id,
                tipo_acao=TipoAcao.ALTERACAO_USUARIO,
                descricao=f"Criação de novo fornecedor: {nome} (CNPJ: {cnpj})",
                tabela_afetada="fornecedores",
                referencia_id=fornecedor.id
            )
            self.db.add(log)

            self.db.commit()
            return fornecedor

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao criar fornecedor: {str(e)}")

    def atualizar_fornecedor(self, fornecedor_id: int, usuario_id: int,
                             **dados_atualizacao) -> Optional[Fornecedor]:
        """
        Atualiza os dados de um fornecedor
        dados_atualizacao pode conter: nome, telefone, email
        """
        try:
            fornecedor = self.db.query(Fornecedor).filter(
                Fornecedor.id == fornecedor_id,
                Fornecedor.ativo == True
            ).first()

            if not fornecedor:
                raise ValueError("Fornecedor não encontrado ou inativo")

            # Atualiza apenas os campos fornecidos
            campos_atualizados = []
            for campo, valor in dados_atualizacao.items():
                if hasattr(fornecedor, campo) and valor is not None:
                    valor_antigo = getattr(fornecedor, campo)
                    if valor_antigo != valor:
                        setattr(fornecedor, campo, valor)
                        campos_atualizados.append(f"{campo}: {valor_antigo} -> {valor}")

            if campos_atualizados:
                # Registra as alterações no log
                log = LogAcao(
                    usuario_id=usuario_id,
                    tipo_acao=TipoAcao.ALTERACAO_USUARIO,
                    descricao=f"Atualização do fornecedor {fornecedor.nome}: {', '.join(campos_atualizados)}",
                    tabela_afetada="fornecedores",
                    referencia_id=fornecedor.id
                )
                self.db.add(log)

                self.db.commit()

            return fornecedor

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao atualizar fornecedor: {str(e)}")

    def desativar_fornecedor(self, fornecedor_id: int, usuario_id: int) -> bool:
        """
        Desativa um fornecedor (exclusão lógica)
        Retorna True se desativado com sucesso
        """
        try:
            fornecedor = self.db.query(Fornecedor).filter(
                Fornecedor.id == fornecedor_id,
                Fornecedor.ativo == True
            ).first()

            if not fornecedor:
                raise ValueError("Fornecedor não encontrado ou já inativo")

            fornecedor.ativo = False

            # Registra a desativação no log
            log = LogAcao(
                usuario_id=usuario_id,
                tipo_acao=TipoAcao.ALTERACAO_USUARIO,
                descricao=f"Desativação do fornecedor: {fornecedor.nome}",
                tabela_afetada="fornecedores",
                referencia_id=fornecedor.id
            )
            self.db.add(log)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao desativar fornecedor: {str(e)}")

    def buscar_fornecedor(self, fornecedor_id: int) -> Optional[Fornecedor]:
        """Busca um fornecedor pelo ID"""
        try:
            return self.db.query(Fornecedor).filter(
                Fornecedor.id == fornecedor_id,
                Fornecedor.ativo == True
            ).first()
        except Exception as e:
            raise Exception(f"Erro ao buscar fornecedor: {str(e)}")

    def listar_fornecedores(self, apenas_ativos: bool = True) -> List[Fornecedor]:
        """Lista todos os fornecedores"""
        try:
            query = self.db.query(Fornecedor)
            if apenas_ativos:
                query = query.filter(Fornecedor.ativo == True)
            return query.order_by(Fornecedor.nome).all()
        except Exception as e:
            raise Exception(f"Erro ao listar fornecedores: {str(e)}")

    def pesquisar_fornecedores(self, termo_busca: str) -> List[Fornecedor]:
        """
        Pesquisa fornecedores por nome ou CNPJ
        Retorna lista de fornecedores que correspondem à busca
        """
        try:
            return self.db.query(Fornecedor).filter(
                Fornecedor.ativo == True,
                or_(
                    Fornecedor.nome.ilike(f"%{termo_busca}%"),
                    Fornecedor.cnpj.ilike(f"%{termo_busca}%")
                )
            ).order_by(Fornecedor.nome).all()
        except Exception as e:
            raise Exception(f"Erro ao pesquisar fornecedores: {str(e)}")

    def validar_cnpj(self, cnpj: str) -> bool:
        """Valida o formato e dígitos verificadores do CNPJ"""
        # Remove caracteres não numéricos
        cnpj = ''.join(filter(str.isdigit, cnpj))

        # Verifica se tem 14 dígitos
        if len(cnpj) != 14:
            return False

        # Verifica se todos os dígitos são iguais
        if len(set(cnpj)) == 1:
            return False

        # Calcula primeiro dígito verificador
        soma = 0
        peso = 5
        for i in range(12):
            soma += int(cnpj[i]) * peso
            peso = peso - 1 if peso > 2 else 9

        digito1 = 11 - (soma % 11)
        digito1 = 0 if digito1 > 9 else digito1

        # Calcula segundo dígito verificador
        soma = 0
        peso = 6
        for i in range(13):
            soma += int(cnpj[i]) * peso
            peso = peso - 1 if peso > 2 else 9

        digito2 = 11 - (soma % 11)
        digito2 = 0 if digito2 > 9 else digito2

        # Verifica se os dígitos calculados são iguais aos do CNPJ
        return int(cnpj[12]) == digito1 and int(cnpj[13]) == digito2

    # Adicionar ao src/controllers/fornecedor.py

    def alterar_status_fornecedor(self, fornecedor_id: int, ativo: bool, usuario_id: int) -> bool:
        """
        Altera o status de um fornecedor (ativar/desativar)
        """
        try:
            # Busca o fornecedor
            fornecedor = self.db.query(Fornecedor).filter(
                Fornecedor.id == fornecedor_id
            ).first()

            if not fornecedor:
                raise ValueError("Fornecedor não encontrado")

            # Se estiver desativando, verifica se há notas ativas
            if not ativo:
                notas_ativas = self.db.query(NotaEntrada).filter(
                    NotaEntrada.fornecedor_id == fornecedor_id,
                    NotaEntrada.status == StatusNota.ATIVA
                ).first()

                if notas_ativas:
                    raise ValueError("Não é possível desativar fornecedor com notas ativas")

            # Atualiza o status
            fornecedor.ativo = ativo

            # Registra no log
            log = LogAcao(
                usuario_id=usuario_id,
                tipo_acao=TipoAcao.ALTERACAO_USUARIO,
                descricao=f"{'Ativação' if ativo else 'Desativação'} do fornecedor: {fornecedor.nome}",
                tabela_afetada="fornecedores",
                referencia_id=fornecedor.id
            )
            self.db.add(log)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao alterar status do fornecedor: {str(e)}")