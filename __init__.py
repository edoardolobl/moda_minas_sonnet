# init_db.py
from src.utils.database import inicializar_banco

if __name__ == "__main__":
    try:
        inicializar_banco()
    except Exception as e:
        print("\nFalha na inicialização do banco de dados!")
        print(f"Erro: {str(e)}")
        exit(1)