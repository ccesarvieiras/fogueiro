import customtkinter as ctk
from tkinter import messagebox # Importar messagebox para exibir mensagens de erro
from employees_module import EmployeesModule
from users_module import UsersModule
from db_config import DB_CONFIG # Importar as configurações do banco de dados

class CadastrosModule(ctk.CTkFrame):
    # Adicionando o parâmetro is_admin ao construtor
    def __init__(self, master, is_admin=False, **kwargs):
        super().__init__(master, **kwargs)

        self.master = master
        self.is_admin = is_admin # Armazena o status de admin

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Título/Menu de opções
        self.grid_rowconfigure(1, weight=1) # Frame para exibir o conteúdo do módulo de cadastro

        # Frame para conter o menu de opções de cadastro
        self.menu_frame = ctk.CTkFrame(self)
        self.menu_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.menu_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.menu_frame,
            text="Módulo de Cadastros",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Botão para Cadastro de Profissionais
        self.employees_button = ctk.CTkButton(
            self.menu_frame,
            text="Cadastro de Profissionais",
            command=self.show_employees_registration
        )
        self.employees_button.grid(row=1, column=0, padx=20, pady=10)

        # Novo Botão para Cadastro de Usuários
        self.users_button = ctk.CTkButton(
            self.menu_frame,
            text="Cadastro de Usuários",
            command=self.show_users_registration
        )
        self.users_button.grid(row=2, column=0, padx=20, pady=10)


        # Frame para exibir o conteúdo do módulo de cadastro selecionado
        self.content_display_frame = ctk.CTkFrame(self)
        self.content_display_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.content_display_frame.grid_columnconfigure(0, weight=1)
        self.content_display_frame.grid_rowconfigure(0, weight=1)

        # Exibe uma mensagem inicial no frame de conteúdo
        self.initial_message = ctk.CTkLabel(
            self.content_display_frame,
            text="Selecione uma opção de cadastro no menu.",
            font=ctk.CTkFont(size=16)
        )
        self.initial_message.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)


    def show_employees_registration(self):
        # Limpa o frame de conteúdo para exibir o novo módulo
        for widget in self.content_display_frame.winfo_children():
            widget.destroy()

        # Instancia e exibe o EmployeesModule dentro do content_display_frame
        # db_config não é mais passado como argumento, pois é importado diretamente no módulo EmployeesModule
        self.current_registration_module = EmployeesModule(self.content_display_frame)
        self.current_registration_module.grid(row=0, column=0, sticky="nsew")

    def show_users_registration(self):
        # Verifica se o usuário é administrador antes de abrir o módulo de usuários
        if not self.is_admin:
            messagebox.showerror("Acesso Negado", "Você não tem permissão para acessar o Cadastro de Usuários.")
            return

        # Limpa o frame de conteúdo para exibir o novo módulo
        for widget in self.content_display_frame.winfo_children():
            widget.destroy()

        # Instancia e exibe o UsersModule dentro do content_display_frame, passando o status de admin
        # db_config não é mais passado como argumento, pois é importado diretamente no módulo UsersModule
        self.current_registration_module = UsersModule(self.content_display_frame, is_admin=self.is_admin)
        self.current_registration_module.grid(row=0, column=0, sticky="nsew")


# Para teste standalone (opcional)
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Teste do Módulo de Cadastros")
    app.geometry("1000x800")
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    # Para testar o módulo de cadastros diretamente, você pode passar is_admin=True ou False
    # Certifique-se de que db_config.py existe no mesmo diretório para o teste standalone
    cadastros_module = CadastrosModule(app, is_admin=False) # Teste como não-admin para ver a restrição
    cadastros_module.grid(row=0, column=0, sticky="nsew")

    app.mainloop()
