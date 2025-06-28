import customtkinter as ctk
from tkinter import messagebox
import os
from datetime import datetime
import psycopg2

# Importar configurações do banco de dados de um arquivo externo
from db_config import DB_CONFIG


def listar_usuarios():
    """
    Função para listar todos os usuários do banco de dados.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id, nome, usuario, senha, ativo, admin FROM usuarios ORDER BY nome ASC")
        usuarios = cur.fetchall()
        lista = []
        for row in usuarios:
            lista.append({
                "id": row[0],
                "nome": row[1],
                "usuario": row[2],
                "senha": row[3],
                "ativo": row[4],
                "admin": row[5]
            })
        return lista
    except psycopg2.Error as e:
        print(f"Erro ao listar usuários: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def salvar_usuario_no_banco(user_data):
    """
    Salva ou atualiza um usuário no banco de dados.
    Se user_data contém 'id', tenta atualizar; caso contrário, insere um novo.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        usuario_id = user_data.get("id")

        if usuario_id:
            # Atualizar usuário existente
            cur.execute("""
                UPDATE usuarios SET
                    nome = %s,
                    usuario = %s,
                    senha = %s,
                    ativo = %s,
                    admin = %s
                WHERE id = %s
            """, (
                user_data["nome"],
                user_data["usuario"],
                user_data["senha"],
                user_data["ativo"],
                user_data["admin"],
                usuario_id
            ))
        else:
            # Inserir novo usuário
            cur.execute("""
                INSERT INTO usuarios (nome, usuario, senha, ativo, admin)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_data["nome"],
                user_data["usuario"],
                user_data["senha"],
                user_data["ativo"],
                user_data["admin"]
            ))
            usuario_id = cur.fetchone()[0]

        conn.commit()
        return usuario_id
    except psycopg2.Error as e:
        print(f"Erro ao salvar usuário no banco de dados: {e}")
        print(f"Detalhes do erro do PostgreSQL: {e.diag.message_detail if e.diag else 'N/A'}")
        print(f"Código SQLSTATE: {e.pgcode if e.pgcode else 'N/A'}")
        if conn:
            conn.rollback()
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def excluir_usuario_do_banco(usuario_id):
    """
    Exclui um usuário do banco de dados.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        return True
    except psycopg2.Error as e:
        print(f"Erro ao excluir usuário do banco de dados: {e}")
        print(f"Detalhes do erro do PostgreSQL: {e.diag.message_detail if e.diag else 'N/A'}")
        print(f"Código SQLSTATE: {e.pgcode if e.pgcode else 'N/A'}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


class UserForm(ctk.CTkToplevel):
    def __init__(self, master, user_data=None, on_save=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.user_data = user_data
        self.on_save = on_save

        # Configuração da janela
        self.title("Cadastro de Usuário" if not user_data else "Editar Usuário")
        self.geometry("500x600")
        self.resizable(False, False)
        self.grab_set()  # Torna a janela modal

        # Configuração do grid para a janela (self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Título - não expande
        self.grid_rowconfigure(1, weight=1)  # form_frame - pode expandir
        self.grid_rowconfigure(2, weight=0)  # button_frame - não expande

        # Título
        self.title_label = ctk.CTkLabel(
            self,
            text="Cadastro de Usuário" if not user_data else "Editar Usuário",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Frame do formulário
        self.form_frame = ctk.CTkFrame(self)
        self.form_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.form_frame.grid_columnconfigure(1, weight=1)

        # Campos do formulário
        # Nome
        self.name_label = ctk.CTkLabel(
            self.form_frame,
            text="Nome:",
            anchor="w"
        )
        self.name_label.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="w")

        self.name_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="Nome Completo"
        )
        self.name_entry.grid(row=0, column=1, padx=(0, 20), pady=(20, 10), sticky="ew")

        # Usuário (login)
        self.username_label = ctk.CTkLabel(
            self.form_frame,
            text="Usuário (Login):",
            anchor="w"
        )
        self.username_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")

        self.username_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="nome_de_usuario"
        )
        self.username_entry.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Senha
        self.password_label = ctk.CTkLabel(
            self.form_frame,
            text="Senha:",
            anchor="w"
        )
        self.password_label.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="w")

        self.password_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="********",
            show="*"  # Esconde a senha
        )
        self.password_entry.grid(row=2, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Ativo
        self.active_checkbox = ctk.CTkCheckBox(
            self.form_frame,
            text="Ativo",
            checkbox_width=20,
            checkbox_height=20,
            width=20,
        )
        self.active_checkbox.grid(row=3, column=0, columnspan=2, padx=20, pady=(10, 5), sticky="w")
        self.active_checkbox.select()  # Por padrão, o usuário é ativo

        # Admin
        self.admin_checkbox = ctk.CTkCheckBox(
            self.form_frame,
            text="Administrador",
            checkbox_width=20,
            checkbox_height=20,
            width=20,
        )
        self.admin_checkbox.grid(row=4, column=0, columnspan=2, padx=20, pady=(5, 20), sticky="w")

        # Botões
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1), weight=1)

        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancelar",
            fg_color="#D22B2B",
            hover_color="#AA0000",
            command=self.destroy
        )
        self.cancel_button.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="e")

        self.save_button = ctk.CTkButton(
            self.button_frame,
            text="Salvar",
            command=self.save_user
        )
        self.save_button.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="w")

        # Preencher os campos se for edição
        if self.user_data:
            self.name_entry.insert(0, self.user_data.get("nome", ""))
            self.username_entry.insert(0, self.user_data.get("usuario", ""))
            self.password_entry.insert(0, self.user_data.get("senha",
                                                             ""))  # Cuidado ao preencher senhas (apenas para exibição)
            if self.user_data.get("ativo"):
                self.active_checkbox.select()
            else:
                self.active_checkbox.deselect()
            if self.user_data.get("admin"):
                self.admin_checkbox.select()
            else:
                self.admin_checkbox.deselect()

    def save_user(self):
        # Validar campos
        nome = self.name_entry.get().strip()
        usuario = self.username_entry.get().strip()
        senha = self.password_entry.get().strip()
        ativo = self.active_checkbox.get() == 1
        admin = self.admin_checkbox.get() == 1

        if not nome or not usuario or not senha:
            messagebox.showerror("Erro", "Nome, Usuário e Senha são obrigatórios.")
            return

        # Coletar dados do formulário
        user_data = {
            "nome": nome,
            "usuario": usuario,
            "senha": senha,
            "ativo": ativo,
            "admin": admin
        }

        # Se for edição, manter o ID do usuário
        if self.user_data and "id" in self.user_data:
            user_data["id"] = self.user_data["id"]

        # Chamar a função de callback para salvar
        if self.on_save:
            self.on_save(user_data)

        # Fechar o formulário
        self.destroy()


class UsersModule(ctk.CTkFrame):
    def __init__(self, master, is_admin=False, **kwargs):  # Adicionado is_admin para controle de acesso
        super().__init__(master, **kwargs)

        self.is_admin = is_admin  # Armazena o status de admin do usuário logado (passado pelo master)

        self.selected_user = None
        self.user_row_frames = []  # Lista para armazenar as tuplas (user_data, ctk_frame_widget)

        # Configuração do grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Faz a table_frame expandir verticalmente

        # Título
        self.title_label = ctk.CTkLabel(
            self,
            text="Gerenciamento de Usuários",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Frame de pesquisa
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Buscar usuário por nome ou login..."
        )
        self.search_entry.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="ew")

        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Buscar",
            width=100,
            command=self.search_users
        )
        self.search_button.grid(row=0, column=1, padx=(0, 20), pady=20)

        # Frame de botões de ação
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.action_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)  # Distribui o espaço

        self.add_button = ctk.CTkButton(
            self.action_frame,
            text="Novo Usuário",
            width=150,
            command=self.add_user
        )
        self.add_button.grid(row=0, column=0, padx=10, pady=20)

        self.edit_button = ctk.CTkButton(
            self.action_frame,
            text="Editar",
            width=150,
            state="disabled",
            command=self.edit_user
        )
        self.edit_button.grid(row=0, column=1, padx=10, pady=20)

        self.delete_button = ctk.CTkButton(
            self.action_frame,
            text="Excluir",
            width=150,
            fg_color="#D22B2B",
            hover_color="#AA0000",
            state="disabled",
            command=self.delete_user
        )
        self.delete_button.grid(row=0, column=2, padx=10, pady=20)

        self.refresh_button = ctk.CTkButton(
            self.action_frame,
            text="Atualizar Lista",
            width=150,
            command=self.populate_table
        )
        self.refresh_button.grid(row=0, column=3, padx=10, pady=20)

        # Frame da tabela de usuários
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Cabeçalho da tabela
        self.header_frame = ctk.CTkFrame(self.table_frame, fg_color=("#EEEEEE", "#333333"))
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.table_frame.grid_columnconfigure(0, weight=1)

        headers = ["ID", "Nome", "Usuário", "Ativo", "Admin"]
        widths = [50, 200, 150, 80, 80]

        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                self.header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            )
            if header == "ID":
                label.configure(anchor="e")
            elif header in ["Ativo", "Admin"]:
                label.configure(anchor="center")
            else:
                label.configure(anchor="w")
            label.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            self.header_frame.grid_columnconfigure(i, weight=1, minsize=widths[i])

        # Conteúdo da tabela
        self.content_frame = ctk.CTkScrollableFrame(self.table_frame, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.table_frame.grid_rowconfigure(1, weight=1)

        # Status bar
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Total de usuários: 0"
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.active_users_label = ctk.CTkLabel(
            self.status_frame,
            text="Usuários ativos: 0",
            text_color="green"
        )
        self.active_users_label.grid(row=0, column=1, padx=20, pady=10, sticky="e")

        self.admin_users_label = ctk.CTkLabel(
            self.status_frame,
            text="Administradores: 0",
            text_color="blue"
        )
        self.admin_users_label.grid(row=0, column=2, padx=20, pady=10, sticky="e")

        # Carregar usuários do banco de dados
        self.all_users = listar_usuarios()

        # Se o usuário não for admin, exibe a mensagem de acesso negado
        if not self.is_admin:
            self.display_permission_denied_message()
        else:
            self.populate_table()

    def populate_table(self, filtered_users=None):
        # Limpar a tabela atual e as referências aos frames de linha
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.user_row_frames = []  # Limpa a lista de referências de frames de linha

        # Recarregar os usuários do banco de dados para garantir que os dados estão atualizados
        self.all_users = listar_usuarios()

        # Usar a lista filtrada ou a lista completa
        users_to_display = filtered_users if filtered_users is not None else self.all_users

        # Atualizar os status labels
        self.status_label.configure(text=f"Total de usuários: {len(users_to_display)}")
        active_count = sum(1 for user in self.all_users if user.get("ativo", False))
        self.active_users_label.configure(text=f"Usuários ativos: {active_count}")
        admin_count = sum(1 for user in self.all_users if user.get("admin", False))
        self.admin_users_label.configure(text=f"Administradores: {admin_count}")

        # Definir larguras das colunas
        widths = [50, 200, 150, 80, 80]

        # Preencher com os dados
        for row_idx, user in enumerate(users_to_display):
            row_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            row_frame.grid(row=row_idx * 2, column=0, sticky="ew", pady=5)
            self.user_row_frames.append((user, row_frame))  # Armazena a tupla (user_data, frame)

            for i in range(len(widths)):
                row_frame.grid_columnconfigure(i, weight=1)

            # Determinar a cor do status ativo
            active_status = "Sim" if user.get("ativo", False) else "Não"
            active_color = "green" if user.get("ativo", False) else "red"

            # Determinar a cor do status admin
            admin_status = "Sim" if user.get("admin", False) else "Não"
            admin_color = "blue" if user.get("admin", False) else "red"

            # Adicionar os dados do usuário
            values = [
                user.get("id", ""),
                user.get("nome", ""),
                user.get("usuario", ""),
                active_status,
                admin_status
            ]

            for col_idx, value in enumerate(values):
                label = ctk.CTkLabel(
                    row_frame,
                    text=str(value),
                    text_color=active_color if col_idx == 3 else (admin_color if col_idx == 4 else None)
                )
                if col_idx == 0:
                    label.configure(anchor="e")
                elif col_idx in [3, 4]:
                    label.configure(anchor="center")
                else:
                    label.configure(anchor="w")

                label.grid(row=0, column=col_idx, padx=10, pady=5, sticky="nsew")

            # Adicionar evento de clique para selecionar o usuário à moldura da linha
            row_frame.bind("<Button-1>", lambda e, u=user: self.select_user(u))
            # Removemos a iteração sobre os filhos para vincular eventos, pois a moldura da linha já basta
            # e evita problemas se os filhos mudarem ou forem mais complexos.

            # Adicionar linha separadora
            if row_idx < len(users_to_display) - 1:
                separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=("#DDDDDD", "#555555"))
                separator.grid(row=row_idx * 2 + 1, column=0, sticky="ew", padx=10)

        self.reset_selection_buttons()

    def select_user(self, user):
        # Desmarcar o usuário anterior
        if self.selected_user:
            for old_user_data, old_row_frame in self.user_row_frames:
                if old_user_data.get("id") == self.selected_user.get("id"):
                    old_row_frame.configure(fg_color="transparent")
                    break

        # Marcar o usuário selecionado
        for current_user_data, current_row_frame in self.user_row_frames:
            if current_user_data.get("id") == user.get("id"):
                current_row_frame.configure(fg_color=("gray90", "gray20"))
                break

        self.selected_user = user

        # Habilitar os botões de ação
        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")

    def search_users(self):
        search_term = self.search_entry.get().strip().lower()

        if not search_term:
            self.populate_table()
            return

        filtered_users = [
            user for user in self.all_users
            if search_term in user.get("nome", "").lower() or search_term in user.get("usuario", "").lower()
        ]

        self.populate_table(filtered_users)

    def add_user(self):
        # Verifica a permissão antes de abrir o formulário
        if not self.is_admin:
            messagebox.showerror("Acesso Negado", "Você não tem permissão para adicionar usuários.")
            return

        form = UserForm(self, on_save=self.save_new_user)
        form.focus()

    def save_new_user(self, user_data):
        new_id = salvar_usuario_no_banco(user_data)
        if new_id is not None:
            self.populate_table()
            messagebox.showinfo("Sucesso", "Usuário cadastrado com sucesso!")
        else:
            messagebox.showerror("Erro",
                                 "Falha ao cadastrar o usuário no banco de dados. Verifique o console para detalhes.")

    def edit_user(self):
        if not self.selected_user:
            return

        # Verifica a permissão antes de abrir o formulário
        if not self.is_admin:
            messagebox.showerror("Acesso Negado", "Você não tem permissão para editar usuários.")
            return

        form = UserForm(self, user_data=self.selected_user, on_save=self.save_edited_user)
        form.focus()

    def save_edited_user(self, user_data):
        updated_id = salvar_usuario_no_banco(user_data)
        if updated_id is not None:
            self.populate_table()
            messagebox.showinfo("Sucesso", "Usuário atualizado com sucesso!")
        else:
            messagebox.showerror("Erro",
                                 "Falha ao atualizar o usuário no banco de dados. Verifique o console para detalhes.")

        self.reset_selection_buttons()

    def delete_user(self):
        if not self.selected_user:
            return

        # Verifica a permissão antes de excluir
        if not self.is_admin:
            messagebox.showerror("Acesso Negado", "Você não tem permissão para excluir usuários.")
            return

        if messagebox.askyesno("Confirmar Exclusão",
                               f"Tem certeza que deseja excluir o usuário '{self.selected_user.get('usuario')}'?"):
            if excluir_usuario_do_banco(self.selected_user.get("id")):
                self.populate_table()
                messagebox.showinfo("Sucesso", "Usuário excluído com sucesso!")
            else:
                messagebox.showerror("Erro",
                                     "Falha ao excluir o usuário do banco de dados. Verifique o console para detalhes.")

        self.reset_selection_buttons()

    def reset_selection_buttons(self):
        """Reseta a seleção de usuário e desabilita os botões de ação."""
        self.selected_user = None
        self.edit_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")

    def display_permission_denied_message(self):
        # Limpa o frame atual e exibe uma mensagem de acesso negado
        for widget in self.winfo_children():
            widget.destroy()

        message_label = ctk.CTkLabel(
            self,
            text="Acesso Negado.\nVocê não tem permissão para acessar este módulo.",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="red"
        )
        message_label.place(relx=0.5, rely=0.5, anchor="center")  # Centraliza a mensagem


# Para teste standalone
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Teste do Módulo de Usuários")
    app.geometry("1000x600")

    # Configuração do grid
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    # Exemplo de como você passaria o status de admin para o módulo em um ambiente real
    # is_current_user_admin = True # Mude para False para testar o acesso negado

    # Instanciar o módulo - no uso real, o 'is_admin' viria do usuário logado
    # users_module = UsersModule(app, is_admin=is_current_user_admin)
    users_module = UsersModule(app, is_admin=True)  # Para fins de teste, assume True
    users_module.grid(row=0, column=0, sticky="nsew")

    app.mainloop()
