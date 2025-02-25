# src/controllers/auth.py
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Usuario, LogAcao, TipoAcao
from ..utils.database import verificar_senha


class AuthController:
    def __init__(self, db: Session):
        self.db = db

    def autenticar_usuario(self, login: str, senha: str) -> Optional[Usuario]:
        """
        Autentica um usuário com login e senha
        Retorna o usuário se autenticado, None caso contrário
        """
        try:
            # Busca o usuário pelo login
            usuario = self.db.query(Usuario).filter(Usuario.login == login).first()

            if usuario and usuario.ativo and verificar_senha(senha, usuario.senha_hash):
                # Registra o log de login
                log = LogAcao(
                    usuario_id=usuario.id,
                    tipo_acao=TipoAcao.LOGIN,
                    descricao=f"Login realizado com sucesso - {datetime.now()}",
                    tabela_afetada="usuarios"
                )
                self.db.add(log)
                self.db.commit()
                return usuario

            return None

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro durante autenticação: {str(e)}")

    def verificar_permissao(self, usuario_id: int, tipo_permissao: str) -> bool:
        """
        Verifica se um usuário tem determinada permissão
        tipo_permissao pode ser 'master' para verificar se é administrador
        """
        try:
            usuario = self.db.query(Usuario).filter(Usuario.id == usuario_id).first()

            if not usuario or not usuario.ativo:
                return False

            if tipo_permissao == 'master':
                return usuario.tipo.value == 'master'

            return True  # Usuários ativos têm permissões básicas

        except Exception as e:
            raise Exception(f"Erro ao verificar permissão: {str(e)}")

    def obter_usuario(self, usuario_id: int) -> Optional[Usuario]:
        """Retorna os dados de um usuário pelo ID"""
        try:
            return self.db.query(Usuario).filter(
                Usuario.id == usuario_id,
                Usuario.ativo == True
            ).first()
        except Exception as e:
            raise Exception(f"Erro ao obter usuário: {str(e)}")

    def alterar_senha(self, usuario_id: int, senha_atual: str, nova_senha: str) -> bool:
        """
        Altera a senha de um usuário
        Retorna True se alterada com sucesso, False caso contrário
        """
        try:
            usuario = self.db.query(Usuario).filter(Usuario.id == usuario_id).first()

            if not usuario or not usuario.ativo:
                return False

            # Verifica se a senha atual está correta
            if not verificar_senha(senha_atual, usuario.senha_hash):
                return False

            from ..utils.database import hash_senha
            usuario.senha_hash = hash_senha(nova_senha)

            # Registra a alteração no log
            log = LogAcao(
                usuario_id=usuario_id,
                tipo_acao=TipoAcao.ALTERACAO_USUARIO,
                descricao="Alteração de senha realizada",
                tabela_afetada="usuarios"
            )
            self.db.add(log)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao alterar senha: {str(e)}")

    def listar_usuarios(self) -> list[Usuario]:
        """Retorna lista de todos os usuários ativos"""
        try:
            return self.db.query(Usuario).filter(Usuario.ativo == True).all()
        except Exception as e:
            raise Exception(f"Erro ao listar usuários: {str(e)}")

    def criar_usuario(self, nome: str, login: str, senha: str, tipo: str,
                      usuario_criador_id: int) -> Optional[Usuario]:
        """
        Cria um novo usuário
        Retorna o usuário criado ou None em caso de erro
        """
        try:
            # Verifica se o login já existe
            if self.db.query(Usuario).filter(Usuario.login == login).first():
                return None

            from ..utils.database import hash_senha
            from ..models import TipoUsuario

            novo_usuario = Usuario(
                nome=nome,
                login=login,
                senha_hash=hash_senha(senha),
                tipo=TipoUsuario[tipo.upper()],
                ativo=True
            )

            self.db.add(novo_usuario)
            self.db.flush()  # Para obter o ID do novo usuário

            # Registra a criação no log
            log = LogAcao(
                usuario_id=usuario_criador_id,
                tipo_acao=TipoAcao.ALTERACAO_USUARIO,
                descricao=f"Criação de novo usuário: {login}",
                tabela_afetada="usuarios",
                referencia_id=novo_usuario.id
            )
            self.db.add(log)

            self.db.commit()
            return novo_usuario

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao criar usuário: {str(e)}")