# src/utils/database.py
import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from ..models import create_tables, get_db, Usuario, TipoUsuario, LogAcao, TipoAcao


def hash_senha(senha: str) -> str:
    """Cria um hash da senha fornecida"""
    senha_bytes = senha.encode('utf-8')
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(senha_bytes, salt)
    return hash_bytes.decode('utf-8')


def verificar_senha(senha: str, hash_senha: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    senha_bytes = senha.encode('utf-8')
    hash_bytes = hash_senha.encode('utf-8')
    return bcrypt.checkpw(senha_bytes, hash_bytes)


def verificar_tabelas_existem(engine):
    """Verifica se todas as tabelas foram criadas"""
    inspector = inspect(engine)
    tabelas_esperadas = ['usuarios', 'log_acoes', 'fornecedores', 'notas_entrada',
                         'produtos', 'vendas', 'itens_venda']
    tabelas_existentes = inspector.get_table_names()

    for tabela in tabelas_esperadas:
        if tabela not in tabelas_existentes:
            return False
    return True


def criar_usuario_admin(db: Session, login: str, senha: str, nome: str):
    """Cria um usuário administrador se ele não existir"""
    try:
        # Verifica se já existe um usuário admin
        usuario = db.query(Usuario).filter(Usuario.login == login).first()
        if not usuario:
            print(f"Criando usuário administrador '{login}'...")
            # Cria o usuário admin
            usuario = Usuario(
                nome=nome,
                login=login,
                senha_hash=hash_senha(senha),
                tipo=TipoUsuario.MASTER,
                ativo=True
            )
            db.add(usuario)
            db.flush()  # Para obter o ID do usuário

            # Registra a criação no log
            log = LogAcao(
                usuario_id=usuario.id,
                tipo_acao=TipoAcao.ALTERACAO_USUARIO,
                descricao="Criação do usuário administrador inicial",
                tabela_afetada="usuarios"
            )
            db.add(log)

            db.commit()
            print(f"Usuário administrador '{login}' criado com sucesso!")
            return usuario
        else:
            print(f"Usuário administrador '{login}' já existe.")
            return usuario
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar usuário administrador: {str(e)}")
        raise


def inicializar_banco():
    """Inicializa o banco de dados com as tabelas e usuário admin"""
    try:
        print("Iniciando criação das tabelas...")
        create_tables()

        # Verifica se as tabelas foram criadas
        from ..models import engine
        if not verificar_tabelas_existem(engine):
            raise Exception("Erro: Algumas tabelas não foram criadas corretamente")

        print("Tabelas criadas com sucesso!")

        # Cria usuário admin
        print("Iniciando criação do usuário administrador...")
        db = next(get_db())
        criar_usuario_admin(
            db=db,
            login="admin",
            senha="admin123",  # Você deve alterar esta senha em produção!
            nome="Administrador"
        )

        print("\nInicialização do banco de dados concluída com sucesso!")
        print("\nDados de acesso do administrador:")
        print("Login: admin")
        print("Senha: admin123")
        print("\nIMPORTANTE: Altere a senha do administrador após o primeiro acesso!")

    except Exception as e:
        print(f"\nERRO durante a inicialização do banco de dados: {str(e)}")
        raise


if __name__ == "__main__":
    print("=" * 50)
    print("Inicializando banco de dados...")
    print("=" * 50)
    inicializar_banco()