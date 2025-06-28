import customtkinter as ctk
from tkinter import messagebox
import psycopg2

# Importar configurações do banco de dados de um arquivo externo
from db_config import DB_CONFIG


# --- Funções de Banco de Dados para Logradouro, Localidade, Cidade ---

def _get_all_from_table(table_name):
    """Função genérica para obter id e descricao de tabelas de lookup (logradouro, localidade, cidade)."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(f"SELECT id, descricao FROM {table_name} ORDER BY descricao")
        rows = cur.fetchall()
        return [{"id": row[0], "descricao": row[1]} for row in rows]
    except psycopg2.Error as e:
        print(f"Erro ao obter de {table_name}: {e}")
        messagebox.showerror("Erro de Conexão", f"Não foi possível obter dados de {table_name}: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def _insert_into_table(table_name, description):
    """Função genérica para inserir uma nova descricao em tabelas de lookup."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(f"INSERT INTO {table_name} (descricao) VALUES (%s) RETURNING id", (description,))
        new_id = cur.fetchone()[0]
        conn.commit()
        return new_id
    except psycopg2.Error as e:
        print(f"Erro ao inserir em {table_name}: {e}")
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível inserir '{description}' em {table_name}: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# Funções específicas para cada tabela
def obter_logradouros():
    return _get_all_from_table("logradouro")


def inserir_logradouro(descricao):
    return _insert_into_table("logradouro", descricao)


def obter_localidades():
    return _get_all_from_table("localidade")


def inserir_localidade(descricao):
    return _insert_into_table("localidade", descricao)


def obter_cidades():
    return _get_all_from_table("cidade")


def inserir_cidade(descricao):
    return _insert_into_table("cidade", descricao)


# --- Funções de Banco de Dados para Clientes (Atualizadas) ---

def obter_clientes():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                c.id,
                c.nome,
                l.descricao AS logradouro_descricao,
                loc.descricao AS localidade_descricao,
                cid.descricao AS cidade_descricao,
                c.telefone,
                c.email,
                c.logradouro_id,
                c.localidade_id,
                c.cidade_id,
                c.numero_endereco,
                c.complemento_endereco
            FROM clientes c
            LEFT JOIN logradouro l ON c.logradouro_id = l.id
            LEFT JOIN localidade loc ON c.localidade_id = loc.id
            LEFT JOIN cidade cid ON c.cidade_id = cid.id
            ORDER BY c.nome
        """)
        rows = cur.fetchall()

        clientes = []
        for row in rows:
            clientes.append({
                "id": row[0],
                "nome": row[1],
                "logradouro_descricao": row[2],
                "localidade_descricao": row[3],
                "cidade_descricao": row[4],
                "telefone": row[5],
                "email": row[6],
                "logradouro_id": row[7],
                "localidade_id": row[8],
                "cidade_id": row[9],
                "numero_endereco": row[10],
                "complemento_endereco": row[11]
            })

        return clientes

    except psycopg2.Error as e:
        print(f"Erro ao obter clientes: {e}")
        messagebox.showerror("Erro de Conexão", f"Não foi possível obter clientes do banco de dados: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()



def inserir_cliente(nome, telefone, email, logradouro_id, localidade_id, cidade_id, numero_endereco,
                    complemento_endereco):
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO clientes (nome, telefone, email, logradouro_id, localidade_id, cidade_id, numero_endereco, complemento_endereco)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (nome, telefone, email, logradouro_id, localidade_id, cidade_id, numero_endereco, complemento_endereco))
        new_id = cur.fetchone()[0]
        conn.commit()
        return True
    except psycopg2.Error as e:
        print(f"Erro ao inserir cliente: {e}")
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível inserir o cliente: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def atualizar_cliente(id, nome, telefone, email, logradouro_id, localidade_id, cidade_id, numero_endereco,
                      complemento_endereco):
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            UPDATE clientes SET
                nome=%s,
                telefone=%s,
                email=%s,
                logradouro_id=%s,
                localidade_id=%s,
                cidade_id=%s,
                numero_endereco=%s,
                complemento_endereco=%s -- NOVO
            WHERE id=%s
        """, (
        nome, telefone, email, logradouro_id, localidade_id, cidade_id, numero_endereco, complemento_endereco, id))
        conn.commit()
        return True
    except psycopg2.Error as e:
        print(f"Erro ao atualizar cliente: {e}")
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível atualizar o cliente: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def excluir_cliente(id):
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("DELETE FROM clientes WHERE id=%s", (id,))
        conn.commit()
        return True
    except psycopg2.Error as e:
        print(f"Erro ao excluir cliente: {e}")
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível excluir o cliente: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# --- Formulário Genérico para Adicionar Descrições (Logradouro, Localidade, Cidade) ---

class AddDescriptionForm(ctk.CTkToplevel):
    def __init__(self, master, title_text, table_name, on_save_callback, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title_text = title_text
        self.table_name = table_name
        self.on_save_callback = on_save_callback

        self.title(f"Novo(a) {self.title_text}")
        self.geometry("300x200")
        self.resizable(False, False)
        self.grab_set()  # Make the window modal
        self.transient(master)  # Make the new window a child of the main window

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=f"Adicionar Novo(a) {self.title_text}", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 10))

        self.description_entry = ctk.CTkEntry(self, placeholder_text=f"Digite o(a) {self.title_text}")
        self.description_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=20, pady=10)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        cancel_btn = ctk.CTkButton(button_frame, text="Cancelar", command=self.destroy)
        cancel_btn.grid(row=0, column=0, padx=10)

        save_btn = ctk.CTkButton(button_frame, text="Salvar", command=self.save_description)
        save_btn.grid(row=0, column=1, padx=10)

    def save_description(self):
        description = self.description_entry.get().strip()
        if not description:
            messagebox.showerror("Erro", "A descrição não pode estar vazia.")
            return

        new_id = None
        if self.table_name == "logradouro":
            new_id = inserir_logradouro(description)
        elif self.table_name == "localidade":
            new_id = inserir_localidade(description)
        elif self.table_name == "cidade":
            new_id = inserir_cidade(description)

        if new_id:
            messagebox.showinfo("Sucesso", f"{self.title_text} '{description}' adicionado(a) com sucesso!")
            if self.on_save_callback:
                self.on_save_callback(new_id, description)
            self.destroy()
        else:
            messagebox.showerror("Erro", f"Falha ao adicionar {self.title_text}.")


# --- ClientForm (Updated for Address ComboBoxes) ---

class ClientForm(ctk.CTkToplevel):
    def __init__(self, master, client_data=None, on_save=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.client_data = client_data
        self.on_save = on_save

        self.logradouros_data = []
        self.localidades_data = []
        self.cidades_data = []

        self.logradouro_id_map = {}  # Maps of name_description -> id
        self.localidade_id_map = {}
        self.cidade_id_map = {}

        self.title("Cadastro de Cliente" if not client_data else "Editar Cliente")
        self.geometry("500x700")  # Increased height for new fields
        self.resizable(False, False)
        self.grab_set()  # Makes the window modal
        self.transient(master)

        self.grid_columnconfigure(0, weight=1)

        # Form Title
        form_title_label = ctk.CTkLabel(
            self,
            text="Cadastro de Cliente" if not client_data else "Editar Cliente",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        form_title_label.grid(row=0, column=0, padx=20, pady=(20, 20), sticky="ew")

        # Form Frame for better organization
        form_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_content_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        form_content_frame.grid_columnconfigure(0, weight=1)  # Column for labels
        form_content_frame.grid_columnconfigure(1, weight=2)  # Column for entries/comboboxes (larger)
        form_content_frame.grid_columnconfigure(2, weight=0)  # Column for "+" buttons

        # Name
        ctk.CTkLabel(form_content_frame, text="Nome:", anchor="w").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.name_entry = ctk.CTkEntry(form_content_frame, placeholder_text="Nome Completo")
        self.name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew", columnspan=2)  # Occupies 2 columns

        # Phone
        ctk.CTkLabel(form_content_frame, text="Telefone:", anchor="w").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.phone_entry = ctk.CTkEntry(form_content_frame, placeholder_text="Telefone (ex: 11987654321)")
        self.phone_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew", columnspan=2)

        # Email
        ctk.CTkLabel(form_content_frame, text="Email:", anchor="w").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.email_entry = ctk.CTkEntry(form_content_frame, placeholder_text="email@exemplo.com")
        self.email_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew", columnspan=2)

        # Logradouro
        ctk.CTkLabel(form_content_frame, text="Logradouro:", anchor="w").grid(row=3, column=0, padx=5, pady=5,
                                                                              sticky="w")
        self.logradouro_combo = ctk.CTkComboBox(form_content_frame, values=[])
        self.logradouro_combo.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.logradouro_add_button = ctk.CTkButton(form_content_frame, text="+", width=30, command=self.add_logradouro)
        self.logradouro_add_button.grid(row=3, column=2, padx=(0, 5), pady=5, sticky="e")

        # Address Number
        ctk.CTkLabel(form_content_frame, text="Número:", anchor="w").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.numero_endereco_entry = ctk.CTkEntry(form_content_frame, placeholder_text="Número da casa/apto")
        self.numero_endereco_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew", columnspan=2)

        # NEW: Address Complement
        ctk.CTkLabel(form_content_frame, text="Complemento:", anchor="w").grid(row=5, column=0, padx=5, pady=5,
                                                                               sticky="w")
        self.complemento_endereco_entry = ctk.CTkEntry(form_content_frame, placeholder_text="Apto, Bloco, Casa, etc.")
        self.complemento_endereco_entry.grid(row=5, column=1, padx=5, pady=5, sticky="ew", columnspan=2)

        # Locality (Neighborhood)
        ctk.CTkLabel(form_content_frame, text="Localidade (Bairro):", anchor="w").grid(row=6, column=0, padx=5, pady=5,
                                                                                       # Adjusted row
                                                                                       sticky="w")
        self.localidade_combo = ctk.CTkComboBox(form_content_frame, values=[])
        self.localidade_combo.grid(row=6, column=1, padx=5, pady=5, sticky="ew")  # Adjusted row
        self.localidade_add_button = ctk.CTkButton(form_content_frame, text="+", width=30, command=self.add_localidade)
        self.localidade_add_button.grid(row=6, column=2, padx=(0, 5), pady=5, sticky="e")  # Adjusted row

        # City
        ctk.CTkLabel(form_content_frame, text="Cidade:", anchor="w").grid(row=7, column=0, padx=5, pady=5,
                                                                          sticky="w")  # Adjusted row
        self.cidade_combo = ctk.CTkComboBox(form_content_frame, values=[])
        self.cidade_combo.grid(row=7, column=1, padx=5, pady=5, sticky="ew")  # Adjusted row
        self.cidade_add_button = ctk.CTkButton(form_content_frame, text="+", width=30, command=self.add_cidade)
        self.cidade_add_button.grid(row=7, column=2, padx=(0, 5), pady=5, sticky="e")  # Adjusted row

        # Form action buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancelar",
            fg_color="#D22B2B",
            hover_color="#AA0000",
            command=self.destroy
        )
        cancel_button.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="e")

        self.save_button = ctk.CTkButton(button_frame, text="Salvar", command=self.save_client)
        self.save_button.grid(row=0, column=1, padx=(10, 0), pady=10, sticky="w")

        self._load_address_comboboxes()  # Load data for comboboxes

        # Populate fields if editing
        if client_data:
            self.name_entry.insert(0, client_data["nome"])
            self.phone_entry.insert(0, client_data["telefone"])
            self.email_entry.insert(0, client_data["email"])
            self.numero_endereco_entry.insert(0, client_data.get("numero_endereco", ""))  # Populate number
            self.complemento_endereco_entry.insert(0,
                                                   client_data.get("complemento_endereco", ""))  # Populate complement

            # Populate comboboxes with existing client values
            # client_data already comes with descriptions from obter_clientes
            if client_data.get("logradouro_descricao"):
                self.logradouro_combo.set(client_data["logradouro_descricao"])
            if client_data.get("localidade_descricao"):
                self.localidade_combo.set(client_data["localidade_descricao"])
            if client_data.get("cidade_descricao"):
                self.cidade_combo.set(client_data["cidade_descricao"])

    def _load_address_comboboxes(self):
        """Loads data for logradouro, localidade, and cidade comboboxes."""
        self.logradouros_data = obter_logradouros()
        self.localidades_data = obter_localidades()
        self.cidades_data = obter_cidades()

        logradouro_names = ["Selecione..."] + [l["descricao"] for l in self.logradouros_data]
        localidade_names = ["Selecione..."] + [l["descricao"] for l in self.localidades_data]
        cidade_names = ["Selecione..."] + [c["descricao"] for c in self.cidades_data]

        self.logradouro_combo.configure(values=logradouro_names)
        self.localidade_combo.configure(values=localidade_names)
        self.cidade_combo.configure(values=cidade_names)

        self.logradouro_combo.set("Selecione...")
        self.localidade_combo.set("Selecione...")
        self.cidade_combo.set("Selecione...")

        # Populate name_description -> id maps
        self.logradouro_id_map = {l["descricao"]: l["id"] for l in self.logradouros_data}
        self.localidade_id_map = {l["descricao"]: l["id"] for l in self.localidades_data}
        self.cidade_id_map = {c["descricao"]: c["id"] for c in self.cidades_data}

    def add_logradouro(self):
        def on_save_callback(new_id, description):
            self._load_address_comboboxes()  # Reload comboboxes
            self.logradouro_combo.set(description)  # Select new item

        AddDescriptionForm(self, "Logradouro", "logradouro", on_save_callback)

    def add_localidade(self):
        def on_save_callback(new_id, description):
            self._load_address_comboboxes()
            self.localidade_combo.set(description)

        AddDescriptionForm(self, "Localidade", "localidade", on_save_callback)

    def add_cidade(self):
        def on_save_callback(new_id, description):
            self._load_address_comboboxes()
            self.cidade_combo.set(description)

        AddDescriptionForm(self, "Cidade", "cidade", on_save_callback)



    def save_client(self):
        nome = self.name_entry.get().strip()
        telefone = self.phone_entry.get().strip()
        email = self.email_entry.get().strip()
        numero_endereco = self.numero_endereco_entry.get().strip()
        complemento_endereco = self.complemento_endereco_entry.get().strip()  # NEW: Get complement

        selected_logradouro_name = self.logradouro_combo.get()
        selected_localidade_name = self.localidade_combo.get()
        selected_cidade_name = self.cidade_combo.get()

        logradouro_id = self.logradouro_id_map.get(selected_logradouro_name)
        localidade_id = self.localidade_id_map.get(selected_localidade_name)
        cidade_id = self.cidade_id_map.get(selected_cidade_name)

        if not nome:
            messagebox.showerror("Erro", "O nome é obrigatório.")
            return

        # Basic validation for address selection
        if selected_logradouro_name == "Selecione..." or selected_localidade_name == "Selecione..." or selected_cidade_name == "Selecione...":
            messagebox.showwarning("Aviso", "Por favor, selecione um Logradouro, Localidade e Cidade válidos.")
            return

        # Convert to None if string is empty or 'Selecione...'
        logradouro_id = logradouro_id if logradouro_id else None
        localidade_id = localidade_id if localidade_id else None
        cidade_id = cidade_id if cidade_id else None
        # For complement, if empty, can be None or empty string, depending on your DB preference
        complemento_endereco = complemento_endereco if complemento_endereco else None

        if self.client_data:
            success = atualizar_cliente(self.client_data["id"], nome, telefone, email,
                                        logradouro_id, localidade_id, cidade_id, numero_endereco, complemento_endereco)
        else:
            success = inserir_cliente(nome, telefone, email,
                                      logradouro_id, localidade_id, cidade_id, numero_endereco, complemento_endereco)

        if success and self.on_save:
            new_client_data = {
                "id": self.client_data["id"] if self.client_data else None,
                "nome": nome,
                "telefone": telefone,
                "email": email,
                "logradouro_descricao": selected_logradouro_name,
                "localidade_descricao": selected_localidade_name,
                "cidade_descricao": selected_cidade_name,
                "numero_endereco": numero_endereco,
                "complemento_endereco": complemento_endereco
            }
            self.on_save(new_client_data)
            self.destroy()


# --- ClientsModule (Updated to Display New Address Format) ---

class ClientsModule(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Make the scrollable frame expand

        self.title_label = ctk.CTkLabel(self, text="Gerenciamento de Clientes",
                                        font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Filter Frame - New layout for additional filters
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.filter_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)  # Adjust columns

        # General search field by Name, Phone, Email, etc.
        self.search_label = ctk.CTkLabel(self.filter_frame, text="Buscar Cliente:")
        self.search_label.grid(row=0, column=0, padx=(10, 5), pady=(10, 5), sticky="w")
        self.search_entry = ctk.CTkEntry(
            self.filter_frame,
            placeholder_text="Nome, telefone, email ou endereço...",
            width=200
        )
        self.search_entry.grid(row=0, column=1, padx=(0, 10), pady=(10, 5), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.apply_filters)  # Bind to apply filters on typing

        # Filter by Logradouro (Kept)
        self.logradouro_filter_label = ctk.CTkLabel(self.filter_frame, text="Logradouro:")
        self.logradouro_filter_label.grid(row=0, column=2, padx=(10, 5), pady=(10, 5), sticky="w")
        self.logradouro_filter_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="Logradouro...", width=150)
        self.logradouro_filter_entry.grid(row=0, column=3, padx=(0, 10), pady=(10, 5), sticky="ew")
        self.logradouro_filter_entry.bind("<KeyRelease>", self.apply_filters)

        # Filter by Locality (Neighborhood) (Kept)
        self.localidade_filter_label = ctk.CTkLabel(self.filter_frame, text="Localidade:")
        self.localidade_filter_label.grid(row=1, column=0, padx=(10, 5), pady=(5, 10), sticky="w")
        self.localidade_filter_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="Bairro/Localidade...",
                                                    width=200)
        self.localidade_filter_entry.grid(row=1, column=1, padx=(0, 10), pady=(5, 10), sticky="ew")
        self.localidade_filter_entry.bind("<KeyRelease>", self.apply_filters)

        # Clear Filters Button
        self.clear_filters_button = ctk.CTkButton(self.filter_frame, text="Limpar Filtros", command=self.clear_filters)
        self.clear_filters_button.grid(row=1, column=2, padx=(10, 10), pady=(5, 10), sticky="ew",
                                       columnspan=2)  # Adjusted colspan

        self.client_list_frame = ctk.CTkScrollableFrame(self)
        self.client_list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        # Client table header
        self.header_frame = ctk.CTkFrame(self.client_list_frame, fg_color=("#EEEEEE", "#333333"))
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.client_list_frame.grid_columnconfigure(0, weight=1)

        # Updating column headers
        # REMOVED: "Logradouro", "Número", "Localidade", "Cidade"
        headers = ["ID", "Nome", "Endereço Completo", "Telefone", "Email"]
        # Adjusted widths for the new "Endereço Completo" column
        widths = [50, 150, 350, 100, 150]

        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                self.header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            )
            label.grid(row=0, column=i, padx=10, pady=10, sticky="w")
            self.header_frame.grid_columnconfigure(i, minsize=widths[i], weight=1)

        # Table content will be populated here
        self.table_content_frame = ctk.CTkFrame(self.client_list_frame, fg_color="transparent")
        self.table_content_frame.grid(row=1, column=0, sticky="nsew")
        self.client_list_frame.grid_rowconfigure(1, weight=1)

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.add_button = ctk.CTkButton(self.button_frame, text="Novo Cliente", command=self.add_client)
        self.add_button.grid(row=0, column=0, padx=10, pady=10)

        self.edit_button = ctk.CTkButton(self.button_frame, text="Editar", command=self.edit_client, state="disabled")
        self.edit_button.grid(row=0, column=1, padx=10, pady=10)

        self.delete_button = ctk.CTkButton(self.button_frame, text="Excluir", command=self.delete_client,
                                           state="disabled")
        self.delete_button.grid(row=0, column=2, padx=10, pady=10)

        self.refresh_button = ctk.CTkButton(self.button_frame, text="Atualizar", command=self.populate_table)
        self.refresh_button.grid(row=0, column=3, padx=10, pady=10)

        self.status_label = ctk.CTkLabel(self, text="Total de clientes: 0")
        self.status_label.grid(row=4, column=0, padx=20, pady=5, sticky="w")

        self.selected_client = None
        self.all_clients = []
        self.populate_table()

    def populate_table(self, filtered_clients=None):
        """
        Populates the client table. If `filtered_clients` is provided, uses it.
        Otherwise, loads all clients from the database.
        """
        for widget in self.table_content_frame.winfo_children():
            widget.destroy()

        self.all_clients = obter_clientes()  # Agora retorna lista de dicionários

        clients_to_display = filtered_clients if filtered_clients is not None else self.all_clients

        self.selected_client = None
        self.edit_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")

        widths = [50, 150, 350, 100, 150]

        for row_idx, cliente in enumerate(clients_to_display):
            row_frame = ctk.CTkFrame(self.table_content_frame, fg_color="transparent")
            row_frame.grid(row=row_idx * 2, column=0, sticky="ew", pady=2)
            self.table_content_frame.grid_columnconfigure(0, weight=1)

            for i in range(len(widths)):
                row_frame.grid_columnconfigure(i, weight=1)

            # Montar endereço completo
            logradouro = cliente.get("logradouro_descricao") or ""
            numero = str(cliente.get("numero_endereco") or "")
            complemento = cliente.get("complemento_endereco") or ""
            localidade = cliente.get("localidade_descricao") or ""
            cidade = cliente.get("cidade_descricao") or ""

            endereco_completo_parts = []
            if logradouro:
                endereco_completo_parts.append(logradouro)
            if numero:
                endereco_completo_parts.append(f"Nº {numero}")
            if complemento:
                endereco_completo_parts.append(f"({complemento})")
            if localidade:
                endereco_completo_parts.append(localidade)
            if cidade:
                endereco_completo_parts.append(cidade)

            endereco_completo = ", ".join(endereco_completo_parts) if endereco_completo_parts else "Não informado"

            # Mapear dados para as colunas da tabela
            values = [
                cliente.get("id"),
                cliente.get("nome"),
                endereco_completo,
                cliente.get("telefone"),
                cliente.get("email")
            ]

            for col_idx, value in enumerate(values):
                label = ctk.CTkLabel(
                    row_frame,
                    text=str(value) if value is not None else "",
                    anchor="w"
                )
                label.grid(row=0, column=col_idx, padx=10, pady=5, sticky="nsew")

            # Bind para seleção com clique
            row_frame.bind("<Button-1>", lambda e, c=cliente: self.select_client(c))
            for widget in row_frame.winfo_children():
                widget.bind("<Button-1>", lambda e, c=cliente: self.select_client(c))

            # Bind para abrir a edição com duplo clique
            row_frame.bind("<Double-Button-1>", lambda e, c=cliente: self._handle_double_click_edit(c))
            for widget in row_frame.winfo_children():
                widget.bind("<Double-Button-1>", lambda e, c=cliente: self._handle_double_click_edit(c))

            # Separador entre as linhas
            if row_idx < len(clients_to_display) - 1:
                separator = ctk.CTkFrame(self.table_content_frame, height=1, fg_color=("#DDDDDD", "#555555"))
                separator.grid(row=row_idx * 2 + 1, column=0, sticky="ew", padx=10)

        self.status_label.configure(text=f"Total de clientes: {len(clients_to_display)}")

    def select_client(self, cliente_data):
        """
        Seleciona um cliente e ativa os botões de ação (Editar / Excluir).
        cliente_data: dicionário contendo os dados completos do cliente.
        """

        # Deseleciona o cliente anterior (se houver)
        if self.selected_client:
            for row_frame in self.table_content_frame.winfo_children():
                if isinstance(row_frame, ctk.CTkFrame) and row_frame.winfo_children():
                    primeiro_campo = row_frame.winfo_children()[0].cget("text")
                    if primeiro_campo == str(self.selected_client.get("id")):
                        row_frame.configure(fg_color="transparent")
                        break

        # Atualiza o cliente selecionado
        self.selected_client = {
            "id": cliente_data.get("id"),
            "nome": cliente_data.get("nome"),
            "logradouro_descricao": cliente_data.get("logradouro_descricao"),
            "localidade_descricao": cliente_data.get("localidade_descricao"),
            "cidade_descricao": cliente_data.get("cidade_descricao"),
            "telefone": cliente_data.get("telefone"),
            "email": cliente_data.get("email"),
            "logradouro_id": cliente_data.get("logradouro_id"),
            "localidade_id": cliente_data.get("localidade_id"),
            "cidade_id": cliente_data.get("cidade_id"),
            "numero_endereco": cliente_data.get("numero_endereco"),
            "complemento_endereco": cliente_data.get("complemento_endereco")
        }

        # Marca o cliente selecionado na interface
        for row_frame in self.table_content_frame.winfo_children():
            if isinstance(row_frame, ctk.CTkFrame) and row_frame.winfo_children():
                primeiro_campo = row_frame.winfo_children()[0].cget("text")
                if primeiro_campo == str(self.selected_client.get("id")):
                    row_frame.configure(fg_color=("gray90", "gray20"))  # Cor de destaque
                    break

        # Ativa os botões de ação
        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")

    def _handle_double_click_edit(self, cliente_data_tuple):
        """
        Handles double click on a client table row.
        Selects the client and opens the edit screen.
        """
        self.select_client(cliente_data_tuple)  # First, ensure the client is selected
        self.edit_client()  # Then, call the edit method

    def apply_filters(self, event=None):
        """
        Filters the client list based on search terms in all filter fields.
        """
        # Get all search terms (converting to lowercase for case-insensitive search)
        search_term_general = self.search_entry.get().strip().lower()
        search_term_logradouro = self.logradouro_filter_entry.get().strip().lower()
        search_term_localidade = self.localidade_filter_entry.get().strip().lower()

        filtered_clients = []
        for client in self.all_clients:
            # Unpack client data for easier reading
            client_id, client_name, logradouro_desc, localidade_desc, cidade_desc, \
                telefone, email, logradouro_id, localidade_id, cidade_id, numero_endereco, complemento_endereco = client  # NEW: complemento_endereco

            # Convert to lowercase and string (for numero_endereco which can be int/None)
            client_name_lower = str(client_name).lower() if client_name else ""
            telefone_lower = str(telefone).lower() if telefone else ""
            email_lower = str(email).lower() if email else ""
            logradouro_desc_lower = str(logradouro_desc).lower() if logradouro_desc else ""
            localidade_desc_lower = str(localidade_desc).lower() if localidade_desc else ""
            numero_endereco_str = str(numero_endereco).lower() if numero_endereco is not None else ""
            complemento_endereco_lower = str(
                complemento_endereco).lower() if complemento_endereco else ""  # NEW: for filter

            cidade_desc_lower = str(cidade_desc).lower() if cidade_desc else ""
            # CONCATENATION for general filter
            full_address_for_search = f"{logradouro_desc_lower} {numero_endereco_str} {complemento_endereco_lower} {localidade_desc_lower} {cidade_desc_lower}".strip()

            # Filter criteria
            match_general_search = (
                    search_term_general in client_name_lower or
                    search_term_general in telefone_lower or
                    search_term_general in email_lower or
                    search_term_general in full_address_for_search
            )

            match_logradouro = (not search_term_logradouro) or (search_term_logradouro in logradouro_desc_lower)
            match_localidade = (not search_term_localidade) or (search_term_localidade in localidade_desc_lower)

            # If general search is empty, we don't use it as a primary criterion
            # If searching for specific terms, all must be met
            if (not search_term_general or match_general_search) and \
                    match_logradouro and match_localidade:
                filtered_clients.append(client)

        self.populate_table(filtered_clients)

    def clear_filters(self):
        """Clears all filter fields and reloads all clients."""
        self.search_entry.delete(0, ctk.END)
        self.logradouro_filter_entry.delete(0, ctk.END)
        self.localidade_filter_entry.delete(0, ctk.END)
        self.populate_table()

    def add_client(self):
        def on_save_callback():
            self.populate_table()

        form = ClientForm(self, on_save=on_save_callback)
        form.grab_set()

    def edit_client(self):
        if not self.selected_client:
            messagebox.showwarning("Selecione", "Selecione um cliente para editar.")
            return

        def on_save_callback():
            self.populate_table()

        form = ClientForm(self, client_data=self.selected_client, on_save=on_save_callback)
        form.grab_set()

    def delete_client(self):
        if not self.selected_client:
            messagebox.showwarning("Selecione", "Selecione um cliente para excluir.")
            return

        self._show_confirm_dialog(
            title="Confirmar Exclusão",
            message=f"Excluir o cliente:\\n{self.selected_client['nome']}?",
            on_confirm=self._perform_delete_client
        )

    def _perform_delete_client(self):
        """Internal function to perform deletion after confirmation."""
        if excluir_cliente(self.selected_client["id"]):
            messagebox.showinfo("Sucesso", "Cliente excluído com sucesso!")
            self.selected_client = None
            self.populate_table()

    def _show_confirm_dialog(self, title, message, on_confirm):
        """
        Creates a custom confirmation dialog window, as messagebox.askyesno
        can cause issues in some CustomTkinter/PyInstaller configurations.
        """
        confirm_window = ctk.CTkToplevel(self)
        confirm_window.title(title)
        confirm_window.geometry("350x180")
        confirm_window.resizable(False, False)
        confirm_window.grid_columnconfigure(0, weight=1)
        confirm_window.transient(self)
        confirm_window.grab_set()
        confirm_window.focus_force()

        msg_label = ctk.CTkLabel(confirm_window, text=message, justify="center", wraplength=300)
        msg_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        button_frame = ctk.CTkFrame(confirm_window, fg_color="transparent")
        button_frame.grid(row=1, column=0, pady=10)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        cancel_btn = ctk.CTkButton(button_frame, text="Cancelar", command=confirm_window.destroy)
        cancel_btn.grid(row=0, column=0, padx=10)

        confirm_btn = ctk.CTkButton(button_frame, text="Confirmar", fg_color="#D22B2B", hover_color="#AA0000",
                                    command=lambda: [on_confirm(), confirm_window.destroy()])
        confirm_btn.grid(row=0, column=1, padx=10)

        self.wait_window(confirm_window)


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1000x700")
    root.title("Clientes")

    clients_module = ClientsModule(root)
    clients_module.pack(fill="both", expand=True)

    root.mainloop()
