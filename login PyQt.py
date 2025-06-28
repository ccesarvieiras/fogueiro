import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtCore import Qt

import psycopg2

# Importar configurações do banco de dados de um arquivo externo
# Certifique-se de que 'db_config.py' existe no mesmo diretório
from db_config import DB_CONFIG

def autenticar_usuario(username, password):
    """
    Autentica um usuário no banco de dados e retorna suas informações,
    incluindo o status 'admin'.
    """
    conn = None
    cur = None
    user_info = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, nome, usuario, senha, ativo, admin FROM usuarios WHERE usuario = %s AND senha = %s AND ativo = TRUE",
            (username, password)
        )
        user_record = cur.fetchone()

        if user_record:
            user_info = {
                "id": user_record[0],
                "nome": user_record[1],
                "usuario": user_record[2],
                "senha": user_record[3],
                "ativo": user_record[4],
                "admin": user_record[5]
            }
        return user_info
    except psycopg2.Error as e:
        print(f"Erro ao autenticar usuário: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

class LoginWindow(QWidget):
    def __init__(self, on_login_success_callback=None):
        super().__init__()
        self.on_login_success = on_login_success_callback
        self.setWindowTitle("Fogueiro Burger - Login")
        self.setFixedSize(450, 480) # Tamanho ligeiramente maior para o novo design

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        # Layout principal da janela
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0) # Remover margens padrão para controle total do QSS

        # Frame principal para o formulário de login
        # Este frame agora é a "cartão" central do login
        self.login_card_frame = QFrame(self)
        self.login_card_frame.setObjectName("loginCardFrame") # Usar objectName para QSS
        login_card_layout = QVBoxLayout(self.login_card_frame)
        login_card_layout.setAlignment(Qt.AlignCenter)
        login_card_layout.setSpacing(15) # Espaçamento entre os widgets dentro do card

        # Título do sistema
        self.title_label = QLabel("FOGUEIRO BURGER", self.login_card_frame) # Título atualizado
        self.title_label.setObjectName("titleLabel")
        self.title_label.setFont(QFont("Arial", 28, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        login_card_layout.addWidget(self.title_label)

        # Subtítulo (Login do Sistema)
        self.subtitle_label = QLabel("Bem-vindo ao sistema!", self.login_card_frame) # Subtítulo atualizado
        self.subtitle_label.setObjectName("subtitleLabel")
        self.subtitle_label.setFont(QFont("Arial", 14))
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        login_card_layout.addWidget(self.subtitle_label)

        # Espaçador
        login_card_layout.addSpacing(25)

        # Campo de Usuário
        self.username_entry = QLineEdit(self.login_card_frame)
        self.username_entry.setObjectName("usernameEntry")
        self.username_entry.setPlaceholderText("Usuário")
        self.username_entry.setFont(QFont("Arial", 13))
        self.username_entry.setClearButtonEnabled(True) # Botão para limpar texto
        login_card_layout.addWidget(self.username_entry)

        # Campo de Senha
        self.password_entry = QLineEdit(self.login_card_frame)
        self.password_entry.setObjectName("passwordEntry")
        self.password_entry.setPlaceholderText("Senha")
        self.password_entry.setEchoMode(QLineEdit.Password)
        self.password_entry.setFont(QFont("Arial", 13))
        self.password_entry.setClearButtonEnabled(True) # Botão para limpar texto
        login_card_layout.addWidget(self.password_entry)

        # Espaçador
        login_card_layout.addSpacing(20)

        # Botão de Login
        self.login_button = QPushButton("ENTRAR", self.login_card_frame)
        self.login_button.setObjectName("loginButton")
        self.login_button.setFont(QFont("Arial", 15, QFont.Bold))
        self.login_button.setFixedSize(200, 50) # Tamanho fixo para o botão
        self.login_button.clicked.connect(self.perform_login)

        # Adicionar sombra ao botão para um efeito 3D
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 100)) # Cor da sombra (preto com transparência)
        shadow.setOffset(3, 3) # Deslocamento da sombra
        self.login_button.setGraphicsEffect(shadow)

        login_card_layout.addWidget(self.login_button, alignment=Qt.AlignCenter)

        # Adicionar o "cartão" de login ao layout principal da janela
        main_layout.addWidget(self.login_card_frame, alignment=Qt.AlignCenter)

    def apply_styles(self):
        # Estilos usando QSS (Qt Style Sheets) para uma aparência minimalista e chamativa

        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #FF5733, stop:1 #FFC300); /* Gradiente de vermelho-alaranjado para dourado (fogo/comida) */
                color: #FFFFFF; /* Texto branco */
                font-family: 'Poppins', sans-serif; /* Fonte moderna e mais "amigável" */
            }

            #loginCardFrame {
                background-color: rgba(255, 255, 255, 0.15); /* Fundo translúcido para o card */
                border-radius: 20px; /* Bordas mais arredondadas */
                padding: 40px; /* Aumentar o padding interno */
                border: 1px solid rgba(255, 255, 255, 0.3); /* Borda sutil e mais visível */
                box-shadow: 0px 10px 30px rgba(0, 0, 0, 0.4); /* Sombra mais pronunciada */
            }

            #titleLabel {
                color: #FFFFFF;
                font-weight: bold;
                margin-bottom: 5px; /* Espaçamento menor */
                text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.5); /* Sombra no texto do título */
            }

            #subtitleLabel {
                color: #FFDAB9; /* Tom de pêssego/creme para o subtítulo */
                font-style: italic;
                margin-bottom: 20px; /* Aumenta espaço para entradas */
            }

            QLineEdit {
                background-color: rgba(255, 255, 255, 0.25); /* Fundo translúcido para entradas */
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 12px; /* Bordas mais arredondadas para entradas */
                padding: 14px 18px; /* Mais padding para melhor toque e visual */
                color: #FFFFFF;
                selection-background-color: #FFA07A; /* Cor de seleção (salmão claro) */
                selection-color: #333333; /* Cor do texto selecionado */
                placeholder-text-color: rgba(255, 255, 255, 0.7);
            }

            QLineEdit:focus {
                border: 2px solid #FFD700; /* Borda dourada vibrante ao focar */
                background-color: rgba(255, 255, 255, 0.35);
            }

            QPushButton {
                background-color: #FFC300; /* Botão dourado */
                border: none;
                border-radius: 28px; /* Botão mais pilular */
                color: #8B0000; /* Texto do botão em vermelho escuro (cor de carne) */
                padding: 12px 25px;
                font-weight: bold;
                text-transform: uppercase; /* Texto em maiúsculas */
                min-width: 180px;
                transition: all 0.3s ease; /* Transição suave para hover */
            }

            QPushButton:hover {
                background-color: #FFD700; /* Dourado mais claro ao passar o mouse */
                /* Efeito de escala é limitado em QSS, mas a mudança de cor já ajuda */
            }

            QPushButton:pressed {
                background-color: #FFB300; /* Dourado mais escuro ao clicar */
            }

            QMessageBox {
                background-color: #4a00e0; /* Mantém o tema roxo para as mensagens de erro */
                color: #f0f2f5;
                font-family: Arial, sans-serif;
            }
            QMessageBox QLabel {
                color: #f0f2f5;
            }
            QMessageBox QPushButton {
                background-color: #1f77b4;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QMessageBox QPushButton:hover {
                background-color: #2c8ed6;
            }
        """)

        # A paleta pode ser usada para alguns elementos que QSS não cobre totalmente ou para fallback
        palette = self.palette()
        palette.setColor(QPalette.WindowText, QColor("#FFFFFF"))
        palette.setColor(QPalette.ButtonText, QColor("#8B0000")) # Definir cor do texto do botão explicitamente
        self.setPalette(palette)


    def perform_login(self):
        username = self.username_entry.text().strip()
        password = self.password_entry.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Erro de Login", "Por favor, preencha todos os campos.")
            return

        user = autenticar_usuario(username, password)

        if user:
            QMessageBox.information(self, "Sucesso", f"Bem-vindo, {user.get('nome')}!")
            if self.on_login_success:
                self.on_login_success(user)
            self.close() # Fecha a janela de login
        else:
            QMessageBox.critical(self, "Erro de Login", "Usuário, senha ou status inativo inválidos.")

# Para teste standalone
if __name__ == "__main__":
    app = QApplication(sys.argv)

    def on_success_callback(user_data):
        print(f"Login bem-sucedido para: {user_data.get('usuario')}")
        app.quit()

    login_window = LoginWindow(on_login_success_callback=on_success_callback)
    login_window.show()

    sys.exit(app.exec())
