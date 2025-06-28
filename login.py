import customtkinter as ctk
from tkinter import messagebox
import psycopg2

# Importar configurações do banco de dados de um arquivo externo
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
                "senha": user_record[3], # Idealmente não deveria ser retornado para a interface
                "ativo": user_record[4],
                "admin": user_record[5] # <--- ESTE É O CAMPO CRÍTICO QUE PRECISA SER INCLUÍDO
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

class LoginWindow(ctk.CTkFrame):
    def __init__(self, master, on_login_success, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.on_login_success = on_login_success

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20)

        self.login_label = ctk.CTkLabel(
            self.main_frame,
            text="Login do Sistema",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.login_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 30))

        self.username_label = ctk.CTkLabel(self.main_frame, text="Usuário:")
        self.username_label.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.username_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Digite seu usuário")
        self.username_entry.grid(row=1, column=1, padx=20, pady=5, sticky="ew")
        # NOVO: Bind da tecla Enter para o campo de usuário
        self.username_entry.bind("<Return>", lambda event: self.perform_login())


        self.password_label = ctk.CTkLabel(self.main_frame, text="Senha:")
        self.password_label.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Digite sua senha", show="*")
        self.password_entry.grid(row=2, column=1, padx=20, pady=5, sticky="ew")
        # NOVO: Bind da tecla Enter para o campo de senha
        self.password_entry.bind("<Return>", lambda event: self.perform_login())

        self.login_button = ctk.CTkButton(
            self.main_frame,
            text="Entrar",
            command=self.perform_login
        )
        self.login_button.grid(row=3, column=0, columnspan=2, padx=20, pady=(20, 10))

    def perform_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        user = autenticar_usuario(username, password)

        if user:
            # REMOVIDO: messagebox.showinfo("Sucesso", f"Bem-vindo, {user.get('nome')}!")
            self.on_login_success(user)
            self.destroy() # Destrói a janela de login
        else:
            messagebox.showerror("Erro de Login", "Usuário, senha ou status inativo inválidos.")

# Para teste standalone
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Teste de Login")
    app.geometry("400x300")

    def on_success(user_data):
        print(f"Login bem-sucedido: {user_data}")
        app.destroy()

    login_window = LoginWindow(app, on_success)
    login_window.pack(fill="both", expand=True)
    app.mainloop()
