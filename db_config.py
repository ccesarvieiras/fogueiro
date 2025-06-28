import os
import sys  # Importar o módulo sys

def carregar_configuracao_db():
    """
    Lê as configurações do banco de dados a partir de um arquivo 'db_config.txt'.
    Esta função foi ajustada para funcionar tanto em execução normal (.py)
    quanto em executáveis compilados com PyInstaller (.exe).
    """
    config = {}

    # Determina o diretório base da aplicação de forma robusta
    if getattr(sys, 'frozen', False):
        # Se a aplicação estiver 'congelada' (compilada com PyInstaller)
        # sys.executable aponta para o caminho completo do executável
        pasta_base = os.path.dirname(sys.executable)
    else:
        # Se estiver executando como um script Python normal
        # __file__ aponta para o caminho do arquivo .py atual
        pasta_base = os.path.dirname(os.path.abspath(__file__))

    # Constrói o caminho completo para o arquivo db_config.txt
    caminho_config = os.path.join(pasta_base, "db_config.txt")

    try:
        with open(caminho_config, "r", encoding="utf-8") as arquivo:
            for linha in arquivo:
                linha = linha.strip()
                # Ignora linhas vazias ou comentários
                if linha and "=" in linha and not linha.startswith("#"):
                    chave, valor = linha.split("=", 1)
                    config[chave.strip()] = valor.strip()
    except FileNotFoundError:
        print(f"Erro: Arquivo de configuração '{caminho_config}' não encontrado.")
        # É uma boa prática informar o usuário, talvez com um messagebox no ponto de chamada
        # que utiliza DB_CONFIG, pois db_config.py é um módulo de utilidade e não deve ter GUI.
    except Exception as e:
        print(f"Erro ao ler o arquivo de configuração '{caminho_config}': {e}")
        # O mesmo para outros erros de leitura.

    # Opcional: Adicionar uma verificação para garantir que todas as chaves essenciais existam
    required_keys = ["host", "port", "user", "password", "dbname"]
    for key in required_keys:
        if key not in config:
            print(f"Aviso: Chave '{key}' faltando no arquivo de configuração db_config.txt. Verifique o arquivo.")
            # Você pode optar por levantar uma exceção aqui se a configuração for crítica
            # raise ValueError(f"Chave de configuração essencial '{key}' faltando em db_config.txt")

    return config

# Variável global de configuração que o sistema inteiro vai importar
DB_CONFIG = carregar_configuracao_db()

# Opcional: Adicionar uma mensagem de depuração para ver o caminho carregado
# if not DB_CONFIG:
#     print("DB_CONFIG está vazio. A conexão pode falhar.")
# else:
#     print(f"DB_CONFIG carregado com sucesso (host: {DB_CONFIG.get('host')}, dbname: {DB_CONFIG.get('dbname')})")