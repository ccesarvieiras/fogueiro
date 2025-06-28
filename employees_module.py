import customtkinter as ctk
from tkinter import messagebox
import os
from datetime import datetime
import psycopg2

# Importar configurações do banco de dados de um arquivo externo
from db_config import DB_CONFIG


def listar_funcionarios():
    """
    Função para listar todos os funcionários do banco de dados.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Removendo 'senha' da seleção
        cur.execute("SELECT id, nome, cargo, telefone, email, ativo FROM funcionarios ORDER BY nome ASC")
        funcionarios = cur.fetchall()
        lista = []
        for row in funcionarios:
            lista.append({
                "id": row[0],
                "nome": row[1],
                "cargo": row[2],
                "telefone": row[3],
                "email": row[4],
                "ativo": row[5]  # Ativo agora é o item na posição 5
            })
        return lista
    except psycopg2.Error as e:
        print(f"Erro ao listar funcionários: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def salvar_funcionario_no_banco(employee_data):
    """
    Salva ou atualiza um funcionário no banco de dados.
    Se employee_data contém 'id', tenta atualizar; caso contrário, insere um novo.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        funcionario_id = employee_data.get("id")

        if funcionario_id:
            # Atualizar funcionário existente - Removendo 'senha'
            cur.execute("""
                UPDATE funcionarios SET
                    nome = %s,
                    cargo = %s,
                    telefone = %s,
                    email = %s,
                    ativo = %s
                WHERE id = %s
            """, (
                employee_data["nome"],
                employee_data["cargo"],
                employee_data["telefone"],
                employee_data["email"],
                employee_data["ativo"],
                funcionario_id
            ))
        else:
            # Inserir novo funcionário - Removendo 'senha'
            cur.execute("""
                INSERT INTO funcionarios (nome, cargo, telefone, email, ativo)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                employee_data["nome"],
                employee_data["cargo"],
                employee_data["telefone"],
                employee_data["email"],
                employee_data["ativo"]
            ))
            funcionario_id = cur.fetchone()[0]

        conn.commit()
        return funcionario_id
    except psycopg2.Error as e:
        print(f"Erro ao salvar funcionário no banco de dados: {e}")
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


def excluir_funcionario_do_banco(funcionario_id):
    """
    Exclui um funcionário do banco de dados.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("DELETE FROM funcionarios WHERE id = %s", (funcionario_id,))
        conn.commit()
        return True
    except psycopg2.Error as e:
        print(f"Erro ao excluir funcionário do banco de dados: {e}")
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


class EmployeeForm(ctk.CTkToplevel):
    def __init__(self, master, employee_data=None, on_save=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.employee_data = employee_data
        self.on_save = on_save

        # Configuração da janela
        self.title("Cadastro de Funcionário" if not employee_data else "Editar Funcionário")
        self.geometry("500x550")  # Ajustado para ter menos altura, já que um campo foi removido
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
            text="Cadastro de Funcionário" if not employee_data else "Editar Funcionário",
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

        # Cargo
        self.role_label = ctk.CTkLabel(
            self.form_frame,
            text="Cargo:",
            anchor="w"
        )
        self.role_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")

        self.role_combo = ctk.CTkComboBox(
            self.form_frame,
            values=["Administrador", "Gerente", "Atendente", "Cozinheiro", "Entregador", "Auxiliar"]
        )
        self.role_combo.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="ew")
        self.role_combo.set("Atendente")

        # Telefone
        self.phone_label = ctk.CTkLabel(
            self.form_frame,
            text="Telefone:",
            anchor="w"
        )
        self.phone_label.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="w")

        self.phone_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="(99) 99999-9999"
        )
        self.phone_entry.grid(row=2, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Email
        self.email_label = ctk.CTkLabel(
            self.form_frame,
            text="Email:",
            anchor="w"
        )
        self.email_label.grid(row=3, column=0, padx=(20, 10), pady=10, sticky="w")

        self.email_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="exemplo@email.com"
        )
        self.email_entry.grid(row=3, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Ativo (agora na linha 4)
        self.active_checkbox = ctk.CTkCheckBox(
            self.form_frame,
            text="Ativo",
            checkbox_width=20,
            checkbox_height=20,
            width=20,
        )
        self.active_checkbox.grid(row=4, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="w")
        self.active_checkbox.select()

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
            command=self.save_employee
        )
        self.save_button.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="w")

        # Preencher os campos se for edição
        if self.employee_data:
            self.name_entry.insert(0, self.employee_data.get("nome", ""))
            self.role_combo.set(self.employee_data.get("cargo", ""))
            self.phone_entry.insert(0, self.employee_data.get("telefone", ""))
            self.email_entry.insert(0, self.employee_data.get("email", ""))
            # Removido self.password_entry.insert
            if self.employee_data.get("ativo"):
                self.active_checkbox.select()
            else:
                self.active_checkbox.deselect()

    def save_employee(self):
        # Validar campos
        nome = self.name_entry.get().strip()
        cargo = self.role_combo.get()
        telefone = self.phone_entry.get().strip()
        email = self.email_entry.get().strip()
        ativo = self.active_checkbox.get() == 1

        # Removido 'senha' da validação de obrigatórios
        if not nome or not cargo or not telefone or not email:
            messagebox.showerror("Erro", "Nome, Cargo, Telefone e Email são obrigatórios.")
            return

        # Coletar dados do formulário - Removido 'senha'
        employee_data = {
            "nome": nome,
            "cargo": cargo,
            "telefone": telefone,
            "email": email,
            "ativo": ativo
        }

        # Se for edição, manter o ID do funcionário
        if self.employee_data and "id" in self.employee_data:
            employee_data["id"] = self.employee_data["id"]

        # Chamar a função de callback para salvar
        if self.on_save:
            self.on_save(employee_data)

        # Fechar o formulário
        self.destroy()


class EmployeesModule(ctk.CTkFrame):
    def __init__(self, master, db_config=None, **kwargs): # Adicionado db_config como parâmetro
        super().__init__(master, **kwargs)

        # Armazenar a configuração do banco de dados
        self.db_config = db_config if db_config is not None else DB_CONFIG # Usar o passado ou o importado

        self.selected_employee = None

        # Configuração do grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Faz a table_frame expandir verticalmente

        # Título
        self.title_label = ctk.CTkLabel(
            self,
            text="Gerenciamento de Funcionários",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Frame de pesquisa
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Buscar funcionário por nome ou cargo..."
        )
        self.search_entry.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="ew")

        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Buscar",
            width=100,
            command=self.search_employees
        )
        self.search_button.grid(row=0, column=1, padx=(0, 20), pady=20)

        # Frame de botões de ação
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.action_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)  # Distribui o espaço

        self.add_button = ctk.CTkButton(
            self.action_frame,
            text="Novo Funcionário",
            width=150,
            command=self.add_employee
        )
        self.add_button.grid(row=0, column=0, padx=10, pady=20)

        self.edit_button = ctk.CTkButton(
            self.action_frame,
            text="Editar",
            width=150,
            state="disabled",
            command=self.edit_employee
        )
        self.edit_button.grid(row=0, column=1, padx=10, pady=20)

        self.delete_button = ctk.CTkButton(
            self.action_frame,
            text="Excluir",
            width=150,
            fg_color="#D22B2B",
            hover_color="#AA0000",
            state="disabled",
            command=self.delete_employee
        )
        self.delete_button.grid(row=0, column=2, padx=10, pady=20)

        self.refresh_button = ctk.CTkButton(
            self.action_frame,
            text="Atualizar Lista",
            width=150,
            command=self.populate_table
        )
        self.refresh_button.grid(row=0, column=3, padx=10, pady=20)

        # Frame da tabela de funcionários
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Cabeçalho da tabela
        self.header_frame = ctk.CTkFrame(self.table_frame, fg_color=("#EEEEEE", "#333333"))
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.table_frame.grid_columnconfigure(0, weight=1)

        # Removido 'Senha' dos headers
        headers = ["ID", "Nome", "Cargo", "Telefone", "Email", "Ativo"]
        widths = [50, 180, 120, 120, 180, 80]

        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                self.header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            )
            # Ajustando o anchor para alinhamento (ID à direita, outros à esquerda)
            if header == "ID":
                label.configure(anchor="e")
            elif header == "Ativo":  # Centraliza o "Sim"/"Não"
                label.configure(anchor="center")
            else:
                label.configure(anchor="w")
            label.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            self.header_frame.grid_columnconfigure(i, weight=1, minsize=widths[i])

        # Conteúdo da tabela
        self.content_frame = ctk.CTkScrollableFrame(self.table_frame, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.table_frame.grid_rowconfigure(1, weight=1)

        # Status bar - Garante que esses labels são criados antes de populate_table()
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Total de funcionários: 0"
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.active_employees_label = ctk.CTkLabel(
            self.status_frame,
            text="Funcionários ativos: 0",
            text_color="green"
        )
        self.active_employees_label.grid(row=0, column=1, padx=20, pady=10, sticky="e")

        # Carregar funcionários do banco de dados (será a lista completa para filtragem)
        self.all_employees = self._listar_funcionarios_com_db_config() # Usar a nova função interna
        # Chamar populate_table após a inicialização dos status labels
        self.populate_table()

    # Métodos internos para acessar o banco de dados usando self.db_config
    def _listar_funcionarios_com_db_config(self):
        conn = None
        cur = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            cur.execute("SELECT id, nome, cargo, telefone, email, ativo FROM funcionarios ORDER BY nome ASC")
            funcionarios = cur.fetchall()
            lista = []
            for row in funcionarios:
                lista.append({
                    "id": row[0],
                    "nome": row[1],
                    "cargo": row[2],
                    "telefone": row[3],
                    "email": row[4],
                    "ativo": row[5]
                })
            return lista
        except psycopg2.Error as e:
            print(f"Erro ao listar funcionários: {e}")
            return []
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    def _salvar_funcionario_no_banco_com_db_config(self, employee_data):
        conn = None
        cur = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            funcionario_id = employee_data.get("id")

            if funcionario_id:
                cur.execute("""
                    UPDATE funcionarios SET
                        nome = %s,
                        cargo = %s,
                        telefone = %s,
                        email = %s,
                        ativo = %s
                    WHERE id = %s
                """, (
                    employee_data["nome"],
                    employee_data["cargo"],
                    employee_data["telefone"],
                    employee_data["email"],
                    employee_data["ativo"],
                    funcionario_id
                ))
            else:
                cur.execute("""
                    INSERT INTO funcionarios (nome, cargo, telefone, email, ativo)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    employee_data["nome"],
                    employee_data["cargo"],
                    employee_data["telefone"],
                    employee_data["email"],
                    employee_data["ativo"]
                ))
                funcionario_id = cur.fetchone()[0]

            conn.commit()
            return funcionario_id
        except psycopg2.Error as e:
            print(f"Erro ao salvar funcionário no banco de dados: {e}")
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

    def _excluir_funcionario_do_banco_com_db_config(self, funcionario_id):
        conn = None
        cur = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            cur.execute("DELETE FROM funcionarios WHERE id = %s", (funcionario_id,))
            conn.commit()
            return True
        except psycopg2.Error as e:
            print(f"Erro ao excluir funcionário do banco de dados: {e}")
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


    def populate_table(self, filtered_employees=None):
        # Limpar a tabela atual
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Recarregar os funcionários do banco de dados para garantir que os dados estão atualizados
        self.all_employees = self._listar_funcionarios_com_db_config() # Usar a nova função interna

        # Usar a lista filtrada ou a lista completa
        employees_to_display = filtered_employees if filtered_employees is not None else self.all_employees

        # Atualizar os status labels
        self.status_label.configure(text=f"Total de funcionários: {len(employees_to_display)}")
        active_count = sum(1 for emp in self.all_employees if emp.get("ativo", False))
        self.active_employees_label.configure(text=f"Funcionários ativos: {active_count}")

        # Definir larguras das colunas
        # Ajustado as larguras para corresponder aos novos headers
        widths = [50, 180, 120, 120, 180, 80]

        # Preencher com os dados
        for row_idx, employee in enumerate(employees_to_display):
            row_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            row_frame.grid(row=row_idx * 2, column=0, sticky="ew", pady=5)

            # Make columns in the row_frame expand proportionally
            for i in range(len(widths)):
                row_frame.grid_columnconfigure(i, weight=1)

            # Determinar a cor do status ativo
            active_status = "Sim" if employee.get("ativo", False) else "Não"
            status_color = "green" if employee.get("ativo", False) else "red"

            # Adicionar os dados do funcionário - Removido 'senha'
            values = [
                employee.get("id", ""),
                employee.get("nome", ""),
                employee.get("cargo", ""),
                employee.get("telefone", ""),
                employee.get("email", ""),
                active_status
            ]

            for col_idx, value in enumerate(values):
                label = ctk.CTkLabel(
                    row_frame,
                    text=str(value),
                    text_color=status_color if col_idx == 5 else None  # Aplica cor à coluna 'Ativo' (agora índice 5)
                )
                # Ajustando o anchor para alinhamento
                if col_idx == 0:  # ID
                    label.configure(anchor="e")
                elif col_idx == 5:  # Ativo (novo índice)
                    label.configure(anchor="center")
                else:
                    label.configure(anchor="w")

                label.grid(row=0, column=col_idx, padx=10, pady=5, sticky="nsew")

            # Adicionar evento de clique para selecionar o funcionário
            row_frame.bind("<Button-1>", lambda e, emp=employee: self.select_employee(emp))
            for widget in row_frame.winfo_children():
                widget.bind("<Button-1>", lambda e, emp=employee: self.select_employee(emp))

            # Adicionar linha separadora
            if row_idx < len(employees_to_display) - 1:
                separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=("#DDDDDD", "#555555"))
                separator.grid(row=row_idx * 2 + 1, column=0, sticky="ew", padx=10)

        # Resetar a seleção após repopular a tabela
        self.reset_selection_buttons()

    def select_employee(self, employee):
        # Desmarcar o funcionário anterior
        if self.selected_employee:
            for widget_row_frame in self.content_frame.winfo_children():
                if isinstance(widget_row_frame, ctk.CTkFrame) and hasattr(widget_row_frame.winfo_children()[0],
                                                                          'cget') and widget_row_frame.winfo_children()[
                    0].cget("text") == str(self.selected_employee.get("id", "")):
                    widget_row_frame.configure(fg_color="transparent")
                    break

        # Marcar o funcionário selecionado
        for widget_row_frame in self.content_frame.winfo_children():
            if isinstance(widget_row_frame, ctk.CTkFrame) and hasattr(widget_row_frame.winfo_children()[0], 'cget') and \
                    widget_row_frame.winfo_children()[0].cget("text") == str(employee.get("id", "")):
                widget_row_frame.configure(fg_color=("gray90", "gray20"))
                break

        # Atualizar o funcionário selecionado
        self.selected_employee = employee

        # Habilitar os botões de ação
        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")

    def search_employees(self):
        search_term = self.search_entry.get().strip().lower()

        if not search_term:
            self.populate_table()
            return

        # Atualizado para buscar apenas por nome ou cargo (já que 'usuario' e 'senha' foram removidos)
        filtered_employees = [
            emp for emp in self.all_employees
            if search_term in emp.get("nome", "").lower() or search_term in emp.get("cargo", "").lower()
        ]

        self.populate_table(filtered_employees)

    def add_employee(self):
        form = EmployeeForm(self, on_save=self.save_new_employee)
        form.focus()

    def save_new_employee(self, employee_data):
        # Salvar no banco de dados
        new_id = self._salvar_funcionario_no_banco_com_db_config(employee_data) # Usar a nova função interna
        if new_id is not None:
            self.populate_table()
            messagebox.showinfo("Sucesso", "Funcionário cadastrado com sucesso!")
        else:
            messagebox.showerror("Erro",
                                 "Falha ao cadastrar o funcionário no banco de dados. Verifique o console para detalhes.")

    def edit_employee(self):
        if not self.selected_employee:
            return

        form = EmployeeForm(self, employee_data=self.selected_employee, on_save=self.save_edited_employee)
        form.focus()

    def save_edited_employee(self, employee_data):
        # Salvar no banco de dados
        updated_id = self._salvar_funcionario_no_banco_com_db_config(employee_data) # Usar a nova função interna
        if updated_id is not None:
            self.populate_table()
            messagebox.showinfo("Sucesso", "Funcionário atualizado com sucesso!")
        else:
            messagebox.showerror("Erro",
                                 "Falha ao atualizar o funcionário no banco de dados. Verifique o console para detalhes.")

        self.reset_selection_buttons()

    def delete_employee(self):
        if not self.selected_employee:
            return

        if messagebox.askyesno("Confirmar Exclusão",
                               f"Tem certeza que deseja excluir o funcionário '{self.selected_employee.get('nome')}'?"):
            if self._excluir_funcionario_do_banco_com_db_config(self.selected_employee.get("id")): # Usar a nova função interna
                self.populate_table()
                messagebox.showinfo("Sucesso", "Funcionário excluído com sucesso!")
            else:
                messagebox.showerror("Erro",
                                     "Falha ao excluir o funcionário do banco de dados. Verifique o console para detalhes.")

        self.reset_selection_buttons()

    def reset_selection_buttons(self):
        """Reseta a seleção de funcionário e desabilita os botões de ação."""
        self.selected_employee = None
        self.edit_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")


# Para teste standalone
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Teste do Módulo de Funcionários")
    app.geometry("1000x600")

    # Configuração do grid
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    # Instanciar o módulo
    employees_module = EmployeesModule(app)
    employees_module.grid(row=0, column=0, sticky="nsew")

    app.mainloop()
