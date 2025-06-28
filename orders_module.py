import customtkinter as ctk
from tkinter import messagebox
import os
from datetime import datetime, timedelta
import json
import psycopg2
import tempfile  # Importar para criar arquivos temporários
import platform  # Importar para detectar o sistema operacional
from delivery_module import salvar_entrega_no_banco, listar_funcionarios_entregadores
from clients_module import ClientForm



# Importar funções do módulo de inventário
from inventory_module import salvar_movimentacao_estoque_no_banco, listar_itens_estoque

# Importar configurações do banco de dados de um arquivo externo
from db_config import DB_CONFIG

# TODO: Integrar com a função real de adicionar cliente do clients_module.py
# Simulação de uma função para adicionar cliente.
# No projeto real, você importaria e usaria uma função do clients_module.py
def adicionar_cliente_mock(nome, endereco, telefone, email):
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Inserir um cliente sem logradouro, localidade, cidade, etc., para simplificar a mock
        cur.execute("INSERT INTO clientes (nome, endereco, telefone, email) VALUES (%s, %s, %s, %s) RETURNING id",
                    (nome, endereco, telefone, email))
        new_id = cur.fetchone()[0]
        conn.commit()
        return {"id": new_id, "nome": nome, "endereco": endereco, "telefone": telefone, "email": email}
    except psycopg2.Error as e:
        print(f"Erro ao inserir cliente mock: {e}")
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível inserir o cliente: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def listar_pedidos():
    """
    Função para listar todos os pedidos do banco de dados,
    incluindo informações do cliente associado a cada pedido.
    """
    conn = None  # Inicializa a conexão como None
    cur = None  # Inicializa o cursor como None
    try:
        # Conecta ao banco de dados PostgreSQL usando as configurações fornecidas
        conn = psycopg2.connect(**DB_CONFIG)
        # Cria um objeto cursor, que permite a execução de comandos SQL
        cur = conn.cursor()

        # Executa uma consulta SQL para selecionar dados de pedidos e clientes
        # JOIN é usado para combinar as tabelas 'pedidos' e 'clientes'
        # ORDER BY p.data_pedido DESC garante que os pedidos mais recentes apareçam primeiro
        cur.execute("""
            SELECT 
                p.id, 
                p.cliente_id, 
                p.data_pedido, 
                p.tipo, 
                p.status, 
                p.subtotal, 
                p.desconto, 
                p.total, 
                p.forma_pagamento, 
                c.nome
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            ORDER BY p.data_pedido DESC
        """)
        # Recupera todas as linhas retornadas pela consulta
        pedidos = cur.fetchall()

        lista = []
        # Itera sobre cada linha de pedido recuperada
        for row in pedidos:
            pedido_dict = {
                "id": row[0],
                "cliente_id": row[1],
                # Formata a data e hora do pedido para exibição amigável
                "data_pedido": row[2],  # Manter como objeto datetime para facilitar a comparação
                "data_pedido_str": row[2].strftime("%d/%m/%Y %H:%M"),  # String formatada para exibição
                "tipo": row[3],
                "status": row[4],
                # Converte os valores de subtotal, desconto e total para float
                "subtotal": float(row[5]),
                "desconto": float(row[6]),
                "total": float(row[7]),
                "forma_pagamento": row[8],
                "cliente_nome": row[9],
                "itens": []  # Inicializa uma lista vazia para itens do pedido, se aplicável
            }
            lista.append(pedido_dict)

        # Agora, buscar os itens para cada pedido
        for pedido in lista:
            cur.execute("""
                SELECT
                    ip.produto_id,
                    pr.nome as produto_nome,
                    ip.quantidade,
                    ip.preco_unitario,
                    ip.subtotal
                FROM itens_pedidos ip
                JOIN produtos pr ON ip.produto_id = pr.id
                WHERE ip.pedido_id = %s
            """, (pedido["id"],))
            itens_pedido = cur.fetchall()

            # Concatena os itens em uma string para exibição na grid
            itens_concatenados = []
            for item in itens_pedido:
                item_dict = {
                    "produto_id": item[0],
                    "produto_nome": item[1],
                    "quantidade": item[2],
                    "preco_unitario": float(item[3]),
                    "subtotal": float(item[4])
                }
                pedido["itens"].append(item_dict)  # Adiciona o dicionário completo para visualização de detalhes
                itens_concatenados.append(f"{item[1]} (x{item[2]})")  # Para exibição na grid

            pedido["itens_str"] = ", ".join(itens_concatenados)  # Armazena a string concatenada

    except psycopg2.Error as e:
        # Captura e imprime quaisquer erros que ocorram durante a operação do banco de dados
        print(f"Erro ao listar pedidos: {e}")
        return []  # Retorna uma lista vazia em caso de erro
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return lista


def listar_clientes():
    """
    Função para listar todos os clientes do banco de dados.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM clientes ORDER BY nome ASC")
        clientes = cur.fetchall()
        lista = []
        for row in clientes:
            lista.append({
                "id": row[0],
                "nome": row[1]
            })
        return lista
    except psycopg2.Error as e:
        print(f"Erro ao listar clientes: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def listar_produtos():
    """
    Função para listar todos os produtos ativos do banco de dados.
    A tabela de produtos agora tem apenas: id, nome, descricao, categoria, ingredientes, ativo.
    O preço será inserido manualmente na tela do pedido.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Removendo 'preco' da seleção, pois não existe na tabela produtos
        cur.execute(
            "SELECT id, nome, descricao, categoria, ingredientes, ativo FROM produtos WHERE ativo = TRUE ORDER BY nome ASC")
        produtos = cur.fetchall()
        lista = []
        for row in produtos:
            lista.append({
                "id": row[0],
                "nome": row[1],
                "descricao": row[2],
                "categoria": row[3],
                "ingredientes": row[4],
                "ativo": row[5]
                # 'preco' não é mais extraído daqui
            })
        return lista
    except psycopg2.Error as e:
        print(f"Erro ao listar produtos: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def salvar_pedido_no_banco(order_data):
    """
    Salva ou atualiza um pedido e seus itens no banco de dados.
    Se order_data contém 'id', tenta atualizar; caso contrário, insere um novo.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        pedido_id = order_data.get("id")
        itens = order_data.get("itens", [])

        # Converter a string de data_pedido para objeto datetime antes de inserir no banco
        # A data pode vir como DD/MM/AAAA HH:MM ou apenas DD/MM/AAAA
        data_pedido_str = order_data["data_pedido"]
        if " " in data_pedido_str and ":" in data_pedido_str:
            data_pedido_dt = datetime.strptime(data_pedido_str, "%d/%m/%Y %H:%M")
        else:
            data_pedido_dt = datetime.strptime(data_pedido_str, "%d/%m/%Y").replace(
                hour=datetime.now().hour, minute=datetime.now().minute
            )

        if pedido_id:
            # Atualizar pedido existente
            cur.execute("""
                UPDATE pedidos SET
                    cliente_id = %s,
                    data_pedido = %s,
                    tipo = %s,
                    status = %s,
                    subtotal = %s,
                    desconto = %s,
                    total = %s,
                    forma_pagamento = %s
                WHERE id = %s
            """, (
                order_data["cliente_id"],
                data_pedido_dt,  # Passando objeto datetime
                order_data["tipo"],
                order_data["status"],
                order_data["subtotal"],
                order_data["desconto"],
                order_data["total"],
                order_data["forma_pagamento"],
                pedido_id
            ))
            # Deletar itens antigos e inserir novos para simplificar a atualização
            cur.execute("DELETE FROM itens_pedidos WHERE pedido_id = %s", (pedido_id,))
        else:
            # Inserir novo pedido
            cur.execute("""
                INSERT INTO pedidos (cliente_id, data_pedido, tipo, status, subtotal, desconto, total, forma_pagamento)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                order_data["cliente_id"],
                data_pedido_dt,  # Passando objeto datetime
                order_data["tipo"],
                order_data["status"],
                order_data["subtotal"],
                order_data["desconto"],
                order_data["total"],
                order_data["forma_pagamento"]
            ))
            pedido_id = cur.fetchone()[0]  # Obter o ID do novo pedido

        # Inserir itens do pedido
        for item in itens:
            cur.execute("""
                INSERT INTO itens_pedidos (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                pedido_id,
                item["produto_id"],
                item["quantidade"],
                item["preco_unitario"],
                item["subtotal"]
            ))

        conn.commit()

        # INÍCIO: Integração com Delivery
        if order_data["status"] == "Pronto" and order_data["tipo"] == "Delivery":
            try:
                entregadores = listar_funcionarios_entregadores()
                if entregadores:
                    funcionario_id = entregadores[0]["id"]
                    data_saida_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                    entrega_data = {
                        "pedido_id": pedido_id,
                        "funcionario_id": funcionario_id,
                        "status": "Pendente",
                        "data_saida": data_saida_str,
                        "data_entrega": None,
                        "observacoes": f"Entrega criada automaticamente para o pedido {pedido_id}."
                    }
                    salvar_entrega_no_banco(entrega_data)
            except Exception as e:
                print(f"Erro ao criar entrega automática: {e}")
        # FIM: Integração com Delivery

        return pedido_id  # Retorna o ID do pedido salvo/atualizado
    except psycopg2.Error as e:
        print(f"Erro ao salvar pedido no banco de dados: {e}")
        # Imprime o erro detalhado do psycopg2
        print(f"Detalhes do erro do PostgreSQL: {e.diag.message_detail if e.diag else 'N/A'}")
        print(f"Código SQLSTATE: {e.pgcode if e.pgcode else 'N/A'}")
        if conn:
            conn.rollback()  # Reverte a transação em caso de erro
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# --- Função de Macro de Data ---
def _auto_slash_date_entry(event):
    entry_widget = event.widget
    current_text = entry_widget.get()
    new_text = ""

    # Ignora Backspace
    if event.keysym == "BackSpace":
        return

    # Remove caracteres não numéricos, exceto a primeira barra em cada par
    processed_text = ""
    for char in current_text:
        if char.isdigit():
            processed_text += char
        elif char == '/':
            # Mantém apenas as barras nas posições esperadas
            if len(processed_text) == 2 or len(processed_text) == 5:
                processed_text += char

    formatted_text = ""
    for i, char in enumerate(processed_text):
        formatted_text += char
        # Adiciona barra se atinge o ponto certo (DD/MM) e a barra não está lá
        if (i == 1 or i == 3) and len(formatted_text) == i + 1:
            if len(processed_text) > i + 1 and processed_text[i + 1].isdigit():
                formatted_text += '/'

    # Limita o tamanho a DD/MM/YYYY (10 caracteres) para evitar problemas de formatação
    if len(formatted_text) > 10:
        formatted_text = formatted_text[:10]

    if formatted_text != current_text:
        entry_widget.delete(0, ctk.END)
        entry_widget.insert(0, formatted_text)
        # Posiciona o cursor no final
        entry_widget.icursor(ctk.END)

class NewClientForm(ctk.CTkToplevel):
    def __init__(self, master, on_save_callback, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.on_save_callback = on_save_callback

        self.title("Novo Cliente")
        self.geometry("400x350")
        self.resizable(False, False)
        self.grab_set() # Torna a janela modal
        self.transient(master) # Define a janela pai

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Nome:").grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.nome_entry = ctk.CTkEntry(self)
        self.nome_entry.grid(row=0, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Endereço:").grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.endereco_entry = ctk.CTkEntry(self)
        self.endereco_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Telefone:").grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.telefone_entry = ctk.CTkEntry(self)
        self.telefone_entry.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Email:").grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.email_entry = ctk.CTkEntry(self)
        self.email_entry.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

        save_button = ctk.CTkButton(self, text="Salvar", command=self.save_client)
        save_button.grid(row=4, column=0, columnspan=2, padx=20, pady=20)

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

        if not nome or not telefone:
            messagebox.showerror("Erro", "Nome e Telefone são campos obrigatórios.")
            return

        new_client_data = adicionar_cliente_mock(nome, telefone, email,numero_endereco, complemento_endereco, logradouro_id, localidade_id,cidade_id)
        if new_client_data:
            messagebox.showinfo("Sucesso", "Cliente adicionado com sucesso!")
            self.on_save_callback(new_client_data)
            self.destroy()


class OrderForm(ctk.CTkToplevel):
    def __init__(self, master, clients, products, order_data=None, on_save=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.clients = clients
        self.products = products
        self.order_data = order_data
        self.on_save = on_save
        # Se for edição, inicializar order_items com os itens existentes
        if self.order_data and "itens" in self.order_data:
            self.order_items = list(self.order_data["itens"])
        else:
            self.order_items = []

        # Configuração da janela
        self.title("Novo Pedido" if not order_data else "Editar Pedido")
        self.geometry("900x750")  # Aumentado a altura para 750
        self.minsize(900, 750)  # Definido tamanho mínimo para evitar o problema
        self.resizable(True, True)

        # Configuração do grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Título
        self.grid_rowconfigure(1, weight=0)  # info_frame
        self.grid_rowconfigure(2, weight=0)  # add_product_frame
        self.grid_rowconfigure(3, weight=1)  # items_frame (dará espaço vertical extra)
        self.grid_rowconfigure(4, weight=0)  # totals_frame
        self.grid_rowconfigure(5, weight=0)  # button_frame

        # Título
        self.title_label = ctk.CTkLabel(
            self,
            text="Novo Pedido" if not order_data else "Editar Pedido",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Frame de informações do pedido
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.info_frame.grid_columnconfigure(1, weight=1)
        self.info_frame.grid_columnconfigure(3, weight=1)
        self.info_frame.grid_columnconfigure(4, weight=0) # Coluna para o botão "+" do cliente

        # Cliente
        self.client_label = ctk.CTkLabel(
            self.info_frame,
            text="Cliente:",
            anchor="w"
        )
        self.client_label.grid(row=0, column=0, padx=(20, 5), pady=(20, 10), sticky="w") # Ajustado padx

        # Lista de clientes para o combobox
        self.client_names = ["Selecione um cliente..."] + [client["nome"] for client in self.clients]

        self.client_combo = ctk.CTkComboBox(
            self.info_frame,
            values=self.client_names,
            width=200
        )
        self.client_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Ativa o filtro/autocomplete
        self.client_combo.bind("<KeyRelease>", self.filter_clients)

        self.client_combo.grid(row=0, column=1, padx=(0, 5), pady=(20, 10), sticky="ew") # Ajustado padx
        self.client_combo.set("Selecione um cliente...")

        # Botão para adicionar novo cliente
        self.add_client_button = ctk.CTkButton(
            self.info_frame,
            text="+",
            width=30, # Largura menor para o botão
            command=self.open_new_client_form
        )
        self.add_client_button.grid(row=0, column=2, padx=(0, 20), pady=(20, 10), sticky="w") # Nova coluna para o botão


        # Tipo de pedido
        self.order_type_label = ctk.CTkLabel(
            self.info_frame,
            text="Tipo:",
            anchor="w"
        )
        self.order_type_label.grid(row=0, column=3, padx=(20, 10), pady=(20, 10), sticky="w") # Coluna ajustada

        self.order_type_combo = ctk.CTkComboBox(
            self.info_frame,
            values=["Balcão", "Delivery"],
            width=150
        )
        self.order_type_combo.grid(row=0, column=4, padx=(0, 20), pady=(20, 10), sticky="w") # Coluna ajustada
        self.order_type_combo.set("Balcão")

        # Data (apenas campo de texto)
        self.date_label = ctk.CTkLabel(
            self.info_frame,
            text="Data:",
            anchor="w"
        )
        self.date_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")

        current_date_time = datetime.now().strftime("%d/%m/%Y %H:%M")  # Formato completo para edicao de pedidos
        self.date_entry = ctk.CTkEntry(
            self.info_frame,
            width=250
        )
        self.date_entry.insert(0, current_date_time)
        self.date_entry.configure(state="normal")  # Permitir edicao
        self.date_entry.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="w", columnspan=2) # Aumentado columnspan


        # Status
        self.status_label = ctk.CTkLabel(
            self.info_frame,
            text="Status:",
            anchor="w"
        )
        self.status_label.grid(row=1, column=3, padx=(20, 10), pady=10, sticky="w") # Coluna ajustada

        self.status_combo = ctk.CTkComboBox(
            self.info_frame,
            values=["Pendente", "Em preparo", "Pronto", "Em entrega", "Entregue", "Cancelado"],
            width=150
        )
        self.status_combo.grid(row=1, column=4, padx=(0, 20), pady=10, sticky="w") # Coluna ajustada
        self.status_combo.set("Pendente")

        # Frame de adição de produtos
        self.add_product_frame = ctk.CTkFrame(self)
        self.add_product_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.add_product_frame.grid_columnconfigure(1, weight=1)

        # Produto
        self.product_label = ctk.CTkLabel(
            self.add_product_frame,
            text="Produto:",
            anchor="w"
        )
        self.product_label.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="w")

        # Lista de produtos para o combobox
        product_names = ["Selecione um produto..."] + [product["nome"] for product in self.products if
                                                       product.get("ativo", True)]
        self.product_combo = ctk.CTkComboBox(
            self.add_product_frame,
            values=product_names,
            width=300,
            command=self.update_product_price
        )
        self.product_combo.grid(row=0, column=1, padx=(0, 20), pady=(20, 10), sticky="ew")
        self.product_combo.set("Selecione um produto...")

        # Quantidade
        self.quantity_label = ctk.CTkLabel(
            self.add_product_frame,
            text="Quantidade:",
            anchor="w"
        )
        self.quantity_label.grid(row=0, column=2, padx=(20, 10), pady=(20, 10), sticky="w")

        self.quantity_entry = ctk.CTkEntry(
            self.add_product_frame,
            width=80
        )
        self.quantity_entry.insert(0, "1")
        self.quantity_entry.grid(row=0, column=3, padx=(0, 20), pady=(20, 10), sticky="w")

        # Preço unitário
        self.price_label = ctk.CTkLabel(
            self.add_product_frame,
            text="Preço unitário:",
            anchor="w"
        )
        self.price_label.grid(row=1, column=0, padx=(20, 10), pady=(0, 20), sticky="w")

        self.price_entry = ctk.CTkEntry(
            self.add_product_frame,
            width=150
        )
        self.price_entry.insert(0, "0,00")
        self.price_entry.grid(row=1, column=1, padx=(0, 20), pady=(0, 20), sticky="w")

        # Botão de adicionar produto
        self.add_button = ctk.CTkButton(
            self.add_product_frame,
            text="Adicionar Item",
            width=150,
            command=self.add_item
        )
        self.add_button.grid(row=1, column=3, padx=(0, 20), pady=(0, 20), sticky="e")

        # Frame da tabela de itens
        self.items_frame = ctk.CTkFrame(self)
        self.items_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.items_frame.grid_rowconfigure(2, weight=1)  # Faz o content_frame expandir

        # Título da tabela
        self.items_title = ctk.CTkLabel(
            self.items_frame,
            text="Itens do Pedido",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.items_title.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Cabeçalho da tabela
        self.header_frame = ctk.CTkFrame(self.items_frame, fg_color=("#EEEEEE", "#333333"))
        self.header_frame.grid(row=1, column=0, sticky="ew")
        self.items_frame.grid_columnconfigure(0, weight=1)

        headers = ["Produto", "Quantidade", "Preço Unitário", "Subtotal", "Ações"]
        widths = [300, 100, 150, 150, 100]

        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                self.header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            )
            label.grid(row=0, column=i, padx=10, pady=10, sticky="w")
            self.header_frame.grid_columnconfigure(i, minsize=widths[i])

        # Conteúdo da tabela
        self.content_frame = ctk.CTkScrollableFrame(self.items_frame, fg_color="transparent",
                                                    height=200)  # Manter height para o scroll
        self.content_frame.grid(row=2, column=0, sticky="nsew")

        # Frame de totais
        self.totals_frame = ctk.CTkFrame(self)
        self.totals_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.totals_frame.grid_columnconfigure(1, weight=1)
        self.totals_frame.grid_columnconfigure(3, weight=1)

        # Subtotal
        self.subtotal_label = ctk.CTkLabel(
            self.totals_frame,
            text="Subtotal:",
            anchor="w"
        )
        self.subtotal_label.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="w")

        self.subtotal_value = ctk.CTkLabel(
            self.totals_frame,
            text="R$ 0,00",
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        self.subtotal_value.grid(row=0, column=1, padx=(0, 20), pady=(20, 10), sticky="w")

        # Desconto
        self.discount_label = ctk.CTkLabel(
            self.totals_frame,
            text="Desconto (R$):",
            anchor="w"
        )
        self.discount_label.grid(row=0, column=2, padx=(20, 10), pady=(20, 10), sticky="w")

        self.discount_entry = ctk.CTkEntry(
            self.totals_frame,
            width=100
        )
        self.discount_entry.insert(0, "0,00")
        self.discount_entry.grid(row=0, column=3, padx=(0, 20), pady=(20, 10), sticky="w")

        # Botão de aplicar desconto
        self.apply_discount_button = ctk.CTkButton(
            self.totals_frame,
            text="Aplicar",
            width=100,
            command=self.update_total
        )
        self.apply_discount_button.grid(row=0, column=4, padx=(0, 20), pady=(20, 10), sticky="w")

        # Total
        self.total_label = ctk.CTkLabel(
            self.totals_frame,
            text="Total:",
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        self.total_label.grid(row=1, column=0, padx=(20, 10), pady=(10, 20), sticky="w")

        self.total_value = ctk.CTkLabel(
            self.totals_frame,
            text="R$ 0,00",
            anchor="w",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.total_value.grid(row=1, column=1, padx=(0, 20), pady=(10, 20), sticky="w")

        # Forma de pagamento
        self.payment_label = ctk.CTkLabel(
            self.totals_frame,
            text="Pagamento:",
            anchor="w"
        )
        self.payment_label.grid(row=1, column=2, padx=(20, 10), pady=(10, 20), sticky="w")

        self.payment_combo = ctk.CTkComboBox(
            self.totals_frame,
            values=["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "Pix"],
            width=150
        )
        self.payment_combo.grid(row=1, column=3, padx=(0, 20), pady=(10, 20), sticky="w")
        self.payment_combo.set("Dinheiro")

        # Botões de ação
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")
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
            text="Finalizar Pedido",
            command=self.save_order
        )
        self.save_button.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="w")

        # Preencher os campos se for edição
        if self.order_data:
            # Selecionar o cliente
            for client in self.clients:
                if client.get("id") == self.order_data.get("cliente_id"):
                    self.client_combo.set(client.get("nome", ""))
                    break
            # Preencher os outros campos
            self.order_type_combo.set(self.order_data.get("tipo", "Balcão"))
            self.status_combo.set(self.order_data.get("status", "Pendente"))

            # Preencher a data
            if "data_pedido" in self.order_data and self.order_data["data_pedido"]:
                # Assume que data_pedido já é um objeto datetime
                date_to_display = self.order_data["data_pedido"].strftime("%d/%m/%Y %H:%M")
                self.date_entry.delete(0, ctk.END)
                self.date_entry.insert(0, date_to_display)
            else:
                self.date_entry.delete(0, ctk.END)
                self.date_entry.insert(0, datetime.now().strftime("%d/%m/%Y %H:%M"))

            # Preencher os itens
            self.populate_items_table()

            # Preencher os totais
            discount = self.order_data.get("desconto", 0)
            self.discount_entry.delete(0, "end")
            self.discount_entry.insert(0, f"{discount:.2f}".replace(".", ","))

            self.payment_combo.set(self.order_data.get("forma_pagamento", "Dinheiro"))

            # Atualizar os totais
            self.update_total()

    def get_all_client_names(self):
        # Retorna apenas os nomes dos clientes para o combo
        return [cliente["nome"] for cliente in self.clients]

    def filter_clients(self, event):
        typed_text = self.client_combo.get().lower()
        filtered_names = [cliente["nome"] for cliente in self.clients if typed_text in cliente["nome"].lower()]

        # Se não houver resultados, exibe a lista completa
        if not filtered_names:
            filtered_names = self.get_all_client_names()

        # Atualiza os valores da ComboBox
        self.client_combo.configure(values=filtered_names)

        # Mantém o texto digitado
        self.client_combo.set(typed_text)

    def open_new_client_form(self):
        client_form = ClientForm(self, on_save=self.on_new_client_saved)

    def on_new_client_saved(self, new_client_data):
        from clients_module import obter_clientes
        self.clients = obter_clientes()  # Recarrega a lista de clientes do banco

        # Atualiza a ComboBox ou Entry (se for autocomplete)
        all_client_names = [client["nome"] for client in self.clients]
        self.client_combo.configure(values=all_client_names)
        self.client_combo.set(new_client_data["nome"])  # Já seleciona o cliente recém-cadastrado

    def update_product_price(self, product_name):
        # Como a tabela de produtos não tem preço, o preço unitário será sempre "0,00" ou um valor a ser digitado.
        # A combobox já trata o caso de "Selecione um produto...", então apenas garantimos que o campo esteja limpo.
        self.price_entry.delete(0, "end")
        self.price_entry.insert(0, "0,00")

    def add_item(self):
        product_name = self.product_combo.get()

        if product_name == "Selecione um produto...":
            messagebox.showerror("Erro", "Selecione um produto.")
            return

        # Validar quantidade
        try:
            quantity = int(self.quantity_entry.get())
            if quantity <= 0:
                raise ValueError("Quantidade deve ser maior que zero")
        except ValueError:
            messagebox.showerror("Erro", "Quantidade inválida. Use apenas números inteiros positivos.")
            return

        # Validar preço
        try:
            price_str = self.price_entry.get().strip().replace(",", ".")
            price = float(price_str)
            if price < 0:
                raise ValueError("Preço não pode ser negativo")
        except ValueError:
            messagebox.showerror("Erro", "Preço inválido. Use apenas números.")
            return

        # Encontrar o produto selecionado
        product_id = None
        for product in self.products:
            if product.get("nome") == product_name:
                product_id = product.get("id")
                break

        if product_id is None:
            messagebox.showerror("Erro", "Produto não encontrado.")
            return

        # Calcular subtotal
        subtotal = quantity * price

        # Adicionar o item à lista
        item = {
            "produto_id": product_id,
            "produto_nome": product_name,
            "quantidade": quantity,
            "preco_unitario": price,
            "subtotal": subtotal
        }

        self.order_items.append(item)

        # Atualizar a tabela
        self.populate_items_table()

        # Atualizar os totais
        self.update_total()

        # Limpar os campos
        self.product_combo.set("Selecione um produto...")
        self.quantity_entry.delete(0, "end")
        self.quantity_entry.insert(0, "1")
        self.price_entry.delete(0, "end")
        self.price_entry.insert(0, "0,00")

    def populate_items_table(self):
        # Limpar a tabela atual
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Definir larguras das colunas
        widths = [300, 100, 150, 150, 100]

        # Preencher com os dados
        for row_idx, item in enumerate(self.order_items):
            # Usar 2 * row_idx para o item e 2 * row_idx + 1 para o separador
            current_row = row_idx * 2

            row_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            row_frame.grid(row=current_row, column=0, sticky="ew", pady=5)

            # Adicionar os dados do item
            values = [
                item.get("produto_nome", ""),
                item.get("quantidade", ""),
                f"R$ {item.get('preco_unitario', 0):.2f}".replace(".", ","),
                f"R$ {item.get('subtotal', 0):.2f}".replace(".", ",")
            ]

            for col_idx, value in enumerate(values):
                label = ctk.CTkLabel(
                    row_frame,
                    text=str(value)
                )
                label.grid(row=0, column=col_idx, padx=10, pady=5, sticky="w")
                row_frame.grid_columnconfigure(col_idx, minsize=widths[col_idx])

            # Botão de remover
            remove_button = ctk.CTkButton(
                row_frame,
                text="Remover",
                width=80,
                height=25,
                fg_color="#D22B2B",
                hover_color="#AA0000",
                command=lambda idx=row_idx: self.remove_item(idx)
            )
            remove_button.grid(row=0, column=4, padx=10, pady=5)

            # Adicionar linha separadora APENAS se não for o último item
            if row_idx < len(self.order_items) - 1:
                separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=("#DDDDDD", "#555555"))
                separator.grid(row=current_row + 1, column=0, sticky="ew", padx=10)

    def remove_item(self, index):
        # Remover o item da lista
        if 0 <= index < len(self.order_items):
            del self.order_items[index]

            # Atualizar a tabela
            self.populate_items_table()

            # Atualizar os totais
            self.update_total()

    def update_total(self):
        # Calcular subtotal
        subtotal = sum(item.get("subtotal", 0) for item in self.order_items)

        # Obter desconto
        try:
            discount_str = self.discount_entry.get().strip().replace(",", ".")
            discount = float(discount_str) if discount_str else 0
        except ValueError:
            discount = 0
            self.discount_entry.delete(0, "end")
            self.discount_entry.insert(0, "0,00")

        # Calcular total
        total = subtotal - discount
        if total < 0:
            total = 0
            discount = subtotal
            self.discount_entry.delete(0, "end")
            self.discount_entry.insert(0, f"{subtotal:.2f}".replace(".", ","))

        # Atualizar os labels
        self.subtotal_value.configure(text=f"R$ {subtotal:.2f}".replace(".", ","))
        self.total_value.configure(text=f"R$ {total:.2f}".replace(".", ","))

    def save_order(self):
        # Validar cliente
        client_name = self.client_combo.get()
        if client_name == "Selecione um cliente...":
            messagebox.showerror("Erro", "Selecione um cliente.")
            return

        # Validar itens
        if not self.order_items:
            messagebox.showerror("Erro", "Adicione pelo menos um item ao pedido.")
            return

        # Encontrar o cliente selecionado
        client_id = None
        for client in self.clients:
            if client.get("nome") == client_name:
                client_id = client.get("id")
                break

        if client_id is None:
            messagebox.showerror("Erro", "Cliente não encontrado.")
            return

        # Obter os valores
        order_type = self.order_type_combo.get()
        status = self.status_combo.get()

        # Obter a data do campo de entrada
        data_pedido_str = self.date_entry.get().strip()
        if not data_pedido_str:
            messagebox.showerror("Erro", "A data do pedido não pode estar vazia.")
            return

        # Validar formato da data
        try:
            # Tenta com HH:MM, se falhar tenta sem HH:MM (adiciona hora atual)
            if " " in data_pedido_str and ":" in data_pedido_str:
                datetime.strptime(data_pedido_str, "%d/%m/%Y %H:%M")
            else:
                datetime.strptime(data_pedido_str, "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("Erro", "Formato de data inválido. Use DD/MM/AAAA ou DD/MM/AAAA HH:MM.")
            return

        # Obter desconto
        try:
            discount_str = self.discount_entry.get().strip().replace(",", ".")
            discount = float(discount_str) if discount_str else 0
        except ValueError:
            discount = 0

        # Calcular total
        subtotal = sum(item.get("subtotal", 0) for item in self.order_items)
        total = subtotal - discount
        if total < 0:
            total = 0

        payment_method = self.payment_combo.get()

        # Criar o objeto do pedido
        order_data = {
            "cliente_id": client_id,
            "data_pedido": data_pedido_str,  # Usar a string do campo de entrada
            "tipo": order_type,
            "status": status,
            "subtotal": subtotal,
            "desconto": discount,
            "total": total,
            "forma_pagamento": payment_method,
            "itens": self.order_items
        }

        # Se for edição, manter o ID
        if self.order_data and "id" in self.order_data:
            order_data["id"] = self.order_data["id"]

        # Chamar a função de callback para salvar
        if self.on_save:
            self.on_save(order_data)

        # Fechar o formulário
        self.destroy()


class OrdersModule(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        # Adjusting grid rows to accommodate new filters and maintain layout
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=0)  # Filter frame
        self.grid_rowconfigure(2, weight=1)  # list_frame (ScrollableFrame for orders)
        self.grid_rowconfigure(3, weight=0)  # button_frame
        self.grid_rowconfigure(4, weight=0)  # status_frame

        self.title_label = ctk.CTkLabel(self, text="Pedidos", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Filter frame
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        # Removed adjustment for calendar buttons, as they will no longer be there.
        # Adjust grid_columnconfigure to accommodate date fields
        self.filter_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # Client Filter
        self.client_filter_label = ctk.CTkLabel(self.filter_frame, text="Filtrar por Cliente:")
        self.client_filter_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        self.client_filter_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="Nome do cliente...", width=200)
        self.client_filter_entry.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ew")
        self.client_filter_entry.bind("<KeyRelease>", self.apply_filters)  # Filters on typing

        # Status Filter
        self.status_filter_label = ctk.CTkLabel(self.filter_frame, text="Filtrar por Status:")
        self.status_filter_label.grid(row=0, column=2, padx=(10, 5), pady=10, sticky="w")

        # Get all possible statuses (including "All")
        all_statuses = ["Todos", "Pendente", "Em preparo", "Pronto", "Em entrega", "Entregue", "Cancelado"]
        self.status_filter_combo = ctk.CTkComboBox(self.filter_frame, values=all_statuses, width=150,
                                                   command=self.apply_filters)
        self.status_filter_combo.grid(row=0, column=3, padx=(0, 10), pady=10, sticky="ew")
        self.status_filter_combo.set("Todos")  # Initial value

        # "Today's Orders" Checkbox
        self.today_orders_checkbox = ctk.CTkCheckBox(self.filter_frame, text="Pedidos do Dia",
                                                     command=self.toggle_date_filters)
        self.today_orders_checkbox.grid(row=0, column=4, padx=(10, 5), pady=10, sticky="w")
        self.today_orders_checkbox.select()  # Mark by default

        # Period Filter - Start Date (text field only with macro)
        self.start_date_label = ctk.CTkLabel(self.filter_frame, text="De:")
        self.start_date_label.grid(row=1, column=0, padx=(10, 5), pady=10, sticky="w")
        self.start_date_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="DD/MM/AAAA", width=120)
        self.start_date_entry.grid(row=1, column=1, padx=(0, 10), pady=10, sticky="ew")
        self.start_date_entry.bind("<KeyRelease>", _auto_slash_date_entry)  # Adds date macro

        # Period Filter - End Date (text field only with macro)
        self.end_date_label = ctk.CTkLabel(self.filter_frame, text="Até:")
        self.end_date_label.grid(row=1, column=2, padx=(10, 5), pady=10, sticky="w")
        self.end_date_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="DD/MM/AAAA", width=120)
        self.end_date_entry.grid(row=1, column=3, padx=(0, 10), pady=10, sticky="ew")
        self.end_date_entry.bind("<KeyRelease>", _auto_slash_date_entry)  # Adds date macro

        # Apply Filters Button (general)
        self.apply_filters_button = ctk.CTkButton(self.filter_frame, text="Aplicar Filtros", command=self.apply_filters)
        self.apply_filters_button.grid(row=1, column=4, padx=(10, 10), pady=10, sticky="ew")

        # Clear Filters Button
        self.clear_filters_button = ctk.CTkButton(self.filter_frame, text="Limpar Filtros", command=self.clear_filters)
        self.clear_filters_button.grid(row=0, column=5, padx=(0, 10), pady=10,
                                       sticky="e")
        self.filter_frame.grid_columnconfigure(5, weight=1)  # Extra column to push clear button

        # List frame
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)  # Makes the list items expand horizontally

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1), weight=1)
        self.button_frame.grid_columnconfigure((2, 3, 4), weight=1)

        self.add_button = ctk.CTkButton(self.button_frame, text="Novo Pedido", command=self.novo_pedido)
        self.add_button.grid(row=0, column=0, padx=10, pady=10)

        self.refresh_button = ctk.CTkButton(self.button_frame, text="Atualizar", command=self.listar_pedidos)
        self.refresh_button.grid(row=0, column=1, padx=10, pady=10)

        # Initializing action buttons to avoid AttributeError
        self.view_button = ctk.CTkButton(self.button_frame, text="Ver Detalhes", command=self._show_order_details_modal,
                                         state="disabled")
        self.edit_button = ctk.CTkButton(self.button_frame, text="Editar Pedido", command=self.edit_order,
                                         state="disabled")
        self.cancel_button = ctk.CTkButton(self.button_frame, text="Cancelar Pedido", command=self.cancel_order,
                                           state="disabled")

        self.view_button.grid(row=0, column=2, padx=10, pady=10)
        self.edit_button.grid(row=0, column=3, padx=10, pady=10)
        self.cancel_button.grid(row=0, column=4, padx=10, pady=10)

        # Load clients and products on module initialization
        self.clients = listar_clientes()
        self.products = listar_produtos()
        # Load inventory items (needed for deduction)
        self.inventory_items = listar_itens_estoque()

        # Load orders from database (will be the complete list for filtering)
        self.all_orders = listar_pedidos()
        self.orders = list(self.all_orders)  # List that will be displayed (filtered)

        # Status bar
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text=f"Total de pedidos: {len(self.orders)}"
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.selected_order = None
        self.toggle_date_filters()  # Call to initialize date field state
        self.apply_filters()  # Call apply_filters on initialization to populate the list

    def listar_pedidos(self):
        """
        Updates the internal list of all orders and then applies the filters.
        """
        self.all_orders = listar_pedidos()
        self.apply_filters()  # Call apply_filters to redraw with current filters

    # Removed _open_calendar_popup method as there will be no more calendar

    def toggle_date_filters(self):
        """
        Toggles the enablement of "From" and "To" date fields based on the "Today's Orders" checkbox.
        Sets dates to current day if "Today's Orders" is checked.
        """
        if self.today_orders_checkbox.get() == 1:  # Checked
            today = datetime.now().strftime("%d/%m/%Y")
            self.start_date_entry.configure(state="disabled")
            self.end_date_entry.configure(state="disabled")
            # Removed calendar buttons from here
            self.start_date_entry.delete(0, ctk.END)
            self.start_date_entry.insert(0, today)
            self.end_date_entry.delete(0, ctk.END)
            self.end_date_entry.insert(0, today)
        else:
            self.start_date_entry.configure(state="normal")
            self.end_date_entry.configure(state="normal")
            # Removed calendar buttons from here
            # Clear fields so the user can type
            self.start_date_entry.delete(0, ctk.END)
            self.end_date_entry.delete(0, ctk.END)
        self.apply_filters()  # Reapply filters when changing checkbox state

    def apply_filters(self, event=None):
        """
        Applies period, client, and status filters to the order list and updates the display.
        """
        filtered_by_date = []
        if self.today_orders_checkbox.get() == 1:
            # Filter by today's orders
            today = datetime.now().date()
            filtered_by_date = [
                order for order in self.all_orders
                if order["data_pedido"].date() == today  # Here 'data_pedido' should already be datetime
            ]
        else:
            # Filter by manual period
            start_date_str = self.start_date_entry.get().strip()
            end_date_str = self.end_date_entry.get().strip()

            start_date = None
            end_date = None

            # Modification: Handle empty date fields without error
            try:
                if start_date_str:
                    start_date = datetime.strptime(start_date_str, "%d/%m/%Y").date()
            except ValueError:
                messagebox.showerror("Date Error", "Invalid 'From' date format. Use DD/MM/AAAA.")
                # Clear the problematic field so the user can correct it
                self.start_date_entry.delete(0, ctk.END)
                # Call _populate_order_list() with an empty list to clear the table
                self._populate_order_list([])
                self.status_label.configure(text="Total de pedidos: 0")
                return

            try:
                if end_date_str:
                    end_date = datetime.strptime(end_date_str, "%d/%m/%Y").date()
            except ValueError:
                messagebox.showerror("Date Error", "Invalid 'To' date format. Use DD/MM/AAAA.")
                # Clear the problematic field so the user can correct it
                self.end_date_entry.delete(0, ctk.END)
                # Call _populate_order_list() with an empty list to clear the table
                self._populate_order_list([])
                self.status_label.configure(text="Total de pedidos: 0")
                return

            # If no date field is filled, do not apply date filter
            if not start_date and not end_date:
                filtered_by_date = list(self.all_orders)
            else:
                for order in self.all_orders:
                    # Ensure order["data_pedido"] is a datetime object before calling .date()
                    order_date = order["data_pedido"].date() if isinstance(order["data_pedido"],
                                                                           datetime) else datetime.strptime(
                        order["data_pedido_str"].split(" ")[0], "%d/%m/%Y").date()
                    if (start_date is None or order_date >= start_date) and \
                            (end_date is None or order_date <= end_date):
                        filtered_by_date.append(order)

        # Now apply client and status filters over the already date-filtered list
        search_term = self.client_filter_entry.get().strip().lower()
        selected_status = self.status_filter_combo.get()

        final_filtered_orders = []
        for order in filtered_by_date:  # Use the date-filtered list as base
            client_name = next((client["nome"] for client in self.clients if client["id"] == order["cliente_id"]),
                               "").lower()
            order_status = order["status"]

            # Check client name filter
            client_match = search_term in client_name

            # Check status filter
            status_match = (selected_status == "Todos" or order_status == selected_status)

            if client_match and status_match:
                final_filtered_orders.append(order)

        self.orders = final_filtered_orders  # Update the list of orders to be displayed
        self._populate_order_list()  # Call the internal method to populate the interface

        self.status_label.configure(text=f"Total de pedidos: {len(self.orders)}")
        self.reset_selection_buttons()

    def clear_filters(self):
        """
        Clears filter fields and displays all orders again.
        """
        self.client_filter_entry.delete(0, ctk.END)
        self.status_filter_combo.set("Todos")
        self.today_orders_checkbox.select()  # Go back to "Today's Orders"
        self.toggle_date_filters()  # This also calls apply_filters
        # self.apply_filters() # Called by toggle_date_filters

    def _populate_order_list(self, orders_to_display=None):  # Added optional parameter
        """
        Populates the list_frame with orders currently in the self.orders list.
        Internal method to avoid unnecessary network calls.
        """
        # If orders_to_display is provided, use it. Otherwise, use self.orders.
        current_orders = orders_to_display if orders_to_display is not None else self.orders

        for widget in self.list_frame.winfo_children():
            widget.destroy()

        for i, pedido in enumerate(current_orders):
            client_name = next((client["nome"] for client in self.clients if client["id"] == pedido["cliente_id"]),
                               "Cliente Desconhecido")

            # Updated to include concatenated items string
            btn_text = (
                f"ID: {pedido['id']} - Cliente: {client_name} - Itens: {pedido.get('itens_str', 'Nenhum item')} "
                f"- Total: R$ {pedido['total']:.2f} - Status: {pedido['status']}"
            )
            btn = ctk.CTkButton(
                self.list_frame,
                text=btn_text,
                anchor="w",
                command=lambda p=pedido: self.select_order_and_view(p)  # Single click to select
            )
            btn.grid(row=i, column=0, sticky="ew", pady=2, padx=5)
            # Attach order data to the button for easy retrieval on double-click
            btn._order_data = pedido
            # Bind double-click event
            btn.bind("<Double-Button-1>", lambda e, p=pedido: self._handle_double_click_details(p))

    def select_order_and_view(self, order):
        """
        Selects an order and updates the state of action buttons.
        """
        # Deselect previous order
        if self.selected_order:
            for widget in self.list_frame.winfo_children():
                if isinstance(widget, ctk.CTkButton) and hasattr(widget, '_order_data') and widget._order_data.get(
                        "id") == self.selected_order.get("id"):
                    widget.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])

        # Select the new order
        for widget in self.list_frame.winfo_children():
            if isinstance(widget, ctk.CTkButton) and hasattr(widget, '_order_data') and widget._order_data.get(
                    "id") == order.get("id"):
                widget.configure(fg_color=("#808080", "#555555"))  # Color to indicate selection

        # Update selected order
        self.selected_order = order

        # Enable/Disable buttons based on order status
        self.view_button.configure(state="normal")
        status = order.get("status", "")
        if status in ["Pendente", "Em preparo"]:
            self.edit_button.configure(state="normal")
        else:
            self.edit_button.configure(state="disabled")

        if status not in ["Entregue", "Cancelado"]:
            self.cancel_button.configure(state="normal")
        else:
            self.cancel_button.configure(state="disabled")

    def _handle_double_click_details(self, order):
        """
        Handles double-click on a list item to open details modally.
        """
        self.selected_order = order  # Ensures the selected order is correct
        self._show_order_details_modal()  # Opens the modal window

    def novo_pedido(self):
        # Pass self.clients and self.products, and the correct function to save the new order
        form = OrderForm(self, clients=self.clients, products=self.products, on_save=self.save_new_order)
        form.grab_set()

    def editar_pedido(self, pedido):
        # Pass self.clients and self.products, and the correct function to save the edited order
        form = OrderForm(self, clients=self.clients, products=self.products, order_data=pedido,
                         on_save=self.save_edited_order)
        form.grab_set()

    def save_new_order(self, order_data):
        new_id = salvar_pedido_no_banco(order_data)
        if new_id is not None:
            order_data["id"] = new_id  # <<<<<< AQUI CORRIGE O ERRO

            # Garantir que a data fique como datetime
            if isinstance(order_data["data_pedido"], str):
                order_data["data_pedido"] = datetime.strptime(order_data["data_pedido"], "%d/%m/%Y %H:%M")

            # Criar a string de itens
            itens_concatenados = [f"{item['produto_nome']} (x{item['quantidade']})" for item in
                                  order_data.get("itens", [])]
            order_data["itens_str"] = ", ".join(itens_concatenados)

            self.all_orders.append(order_data)
            self.apply_filters()
            messagebox.showinfo("Sucesso", "Pedido cadastrado com sucesso!")
        else:
            messagebox.showerror("Erro", "Falha ao cadastrar pedido no banco de dados.")

    def _generate_printable_order_details(self, order_data):
        """
        Generates a string with order details for printing and saves it to a temporary file.
        Then, attempts to open the file with the system's default viewer.
        """
        try:
            # Encontrar o nome do cliente
            client_name = next((c["nome"] for c in self.clients if c["id"] == order_data["cliente_id"]), "Desconhecido")

            # Construir o conteúdo para impressão
            content = f"===== Detalhes do Pedido #{order_data['id']} =====\n\n"
            content += f"Cliente: {client_name}\n"
            content += f"Data do Pedido: {order_data['data_pedido_str']}\n"
            content += f"Tipo: {order_data['tipo']}\n"
            content += f"Status: {order_data['status']}\n\n"

            content += "--- Itens do Pedido ---\n"
            if order_data.get("itens"):
                for item in order_data["itens"]:
                    content += (
                        f"- {item['produto_nome']} "
                        f"(Qtd: {item['quantidade']}, Preço Unitário: R$ {item['preco_unitario']:.2f}, "
                        f"Subtotal Item: R$ {item['subtotal']:.2f})\n"
                    )
            else:
                content += "Nenhum item neste pedido.\n"
            content += "\n"

            content += "--- Totais ---\n"
            content += f"Subtotal Geral: R$ {order_data['subtotal']:.2f}\n"
            content += f"Desconto: R$ {order_data['desconto']:.2f}\n"
            content += f"Total: R$ {order_data['total']:.2f}\n"
            content += f"Forma de Pagamento: {order_data['forma_pagamento']}\n\n"
            content += "=======================================\n"

            # Salvar em um arquivo temporário
            # Usar 'delete=False' para garantir que o arquivo não seja excluído imediatamente após o fechamento,
            # permitindo que o visualizador o acesse. Ele será excluído quando o programa Python fechar ou manualmente.
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix=".txt") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            # Abrir o arquivo com o aplicativo padrão do sistema
            current_os = platform.system()
            if current_os == "Windows":
                os.startfile(temp_file_path, "print")  # Tenta abrir com a ação de imprimir diretamente
            elif current_os == "Darwin":  # macOS
                os.system(f'open -a "TextEdit" "{temp_file_path}"')  # Abre com TextEdit, que tem opção de imprimir
            else:  # Linux e outros
                os.system(f'xdg-open "{temp_file_path}"')  # Tenta abrir com o aplicativo padrão

            messagebox.showinfo("Imprimir Pedido", f"Detalhes do pedido abertos para impressão.")

        except Exception as e:
            messagebox.showerror("Erro de Impressão",
                                 f"Ocorreu um erro ao preparar ou abrir o arquivo para impressão: {e}")
            print(f"Erro ao imprimir: {e}")
        finally:
            # Considerar se quer deletar o arquivo temporário imediatamente ou deixá-lo.
            # Para impressão, geralmente é bom deixá-lo até o usuário fechar o visualizador.
            # Para exclusão imediata, adicione: os.remove(temp_file_path)
            pass

    def _show_order_details_modal(self):
        """
        Cria e exibe a janela de detalhes do pedido de forma modal.
        """
        if not self.selected_order:
            messagebox.showinfo("Informação", "Por favor, selecione um pedido para ver os detalhes.")
            return

        view_window = ctk.CTkToplevel(self)
        view_window.title(f"Detalhes do Pedido #{self.selected_order.get('id')}")
        view_window.geometry("800x600")
        view_window.resizable(True, True)

        # Torna a janela modal
        view_window.grab_set()
        view_window.transient(self)  # Define a janela pai para que o modal fique acima

        # Configuração do grid
        view_window.grid_columnconfigure(0, weight=1)

        # Título
        title_label = ctk.CTkLabel(
            view_window,
            text=f"Detalhes do Pedido #{self.selected_order.get('id')}",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Frame de informações do pedido
        info_frame = ctk.CTkFrame(view_window)
        info_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        info_frame.grid_columnconfigure(1, weight=1)
        info_frame.grid_columnconfigure(3, weight=1)

        # Cliente
        client_label = ctk.CTkLabel(
            info_frame,
            text="Cliente:",
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        client_label.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="w")

        # Encontrar o nome do cliente
        client_name = ""
        for client in self.clients:
            if client.get("id") == self.selected_order.get("cliente_id"):
                client_name = client.get("nome", "")
                break

        client_value = ctk.CTkLabel(
            info_frame,
            text=client_name,
            anchor="w"
        )
        client_value.grid(row=0, column=1, padx=(0, 20), pady=(20, 10), sticky="w")

        # Tipo de pedido
        type_label = ctk.CTkLabel(
            info_frame,
            text="Tipo:",
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        type_label.grid(row=0, column=2, padx=(20, 10), pady=(20, 10), sticky="w")

        type_value = ctk.CTkLabel(
            info_frame,
            text=self.selected_order.get("tipo", ""),
            anchor="w"
        )
        type_value.grid(row=0, column=3, padx=(0, 20), pady=(20, 10), sticky="w")

        # Data
        date_label = ctk.CTkLabel(
            info_frame,
            text="Data:",
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        date_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")

        # Usar data_pedido_str para exibir a data
        # Formatar a data do pedido dinamicamente, se necessário
        data_pedido_str = self.selected_order.get("data_pedido_str")

        if not data_pedido_str:
            data_pedido = self.selected_order.get("data_pedido")
            if isinstance(data_pedido, datetime):
                data_pedido_str = data_pedido.strftime("%d/%m/%Y %H:%M")
            elif isinstance(data_pedido, str):
                try:
                    # Tenta converter a string do banco para datetime e formatar
                    data_obj = datetime.strptime(data_pedido, "%Y-%m-%d %H:%M:%S")
                    data_pedido_str = data_obj.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    data_pedido_str = data_pedido  # Caso a string não seja formatável, usa como está
            else:
                data_pedido_str = "Data não informada"

        date_value = ctk.CTkLabel(
            info_frame,
            text=data_pedido_str,
            anchor="w"
        )

        date_value.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="w")

        # Status
        status_label = ctk.CTkLabel(
            info_frame,
            text="Status:",
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        status_label.grid(row=1, column=2, padx=(20, 10), pady=10, sticky="w")

        status_value = ctk.CTkLabel(
            info_frame,
            text=self.selected_order.get("status", ""),
            anchor="w"
        )
        status_value.grid(row=1, column=3, padx=(0, 20), pady=10, sticky="w")

        # Items table frame
        items_frame = ctk.CTkFrame(view_window)
        items_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        view_window.grid_rowconfigure(2, weight=1)  # Make items_frame expand to fill space

        # Table title
        items_title = ctk.CTkLabel(
            items_frame,
            text="Itens do Pedido",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        items_title.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Table header
        header_frame = ctk.CTkFrame(items_frame, fg_color=("#EEEEEE", "#333333"))
        header_frame.grid(row=1, column=0, sticky="ew")
        items_frame.grid_columnconfigure(0, weight=1)

        headers = ["Produto", "Quantidade", "Preço Unitário", "Subtotal"]
        widths = [300, 100, 150, 150]

        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            )
            label.grid(row=0, column=i, padx=10, pady=10, sticky="w")
            header_frame.grid_columnconfigure(i, minsize=widths[i])

        # Table content (ScrollableFrame for items)
        content_frame = ctk.CTkScrollableFrame(items_frame, fg_color="transparent",
                                               height=200)  # Keep height for scroll
        content_frame.grid(row=2, column=0, sticky="nsew")
        items_frame.grid_rowconfigure(2, weight=1)  # Make content_frame inside items_frame expand

        # Populate with items
        items = self.selected_order.get("itens", [])

        for row_idx, item in enumerate(items):
            row_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            row_frame.grid(row=row_idx, column=0, sticky="ew", pady=5)

            # Add item data
            values = [
                item.get("produto_nome", ""),
                item.get("quantidade", ""),
                f"R$ {item.get('preco_unitario', 0):.2f}".replace(".", ","),
                f"R$ {item.get('subtotal', 0):.2f}".replace(".", ",")
            ]

            for col_idx, value in enumerate(values):
                label = ctk.CTkLabel(
                    row_frame,
                    text=str(value)
                )
                label.grid(row=0, column=col_idx, padx=10, pady=5, sticky="w")
                row_frame.grid_columnconfigure(col_idx, minsize=widths[col_idx])

            # Add separator line
            if row_idx < len(items) - 1:
                separator = ctk.CTkFrame(content_frame, height=1, fg_color=("#DDDDDD", "#555555"))
                separator.grid(row=row_idx + 0.5, column=0, sticky="ew", padx=10)

        # Totals frame
        totals_frame = ctk.CTkFrame(view_window)
        totals_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        totals_frame.grid_columnconfigure(1, weight=1)
        totals_frame.grid_columnconfigure(3, weight=1)

        # Subtotal
        subtotal_label = ctk.CTkLabel(
            totals_frame,
            text="Subtotal:",
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        subtotal_label.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="w")

        subtotal_value = ctk.CTkLabel(
            totals_frame,
            text=f"R$ {self.selected_order.get('subtotal', 0):.2f}".replace(".", ","),
            anchor="w"
        )
        subtotal_value.grid(row=0, column=1, padx=(0, 20), pady=(20, 10), sticky="w")

        # Desconto
        discount_label = ctk.CTkLabel(
            totals_frame,
            text="Desconto:",
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        discount_label.grid(row=0, column=2, padx=(20, 10), pady=(20, 10), sticky="w")

        discount_value = ctk.CTkLabel(
            totals_frame,
            text=f"R$ {self.selected_order.get('desconto', 0):.2f}".replace(".", ","),
            anchor="w"
        )
        discount_value.grid(row=0, column=3, padx=(0, 20), pady=(20, 10), sticky="w")

        # Total
        total_label = ctk.CTkLabel(
            totals_frame,
            text="Total:",
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        total_label.grid(row=1, column=0, padx=(20, 10), pady=(10, 20), sticky="w")

        total_value = ctk.CTkLabel(
            totals_frame,
            text=f"R$ {self.selected_order.get('total', 0):.2f}".replace(".", ","),
            anchor="w",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        total_value.grid(row=1, column=1, padx=(0, 20), pady=(10, 20), sticky="w")

        # Forma de pagamento
        payment_label = ctk.CTkLabel(
            totals_frame,
            text="Pagamento:",
            anchor="w"
        )
        payment_label.grid(row=1, column=2, padx=(20, 10), pady=(10, 20), sticky="w")

        payment_value = ctk.CTkLabel(
            totals_frame,
            text=self.selected_order.get("forma_pagamento", ""),
            anchor="w"
        )
        payment_value.grid(row=1, column=3, padx=(0, 20), pady=(10, 20), sticky="w")

        # Botões de ação (Fechar e Imprimir)
        button_frame = ctk.CTkFrame(view_window, fg_color="transparent")
        button_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)

        # Botão de Fechar
        close_button = ctk.CTkButton(
            button_frame,
            text="Fechar",
            fg_color="#D22B2B",
            hover_color="#AA0000",
            command=view_window.destroy
        )
        close_button.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="e")

        # Botão de Imprimir
        print_button = ctk.CTkButton(
            button_frame,
            text="Imprimir",
            command=lambda: self._generate_printable_order_details(self.selected_order)
        )
        print_button.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="w")

        # Espera até a janela modal ser fechada
        self.wait_window(view_window)

    def edit_order(self):
        if not self.selected_order:
            return

        # Check if the order can be edited
        status = self.selected_order.get("status", "")
        if status not in ["Pendente", "Em preparo"]:
            messagebox.showerror("Error", "Only pending or preparing orders can be edited.")
            return

        # Open edit form
        form = OrderForm(self, clients=self.clients, products=self.products, order_data=self.selected_order,
                         on_save=self.save_edited_order)
        form.grab_set()  # Make the window modal

    def save_edited_order(self, order_data):
        # Obter o status anterior do pedido (antes da edição)
        old_order_status = None
        for order in self.all_orders:
            if order.get("id") == order_data.get("id"):
                old_order_status = order.get("status")
                break

        # Salvar as alterações no banco de dados
        updated_id = salvar_pedido_no_banco(order_data)

        if updated_id is not None:
            # Atualizar a lista em memória após salvar com sucesso
            for i, order in enumerate(self.all_orders):
                if order.get("id") == order_data.get("id"):
                    # Garantir que a data fique como objeto datetime na memória
                    data_str = order_data["data_pedido"]
                    if " " in data_str and ":" in data_str:
                        order_data["data_pedido"] = datetime.strptime(data_str, "%d/%m/%Y %H:%M")
                    else:
                        order_data["data_pedido"] = datetime.strptime(data_str, "%d/%m/%Y").replace(
                            hour=datetime.now().hour, minute=datetime.now().minute
                        )

                    # Atualizar a string de itens para exibição na lista
                    itens_concatenados = [f"{item['produto_nome']} (x{item['quantidade']})" for item in
                                          order_data.get("itens", [])]
                    order_data["itens_str"] = ", ".join(itens_concatenados)

                    self.all_orders[i] = order_data
                    break

            # Se o status mudou para 'Entregue', realizar a baixa de estoque
            if order_data.get("status") == "Entregue" and old_order_status != "Entregue":
                deduction_successful = True
                self.inventory_items = listar_itens_estoque()  # Atualiza a lista de estoque antes de deduzir

                for item_pedido in order_data.get("itens", []):
                    produto_id = item_pedido.get("produto_id")
                    quantidade_pedido = item_pedido.get("quantidade")

                    # Procurar o item correspondente no estoque
                    estoque_item = next(
                        (inv_item for inv_item in self.inventory_items if inv_item.get("produto_id") == produto_id),
                        None
                    )

                    if estoque_item:
                        estoque_atual = estoque_item.get("quantidade", 0)

                        # Verificar se há estoque suficiente
                        if quantidade_pedido > estoque_atual:
                            messagebox.showerror(
                                "Erro de Estoque",
                                f"Estoque insuficiente para '{estoque_item.get('nome')}'. Disponível: {estoque_atual}, Necessário: {quantidade_pedido}."
                            )
                            deduction_successful = False
                            break

                        # Preparar dados para registrar a saída no estoque
                        movimento = {
                            "item_estoque_id": estoque_item.get("id"),
                            "tipo": "saída",
                            "quantidade": quantidade_pedido,
                            "data": datetime.now().strftime("%d/%m/%Y"),
                            "motivo": "Saída por entrega de pedido",
                            "observacoes": f"Saída automática para o Pedido #{order_data.get('id')}"
                        }

                        movimento_id = salvar_movimentacao_estoque_no_banco(movimento)
                        if movimento_id is None:
                            messagebox.showerror(
                                "Erro de Estoque",
                                f"Falha ao registrar saída de estoque para '{estoque_item.get('nome')}'."
                            )
                            deduction_successful = False
                            break
                    else:
                        messagebox.showwarning(
                            "Aviso de Estoque",
                            f"Item de estoque não encontrado para o produto ID {produto_id}. Baixa manual pode ser necessária."
                        )

                if deduction_successful:
                    messagebox.showinfo("Sucesso", "Pedido atualizado e estoque baixado com sucesso!")

            # Atualizar a exibição da lista de pedidos
            self.listar_pedidos()

            # Mostrar mensagem de sucesso caso não seja um pedido entregue (pois já mostramos antes para entregas)
            if not (order_data.get("status") == "Entregue" and old_order_status != "Entregue"):
                messagebox.showinfo("Sucesso", "Pedido atualizado com sucesso!")

        else:
            # Caso o update falhe no banco
            messagebox.showerror("Erro", "Falha ao atualizar o pedido no banco de dados.")

        # Resetar a seleção de botões
        self.reset_selection_buttons()

    def cancel_order(self):
        if not self.selected_order:
            return

        # Check if the order can be canceled
        status = self.selected_order.get("status", "")
        if status in ["Entregue", "Cancelado"]:
            messagebox.showerror("Error", "This order cannot be canceled.")
            return

        # Confirm cancellation
        if messagebox.askyesno("Confirm Cancellation",
                               f"Are you sure you want to cancel order #{self.selected_order.get('id')}?"):
            # Update status to "Canceled" in the database
            conn = None
            cur = None
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                cur = conn.cursor()
                cur.execute("UPDATE pedidos SET status = %s WHERE id = %s",
                            ("Cancelado", self.selected_order.get("id")))
                conn.commit()
                # Update in-memory list
                for i, order in enumerate(self.all_orders):  # Changed from self.orders to self.all_orders
                    if order.get("id") == self.selected_order.get("id"):
                        self.all_orders[i]["status"] = "Cancelado"
                        break
                self.listar_pedidos()  # Update display
                messagebox.showinfo("Success", "Order canceled successfully!")
            except psycopg2.Error as e:
                print(f"Error canceling order in database: {e}")
                print(f"PostgreSQL error details: {e.diag.message_detail if e.diag else 'N/A'}")
                print(f"SQLSTATE code: {e.pgcode if e.pgcode else 'N/A'}")
                if conn:
                    conn.rollback()
                messagebox.showerror("Error",
                                     "Failed to cancel order in the database. Check console for details.")
            finally:
                if cur:
                    cur.close()
                if conn:
                    conn.close()

            self.reset_selection_buttons()

    def reset_selection_buttons(self):
        """Resets order selection and disables action buttons."""
        self.selected_order = None
        # These buttons are already initialized in __init__, so we just configure the state
        self.view_button.configure(state="disabled")
        self.edit_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")


# For standalone test
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Order Module Test")
    app.geometry("1000x600")

    # Grid configuration
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    # Instantiate module
    orders_module = OrdersModule(app)
    orders_module.grid(row=0, column=0, sticky="nsew")

    app.mainloop()
