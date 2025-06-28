import customtkinter as ctk
from tkinter import messagebox
import psycopg2

# Importar configurações do banco de dados de um arquivo externo
from db_config import DB_CONFIG


def obter_produtos(search_term=None):
    conn = None  # Inicializa a conexão como None
    cur = None  # Inicializa o cursor como None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        sql_query = "SELECT p.id, p.nome, c.nome, p.descricao, p.ingredientes, p.ativo, p.categoria FROM produtos p LEFT JOIN categoria_produto c ON p.categoria = c.id"

        if search_term:
            search_term_lower = f"%{search_term.lower()}%"
            # Adicionando o filtro
            sql_query += " WHERE LOWER(p.nome) LIKE %s OR LOWER(p.descricao) LIKE %s OR LOWER(p.ingredientes) LIKE %s OR LOWER(c.nome) LIKE %s"
            sql_query += " ORDER BY p.nome"
            cur.execute(sql_query, (search_term_lower, search_term_lower, search_term_lower, search_term_lower))
        else:
            sql_query += " ORDER BY p.nome"
            cur.execute(sql_query)

        rows = cur.fetchall()
        return rows
    except psycopg2.Error as e:
        print(f"Erro ao obter produtos: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def obter_categorias():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM categoria_produto ORDER BY nome")
        categorias = cur.fetchall()
        return categorias
    except psycopg2.Error as e:
        print(f"Erro ao obter categorias: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def inserir_produto(nome, categoria_id, descricao, ingredientes, ativo):
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO produtos (nome, categoria, descricao, ingredientes, ativo) VALUES (%s, %s, %s, %s, %s)",
            (nome, categoria_id, descricao, ingredientes, ativo))
        conn.commit()
        return True
    except psycopg2.Error as e:
        print(f"Erro ao inserir produto: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def atualizar_produto(id, nome, categoria_id, descricao, ingredientes, ativo):
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("UPDATE produtos SET nome=%s, categoria=%s, descricao=%s, ingredientes=%s, ativo=%s WHERE id=%s",
                    (nome, categoria_id, descricao, ingredientes, ativo, id))
        conn.commit()
        return True
    except psycopg2.Error as e:
        print(f"Erro ao atualizar produto: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def excluir_produto(id):
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("DELETE FROM produtos WHERE id=%s", (id,))
        conn.commit()
        return True
    except psycopg2.Error as e:
        print(f"Erro ao excluir produto: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


class ProductForm(ctk.CTkToplevel):
    def __init__(self, master, product_data=None, on_save=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.product_data = product_data
        self.on_save = on_save
        self.categorias = obter_categorias()
        self.categoria_id_map = {nome: id for id, nome in self.categorias}

        self.title("Cadastro de Produto" if not product_data else "Editar Produto")
        self.geometry("500x500")
        self.resizable(False, False)
        self.grab_set()  # Torna a janela modal
        self.transient(master)  # Faz com que a nova janela seja filha da principal

        self.grid_columnconfigure(0, weight=1)

        # Campo Nome do Produto
        self.name_label = ctk.CTkLabel(self, text="Nome do Produto:")
        self.name_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.name_entry = ctk.CTkEntry(self, placeholder_text="Ex: Burger Clássico")
        self.name_entry.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Campo Categoria
        self.category_label = ctk.CTkLabel(self, text="Categoria:")
        self.category_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        self.category_combo = ctk.CTkComboBox(self, values=list(self.categoria_id_map.keys()))
        self.category_combo.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Campo Descrição
        self.description_label = ctk.CTkLabel(self, text="Descrição:")
        self.description_label.grid(row=4, column=0, padx=20, pady=(10, 5), sticky="w")
        self.description_entry = ctk.CTkTextbox(self, height=100)
        self.description_entry.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Campo Ingredientes
        self.ingredients_label = ctk.CTkLabel(self, text="Ingredientes:")
        self.ingredients_label.grid(row=6, column=0, padx=20, pady=(10, 5), sticky="w")
        self.ingredients_entry = ctk.CTkTextbox(self, height=80)
        self.ingredients_entry.grid(row=7, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Checkbox Produto Ativo
        self.active_var = ctk.StringVar(value="1")
        self.active_checkbox = ctk.CTkCheckBox(self, text="Produto ativo", variable=self.active_var, onvalue="1",
                                               offvalue="0")
        self.active_checkbox.grid(row=8, column=0, padx=20, pady=10, sticky="w")

        # Botão Salvar
        self.save_button = ctk.CTkButton(self, text="Salvar", command=self.save_product)
        self.save_button.grid(row=9, column=0, padx=20, pady=20, sticky="ew")

        # Preencher campos se for edição
        if self.product_data:
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, self.product_data.get("nome", ""))
            self.category_combo.set(self.product_data.get("categoria_nome", ""))
            self.description_entry.delete("0.0", "end")
            self.description_entry.insert("0.0", self.product_data.get("descricao", ""))
            self.ingredients_entry.delete("0.0", "end")
            self.ingredients_entry.insert("0.0", self.product_data.get("ingredientes", ""))
            self.active_var.set("1" if self.product_data.get("ativo", True) else "0")
        else:
            # Placeholders
            self.description_entry.insert("0.0", "Descrição do produto (ex: pão, carne, queijo...)")
            self.description_entry.bind("<FocusIn>", lambda e: self.clear_placeholder(self.description_entry,
                                                                                      "Descrição do produto (ex: pão, carne, queijo...)",
                                                                                      e))
            self.description_entry.bind("<FocusOut>", lambda e: self.restore_placeholder(self.description_entry,
                                                                                         "Descrição do produto (ex: pão, carne, queijo...)",
                                                                                         e))

            self.ingredients_entry.insert("0.0", "Ingredientes separados por vírgula (ex: carne, alface, tomate)")
            self.ingredients_entry.bind("<FocusIn>", lambda e: self.clear_placeholder(self.ingredients_entry,
                                                                                      "Ingredientes separados por vírgula (ex: carne, alface, tomate)",
                                                                                      e))
            self.ingredients_entry.bind("<FocusOut>", lambda e: self.restore_placeholder(self.ingredients_entry,
                                                                                         "Ingredientes separados por vírgula (ex: carne, alface, tomate)",
                                                                                         e))

    def clear_placeholder(self, widget, placeholder, event):
        current = widget.get("0.0", "end").strip() if isinstance(widget, ctk.CTkTextbox) else widget.get()
        if current == placeholder:
            widget.delete("0.0", "end") if isinstance(widget, ctk.CTkTextbox) else widget.delete(0, "end")
            widget.configure(text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"])

    def restore_placeholder(self, widget, placeholder, event):
        current = widget.get("0.0", "end").strip() if isinstance(widget, ctk.CTkTextbox) else widget.get().strip()
        if not current:
            widget.insert("0.0", placeholder) if isinstance(widget, ctk.CTkTextbox) else widget.insert(0, placeholder)
            widget.configure(text_color="gray")

    def save_product(self):
        nome = self.name_entry.get().strip()
        categoria_nome = self.category_combo.get()
        categoria_id = self.categoria_id_map.get(categoria_nome)
        descricao = self.description_entry.get("0.0", "end").strip()
        ingredientes = self.ingredients_entry.get("0.0", "end").strip()
        ativo = self.active_var.get() == "1"

        # Remover placeholders antes de salvar, se ainda estiverem presentes
        if descricao == "Descrição do produto (ex: pão, carne, queijo...)":
            descricao = ""
        if ingredientes == "Ingredientes separados por vírgula (ex: carne, alface, tomate)":
            ingredientes = ""

        if not nome or not categoria_id:
            messagebox.showerror("Erro", "Nome e categoria são obrigatórios.")
            return

        if self.product_data:
            success = atualizar_produto(self.product_data["id"], nome, categoria_id, descricao, ingredientes, ativo)
            if success:
                messagebox.showinfo("Sucesso", "Produto atualizado com sucesso!")
            else:
                messagebox.showerror("Erro", "Falha ao atualizar produto.")
        else:
            success = inserir_produto(nome, categoria_id, descricao, ingredientes, ativo)
            if success:
                messagebox.showinfo("Sucesso", "Produto cadastrado com sucesso!")
            else:
                messagebox.showerror("Erro", "Falha ao cadastrar produto.")

        if self.on_save and success:  # Chamar on_save apenas se a operação foi bem-sucedida
            self.on_save()

        self.destroy()  # Fechar o formulário após salvar


class ProductsModule(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)  # Linha para o filtro
        self.grid_rowconfigure(2, weight=0)  # Linha para o cabeçalho da tabela
        self.grid_rowconfigure(3, weight=1)  # Linha para a lista de produtos (scrollable)

        self.title_label = ctk.CTkLabel(self, text="Produtos", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # --- Frame para Filtro de Pesquisa ---
        self.filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.filter_frame.grid_columnconfigure(0, weight=1)  # Campo de pesquisa
        self.filter_frame.grid_columnconfigure(1, weight=0)  # Botão de pesquisa

        self.search_entry = ctk.CTkEntry(self.filter_frame,
                                         placeholder_text="Pesquisar por nome, descrição, ingredientes ou categoria...")
        self.search_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.search_entry.bind("<Return>", self.apply_filter_event)  # Pesquisar ao pressionar Enter

        self.search_button = ctk.CTkButton(self.filter_frame, text="Pesquisar", command=self.apply_filter)
        self.search_button.grid(row=0, column=1, sticky="e")

        # Frame para os cabeçalhos da tabela
        self.header_frame = ctk.CTkFrame(self, fg_color=("#EEEEEE", "#333333"))
        self.header_frame.grid(row=2, column=0, padx=20, pady=(0, 5), sticky="ew")  # row ajustada para 2
        # Configurações de coluna para o cabeçalho para alinhar com as linhas de dados
        self.header_frame.grid_columnconfigure(0, minsize=50, weight=0)  # ID
        self.header_frame.grid_columnconfigure(1, minsize=150, weight=1)  # Nome
        self.header_frame.grid_columnconfigure(2, minsize=100, weight=1)  # Categoria
        self.header_frame.grid_columnconfigure(3, minsize=250, weight=2)  # Descrição (maior peso)
        self.header_frame.grid_columnconfigure(4, minsize=250, weight=2)  # Ingredientes (maior peso)
        self.header_frame.grid_columnconfigure(5, minsize=70, weight=0)  # Ativo

        headers = ["ID", "Nome", "Categoria", "Descrição", "Ingredientes", "Ativo"]

        for i, header in enumerate(headers):
            label = ctk.CTkLabel(self.header_frame, text=header, font=ctk.CTkFont(weight="bold"))
            label.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            # Nao é necessário minsize e weight aqui pois ja foi feito no frame

        # Frame para a lista de produtos (com scrollbar)
        self.product_list_frame = ctk.CTkScrollableFrame(self)
        self.product_list_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="nsew")  # row ajustada para 3

        # As colunas dentro do scrollable frame devem corresponder ao header
        self.product_list_frame.grid_columnconfigure(0, minsize=50, weight=0)  # ID
        self.product_list_frame.grid_columnconfigure(1, minsize=150, weight=1)  # Nome
        self.product_list_frame.grid_columnconfigure(2, minsize=100, weight=1)  # Categoria
        self.product_list_frame.grid_columnconfigure(3, minsize=250, weight=2)  # Descrição
        self.product_list_frame.grid_columnconfigure(4, minsize=250, weight=2)  # Ingredientes
        self.product_list_frame.grid_columnconfigure(5, minsize=70, weight=0)  # Ativo

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")  # row ajustada para 4
        self.button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.add_button = ctk.CTkButton(self.button_frame, text="Novo Produto", command=self.add_product)
        self.add_button.grid(row=0, column=0, padx=10, pady=10)

        self.edit_button = ctk.CTkButton(self.button_frame, text="Editar", command=self.edit_product,
                                         state="disabled")  # Inicializa desabilitado
        self.edit_button.grid(row=0, column=1, padx=10, pady=10)

        self.delete_button = ctk.CTkButton(self.button_frame, text="Excluir", command=self.delete_product,
                                           state="disabled")  # Inicializa desabilitado
        self.delete_button.grid(row=0, column=2, padx=10, pady=10)

        self.refresh_button = ctk.CTkButton(self.button_frame, text="Atualizar", command=self.populate_table)
        self.refresh_button.grid(row=0, column=3, padx=10, pady=10)

        self.status_label = ctk.CTkLabel(self, text="Total de produtos: 0")
        self.status_label.grid(row=5, column=0, padx=20, pady=5, sticky="w")  # Row ajustada para 5

        self.selected_product = None
        self.product_row_frames = []  # Para armazenar os frames das linhas

        self.populate_table()

    def apply_filter_event(self, event=None):
        self.apply_filter()

    def apply_filter(self):
        search_term = self.search_entry.get().strip()
        self.populate_table(search_term)

    def populate_table(self, search_term=None):
        # Limpa todas as linhas existentes, exceto o cabeçalho
        for widget in self.product_list_frame.winfo_children():
            widget.destroy()

        self.products = obter_produtos(search_term)
        self.product_row_frames = []  # Resetar a lista de frames das linhas

        for i, produto_tuple in enumerate(self.products):
            # Formato do produto retornado por obter_produtos: (id, nome, categoria_nome, descricao, ingredientes, ativo, categoria_id)
            product_data_dict = {
                "id": produto_tuple[0],
                "nome": produto_tuple[1],
                "categoria_nome": produto_tuple[2],  # Nome da categoria para exibição
                "descricao": produto_tuple[3],
                "ingredientes": produto_tuple[4],
                "ativo": produto_tuple[5],
                "categoria": produto_tuple[6]  # ID da categoria
            }

            row_frame = ctk.CTkFrame(self.product_list_frame, fg_color="transparent")
            # row_frame.grid(row=i, column=0, sticky="ew", pady=1) # Desnecessário, já que as labels serão direto no scrollable frame
            row_frame.grid(row=i, column=0, columnspan=6, sticky="ew", pady=1)  # Uma linha inteira para cada produto

            # Configura as colunas dentro do row_frame para alinhamento.
            # Estes pesos e minsize devem ser os mesmos do header_frame e do product_list_frame
            row_frame.grid_columnconfigure(0, minsize=50, weight=0)  # ID
            row_frame.grid_columnconfigure(1, minsize=150, weight=1)  # Nome
            row_frame.grid_columnconfigure(2, minsize=100, weight=1)  # Categoria
            row_frame.grid_columnconfigure(3, minsize=250, weight=2)  # Descrição
            row_frame.grid_columnconfigure(4, minsize=250, weight=2)  # Ingredientes
            row_frame.grid_columnconfigure(5, minsize=70, weight=0)  # Ativo

            # Preenche as células
            values = [
                product_data_dict["id"],
                product_data_dict["nome"],
                product_data_dict["categoria_nome"],
                product_data_dict["descricao"],
                product_data_dict["ingredientes"],
                "Sim" if product_data_dict["ativo"] else "Não"
            ]

            for col_idx, value in enumerate(values):
                # Usar wraplength para descrição e ingredientes para quebrar o texto
                if col_idx == 3:  # Descricao
                    label = ctk.CTkLabel(row_frame, text=str(value), anchor="w",
                                         wraplength=240)  # Ajuste wraplength conforme minsize
                elif col_idx == 4:  # Ingredientes
                    label = ctk.CTkLabel(row_frame, text=str(value), anchor="w",
                                         wraplength=240)  # Ajuste wraplength conforme minsize
                else:
                    label = ctk.CTkLabel(row_frame, text=str(value), anchor="w")

                label.grid(row=0, column=col_idx, padx=5, pady=2, sticky="ew")

            # Bind para clique único (seleciona o produto)
            row_frame.bind("<Button-1>", lambda e, p=product_data_dict: self.select_product(p))
            for widget in row_frame.winfo_children():  # Binda os widgets internos também
                widget.bind("<Button-1>", lambda e, p=product_data_dict: self.select_product(p))

            # NOVO: Bind para clique duplo (abre a tela de edição)
            row_frame.bind("<Double-Button-1>", lambda e, p=product_data_dict: self._handle_double_click_edit(p))
            for widget in row_frame.winfo_children():  # Binda os widgets internos também
                widget.bind("<Double-Button-1>", lambda e, p=product_data_dict: self._handle_double_click_edit(p))

            self.product_row_frames.append((row_frame, product_data_dict))  # Armazena o frame e os dados

        self.status_label.configure(text=f"Total de produtos: {len(self.products)}")
        self.reset_selection_buttons()  # Reseta a seleção e os botões após repopular a tabela

    def select_product(self, product_data):
        # Desmarcar o produto anterior
        if self.selected_product:
            for btn_frame, p_data in self.product_row_frames:
                if p_data["id"] == self.selected_product["id"]:
                    btn_frame.configure(fg_color="transparent")  # Resetar a cor do frame
                    break

        # Marcar o produto selecionado
        for btn_frame, p_data in self.product_row_frames:
            if p_data["id"] == product_data["id"]:
                btn_frame.configure(fg_color=("gray90", "gray20"))  # Cor para indicar seleção do frame
                break

        self.selected_product = product_data
        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")

    def _handle_double_click_edit(self, product_data_dict):
        """
        Lida com o clique duplo em uma linha da tabela de produtos.
        Seleciona o produto e abre a tela de edição.
        """
        self.select_product(product_data_dict)  # Primeiro, garante que o produto esteja selecionado
        self.edit_product()  # Em seguida, chama o método de edição

    def add_product(self):
        def on_save_callback():
            self.populate_table()  # Repopula a tabela e reseta a seleção
            # O formulário é destruído dentro do ProductForm.save_product()

        form = ProductForm(self, on_save=on_save_callback)
        form.grab_set()

    def edit_product(self):
        if not self.selected_product:
            messagebox.showwarning("Selecione", "Selecione um produto para editar.")
            return

        def on_save_callback():
            self.populate_table()  # Repopula a tabela e reseta a seleção
            # O formulário é destruído dentro do ProductForm.save_product()

        form = ProductForm(self, product_data=self.selected_product, on_save=on_save_callback)
        form.grab_set()

    def delete_product(self):
        if not self.selected_product:
            messagebox.showwarning("Selecione", "Selecione um produto para excluir.")
            return

        def confirmar_exclusao():
            success = excluir_produto(self.selected_product["id"])
            if success:
                messagebox.showinfo("Sucesso", "Produto excluído com sucesso!")
                self.populate_table()  # Repopula a tabela e reseta a seleção
            else:
                messagebox.showerror("Erro",
                                     "Falha ao excluir produto. Verifique se não há pedidos associados a este produto.")
            confirm_window.destroy()

        confirm_window = ctk.CTkToplevel(self)
        confirm_window.title("Confirmar Exclusão")
        confirm_window.geometry("300x150")
        confirm_window.resizable(False, False)
        confirm_window.grid_columnconfigure(0, weight=1)

        confirm_window.lift()
        confirm_window.focus_force()
        confirm_window.attributes('-topmost', True)

        msg = ctk.CTkLabel(confirm_window, text=f"Excluir o produto:\n{self.selected_product['nome']}?",
                           justify="center")
        msg.grid(row=0, column=0, padx=20, pady=(20, 10))

        button_frame = ctk.CTkFrame(confirm_window, fg_color="transparent")
        button_frame.grid(row=1, column=0, pady=10)

        cancel_btn = ctk.CTkButton(button_frame, text="Cancelar", command=confirm_window.destroy)
        cancel_btn.grid(row=0, column=0, padx=10)

        confirm_btn = ctk.CTkButton(button_frame, text="Excluir", fg_color="#D22B2B", hover_color="#AA0000",
                                    command=confirmar_exclusao)
        confirm_btn.grid(row=0, column=1, padx=10)

        confirm_window.wait_window(confirm_window)  # Faz a janela principal esperar por este modal

    def reset_selection_buttons(self):
        """Reseta a seleção de produto e desabilita os botões de ação."""
        # Desmarca visualmente qualquer seleção anterior
        if self.selected_product:
            for btn_frame, p_data in self.product_row_frames:
                if p_data["id"] == self.selected_product["id"]:
                    btn_frame.configure(fg_color="transparent")
                    break

        self.selected_product = None
        self.edit_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1200x700")  # Aumentei um pouco mais para a nova barra de filtro
    root.title("Produtos")

    products_module = ProductsModule(root)
    products_module.pack(fill="both", expand=True)

    root.mainloop()
