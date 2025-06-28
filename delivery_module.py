import customtkinter as ctk
from tkinter import messagebox
import os
from datetime import datetime
import psycopg2

# Importar configurações do banco de dados de um arquivo externo
from db_config import DB_CONFIG


def listar_entregas():
    """
    Função para listar todas as entregas do banco de dados,
    incluindo informações do pedido, cliente (com endereço completo) e funcionário associados.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                e.id, 
                e.pedido_id, 
                e.funcionario_id, 
                e.status, 
                e.data_saida, 
                e.data_entrega, 
                e.observacoes,
                p.cliente_id,
                c.nome as cliente_nome,
                -- Concatena as partes do endereço, incluindo complemento
                COALESCE(l.descricao, '') || 
                CASE WHEN c.numero_endereco IS NOT NULL THEN ', Nº ' || c.numero_endereco ELSE '' END || 
                CASE WHEN c.complemento_endereco IS NOT NULL AND c.complemento_endereco <> '' THEN ' (' || c.complemento_endereco || ')' ELSE '' END ||
                COALESCE(', ' || loc.descricao, '') || 
                COALESCE(', ' || cid.descricao, '') AS cliente_endereco,
                f.nome as funcionario_nome
            FROM entregas e
            JOIN pedidos p ON e.pedido_id = p.id
            JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN logradouro l ON c.logradouro_id = l.id
            LEFT JOIN localidade loc ON c.localidade_id = loc.id
            LEFT JOIN cidade cid ON c.cidade_id = cid.id
            JOIN funcionarios f ON e.funcionario_id = f.id
            ORDER BY e.data_saida DESC
        """)
        entregas = cur.fetchall()
        lista = []
        for row in entregas:
            lista.append({
                "id": row[0],
                "pedido_id": row[1],
                "funcionario_id": row[2],
                "status": row[3],
                "data_saida": row[4].strftime("%d/%m/%Y %H:%M") if row[4] else "",
                "data_entrega": row[5].strftime("%d/%m/%Y %H:%M") if row[5] else "",
                "observacoes": row[6],
                "cliente_id": row[7],
                "cliente_nome": row[8],
                "cliente_endereco": row[9],  # Este agora contém o endereço concatenado
                "funcionario_nome": row[10]
            })
        return lista
    except psycopg2.Error as e:
        print(f"Erro ao listar entregas: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def listar_pedidos_delivery_disponiveis():
    """
    Lista pedidos do tipo 'Delivery' que não foram entregues ou cancelados
    e que ainda não estão associados a uma entrega ativa,
    incluindo o endereço completo do cliente.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                p.id, 
                p.cliente_id, 
                c.nome as cliente_nome,
                -- Concatena as partes do endereço, incluindo complemento
                COALESCE(l.descricao, '') || 
                CASE WHEN c.numero_endereco IS NOT NULL THEN ', Nº ' || c.numero_endereco ELSE '' END || 
                CASE WHEN c.complemento_endereco IS NOT NULL AND c.complemento_endereco <> '' THEN ' (' || c.complemento_endereco || ')' ELSE '' END ||
                COALESCE(', ' || loc.descricao, '') || 
                COALESCE(', ' || cid.descricao, '') AS cliente_endereco
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN logradouro l ON c.logradouro_id = l.id
            LEFT JOIN localidade loc ON c.localidade_id = loc.id
            LEFT JOIN cidade cid ON c.cidade_id = cid.id
            LEFT JOIN entregas e ON p.id = e.pedido_id AND e.status NOT IN ('Concluída', 'Cancelada')
            WHERE p.tipo = 'Delivery' AND p.status NOT IN ('Entregue', 'Cancelado') AND e.pedido_id IS NULL
            ORDER BY p.id ASC
        """)
        pedidos = cur.fetchall()
        lista = []
        for row in pedidos:
            lista.append({
                "id": row[0],
                "cliente_id": row[1],
                "cliente_nome": row[2],
                "cliente_endereco": row[3]  # Este agora contém o endereço concatenado
            })
        return lista
    except psycopg2.Error as e:
        print(f"Erro ao listar pedidos delivery disponíveis: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def listar_funcionarios_entregadores():
    """
    Lista todos os funcionários com cargo de 'Entregador'.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, nome FROM funcionarios WHERE (cargo = 'entregador' or cargo = 'Entregador' or cargo = 'ENTREGADOR') AND ativo = TRUE ORDER BY nome ASC")
        funcionarios = cur.fetchall()
        lista = []
        for row in funcionarios:
            lista.append({
                "id": row[0],
                "nome": row[1]
            })
        return lista
    except psycopg2.Error as e:
        print(f"Erro ao listar funcionários entregadores: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def salvar_entrega_no_banco(delivery_data):
    """
    Salva ou atualiza uma entrega no banco de dados.
    Se delivery_data contém 'id', tenta atualizar; caso contrário, insere uma nova.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        entrega_id = delivery_data.get("id")

        data_saida_dt = datetime.strptime(delivery_data["data_saida"], "%d/%m/%Y %H:%M")
        data_entrega_dt = None
        if delivery_data["data_entrega"]:
            data_entrega_dt = datetime.strptime(delivery_data["data_entrega"], "%d/%m/%Y %H:%M")

        if entrega_id:
            # Atualizar entrega existente
            cur.execute("""
                UPDATE entregas SET
                    pedido_id = %s,
                    funcionario_id = %s,
                    status = %s,
                    data_saida = %s,
                    data_entrega = %s,
                    observacoes = %s
                WHERE id = %s
            """, (
                delivery_data["pedido_id"],
                delivery_data["funcionario_id"],
                delivery_data["status"],
                data_saida_dt,
                data_entrega_dt,
                delivery_data["observacoes"],
                entrega_id
            ))
        else:
            # Inserir nova entrega
            cur.execute("""
                INSERT INTO entregas (pedido_id, funcionario_id, status, data_saida, data_entrega, observacoes)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                delivery_data["pedido_id"],
                delivery_data["funcionario_id"],
                delivery_data["status"],
                data_saida_dt,
                data_entrega_dt,
                delivery_data["observacoes"]
            ))
            entrega_id = cur.fetchone()[0]

        conn.commit()
        return entrega_id
    except psycopg2.Error as e:
        print(f"Erro ao salvar entrega no banco de dados: {e}")
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


def atualizar_status_pedido(pedido_id, new_status):
    """
    Atualiza o status de um pedido na tabela 'pedidos'.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("UPDATE pedidos SET status = %s WHERE id = %s", (new_status, pedido_id))
        conn.commit()
        return True
    except psycopg2.Error as e:
        print(f"Erro ao atualizar status do pedido {pedido_id}: {e}")
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


class DeliveryAssignmentForm(ctk.CTkToplevel):
    def __init__(self, master, orders, employees, delivery_data=None, on_save=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.orders = orders  # Pedidos disponíveis para atribuição
        self.employees = employees  # Entregadores disponíveis
        self.delivery_data = delivery_data  # Dados da entrega se for edição
        self.on_save = on_save
        self.selected_order_data = None  # Para armazenar dados do pedido selecionado

        # Configuração da janela
        self.title("Atribuir Entrega" if not delivery_data else "Editar Entrega")
        self.geometry("500x650")  # Aumenta a altura da janela
        self.resizable(True, True)  # Torna a janela redimensionável
        self.grab_set()  # Torna a janela modal

        # Configuração do grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Título - não expande
        self.grid_rowconfigure(1, weight=1)  # form_frame - pode expandir
        self.grid_rowconfigure(2, weight=0)  # button_frame - não expande

        # Título
        self.title_label = ctk.CTkLabel(
            self,
            text="Atribuir Entrega" if not delivery_data else "Editar Entrega",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Frame do formulário
        self.form_frame = ctk.CTkFrame(self)
        self.form_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.form_frame.grid_columnconfigure(1, weight=1)

        # Campos do formulário
        # Pedido
        self.order_label = ctk.CTkLabel(
            self.form_frame,
            text="Pedido:",
            anchor="w"
        )
        self.order_label.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="w")

        # Lista de pedidos para o combobox
        order_options = ["Selecione um pedido..."] + [f"#{order.get('id')} - {order.get('cliente_nome')}" for order in
                                                      self.orders]

        self.order_combo = ctk.CTkComboBox(
            self.form_frame,
            values=order_options,
            width=300,
            command=self.update_order_info
        )
        self.order_combo.grid(row=0, column=1, padx=(0, 20), pady=(20, 10), sticky="ew")
        self.order_combo.set("Selecione um pedido...")

        # Endereço de entrega
        self.address_label = ctk.CTkLabel(
            self.form_frame,
            text="Endereço:",
            anchor="w"
        )
        self.address_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")

        self.address_value = ctk.CTkLabel(
            self.form_frame,
            text="",
            anchor="w",
            wraplength=300
        )
        self.address_value.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="w")

        # Entregador
        self.deliverer_label = ctk.CTkLabel(
            self.form_frame,
            text="Entregador:",
            anchor="w"
        )
        self.deliverer_label.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="w")

        # Lista de entregadores para o combobox
        deliverer_options = ["Selecione um entregador..."] + [employee.get("nome") for employee in self.employees]

        self.deliverer_combo = ctk.CTkComboBox(
            self.form_frame,
            values=deliverer_options,
            width=300
        )
        self.deliverer_combo.grid(row=2, column=1, padx=(0, 20), pady=10, sticky="ew")
        self.deliverer_combo.set("Selecione um entregador...")

        # Status da entrega
        self.status_label = ctk.CTkLabel(
            self.form_frame,
            text="Status:",
            anchor="w"
        )
        self.status_label.grid(row=3, column=0, padx=(20, 10), pady=10, sticky="w")

        self.status_combo = ctk.CTkComboBox(
            self.form_frame,
            values=["Pendente", "Em rota", "Concluída", "Cancelada"],
            width=300
        )
        self.status_combo.grid(row=3, column=1, padx=(0, 20), pady=10, sticky="ew")
        self.status_combo.set("Pendente")

        # Data de saída
        self.departure_date_label = ctk.CTkLabel(
            self.form_frame,
            text="Data de Saída:",
            anchor="w"
        )
        self.departure_date_label.grid(row=4, column=0, padx=(20, 10), pady=10, sticky="w")

        current_date = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.departure_date_entry = ctk.CTkEntry(
            self.form_frame,
            width=300
        )
        self.departure_date_entry.insert(0, current_date)
        self.departure_date_entry.grid(row=4, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Data de entrega
        self.delivery_date_label = ctk.CTkLabel(
            self.form_frame,
            text="Data de Entrega:",
            anchor="w"
        )
        self.delivery_date_label.grid(row=5, column=0, padx=(20, 10), pady=10, sticky="w")

        self.delivery_date_entry = ctk.CTkEntry(
            self.form_frame,
            width=300,
            placeholder_text="Deixe em branco se ainda não entregue"
        )
        self.delivery_date_entry.grid(row=5, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Observações
        self.notes_label = ctk.CTkLabel(
            self.form_frame,
            text="Observações:",
            anchor="w"
        )
        self.notes_label.grid(row=6, column=0, padx=(20, 10), pady=10, sticky="nw")

        self.notes_entry = ctk.CTkTextbox(
            self.form_frame,
            height=80,
            width=300
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
            text="Salvar",
            command=self.save_delivery
        )
        self.save_button.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="w")

        # Preencher os campos se for edição
        if self.delivery_data:
            # Encontrar o pedido selecionado (self.orders contêm os dados completos)
            for order in self.orders:
                if order.get("id") == self.delivery_data.get("pedido_id"):
                    self.selected_order_data = order
                    self.order_combo.set(f"#{order.get('id')} - {order.get('cliente_nome')}")
                    # Desabilitar a seleção de pedido em modo edição para evitar inconsistências
                    self.order_combo.configure(state="disabled")
                    break

            # Atualizar o endereço do pedido selecionado
            if self.selected_order_data:
                self.address_value.configure(
                    text=self.selected_order_data.get("cliente_endereco", "Endereço não encontrado"))

            # Encontrar o entregador
            for employee in self.employees:
                if employee.get("id") == self.delivery_data.get(
                        "funcionario_id"):
                    self.deliverer_combo.set(employee.get("nome"))
                    break

            # Preencher os outros campos
            self.status_combo.set(self.delivery_data.get("status", "Pendente"))
            self.departure_date_entry.delete(0, "end")
            self.departure_date_entry.insert(0, self.delivery_data.get("data_saida", ""))

            if self.delivery_data.get("data_entrega"):
                self.delivery_date_entry.delete(0, "end")
                self.delivery_date_entry.insert(0, self.delivery_data.get("data_entrega"))

            self.notes_entry.delete("0.0", "end")
            self.notes_entry.insert("0.0", self.delivery_data.get("observacoes", ""))

    def update_order_info(self, order_text):
        if order_text == "Selecione um pedido...":
            self.address_value.configure(text="")
            self.selected_order_data = None
            return

        order_id = int(order_text.split(" - ")[0].replace("#", ""))

        self.selected_order_data = next((order for order in self.orders if order.get("id") == order_id), None)

        if self.selected_order_data:
            self.address_value.configure(
                text=self.selected_order_data.get("cliente_endereco", "Endereço não encontrado"))
        else:
            self.address_value.configure(text="Endereço não encontrado")

    def save_delivery(self):
        order_id = None
        if self.delivery_data and self.selected_order_data:
            order_id = self.selected_order_data.get("id")
        else:
            order_text = self.order_combo.get()
            if order_text == "Selecione um pedido...":
                messagebox.showerror("Erro", "Selecione um pedido.")
                return
            order_id = int(order_text.split(" - ")[0].replace("#", ""))

        deliverer_name = self.deliverer_combo.get()
        if deliverer_name == "Selecione um entregador...":
            messagebox.showerror("Erro", "Selecione um entregador.")
            return

        deliverer_id = None
        for employee in self.employees:
            if employee.get("nome") == deliverer_name:
                deliverer_id = employee.get("id")
                break

        if deliverer_id is None:
            messagebox.showerror("Erro", "Entregador não encontrado.")
            return

        departure_date_str = self.departure_date_entry.get().strip()
        try:
            datetime.strptime(departure_date_str, "%d/%m/%Y %H:%M")
        except ValueError:
            messagebox.showerror("Erro", "Formato de Data de Saída inválido. Use DD/MM/AAAA HH:MM.")
            return

        delivery_date_str = self.delivery_date_entry.get().strip()
        if delivery_date_str:
            try:
                datetime.strptime(delivery_date_str, "%d/%m/%Y %H:%M")
            except ValueError:
                messagebox.showerror("Erro",
                                     "Formato de Data de Entrega inválido. Use DD/MM/AAAA HH:MM ou deixe em branco.")
                return

        status = self.status_combo.get()
        if status == "Concluída" and not delivery_date_str:
            messagebox.showerror("Erro", "Para status 'Concluída', a data de entrega é obrigatória.")
            return

        delivery_data = {
            "pedido_id": order_id,
            "funcionario_id": deliverer_id,
            "status": status,
            "data_saida": departure_date_str,
            "data_entrega": delivery_date_str if delivery_date_str else None,
            "observacoes": self.notes_entry.get("0.0", "end").strip()
        }

        if self.delivery_data and "id" in self.delivery_data:
            delivery_data["id"] = self.delivery_data["id"]

        if self.on_save:
            self.on_save(delivery_data)

        self.destroy()


class DeliveryModule(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.selected_delivery = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Faz a tabela de entregas expandir

        self.title_label = ctk.CTkLabel(
            self,
            text="Gerenciamento de Entregas",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Buscar entrega por cliente ou status..."
        )
        self.search_entry.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="ew")

        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Buscar",
            width=100,
            command=self.search_deliveries
        )
        self.search_button.grid(row=0, column=1, padx=(0, 20), pady=20)

        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        # Define 4 colunas com peso 1 para distribuir os botões
        self.action_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.add_button = ctk.CTkButton(
            self.action_frame,
            text="Nova Entrega",
            width=150,
            command=self.add_delivery
        )
        self.add_button.grid(row=0, column=0, padx=20, pady=20)

        self.edit_button = ctk.CTkButton(
            self.action_frame,
            text="Editar",
            width=150,
            state="disabled",
            command=self.edit_delivery
        )
        self.edit_button.grid(row=0, column=1, padx=20, pady=20)

        self.complete_button = ctk.CTkButton(
            self.action_frame,
            text="Marcar como Entregue",
            width=200,
            fg_color="#28A745",
            hover_color="#218838",
            state="disabled",
            command=self.mark_as_delivered
        )
        self.complete_button.grid(row=0, column=2, padx=20, pady=20)

        self.cancel_button = ctk.CTkButton(
            self.action_frame,
            text="Cancelar Entrega",
            width=150,
            fg_color="#D22B2B",
            hover_color="#AA0000",
            state="disabled",
            command=self.cancel_delivery
        )
        self.cancel_button.grid(row=0, column=3, padx=20, pady=20)

        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

        self.header_frame = ctk.CTkFrame(self.table_frame, fg_color=("#EEEEEE", "#333333"))
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.table_frame.grid_columnconfigure(0, weight=1)  # Faz o cabeçalho preencher a largura

        headers = ["ID", "Pedido", "Cliente", "Endereço", "Entregador", "Status", "Saída", "Entrega"]
        # Ajustado o tamanho da coluna "Endereço"
        widths = [50, 80, 150, 300, 150, 100, 120, 120]

        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                self.header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            )
            # Alinhamento do texto no cabeçalho
            if header in ["ID", "Saída", "Entrega"]:
                label.configure(anchor="e")
            else:
                label.configure(anchor="w")

            label.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            self.header_frame.grid_columnconfigure(i, weight=1,
                                                   minsize=widths[i])  # Colunas flexíveis com largura mínima

        self.content_frame = ctk.CTkScrollableFrame(self.table_frame, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.table_frame.grid_rowconfigure(1, weight=1)  # Faz o conteúdo da tabela expandir verticalmente
        self.content_frame.grid_columnconfigure(0, weight=1)  # Permite que os frames das linhas preencham a largura

        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.status_frame.grid_columnconfigure(1, weight=1)  # Para alinhar o contador de pendentes à direita

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Total de entregas: 0"
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.pending_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            text_color="orange"
        )
        self.pending_label.grid(row=0, column=1, padx=20, pady=10, sticky="e")

        # Inicializa as listas de dados
        self.all_deliveries = []
        self.deliveries = []
        self.available_orders_for_assignment = []
        self.delivery_employees = []

        self.populate_table()  # Popula a tabela ao iniciar

    def populate_table(self, filtered_deliveries=None):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.all_deliveries = listar_entregas()  # Sempre recarrega todas as entregas do banco

        # Filtra ou exibe todas as entregas com base no parâmetro
        deliveries_to_display = filtered_deliveries if filtered_deliveries is not None else self.all_deliveries

        self.status_label.configure(text=f"Total de entregas: {len(deliveries_to_display)}")

        # Calcula e exibe o número de entregas pendentes (contando apenas de all_deliveries)
        pending_count = sum(1 for delivery in self.all_deliveries if delivery.get("status") in ["Pendente", "Em rota"])
        if pending_count > 0:
            self.pending_label.configure(text=f"Entregas pendentes: {pending_count}")
        else:
            self.pending_label.configure(text="")

        widths = [50, 80, 150, 300, 150, 100, 120, 120]  # Larguras ajustadas para as colunas de dados

        for row_idx, delivery in enumerate(deliveries_to_display):
            row_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            # Usa 2 * row_idx para o frame da linha e 2 * row_idx + 1 para o separador
            row_frame.grid(row=row_idx * 2, column=0, sticky="ew", pady=5)

            for i in range(len(widths)):
                # Configura cada coluna do frame da linha para ter o peso e minsize definidos
                row_frame.grid_columnconfigure(i, weight=1, minsize=widths[i])

            status = delivery.get("status", "")
            status_color = None
            if status == "Concluída":
                status_color = "green"
            elif status == "Cancelada":
                status_color = "red"
            elif status == "Em rota":
                status_color = "orange"
            else:
                status_color = None

            values = [
                delivery.get("id", ""),
                f"#{delivery.get('pedido_id', '')}",
                delivery.get("cliente_nome", ""),
                delivery.get("cliente_endereco", ""),  # Este agora contém o endereço concatenado
                delivery.get("funcionario_nome", ""),
                status,
                delivery.get("data_saida", ""),
                delivery.get("data_entrega", "")
            ]

            for col_idx, value in enumerate(values):
                label = ctk.CTkLabel(
                    row_frame,
                    text=str(value),
                    text_color=status_color if col_idx == 5 else None  # Aplica cor apenas na coluna de status
                )
                # Alinhamento do texto na linha de dados
                if col_idx in [0, 6, 7]:  # ID, Data Saída, Data Entrega - Alinhados à direita
                    label.configure(anchor="e")
                else:
                    label.configure(anchor="w")

                label.grid(row=0, column=col_idx, padx=10, pady=5, sticky="nsew")

            # Permite selecionar a linha clicando em qualquer parte do frame ou de seus widgets
            row_frame.bind("<Button-1>", lambda e, d=delivery: self.select_delivery(d))
            for widget in row_frame.winfo_children():
                widget.bind("<Button-1>", lambda e, d=delivery: self.select_delivery(d))

            # Adiciona um separador entre as linhas, exceto a última
            if row_idx < len(deliveries_to_display) - 1:
                separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=("#DDDDDD", "#555555"))
                separator.grid(row=row_idx * 2 + 1, column=0, sticky="ew", padx=10)

        self.reset_selection_buttons()  # Resetar a seleção para garantir consistência

    def select_delivery(self, delivery):
        # Desseleciona a entrega anterior na UI
        if self.selected_delivery:
            for widget_row_frame in self.content_frame.winfo_children():
                # Verifica se é um CTkFrame (que representa uma linha de entrega)
                if isinstance(widget_row_frame, ctk.CTkFrame):
                    # Tenta acessar o ID da entrega através do primeiro widget na linha (o label do ID)
                    # Certifica-se de que o widget_row_frame.winfo_children() não esteja vazio antes de acessar o índice 0
                    if widget_row_frame.winfo_children() and hasattr(widget_row_frame.winfo_children()[0], 'cget') and \
                            widget_row_frame.winfo_children()[0].cget("text") == str(
                        self.selected_delivery.get("id", "")):
                        widget_row_frame.configure(fg_color="transparent")  # Volta à cor padrão
                        break

        # Seleciona a nova entrega na UI
        for widget_row_frame in self.content_frame.winfo_children():
            if isinstance(widget_row_frame, ctk.CTkFrame):
                if widget_row_frame.winfo_children() and hasattr(widget_row_frame.winfo_children()[0], 'cget') and \
                        widget_row_frame.winfo_children()[0].cget("text") == str(delivery.get("id", "")):
                    widget_row_frame.configure(fg_color=("gray90", "gray20"))  # Cor para indicar seleção
                    break

        self.selected_delivery = delivery

        # Habilita/Desabilita botões com base no status da entrega
        self.edit_button.configure(state="normal")

        status = delivery.get("status", "")
        if status in ["Pendente",
                      "Em rota"]:  # Pode ser marcada como entregue ou cancelada se estiver pendente ou em rota
            self.complete_button.configure(state="normal")
            self.cancel_button.configure(state="normal")
        else:  # Se já foi concluída ou cancelada, não pode ser alterada
            self.complete_button.configure(state="disabled")
            self.cancel_button.configure(state="disabled")

    def search_deliveries(self):
        search_term = self.search_entry.get().strip().lower()

        if not search_term:
            self.populate_table()  # Se a busca estiver vazia, exibe todas as entregas
            return

        filtered_deliveries = []

        for delivery in self.all_deliveries:
            # Verifica se o termo de busca está em qualquer um dos campos relevantes
            if (search_term in str(delivery.get("id", "")).lower() or  # Busca por ID
                    search_term in delivery.get("status", "").lower() or
                    search_term in delivery.get("cliente_nome", "").lower() or
                    search_term in delivery.get("cliente_endereco", "").lower() or  # Busca no endereço completo
                    search_term in delivery.get("funcionario_nome", "").lower()):
                filtered_deliveries.append(delivery)

        self.populate_table(filtered_deliveries)  # Popula a tabela com os resultados filtrados
        self.reset_selection_buttons()  # Resetar a seleção após a busca

    def add_delivery(self):
        # Recarrega as listas antes de abrir o formulário
        self.available_orders_for_assignment = listar_pedidos_delivery_disponiveis()
        self.delivery_employees = listar_funcionarios_entregadores()

        if not self.available_orders_for_assignment:
            messagebox.showinfo("Informação", "Não há pedidos delivery disponíveis para atribuir.")
            return

        if not self.delivery_employees:
            messagebox.showerror("Erro", "Não há entregadores disponíveis.")
            return

        form = DeliveryAssignmentForm(self, self.available_orders_for_assignment, self.delivery_employees,
                                      on_save=self.save_new_delivery)
        form.focus()  # Coloca o foco na nova janela

    def save_new_delivery(self, delivery_data):
        # Verifica se já existe uma entrega ativa para o pedido
        for existing_delivery in self.all_deliveries:
            if existing_delivery.get("pedido_id") == delivery_data.get("pedido_id") and \
                    existing_delivery.get("status") not in ["Concluída", "Cancelada"]:
                messagebox.showerror("Erro", "Este pedido já está atribuído a uma entrega ativa.")
                return

        new_id = salvar_entrega_no_banco(delivery_data)
        if new_id is not None:
            new_pedido_status = ""
            # Atualiza o status do pedido no módulo de pedidos, se aplicável
            if delivery_data.get("status") == "Pendente":
                new_pedido_status = "Em entrega"
            elif delivery_data.get("status") == "Em rota":
                new_pedido_status = "Em entrega"

            if new_pedido_status:
                atualizar_status_pedido(delivery_data.get("pedido_id"), new_pedido_status)

            self.populate_table()  # Atualiza a tabela de entregas na UI
            messagebox.showinfo("Sucesso", "Entrega atribuída com sucesso!")
        else:
            messagebox.showerror("Erro",
                                 "Falha ao atribuir a entrega no banco de dados. Verifique o console para detalhes.")

        self.reset_selection_buttons()

    def edit_delivery(self):
        if not self.selected_delivery:
            messagebox.showinfo("Informação", "Por favor, selecione uma entrega para editar.")
            return

        status = self.selected_delivery.get("status", "")
        if status in ["Concluída", "Cancelada"]:
            messagebox.showerror("Erro", "Entregas concluídas ou canceladas não podem ser editadas.")
            return

        # Recarrega as listas de pedidos e funcionários
        current_orders = listar_pedidos_delivery_disponiveis()
        # Garante que o pedido da entrega atual esteja na lista de opções para edição
        selected_delivery_order_id = self.selected_delivery.get("pedido_id")

        # Busca os detalhes do pedido da entrega selecionada
        conn = None
        cur = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    p.id, 
                    p.cliente_id, 
                    c.nome as cliente_nome,
                    COALESCE(l.descricao, '') || 
                    CASE WHEN c.numero_endereco IS NOT NULL THEN ', Nº ' || c.numero_endereco ELSE '' END || 
                    CASE WHEN c.complemento_endereco IS NOT NULL AND c.complemento_endereco <> '' THEN ' (' || c.complemento_endereco || ')' ELSE '' END ||
                    COALESCE(', ' || loc.descricao, '') || 
                    COALESCE(', ' || cid.descricao, '') AS cliente_endereco
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                LEFT JOIN logradouro l ON c.logradouro_id = l.id
                LEFT JOIN localidade loc ON c.localidade_id = loc.id
                LEFT JOIN cidade cid ON c.cidade_id = cid.id
                WHERE p.id = %s
             """, (selected_delivery_order_id,))
            current_order_data = cur.fetchone()
            if current_order_data:
                # Adiciona o pedido atual à lista de opções, caso não esteja lá (porque já está associado a uma entrega)
                if selected_delivery_order_id not in [order.get("id") for order in current_orders]:
                    current_orders.append({
                        "id": current_order_data[0],
                        "cliente_id": current_order_data[1],
                        "cliente_nome": current_order_data[2],
                        "cliente_endereco": current_order_data[3]
                    })
        except psycopg2.Error as e:
            print(f"Erro ao buscar detalhes do pedido para edição: {e}")
            messagebox.showerror("Erro de Banco de Dados", "Não foi possível carregar detalhes do pedido para edição.")
            return
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

        form = DeliveryAssignmentForm(self, current_orders, listar_funcionarios_entregadores(),
                                      delivery_data=self.selected_delivery, on_save=self.save_edited_delivery)
        form.focus()

    def save_edited_delivery(self, delivery_data):
        # Busca o status antigo da entrega antes de salvar
        old_delivery = next((d for d in self.all_deliveries if d.get("id") == delivery_data.get("id")), None)
        old_status = old_delivery.get("status") if old_delivery else ""

        updated_id = salvar_entrega_no_banco(delivery_data)
        if updated_id is not None:
            new_delivery_status = delivery_data.get("status")
            pedido_id = delivery_data.get("pedido_id")

            # Mapeamento do status da entrega para o status do pedido
            pedido_status_map = {
                "Pendente": "Pronto",  # Se a entrega for criada como pendente, o pedido já deve estar pronto
                "Em rota": "Em entrega",
                "Concluída": "Entregue",
                "Cancelada": "Cancelado"
            }

            # Se o status da entrega mudou, atualiza o status do pedido correspondente
            if new_delivery_status != old_status:
                new_pedido_status_for_order = pedido_status_map.get(new_delivery_status)
                if new_pedido_status_for_order:
                    atualizar_status_pedido(pedido_id, new_pedido_status_for_order)

            self.populate_table()  # Atualiza a tabela de entregas na UI
            messagebox.showinfo("Sucesso", "Entrega atualizada com sucesso!")
        else:
            messagebox.showerror("Erro",
                                 "Falha ao atualizar a entrega no banco de dados. Verifique o console para detalhes.")

        self.reset_selection_buttons()

    def mark_as_delivered(self):
        if not self.selected_delivery:
            messagebox.showinfo("Informação", "Por favor, selecione uma entrega para marcar como entregue.")
            return

        status = self.selected_delivery.get("status", "")
        if status in ["Concluída", "Cancelada"]:
            messagebox.showerror("Erro", "Esta entrega não pode ser marcada como entregue.")
            return

        # Usa a caixa de diálogo de confirmação personalizada
        self._show_confirm_dialog(
            "Confirmar Entrega",
            "Deseja marcar esta entrega como entregue?",
            self._execute_mark_as_delivered
        )

    def _execute_mark_as_delivered(self):
        if self.selected_delivery:
            delivery_data = self.selected_delivery.copy()
            delivery_data["status"] = "Concluída"
            delivery_data["data_entrega"] = datetime.now().strftime("%d/%m/%Y %H:%M")

            updated_id = salvar_entrega_no_banco(delivery_data)
            if updated_id is not None:
                atualizar_status_pedido(delivery_data.get("pedido_id"), "Entregue")  # Atualiza status do pedido
                self.populate_table()  # Atualiza a tabela de entregas
                messagebox.showinfo("Sucesso", "Entrega marcada como entregue com sucesso!")
            else:
                messagebox.showerror("Erro", "Falha ao marcar a entrega como entregue no banco de dados.")

        self.reset_selection_buttons()

    def cancel_delivery(self):
        if not self.selected_delivery:
            messagebox.showinfo("Informação", "Por favor, selecione uma entrega para cancelar.")
            return

        status = self.selected_delivery.get("status", "")
        if status in ["Concluída", "Cancelada"]:
            messagebox.showerror("Erro", "Esta entrega não pode ser cancelada.")
            return

        # Usa a caixa de diálogo de confirmação personalizada
        self._show_confirm_dialog(
            "Confirmar Cancelamento",
            "Deseja cancelar esta entrega?",
            self._execute_cancel_delivery
        )

    def _execute_cancel_delivery(self):
        if self.selected_delivery:
            delivery_data = self.selected_delivery.copy()
            delivery_data["status"] = "Cancelada"
            delivery_data["data_entrega"] = None  # Data de entrega é nula se cancelada

            updated_id = salvar_entrega_no_banco(delivery_data)
            if updated_id is not None:
                atualizar_status_pedido(delivery_data.get("pedido_id"), "Cancelado")  # Atualiza status do pedido
                self.populate_table()  # Atualiza a tabela de entregas
                messagebox.showinfo("Sucesso", "Entrega cancelada com sucesso!")
            else:
                messagebox.showerror("Erro", "Falha ao cancelar a entrega no banco de dados.")

        self.reset_selection_buttons()

    def reset_selection_buttons(self):
        """Reseta a seleção de entrega e desabilita os botões de ação."""
        # Descolorir a linha selecionada, se houver
        if self.selected_delivery:
            for widget_row_frame in self.content_frame.winfo_children():
                if isinstance(widget_row_frame, ctk.CTkFrame):
                    if widget_row_frame.winfo_children() and hasattr(widget_row_frame.winfo_children()[0], 'cget') and \
                            widget_row_frame.winfo_children()[0].cget("text") == str(
                        self.selected_delivery.get("id", "")):
                        widget_row_frame.configure(fg_color="transparent")
                        break

        self.selected_delivery = None
        self.edit_button.configure(state="disabled")
        self.complete_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")

    def _show_confirm_dialog(self, title, message, on_confirm):
        """
        Cria e exibe uma janela de diálogo de confirmação personalizada.
        Funciona como um modal, bloqueando a interação com a janela pai.
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

        self.wait_window(confirm_window)  # Espera até a janela modal ser fechada


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Teste do Módulo de Entregas")
    app.geometry("1000x600")

    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    delivery_module = DeliveryModule(app)
    delivery_module.grid(row=0, column=0, sticky="nsew")

    app.mainloop()

