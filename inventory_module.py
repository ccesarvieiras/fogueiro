import customtkinter as ctk
from tkinter import messagebox
import os
from datetime import datetime
import psycopg2

# Importar configurações do banco de dados de um arquivo externo
from db_config import DB_CONFIG


def listar_itens_estoque():
    """
    Função para listar todos os itens do estoque do banco de dados,
    incluindo informações do produto associado.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                e.id, 
                e.produto_id, 
                p.nome as produto_nome, 
                e.quantidade, 
                e.unidade, 
                e.estoque_minimo
            FROM estoque e
            JOIN produtos p ON e.produto_id = p.id
            ORDER BY p.nome ASC
        """)
        itens = cur.fetchall()
        lista = []
        for row in itens:
            lista.append({
                "id": row[0],
                "produto_id": row[1],
                "nome": row[2],  # Nome do produto
                "quantidade": float(row[3]),
                "unidade": row[4],
                "estoque_minimo": float(row[5])
            })
        return lista
    except psycopg2.Error as e:
        print(f"Erro ao listar itens do estoque: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def listar_produtos_para_cadastro_estoque():
    """
    Lista apenas os produtos que AINDA NÃO possuem um registro no estoque,
    para que o usuário possa adicionar um novo item de estoque.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Seleciona produtos que não estão na tabela 'estoque'
        cur.execute("""
            SELECT p.id, p.nome
            FROM produtos p
            LEFT JOIN estoque e ON p.id = e.produto_id
            WHERE e.produto_id IS NULL
            ORDER BY p.nome ASC
        """)
        produtos = cur.fetchall()
        lista = []
        for row in produtos:
            lista.append({
                "id": row[0],
                "nome": row[1]
            })
        return lista
    except psycopg2.Error as e:
        print(f"Erro ao listar produtos para cadastro de estoque: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def salvar_item_estoque_no_banco(item_data):
    """
    Salva ou atualiza um item de estoque no banco de dados.
    Se item_data contém 'id', tenta atualizar; caso contrário, insere um novo.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        estoque_id = item_data.get("id")

        if estoque_id:
            # Atualizar item de estoque existente
            cur.execute("""
                UPDATE estoque SET
                    produto_id = %s,
                    quantidade = %s,
                    unidade = %s,
                    estoque_minimo = %s
                WHERE id = %s
            """, (
                item_data["produto_id"],
                item_data["quantidade"],
                item_data["unidade"],
                item_data["estoque_minimo"],
                estoque_id
            ))
        else:
            # Inserir novo item de estoque
            cur.execute("""
                INSERT INTO estoque (produto_id, quantidade, unidade, estoque_minimo)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                item_data["produto_id"],
                item_data["quantidade"],
                item_data["unidade"],
                item_data["estoque_minimo"]
            ))
            estoque_id = cur.fetchone()[0]

        conn.commit()
        return estoque_id
    except psycopg2.Error as e:
        print(f"Erro ao salvar item de estoque no banco de dados: {e}")
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


def salvar_movimentacao_estoque_no_banco(movement_data):
    """
    Salva uma movimentação de estoque no banco de dados.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Inserir movimentação
        cur.execute("""
            INSERT INTO movimentacoes_estoque (item_estoque_id, tipo, quantidade, data, motivo, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            movement_data["item_estoque_id"],
            movement_data["tipo"],
            movement_data["quantidade"],
            datetime.strptime(movement_data["data"], "%d/%m/%Y"),  # Converter string para datetime
            movement_data["motivo"],
            movement_data["observacoes"]
        ))
        movement_id = cur.fetchone()[0]

        # Atualizar a quantidade do item no estoque
        if movement_data["tipo"] == "entrada":
            cur.execute(
                "UPDATE estoque SET quantidade = quantidade + %s WHERE id = %s",
                (movement_data["quantidade"], movement_data["item_estoque_id"])
            )
        else:  # Saída
            cur.execute(
                "UPDATE estoque SET quantidade = quantidade - %s WHERE id = %s",
                (movement_data["quantidade"], movement_data["item_estoque_id"])
            )

        conn.commit()
        return movement_id
    except psycopg2.Error as e:
        print(f"Erro ao salvar movimentação de estoque no banco de dados: {e}")
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


def listar_movimentacoes_por_item(item_estoque_id):
    """
    Lista as movimentações de estoque para um item específico.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                m.id, 
                m.tipo, 
                m.quantidade, 
                m.data, 
                m.motivo, 
                m.observacoes
            FROM movimentacoes_estoque m
            WHERE m.item_estoque_id = %s
            ORDER BY m.data DESC, m.id DESC
        """, (item_estoque_id,))
        movimentacoes = cur.fetchall()
        lista = []
        for row in movimentacoes:
            lista.append({
                "id": row[0],
                "tipo": row[1],
                "quantidade": float(row[2]),
                "data": row[3].strftime("%d/%m/%Y"),  # Formatar para exibição
                "motivo": row[4],
                "observacoes": row[5]
            })
        return lista
    except psycopg2.Error as e:
        print(f"Erro ao listar movimentações do item {item_estoque_id}: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


class InventoryItemForm(ctk.CTkToplevel):
    def __init__(self, master, products_for_new_item, item_data=None, on_save=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.products_for_new_item = products_for_new_item  # Produtos disponíveis para um NOVO item de estoque
        self.item_data = item_data  # Dados do item de estoque se for edição
        self.on_save = on_save

        # Configuração da janela
        self.title("Cadastro de Item de Estoque" if not item_data else "Editar Item de Estoque")
        self.geometry("500x600")  # Aumentado a altura de 500 para 600
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
            text="Cadastro de Item de Estoque" if not item_data else "Editar Item de Estoque",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Frame do formulário
        self.form_frame = ctk.CTkFrame(self)
        self.form_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.form_frame.grid_columnconfigure(1, weight=1)

        # Campos do formulário
        # Nome do Produto (ou ComboBox para novo item)
        self.product_label = ctk.CTkLabel(
            self.form_frame,
            text="Produto:",
            anchor="w"
        )
        self.product_label.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="w")

        if self.item_data:  # Modo edição: exibe o nome do produto
            self.product_name_value = ctk.CTkLabel(
                self.form_frame,
                text=self.item_data.get("nome", "")
            )
            self.product_name_value.grid(row=0, column=1, padx=(0, 20), pady=(20, 10), sticky="ew")
            self.product_id = self.item_data.get("produto_id")  # Armazena o produto_id
        else:  # Modo cadastro: ComboBox para selecionar produto
            product_names = ["Selecione um produto..."] + [p["nome"] for p in self.products_for_new_item]
            self.product_combo = ctk.CTkComboBox(
                self.form_frame,
                values=product_names
            )
            self.product_combo.grid(row=0, column=1, padx=(0, 20), pady=(20, 10), sticky="ew")
            self.product_combo.set("Selecione um produto...")
            self.product_id = None  # Será definido ao salvar

        # Quantidade
        self.quantity_label = ctk.CTkLabel(
            self.form_frame,
            text="Quantidade:",
            anchor="w"
        )
        self.quantity_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")

        self.quantity_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="0"
        )
        self.quantity_entry.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Unidade
        self.unit_label = ctk.CTkLabel(
            self.form_frame,
            text="Unidade:",
            anchor="w"
        )
        self.unit_label.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="w")

        self.unit_combo = ctk.CTkComboBox(
            self.form_frame,
            values=["un", "kg", "g", "l", "ml", "cx", "pct"]
        )
        self.unit_combo.grid(row=2, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Estoque mínimo
        self.min_stock_label = ctk.CTkLabel(
            self.form_frame,
            text="Estoque Mínimo:",
            anchor="w"
        )
        self.min_stock_label.grid(row=3, column=0, padx=(20, 10), pady=10, sticky="w")

        self.min_stock_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="0"
        )
        self.min_stock_entry.grid(row=3, column=1, padx=(0, 20), pady=10, sticky="ew")

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
            command=self.save_item
        )
        self.save_button.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="w")

        # Preencher os campos se for edição
        if self.item_data:
            self.quantity_entry.insert(0, str(self.item_data.get("quantidade", "")))
            self.unit_combo.set(self.item_data.get("unidade", ""))
            self.min_stock_entry.insert(0, str(self.item_data.get("estoque_minimo", "")))

    def save_item(self):
        # Para novo item, obter o produto_id do combobox
        if not self.item_data:
            product_name = self.product_combo.get()
            if product_name == "Selecione um produto...":
                messagebox.showerror("Erro", "Selecione um produto para o item de estoque.")
                return

            # Encontrar o produto_id correspondente ao nome selecionado
            found_product_id = None
            for p in self.products_for_new_item:
                if p["nome"] == product_name:
                    found_product_id = p["id"]
                    break

            if found_product_id is None:
                messagebox.showerror("Erro", "Produto selecionado inválido.")
                return
            self.product_id = found_product_id

        # Validar quantidade
        try:
            quantity = float(self.quantity_entry.get().strip().replace(",", "."))
            if quantity < 0:
                raise ValueError("Quantidade não pode ser negativa")
        except ValueError:
            messagebox.showerror("Erro", "Quantidade inválida. Use apenas números.")
            return

        # Validar estoque mínimo
        try:
            min_stock = float(self.min_stock_entry.get().strip().replace(",", "."))
            if min_stock < 0:
                raise ValueError("Estoque mínimo não pode ser negativo")
        except ValueError:
            messagebox.showerror("Erro", "Estoque mínimo inválido. Use apenas números.")
            return

        unit = self.unit_combo.get()
        if not unit:
            messagebox.showerror("Erro", "A unidade é obrigatória.")
            return

        # Coletar dados do formulário
        item_data = {
            "produto_id": self.product_id,
            "quantidade": quantity,
            "unidade": unit,
            "estoque_minimo": min_stock,
        }

        # Se for edição, manter o ID do estoque
        if self.item_data and "id" in self.item_data:
            item_data["id"] = self.item_data["id"]

        # Chamar a função de callback para salvar
        if self.on_save:
            self.on_save(item_data)

        # Fechar o formulário
        self.destroy()


class InventoryMovementForm(ctk.CTkToplevel):
    def __init__(self, master, inventory_items, movement_type="entrada", on_save=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.inventory_items = inventory_items  # Itens de estoque (do banco)
        self.movement_type = movement_type
        self.on_save = on_save
        self.selected_item_data = None  # Armazena o item de estoque selecionado no combobox

        # Configuração da janela
        self.title(f"Registrar {movement_type.capitalize()} de Estoque")
        self.geometry("500x650")  # Aumentado a altura de 500 para 650
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
            text=f"Registrar {movement_type.capitalize()} de Estoque",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Frame do formulário
        self.form_frame = ctk.CTkFrame(self)
        self.form_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.form_frame.grid_columnconfigure(1, weight=1)

        # Campos do formulário
        # Item
        self.item_label = ctk.CTkLabel(
            self.form_frame,
            text="Item:",
            anchor="w"
        )
        self.item_label.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="w")

        # Lista de nomes de itens para o combobox
        item_names = ["Selecione um item..."] + [item["nome"] for item in self.inventory_items]
        self.item_combo = ctk.CTkComboBox(
            self.form_frame,
            values=item_names,
            width=300,
            command=self.update_item_info
        )
        self.item_combo.grid(row=0, column=1, padx=(0, 20), pady=(20, 10), sticky="ew")
        self.item_combo.set("Selecione um item...")

        # Quantidade atual
        self.current_quantity_label = ctk.CTkLabel(
            self.form_frame,
            text="Quantidade Atual:",
            anchor="w"
        )
        self.current_quantity_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")

        self.current_quantity_value = ctk.CTkLabel(
            self.form_frame,
            text="0",
            anchor="w"
        )
        self.current_quantity_value.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="w")

        # Unidade
        self.unit_label = ctk.CTkLabel(
            self.form_frame,
            text="Unidade:",
            anchor="w"
        )
        self.unit_label.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="w")

        self.unit_value = ctk.CTkLabel(
            self.form_frame,
            text="",
            anchor="w"
        )
        self.unit_value.grid(row=2, column=1, padx=(0, 20), pady=10, sticky="w")

        # Quantidade da movimentação
        self.movement_quantity_label = ctk.CTkLabel(
            self.form_frame,
            text=f"Quantidade de {movement_type.capitalize()}:",
            anchor="w"
        )
        self.movement_quantity_label.grid(row=3, column=0, padx=(20, 10), pady=10, sticky="w")

        self.movement_quantity_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="0"
        )
        self.movement_quantity_entry.grid(row=3, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Data
        self.date_label = ctk.CTkLabel(
            self.form_frame,
            text="Data:",
            anchor="w"
        )
        self.date_label.grid(row=4, column=0, padx=(20, 10), pady=10, sticky="w")

        current_date = datetime.now().strftime("%d/%m/%Y")
        self.date_entry = ctk.CTkEntry(
            self.form_frame
        )
        self.date_entry.insert(0, current_date)
        self.date_entry.grid(row=4, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Motivo
        self.reason_label = ctk.CTkLabel(
            self.form_frame,
            text="Motivo:",
            anchor="w"
        )
        self.reason_label.grid(row=5, column=0, padx=(20, 10), pady=10, sticky="w")

        reason_values = []
        if movement_type == "entrada":
            reason_values = ["Compra", "Devolução", "Ajuste de Estoque", "Outro"]
        else:  # saída
            reason_values = ["Venda", "Consumo Interno", "Perda", "Ajuste de Estoque", "Outro"]

        self.reason_combo = ctk.CTkComboBox(
            self.form_frame,
            values=reason_values
        )
        self.reason_combo.grid(row=5, column=1, padx=(0, 20), pady=10, sticky="ew")
        self.reason_combo.set(reason_values[0])

        # Observações
        self.notes_label = ctk.CTkLabel(
            self.form_frame,
            text="Observações:",
            anchor="w"
        )
        self.notes_label.grid(row=6, column=0, padx=(20, 10), pady=10, sticky="nw")

        self.notes_entry = ctk.CTkTextbox(
            self.form_frame,
            height=80
        )
        self.notes_entry.grid(row=6, column=1, padx=(0, 20), pady=10, sticky="ew")

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
            text="Registrar",
            command=self.save_movement
        )
        self.save_button.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="w")

    def update_item_info(self, item_name):
        # Limpar o item de estoque selecionado
        self.selected_item_data = None

        if item_name == "Selecione um item...":
            self.current_quantity_value.configure(text="0")
            self.unit_value.configure(text="")
            return

        # Encontrar o item de estoque selecionado
        for item in self.inventory_items:
            if item.get("nome") == item_name:
                self.selected_item_data = item
                self.current_quantity_value.configure(text=str(item.get("quantidade", 0)))
                self.unit_value.configure(text=item.get("unidade", ""))
                break

    def save_movement(self):
        if self.selected_item_data is None:
            messagebox.showerror("Erro", "Selecione um item para registrar a movimentação.")
            return

        # Validar quantidade
        try:
            movement_quantity = float(self.movement_quantity_entry.get().strip().replace(",", "."))
            if movement_quantity <= 0:
                raise ValueError("Quantidade deve ser maior que zero")
        except ValueError:
            messagebox.showerror("Erro", "Quantidade inválida. Use apenas números positivos.")
            return

        # Validar data
        date_str = self.date_entry.get().strip()
        try:
            # Tenta converter para datetime para validar o formato
            datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
            return

        # Verificar se há quantidade suficiente para saída
        if self.movement_type == "saída":
            current_quantity = self.selected_item_data.get("quantidade", 0)
            if movement_quantity > current_quantity:
                messagebox.showerror("Erro",
                                     f"Quantidade insuficiente em estoque. Disponível: {current_quantity} {self.selected_item_data.get('unidade', '')}.")
                return

        # Coletar dados do movimento
        movement_data = {
            "item_estoque_id": self.selected_item_data.get("id"),  # ID do item na tabela 'estoque'
            "tipo": self.movement_type,
            "quantidade": movement_quantity,
            "data": date_str,
            "motivo": self.reason_combo.get(),
            "observacoes": self.notes_entry.get("0.0", "end").strip()
        }

        # Chamar a função de callback para salvar
        if self.on_save:
            self.on_save(movement_data)

        # Fechar o formulário
        self.destroy()


class InventoryModule(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.selected_item = None

        # Configuração do grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Faz a table_frame expandir verticalmente

        # Título
        self.title_label = ctk.CTkLabel(
            self,
            text="Controle de Estoque",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Frame de pesquisa
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Buscar item por nome..."
        )
        self.search_entry.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="ew")

        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Buscar",
            width=100,
            command=self.search_items
        )
        self.search_button.grid(row=0, column=1, padx=(0, 20), pady=20)

        # Frame de botões de ação
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")

        # Distribuir o espaço entre os botões
        self.action_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        self.add_button = ctk.CTkButton(
            self.action_frame,
            text="Novo Item",
            width=120,
            command=self.add_item
        )
        self.add_button.grid(row=0, column=0, padx=10, pady=20)

        self.edit_button = ctk.CTkButton(
            self.action_frame,
            text="Editar",
            width=120,
            state="disabled",
            command=self.edit_item
        )
        self.edit_button.grid(row=0, column=1, padx=10, pady=20)

        self.entry_button = ctk.CTkButton(
            self.action_frame,
            text="Entrada",
            width=120,
            fg_color="#28A745",
            hover_color="#218838",
            state="disabled",
            command=self.register_entry
        )
        self.entry_button.grid(row=0, column=2, padx=10, pady=20)

        self.exit_button = ctk.CTkButton(
            self.action_frame,
            text="Saída",
            width=120,
            fg_color="#DC3545",
            hover_color="#C82333",
            state="disabled",
            command=self.register_exit
        )
        self.exit_button.grid(row=0, column=3, padx=10, pady=20)

        self.history_button = ctk.CTkButton(
            self.action_frame,
            text="Histórico",
            width=120,
            state="disabled",
            command=self.view_history
        )
        self.history_button.grid(row=0, column=4, padx=10, pady=20)

        self.refresh_button = ctk.CTkButton(
            self.action_frame,
            text="Atualizar Lista",
            width=120,
            command=self.populate_table
        )
        self.refresh_button.grid(row=0, column=5, padx=10, pady=20)

        # Frame da tabela de itens
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Cabeçalho da tabela
        self.header_frame = ctk.CTkFrame(self.table_frame, fg_color=("#EEEEEE", "#333333"))
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.table_frame.grid_columnconfigure(0, weight=1)

        # Ajustados os cabeçalhos para refletir as colunas do DB de estoque + nome do produto
        headers = ["ID Estoque", "Produto", "Quantidade", "Unidade", "Estoque Mínimo", "Status"]
        widths = [80, 250, 100, 80, 120, 100]

        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                self.header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            )
            label.grid(row=0, column=i, padx=10, pady=10, sticky="w")
            self.header_frame.grid_columnconfigure(i, minsize=widths[i])

        # Conteúdo da tabela
        self.content_frame = ctk.CTkScrollableFrame(self.table_frame, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.table_frame.grid_rowconfigure(1, weight=1)

        # Status bar - Criado ANTES de populate_table() para evitar AttributeError
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Total de itens: 0"  # Valor inicial
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.low_stock_label = ctk.CTkLabel(
            self.status_frame,
            text="",  # Valor inicial vazio
            text_color="red"
        )
        self.low_stock_label.grid(row=0, column=1, padx=20, pady=10, sticky="e")

        # Agora populamos a tabela, após a criação dos labels de status
        self.populate_table()

    def populate_table(self, filtered_items=None):
        # Limpar a tabela atual
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Obter todos os itens do estoque do banco de dados
        self.inventory_items = listar_itens_estoque()

        # Usar a lista filtrada ou a lista completa
        items_to_display = filtered_items if filtered_items is not None else self.inventory_items

        # Atualizar o status
        self.status_label.configure(text=f"Total de itens: {len(items_to_display)}")

        # Verificar itens com estoque baixo e atualizar low_stock_label
        low_stock_count = sum(
            1 for item in self.inventory_items if item.get("quantidade", 0) <= item.get("estoque_minimo", 0))
        if low_stock_count > 0:
            self.low_stock_label.configure(text=f"Alerta: {low_stock_count} itens com estoque baixo!")
        else:
            self.low_stock_label.configure(text="")

            # Definir larguras das colunas
        widths = [80, 250, 100, 80, 120, 100]

        # Preencher com os dados
        for row_idx, item in enumerate(items_to_display):
            row_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            row_frame.grid(row=row_idx, column=0, sticky="ew", pady=5)

            # Determinar o status do estoque
            quantity = item.get("quantidade", 0)
            min_stock = item.get("estoque_minimo", 0)

            if quantity <= 0:
                status = "Esgotado"
                status_color = "red"
            elif quantity <= min_stock:
                status = "Baixo"
                status_color = "orange"
            else:
                status = "Normal"
                status_color = "green"

            # Adicionar os dados do item
            values = [
                item.get("id", ""),
                item.get("nome", ""),
                f"{item.get('quantidade', 0):.2f}".replace(".", ","),
                item.get("unidade", ""),
                f"{item.get('estoque_minimo', 0):.2f}".replace(".", ","),
                status
            ]

            for col_idx, value in enumerate(values):
                label = ctk.CTkLabel(
                    row_frame,
                    text=str(value),
                    text_color=status_color if col_idx == 5 else None
                )
                label.grid(row=0, column=col_idx, padx=10, pady=5, sticky="w")
                row_frame.grid_columnconfigure(col_idx, minsize=widths[col_idx])

            # Adicionar evento de clique para selecionar o item
            row_frame.bind("<Button-1>", lambda e, i=item: self.select_item(i))
            for widget in row_frame.winfo_children():
                widget.bind("<Button-1>", lambda e, i=item: self.select_item(i))

            # Adicionar linha separadora
            if row_idx < len(items_to_display) - 1:
                separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=("#DDDDDD", "#555555"))
                separator.grid(row=row_idx + 1, column=0, sticky="ew", padx=10)

                # Resetar a seleção após repopular a tabela
        self.selected_item = None
        self.edit_button.configure(state="disabled")
        self.entry_button.configure(state="disabled")
        self.exit_button.configure(state="disabled")
        self.history_button.configure(state="disabled")

    def select_item(self, item):
        # Desmarcar o item anterior
        if self.selected_item:
            for widget_row_frame in self.content_frame.winfo_children():
                if isinstance(widget_row_frame, ctk.CTkFrame) and widget_row_frame.winfo_children():
                    if widget_row_frame.winfo_children()[0].cget("text") == str(self.selected_item.get("id", "")):
                        widget_row_frame.configure(fg_color="transparent")
                        break

                        # Marcar o item selecionado
        for widget_row_frame in self.content_frame.winfo_children():
            if isinstance(widget_row_frame, ctk.CTkFrame) and widget_row_frame.winfo_children():
                if widget_row_frame.winfo_children()[0].cget("text") == str(item.get("id", "")):
                    widget_row_frame.configure(fg_color=("gray90", "gray20"))
                    break

                    # Atualizar o item selecionado
        self.selected_item = item

        # Habilitar os botões de ação
        self.edit_button.configure(state="normal")
        self.entry_button.configure(state="normal")
        self.exit_button.configure(state="normal")
        self.history_button.configure(state="normal")

    def search_items(self):
        search_term = self.search_entry.get().strip().lower()

        if not search_term:
            self.populate_table()
            return

        # Filtrar os itens da lista completa (self.inventory_items)
        filtered_items = [
            item for item in self.inventory_items
            if search_term in item.get("nome", "").lower()
        ]

        # Atualizar a tabela com os itens filtrados
        self.populate_table(filtered_items)

        # Resetar a seleção
        self.selected_item = None
        self.edit_button.configure(state="disabled")
        self.entry_button.configure(state="disabled")
        self.exit_button.configure(state="disabled")
        self.history_button.configure(state="disabled")

    def add_item(self):
        # Listar produtos que ainda não estão no estoque
        products_for_new_item = listar_produtos_para_cadastro_estoque()
        if not products_for_new_item:
            messagebox.showinfo("Informação", "Todos os produtos já possuem um registro no estoque.")
            return

        # Abrir o formulário de cadastro, passando os produtos disponíveis
        form = InventoryItemForm(self, products_for_new_item=products_for_new_item, on_save=self.save_new_item)
        form.focus()

    def save_new_item(self, item_data):
        # Salvar no banco de dados primeiro
        new_estoque_id = salvar_item_estoque_no_banco(item_data)
        if new_estoque_id is not None:
            # Se for bem-sucedido, registrar movimento de entrada inicial
            if item_data.get("quantidade", 0) > 0:
                movement_data = {
                    "item_estoque_id": new_estoque_id,
                    "tipo": "entrada",
                    "quantidade": item_data.get("quantidade"),
                    "data": datetime.now().strftime("%d/%m/%Y"),
                    "motivo": "Estoque Inicial",
                    "observacoes": "Cadastro inicial do item de estoque"
                }
                salvar_movimentacao_estoque_no_banco(movement_data)

            self.populate_table()
            messagebox.showinfo("Sucesso", "Item de estoque cadastrado com sucesso!")
        else:
            messagebox.showerror("Erro",
                                 "Falha ao cadastrar o item de estoque no banco de dados. Verifique o console para detalhes.")

    def edit_item(self):
        if not self.selected_item:
            return

        form = InventoryItemForm(self, products_for_new_item=[], item_data=self.selected_item,
                                 on_save=self.save_edited_item)
        form.focus()

    def save_edited_item(self, item_data):
        # Obter a quantidade antiga para comparar e registrar movimento
        old_item = next((item for item in self.inventory_items if item.get("id") == item_data.get("id")), None)
        old_quantity = old_item.get("quantidade", 0) if old_item else 0

        # Salvar no banco de dados
        updated_estoque_id = salvar_item_estoque_no_banco(item_data)
        if updated_estoque_id is not None:
            new_quantity = item_data.get("quantidade", 0)
            if new_quantity != old_quantity:
                # Registrar movimento de ajuste
                if new_quantity > old_quantity:
                    movement_type = "entrada"
                    quantity_diff = new_quantity - old_quantity
                else:
                    movement_type = "saída"
                    quantity_diff = old_quantity - new_quantity

                movement_data = {
                    "item_estoque_id": updated_estoque_id,
                    "tipo": movement_type,
                    "quantidade": quantity_diff,
                    "data": datetime.now().strftime("%d/%m/%Y"),
                    "motivo": "Ajuste de Estoque",
                    "observacoes": "Ajuste durante edição do item de estoque"
                }
                salvar_movimentacao_estoque_no_banco(movement_data)

            self.populate_table()
            messagebox.showinfo("Sucesso", "Item de estoque atualizado com sucesso!")
        else:
            messagebox.showerror("Erro",
                                 "Falha ao atualizar o item de estoque no banco de dados. Verifique o console para detalhes.")

        # Resetar a seleção
        self.selected_item = None
        self.edit_button.configure(state="disabled")
        self.entry_button.configure(state="disabled")
        self.exit_button.configure(state="disabled")
        self.history_button.configure(state="disabled")

    def register_entry(self):
        if not self.selected_item:
            return

        form = InventoryMovementForm(self, self.inventory_items, movement_type="entrada", on_save=self.save_movement)
        form.focus()

        form.item_combo.set(self.selected_item.get("nome", ""))
        form.update_item_info(self.selected_item.get("nome", ""))

    def register_exit(self):
        if not self.selected_item:
            return

        if self.selected_item.get("quantidade", 0) <= 0:
            messagebox.showerror("Erro", "Não há estoque disponível para este item.")
            return

        form = InventoryMovementForm(self, self.inventory_items, movement_type="saída", on_save=self.save_movement)
        form.focus()

        form.item_combo.set(self.selected_item.get("nome", ""))
        form.update_item_info(self.selected_item.get("nome", ""))

    def save_movement(self, movement_data):

        movement_id = salvar_movimentacao_estoque_no_banco(movement_data)
        if movement_id is not None:
            self.populate_table()
            tipo = "entrada" if movement_data.get("tipo") == "entrada" else "saída"
            messagebox.showinfo("Sucesso", f"{tipo.capitalize()} registrada com sucesso!")
        else:
            messagebox.showerror("Erro",
                                 "Falha ao registrar a movimentação no banco de dados. Verifique o console para detalhes.")

        # Resetar a seleção após salvar o movimento
        self.selected_item = None
        self.edit_button.configure(state="disabled")
        self.entry_button.configure(state="disabled")
        self.exit_button.configure(state="disabled")
        self.history_button.configure(state="disabled")

    def view_history(self):
        if not self.selected_item:
            return

        item_movements = listar_movimentacoes_por_item(self.selected_item.get("id"))

        if not item_movements:
            messagebox.showinfo("Histórico", "Não há movimentações registradas para este item.")
            return

        # Criar uma janela para mostrar o histórico
        history_window = ctk.CTkToplevel(self)
        history_window.title(f"Histórico de Movimentações - {self.selected_item.get('nome')}")
        history_window.geometry("800x500")
        history_window.resizable(True, True)
        history_window.grab_set()

        # Configuração do grid
        history_window.grid_columnconfigure(0, weight=1)
        history_window.grid_rowconfigure(1, weight=1)

        # Título
        title_label = ctk.CTkLabel(
            history_window,
            text=f"Histórico de Movimentações - {self.selected_item.get('nome')}",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=20)

        # Frame da tabela
        table_frame = ctk.CTkFrame(history_window)
        table_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Cabeçalho da tabela
        header_frame = ctk.CTkFrame(table_frame, fg_color=("#EEEEEE", "#333333"))
        header_frame.grid(row=0, column=0, sticky="ew")
        table_frame.grid_columnconfigure(0, weight=1)

        headers = ["ID Mov.", "Data", "Tipo", "Quantidade", "Motivo", "Observações"]
        widths = [80, 100, 100, 100, 150, 250]

        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            )
            label.grid(row=0, column=i, padx=10, pady=10, sticky="w")
            header_frame.grid_columnconfigure(i, minsize=widths[i])

        # Conteúdo da tabela
        content_frame = ctk.CTkScrollableFrame(table_frame, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(1, weight=1)

        # Preencher com os dados
        for row_idx, movement in enumerate(item_movements):
            row_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            row_frame.grid(row=row_idx * 2, column=0, sticky="ew", pady=5)

            # Determinar a cor do tipo
            tipo = movement.get("tipo", "")
            tipo_color = "green" if tipo == "entrada" else "red"

            # Adicionar os dados do movimento
            values = [
                movement.get("id", ""),
                movement.get("data", ""),
                tipo.capitalize(),
                f"{movement.get('quantidade', 0)} {self.selected_item.get('unidade', '')}",
                movement.get("motivo", ""),
                movement.get("observacoes", "")
            ]

            for col_idx, value in enumerate(values):
                label = ctk.CTkLabel(
                    row_frame,
                    text=str(value),
                    text_color=tipo_color if col_idx == 2 else None
                )
                label.grid(row=0, column=col_idx, padx=10, pady=5, sticky="w")
                row_frame.grid_columnconfigure(col_idx, minsize=widths[col_idx])

            # Adicionar linha separadora
            if row_idx < len(item_movements) - 1:
                separator = ctk.CTkFrame(content_frame, height=1, fg_color=("#DDDDDD", "#555555"))
                separator.grid(row=row_idx * 2 + 1, column=0, sticky="ew", padx=10)

                # Botão de fechar
        close_button = ctk.CTkButton(
            history_window,
            text="Fechar",
            command=history_window.destroy
        )
        close_button.grid(row=2, column=0, padx=20, pady=(0, 20))


# Para teste standalone
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Teste do Módulo de Estoque")
    app.geometry("1000x600")

    # Configuração do grid
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    # Instanciar o módulo
    inventory_module = InventoryModule(app)
    inventory_module.grid(row=0, column=0, sticky="nsew")

    app.mainloop()
