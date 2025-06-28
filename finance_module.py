import customtkinter as ctk
from tkinter import messagebox
import psycopg2
from datetime import datetime, timedelta
import calendar
import json
import os
import platform
import subprocess  # Para abrir arquivos PDF

# Tentar importar fpdf para geração de PDF. Se não estiver instalado, avisar.
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None
    print("Aviso: A biblioteca 'fpdf' não está instalada. A geração de relatórios em PDF não estará disponível.")
    print("Para instalá-la, execute: pip install fpdf")

# Tentar importar matplotlib para gráficos. Se não estiver instalado, avisar.
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    plt = None
    FigureCanvasTkAgg = None
    MATPLOTLIB_AVAILABLE = False
    print("Aviso: A biblioteca 'matplotlib' não está instalada. Os gráficos do dashboard não estarão disponíveis.")
    print("Para instalá-la, execute: pip install matplotlib")

# Importar configurações do banco de dados de um arquivo externo
from db_config import DB_CONFIG


# --- Funções de Banco de Dados para o Módulo Financeiro ---

def listar_categorias_despesa():
    """Lista todas as categorias de despesa."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM categoria_despesa ORDER BY nome")
        return [{"id": row[0], "nome": row[1]} for row in cur.fetchall()]
    except psycopg2.Error as e:
        print(f"Erro ao listar categorias de despesa: {e}")
        messagebox.showerror("Erro de BD", "Não foi possível listar categorias de despesa.")
        return []
    finally:
        if cur: cur.close()
        if conn: conn.close()


def inserir_categoria_despesa(nome):
    """Insere uma nova categoria de despesa."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("INSERT INTO categoria_despesa (nome) VALUES (%s) RETURNING id", (nome,))
        new_id = cur.fetchone()[0]
        conn.commit()
        messagebox.showinfo("Sucesso", f"Categoria '{nome}' adicionada com sucesso!")
        return new_id
    except psycopg2.errors.UniqueViolation:
        messagebox.showerror("Erro", f"Categoria '{nome}' já existe.")
        if conn: conn.rollback()
        return None
    except psycopg2.Error as e:
        print(f"Erro ao inserir categoria de despesa: {e}")
        messagebox.showerror("Erro de BD", "Não foi possível adicionar a categoria.")
        if conn: conn.rollback()
        return None
    finally:
        if cur: cur.close()
        if conn: cur.close()


def atualizar_categoria_despesa(id_categoria, novo_nome):
    """Atualiza uma categoria de despesa existente."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("UPDATE categoria_despesa SET nome = %s WHERE id = %s", (novo_nome, id_categoria))
        conn.commit()
        messagebox.showinfo("Sucesso", "Categoria atualizada com sucesso!")
        return True
    except psycopg2.errors.UniqueViolation:
        messagebox.showerror("Erro", f"Categoria '{novo_nome}' já existe.")
        if conn: conn.rollback()
        return False
    except psycopg2.Error as e:
        print(f"Erro ao atualizar categoria de despesa: {e}")
        messagebox.showerror("Erro de BD", "Não foi possível atualizar a categoria.")
        if conn: conn.close()
        return False
    finally:
        if cur: cur.close()
        if conn: cur.close()


def deletar_categoria_despesa(id_categoria):
    """Deleta uma categoria de despesa."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("DELETE FROM categoria_despesa WHERE id = %s", (id_categoria,))
        conn.commit()
        messagebox.showinfo("Sucesso", "Categoria excluída com sucesso!")
        return True
    except psycopg2.errors.ForeignKeyViolation:
        messagebox.showerror("Erro", "Não é possível excluir esta categoria porque há despesas associadas a ela.")
        if conn: conn.rollback()
        return False
    except psycopg2.Error as e:
        print(f"Erro ao deletar categoria de despesa: {e}")
        messagebox.showerror("Erro de BD", "Não foi possível excluir a categoria.")
        if conn: conn.rollback()
        return False
    finally:
        if cur: cur.close()
        if conn: cur.close()


def listar_despesas(data_inicio=None, data_fim=None):
    """Lista todas as despesas, opcionalmente filtradas por data."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        sql_query = """
            SELECT d.id, d.descricao, d.valor, d.data, cd.nome as categoria_nome, d.observacoes, d.categoria_id
            FROM despesas d
            LEFT JOIN categoria_despesa cd ON d.categoria_id = cd.id
        """
        params = []
        if data_inicio and data_fim:
            sql_query += " WHERE d.data BETWEEN %s AND %s"
            params.extend([data_inicio, data_fim])
        sql_query += " ORDER BY d.data DESC, d.id DESC"
        cur.execute(sql_query, params)
        rows = cur.fetchall()
        despesas = []
        for row in rows:
            despesas.append({
                "id": row[0],
                "descricao": row[1],
                "valor": row[2],
                "data": row[3],
                "categoria_nome": row[4],
                "observacoes": row[5],
                "categoria_id": row[6]
            })
        return despesas
    except psycopg2.Error as e:
        print(f"Erro ao listar despesas: {e}")
        messagebox.showerror("Erro de BD", "Não foi possível listar as despesas.")
        return []
    finally:
        if cur: cur.close()
        if conn: cur.close()


def inserir_despesa(descricao, valor, data, categoria_id, observacoes):
    """Insere uma nova despesa."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO despesas (descricao, valor, data, categoria_id, observacoes) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (descricao, valor, data, categoria_id, observacoes)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        messagebox.showinfo("Sucesso", "Despesa adicionada com sucesso!")
        return new_id
    except psycopg2.Error as e:
        print(f"Erro ao inserir despesa: {e}")
        messagebox.showerror("Erro de BD", "Não foi possível adicionar a despesa.")
        if conn: conn.rollback()
        return None
    finally:
        if cur: cur.close()
        if conn: cur.close()


def atualizar_despesa(id_despesa, descricao, valor, data, categoria_id, observacoes):
    """Atualiza uma despesa existente."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "UPDATE despesas SET descricao = %s, valor = %s, data = %s, categoria_id = %s, observacoes = %s WHERE id = %s",
            (descricao, valor, data, categoria_id, observacoes, id_despesa)
        )
        conn.commit()
        messagebox.showinfo("Sucesso", "Despesa atualizada com sucesso!")
        return True
    except psycopg2.Error as e:
        print(f"Erro ao atualizar despesa: {e}")
        messagebox.showerror("Erro de BD", "Não foi possível atualizar a despesa.")
        if conn: conn.rollback()
        return False
    finally:
        if cur: cur.close()
        if conn: cur.close()


def deletar_despesa(id_despesa):
    """Deleta uma despesa."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("DELETE FROM despesas WHERE id = %s", (id_despesa,))
        conn.commit()
        messagebox.showinfo("Sucesso", "Despesa excluída com sucesso!")
        return True
    except psycopg2.Error as e:
        print(f"Erro ao deletar despesa: {e}")
        messagebox.showerror("Erro de BD", "Não foi possível excluir a despesa.")
        if conn: conn.rollback()
        return False
    finally:
        if cur: cur.close()
        if conn: cur.close()


def obter_receita_total(data_inicio, data_fim):
    """Obtém a receita total de pedidos concluídos em um período."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Assume que "Concluído" é o status de pedido que gera receita
        cur.execute("""
            SELECT COALESCE(SUM(total), 0)
            FROM pedidos
            WHERE status = 'Concluído' AND data_pedido BETWEEN %s AND %s;
        """, (data_inicio, data_fim))
        return cur.fetchone()[0]
    except psycopg2.Error as e:
        print(f"Erro ao obter receita total: {e}")
        return 0.0
    finally:
        if cur: cur.close()
        if conn: cur.close()


def obter_despesa_total(data_inicio, data_fim):
    """Obtém a despesa total em um período."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(SUM(valor), 0)
            FROM despesas
            WHERE data BETWEEN %s AND %s;
        """, (data_inicio, data_fim))
        return cur.fetchone()[0]
    except psycopg2.Error as e:
        print(f"Erro ao obter despesa total: {e}")
        return 0.0
    finally:
        if cur: cur.close()
        if conn: cur.close()


def obter_despesas_por_categoria(data_inicio, data_fim):
    """Obtém despesas totais por categoria em um período."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(cd.nome, 'Sem Categoria'), COALESCE(SUM(d.valor), 0)
            FROM despesas d
            LEFT JOIN categoria_despesa cd ON d.categoria_id = cd.id
            WHERE d.data BETWEEN %s AND %s
            GROUP BY COALESCE(cd.nome, 'Sem Categoria')
            ORDER BY COALESCE(cd.nome, 'Sem Categoria');
        """, (data_inicio, data_fim))
        return [{"categoria": row[0], "valor": row[1]} for row in cur.fetchall()]
    except psycopg2.Error as e:
        print(f"Erro ao obter despesas por categoria: {e}")
        return []
    finally:
        if cur: cur.close()
        if conn: cur.close()


# --- Classe do Módulo Financeiro ---

class FinanceModule(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tabview.add("Dashboard")
        self.tabview.add("Despesas")
        self.tabview.add("Relatórios")
        self.tabview.add("Categorias de Despesa")

        # Variáveis para controle de seleção de despesa
        self.selected_expense = None
        self.expense_form_mode = "add"  # "add" ou "edit"
        self.expense_table_widgets = []  # Lista para armazenar todos os widgets das linhas da tabela de despesas

        # Variáveis para controle de seleção de categoria
        self.selected_category = None
        self.category_form_mode = "add"  # "add" ou "edit"
        self.category_table_widgets = []  # Lista para armazenar todos os widgets das linhas da tabela de categorias

        # Variável para o canvas do gráfico
        self.chart_canvas = None

        # Inicializa as abas
        # Os métodos _create_tab chamam as funções que precisam ser definidas antes.
        self._create_dashboard_tab(self.tabview.tab("Dashboard"))
        self._create_expense_tab(self.tabview.tab("Despesas"))
        self._create_reports_tab(self.tabview.tab("Relatórios"))
        self._create_category_tab(self.tabview.tab("Categorias de Despesa"))

        # Selecionar a aba de Dashboard por padrão
        self.tabview.set("Dashboard")

    def _create_table_header(self, parent_frame, columns_dict):
        """Cria os rótulos de cabeçalho para uma tabela genérica."""
        col_index = 0
        for col_name, col_width in columns_dict.items():
            header_label = ctk.CTkLabel(parent_frame, text=col_name, font=ctk.CTkFont(weight="bold"))
            header_label.grid(row=0, column=col_index, padx=5, pady=5, sticky="w")
            parent_frame.grid_columnconfigure(col_index, minsize=col_width, weight=0)  # Fix width for header
            col_index += 1

    def _format_date_entry(self, event):
        """
        Formata o texto de um campo de entrada de data para DD-MM-YYYY.
        Ignora a formatação se for backspace ou delete para permitir apagar livremente.
        Avança o cursor após a inserção de um traço.
        """
        entry_widget = event.widget
        current_text = entry_widget.get()
        cursor_pos = entry_widget.index(ctk.INSERT)  # Salva a posição do cursor

        # Permite backspace e delete sem formatar imediatamente
        if event.keysym in ("BackSpace", "Delete", "Left", "Right"):  # Adicionado Left, Right para navegação
            return

        # Remove todos os caracteres não numéricos
        clean_text = "".join(filter(str.isdigit, current_text))

        formatted_text = ""
        # Limita a 8 dígitos para DDMMYYYY
        if len(clean_text) > 8:
            clean_text = clean_text[:8]

        # Flag para verificar se um traço foi inserido nesta formatação
        hyphen_inserted_at_cursor_pos = False

        # Adiciona traços automaticamente
        for i, char in enumerate(clean_text):
            formatted_text += char
            # Verifica se o cursor estava na posição onde um traço seria inserido APÓS o caractere atual
            if i == 1 and len(clean_text) > 2:  # Depois do dia (2 dígitos)
                formatted_text += "-"
                if cursor_pos == 2:
                    hyphen_inserted_at_cursor_pos = True
            elif i == 3 and len(clean_text) > 4:  # Depois do mês (4 dígitos totais)
                formatted_text += "-"
                if cursor_pos == 5:
                    hyphen_inserted_at_cursor_pos = True

        # Impede que a data digitada passe de 10 caracteres (DD-MM-YYYY)
        if len(formatted_text) > 10:
            formatted_text = formatted_text[:10]

        # Atualiza o campo se o texto formatado for diferente
        if current_text != formatted_text:
            entry_widget.delete(0, ctk.END)
            entry_widget.insert(0, formatted_text)

            # Ajusta a posição do cursor
            if hyphen_inserted_at_cursor_pos:
                entry_widget.icursor(cursor_pos + 1)
            else:
                # Se não houve inserção de hífen no ponto do cursor,
                # ou se o texto atual é menor que o anterior (remoção),
                # tenta manter a posição relativa.
                new_cursor_pos = cursor_pos
                if len(formatted_text) > len(current_text):
                    # Se o texto cresceu (traço adicionado em outro lugar ou digitação normal)
                    new_cursor_pos = cursor_pos + (len(formatted_text) - len(current_text))

                new_cursor_pos = min(new_cursor_pos, len(formatted_text))
                entry_widget.icursor(new_cursor_pos)

    # --- Métodos de Controle para Despesas (Movidos para cima) ---

    def _load_expense_categories_to_combobox(self):
        """Carrega as categorias de despesa no combobox do formulário de despesa."""
        categories = listar_categorias_despesa()
        category_names = [cat["nome"] for cat in categories]
        if "Nenhuma Categoria" not in category_names:
            category_names.insert(0, "Nenhuma Categoria")
        self.expense_category_combobox.configure(values=category_names)
        self.expense_category_combobox.set(category_names[0] if category_names else "Nenhuma Categoria")

    def _get_category_id_by_name(self, category_name):
        """Retorna o ID de uma categoria de despesa dado o seu nome."""
        categories = listar_categorias_despesa()
        for cat in categories:
            if cat["nome"] == category_name:
                return cat["id"]
        return None

    def _on_expense_row_select(self, event, expense):
        """
        Manipula a seleção de uma linha na tabela de despesas.
        Realça a linha clicada e desrealça as outras.
        """
        self.selected_expense = expense
        self.delete_expense_button.configure(state="normal")
        self.select_expense_button.configure(state="normal")

        # 1. Resetar a cor de todas as linhas de dados antes de aplicar a nova seleção
        # self.expense_table_widgets armazena listas de labels, uma lista por linha de dados
        for row_widgets_list in self.expense_table_widgets:
            for widget in row_widgets_list:
                widget.configure(fg_color="transparent")  # Volta para a cor padrão do frame/widget

        # 2. Realçar a linha clicada
        # O event.widget é o CTkLabel clicado. Precisamos encontrar todos os CTkLabels na mesma linha lógica.
        # A forma mais robusta é usar a lista de widgets que armazenamos para a linha específica.

        # Encontra a lista de widgets correspondente à despesa selecionada
        # Percorre todas as despesas carregadas e compara com a selecionada
        # (O id da despesa é único, então é uma boa chave)
        # Note: A maneira como os widgets são armazenados em self.expense_table_widgets
        # é indexada pela ordem em que são populados. Podemos encontrar a linha pelo ID da despesa.

        # Para ser mais direto, como event.widget já é um label da linha:
        # Pega a linha (row) onde o label clicado está
        clicked_row_grid_row = event.widget.grid_info()['row']

        # Encontra o conjunto de widgets que corresponde a essa linha no self.expense_table_widgets
        # A linha 0 é o cabeçalho. As linhas de dados começam de 1.
        # Portanto, o índice na lista self.expense_table_widgets é (clicked_row_grid_row - 1)
        if 0 < clicked_row_grid_row <= len(self.expense_table_widgets):
            widgets_in_clicked_row = self.expense_table_widgets[clicked_row_grid_row - 1]
            for widget in widgets_in_clicked_row:
                if isinstance(widget, ctk.CTkLabel):  # Garante que estamos configurando apenas labels de dados
                    widget.configure(
                        fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])  # Cor de destaque do botão

    def _reset_expense_form(self):
        """Reseta o formulário de despesas e o estado dos botões."""
        self.expense_form_mode = "add"
        self.selected_expense = None
        self.expense_desc_entry.delete(0, ctk.END)
        self.expense_value_entry.delete(0, ctk.END)
        self.expense_date_entry.delete(0, ctk.END)
        self.expense_date_entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self.expense_obs_entry.delete(0, ctk.END)
        self._load_expense_categories_to_combobox()  # Recarrega e seta o padrão

        self.add_expense_button.configure(text="Adicionar Despesa", state="normal")
        self.edit_expense_button.configure(state="disabled")
        self.delete_expense_button.configure(state="disabled")
        self.cancel_expense_edit_button.configure(state="disabled")
        self.select_expense_button.configure(state="disabled")

        # Ao resetar o formulário, também remove qualquer realce da tabela
        for row_widgets_list in self.expense_table_widgets:
            for widget in row_widgets_list:
                widget.configure(fg_color="transparent")

    def _populate_expense_table(self):
        """Popula a tabela de despesas com dados do banco de dados, aplicando filtros de data."""
        # Limpa todos os widgets de linhas existentes na tabela
        for widget_set in self.expense_table_widgets:
            for widget in widget_set:
                widget.destroy()
        self.expense_table_widgets.clear()

        # Reseta o formulário e a seleção antes de popular a tabela
        # Isso garante que a UI reflete o estado inicial quando a tabela é recarregada
        self._reset_expense_form()

        start_date_str = self.expense_filter_start_date_entry.get()
        end_date_str = self.expense_filter_end_date_entry.get()

        try:
            # Converte de DD-MM-YYYY para o formato aceito pelo banco (YYYY-MM-DD)
            start_date = datetime.strptime(start_date_str, "%d-%m-%Y").date()
            end_date = datetime.strptime(end_date_str, "%d-%m-%Y").date()
        except ValueError:
            messagebox.showerror("Erro de Data", "Formato de data inválido para o filtro. Use DD-MM-YYYY.")
            return

        despesas = listar_despesas(start_date, end_date)

        for i, expense in enumerate(despesas):
            row_widgets = []
            col_index = 0
            # Adiciona uma coluna oculta para o índice da linha, se precisar no futuro, mas não para exibição
            # Usamos i+1 porque a primeira linha (row=0) é o cabeçalho
            for key in ["id", "descricao", "valor", "data", "categoria_nome", "observacoes"]:
                value = expense.get(key)
                if key == "valor":
                    value = f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                elif key == "data":
                    value = value.strftime("%d-%m-%Y")

                label = ctk.CTkLabel(self.expense_table, text=str(value), anchor="w")
                label.grid(row=i + 1, column=col_index, padx=5, pady=2, sticky="ew")
                # Vincula o evento de clique a cada label na linha
                label.bind("<Button-1>", lambda event, exp=expense: self._on_expense_row_select(event, exp))
                row_widgets.append(label)
                col_index += 1
            self.expense_table_widgets.append(row_widgets)

        if not despesas:
            no_data_label = ctk.CTkLabel(self.expense_table, text="Nenhuma despesa encontrada para o período.",
                                         anchor="center")
            no_data_label.grid(row=1, column=0, columnspan=len(self.expense_table_columns), padx=5, pady=20)
            self.expense_table_widgets.append([no_data_label])

    def _add_or_update_expense(self):
        """Adiciona uma nova despesa ou atualiza uma existente."""
        desc = self.expense_desc_entry.get()
        valor_str = self.expense_value_entry.get().replace(",", ".")
        data_str = self.expense_date_entry.get()
        categoria_nome = self.expense_category_combobox.get()
        obs = self.expense_obs_entry.get()

        if not desc or not valor_str or not data_str or not categoria_nome:
            messagebox.showerror("Erro", "Descrição, Valor, Data e Categoria são campos obrigatórios.")
            return

        try:
            # Converte de DD-MM-YYYY para o formato aceito pelo banco (YYYY-MM-DD)
            valor = float(valor_str)
            data = datetime.strptime(data_str, "%d-%m-%Y").date()
        except ValueError:
            messagebox.showerror("Erro",
                                 "Valor ou Data em formato inválido. Valor deve ser numérico e Data em DD-MM-YYYY.")
            return

        categoria_id = self._get_category_id_by_name(categoria_nome)
        if categoria_id is None and categoria_nome != "Nenhuma Categoria":
            messagebox.showerror("Erro", f"Categoria '{categoria_nome}' não encontrada.")
            return
        elif categoria_nome == "Nenhuma Categoria":
            categoria_id = None

        if self.expense_form_mode == "add":
            if inserir_despesa(desc, valor, data, categoria_id, obs):
                self._populate_expense_table()
                self._update_dashboard_metrics()
        elif self.expense_form_mode == "edit":
            if self.selected_expense:
                if atualizar_despesa(self.selected_expense["id"], desc, valor, data, categoria_id, obs):
                    self._populate_expense_table()
                    self._update_dashboard_metrics()
            else:
                messagebox.showerror("Erro", "Nenhuma despesa selecionada para edição.")

    def _set_edit_mode_expense(self):
        """Define o formulário de despesas para o modo de edição com a despesa selecionada."""
        if self.selected_expense:
            self.expense_form_mode = "edit"
            self.expense_desc_entry.delete(0, ctk.END)
            self.expense_desc_entry.insert(0, self.selected_expense["descricao"])
            self.expense_value_entry.delete(0, ctk.END)
            self.expense_value_entry.insert(0, str(self.selected_expense["valor"]))
            self.expense_date_entry.delete(0, ctk.END)
            self.expense_date_entry.insert(0, self.selected_expense["data"].strftime("%d-%m-%Y"))
            self.expense_category_combobox.set(self.selected_expense["categoria_nome"] or "Nenhuma Categoria")
            self.expense_obs_entry.delete(0, ctk.END)
            self.expense_obs_entry.insert(0, self.selected_expense["observacoes"] or "")

            self.add_expense_button.configure(text="Atualizar Despesa", state="normal")  # Habilita para atualizar
            self.edit_expense_button.configure(state="disabled")
            self.delete_expense_button.configure(state="disabled")
            self.cancel_expense_edit_button.configure(state="normal")
            self.select_expense_button.configure(state="disabled")
        else:
            messagebox.showwarning("Aviso", "Nenhuma despesa selecionada para editar.")

    def _select_expense_for_edit(self):
        """Função auxiliar para acionar o modo de edição após seleção na tabela."""
        self._set_edit_mode_expense()

    def _delete_selected_expense(self):
        """Exclui a despesa atualmente selecionada."""
        if self.selected_expense:
            if messagebox.askyesno("Confirmar Exclusão",
                                   f"Tem certeza que deseja excluir a despesa: {self.selected_expense['descricao']}?"):
                if deletar_despesa(self.selected_expense["id"]):
                    self._populate_expense_table()
                    self._update_dashboard_metrics()
        else:
            messagebox.showwarning("Aviso", "Nenhuma despesa selecionada para excluir.")

    # --- Métodos de Controle para Categorias de Despesa (Movidos para cima) ---

    def _populate_category_table(self):
        """Popula a tabela de categorias de despesa."""
        for widget_set in self.category_table_widgets:
            for widget in widget_set:
                widget.destroy()
        self.category_table_widgets.clear()

        # Reseta o formulário e a seleção antes de popular a tabela
        self.selected_category = None
        self._reset_category_form()

        categories = listar_categorias_despesa()

        for i, category in enumerate(categories):
            row_widgets = []
            col_index = 0
            for key in ["id", "nome"]:
                value = category.get(key)
                label = ctk.CTkLabel(self.category_table, text=str(value), anchor="w")
                label.grid(row=i + 1, column=col_index, padx=5, pady=2, sticky="ew")
                label.bind("<Button-1>", lambda event, cat=category: self._on_category_row_select(event, cat))
                row_widgets.append(label)
                col_index += 1
            self.category_table_widgets.append(row_widgets)

        if not categories:
            no_data_label = ctk.CTkLabel(self.category_table, text="Nenhuma categoria encontrada.", anchor="center")
            no_data_label.grid(row=1, column=0, columnspan=len(self.category_table_columns_def), padx=5, pady=20)
            self.category_table_widgets.append([no_data_label])

    def _on_category_row_select(self, event, category):
        """
        Manipula a seleção de uma linha na tabela de categorias.
        Realça a linha clicada e desrealça as outras.
        """
        self.selected_category = category
        self.delete_category_button.configure(state="normal")
        self.select_category_button.configure(state="normal")

        for row_widgets_list in self.category_table_widgets:
            for widget in row_widgets_list:
                widget.configure(fg_color="transparent")

        # Pega a linha (row) onde o label clicado está
        clicked_row_grid_row = event.widget.grid_info()['row']

        # Encontra o conjunto de widgets que corresponde a essa linha no self.category_table_widgets
        # A linha 0 é o cabeçalho. As linhas de dados começam de 1.
        # Portanto, o índice na lista self.category_table_widgets é (clicked_row_grid_row - 1)
        if 0 < clicked_row_grid_row <= len(self.category_table_widgets):
            widgets_in_clicked_row = self.category_table_widgets[clicked_row_grid_row - 1]
            for widget in widgets_in_clicked_row:
                if isinstance(widget, ctk.CTkLabel):
                    widget.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])

    def _add_or_update_category(self):
        """Adiciona uma nova categoria ou atualiza uma existente."""
        nome = self.category_name_entry.get().strip()
        if not nome:
            messagebox.showerror("Erro", "O nome da categoria é obrigatório.")
            return

        if self.category_form_mode == "add":
            if inserir_categoria_despesa(nome):
                self._populate_category_table()
                self._load_expense_categories_to_combobox()  # Atualiza combobox de despesas
        elif self.category_form_mode == "edit":
            if self.selected_category:
                if atualizar_categoria_despesa(self.selected_category["id"], nome):
                    self._populate_category_table()
                    self._load_expense_categories_to_combobox()  # Atualiza combobox de despesas
            else:
                messagebox.showerror("Erro", "Nenhuma categoria selecionada para edição.")

    def _set_edit_mode_category(self):
        """Define o formulário de categorias para o modo de edição com a categoria selecionada."""
        if self.selected_category:
            self.category_form_mode = "edit"
            self.category_name_entry.delete(0, ctk.END)
            self.category_name_entry.insert(0, self.selected_category["nome"])

            self.add_category_button.configure(text="Atualizar Categoria", state="normal")  # Habilita para atualizar
            self.edit_category_button.configure(state="disabled")
            self.delete_category_button.configure(state="disabled")
            self.cancel_category_edit_button.configure(state="normal")
            self.select_category_button.configure(state="disabled")
        else:
            messagebox.showwarning("Aviso", "Nenhuma categoria selecionada para editar.")

    def _reset_category_form(self):
        """Reseta o formulário de categorias e o estado dos botões."""
        self.category_form_mode = "add"
        self.selected_category = None
        self.category_name_entry.delete(0, ctk.END)

        self.add_category_button.configure(text="Adicionar Categoria", state="normal")
        self.edit_category_button.configure(state="disabled")
        self.delete_category_button.configure(state="disabled")
        self.cancel_category_edit_button.configure(state="disabled")
        self.select_category_button.configure(state="disabled")

        # Ao resetar o formulário, também remove qualquer realce da tabela
        for row_widgets_list in self.category_table_widgets:
            for widget in row_widgets_list:
                widget.configure(fg_color="transparent")

    def _select_category_for_edit(self):
        """Função auxiliar para acionar o modo de edição de categoria após seleção na tabela."""
        self._set_edit_mode_category()

    def _delete_selected_category(self):
        """Exclui a categoria atualmente selecionada."""
        if self.selected_category:
            if messagebox.askyesno("Confirmar Exclusão",
                                   f"Tem certeza que deseja excluir a categoria: {self.selected_category['nome']}?\n\nIsso definirá 'NULO' para despesas associadas."):
                if deletar_categoria_despesa(self.selected_category["id"]):
                    self._populate_category_table()
                    self._load_expense_categories_to_combobox()  # Atualiza combobox de despesas
                    self._populate_expense_table()  # Atualiza tabela de despesas após mudança na categoria
        else:
            messagebox.showwarning("Aviso", "Nenhuma categoria selecionada para excluir.")

    # --- Métodos de Criação de Abas (Agora podem chamar os métodos de controle) ---

    def _create_dashboard_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)  # Row for graphs/details

        title_label = ctk.CTkLabel(tab, text="Dashboard Financeiro", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Frame para seleção de período
        period_frame = ctk.CTkFrame(tab)
        period_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        period_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(period_frame, text="De:").grid(row=0, column=0, padx=(0, 5), pady=5)
        self.dashboard_start_date_entry = ctk.CTkEntry(period_frame, placeholder_text="DD-MM-YYYY")
        self.dashboard_start_date_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.dashboard_start_date_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime("%d-%m-%Y"))
        self.dashboard_start_date_entry.bind("<KeyRelease>", self._format_date_entry)  # Vínculo do evento

        ctk.CTkLabel(period_frame, text="Até:").grid(row=0, column=2, padx=(0, 5), pady=5)
        self.dashboard_end_date_entry = ctk.CTkEntry(period_frame, placeholder_text="DD-MM-YYYY")
        self.dashboard_end_date_entry.grid(row=0, column=3, padx=(0, 10), pady=5, sticky="ew")
        self.dashboard_end_date_entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self.dashboard_end_date_entry.bind("<KeyRelease>", self._format_date_entry)  # Vínculo do evento

        update_button = ctk.CTkButton(period_frame, text="Atualizar Dashboard", command=self._update_dashboard_metrics)
        update_button.grid(row=0, column=4, padx=(10, 0), pady=5)

        # Frame para as métricas principais como Cards
        metrics_cards_frame = ctk.CTkFrame(tab, fg_color="transparent")
        metrics_cards_frame.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        metrics_cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Card de Receita
        revenue_card = ctk.CTkFrame(metrics_cards_frame)
        revenue_card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        revenue_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(revenue_card, text="Receita Total", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0,
                                                                                                        pady=(10, 5))
        self.revenue_label = ctk.CTkLabel(revenue_card, text="R$ 0.00", font=ctk.CTkFont(size=22, weight="bold"))
        self.revenue_label.grid(row=1, column=0, pady=(0, 10))

        # Card de Despesa
        expense_card = ctk.CTkFrame(metrics_cards_frame)
        expense_card.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        expense_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(expense_card, text="Despesa Total", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0,
                                                                                                        pady=(10, 5))
        self.expense_label = ctk.CTkLabel(expense_card, text="R$ 0.00", font=ctk.CTkFont(size=22, weight="bold"))
        self.expense_label.grid(row=1, column=0, pady=(0, 10))

        # Card de Lucro Líquido
        profit_card = ctk.CTkFrame(metrics_cards_frame)
        profit_card.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        profit_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(profit_card, text="Lucro Líquido", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0,
                                                                                                       pady=(10, 5))
        self.profit_label = ctk.CTkLabel(profit_card, text="R$ 0.00", font=ctk.CTkFont(size=22, weight="bold"))
        self.profit_label.grid(row=1, column=0, pady=(0, 10))

        # Frame para o Gráfico de Despesas por Categoria
        self.chart_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.chart_frame.grid(row=3, column=0, padx=20, pady=20, sticky="nsew")
        self.chart_frame.grid_columnconfigure(0, weight=1)
        self.chart_frame.grid_rowconfigure(0, weight=1)

        # Placeholder ou mensagem de erro para o gráfico
        if not MATPLOTLIB_AVAILABLE:
            chart_message = "A biblioteca 'matplotlib' não está instalada. Gráfico não disponível."
        else:
            chart_message = "Carregando gráfico..."

        self.chart_message_label = ctk.CTkLabel(self.chart_frame, text=chart_message,
                                                font=ctk.CTkFont(size=14), wraplength=400, justify="center")
        self.chart_message_label.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self._update_dashboard_metrics()  # Initial load

    def _update_dashboard_metrics(self):
        """Atualiza as métricas e possivelmente os gráficos no dashboard."""
        start_date_str = self.dashboard_start_date_entry.get()
        end_date_str = self.dashboard_end_date_entry.get()

        try:
            # Converte de DD-MM-YYYY para o formato aceito pelo banco (YYYY-MM-DD)
            start_date = datetime.strptime(start_date_str, "%d-%m-%Y").date()
            end_date = datetime.strptime(end_date_str, "%d-%m-%Y").date()
        except ValueError:
            messagebox.showerror("Erro de Data", "Formato de data inválido. Use DD-MM-YYYY.")
            return

        total_revenue = obter_receita_total(start_date, end_date)
        total_expense = obter_despesa_total(start_date, end_date)
        net_profit = total_revenue - total_expense

        # Atualiza os labels dos cards
        self.revenue_label.configure(
            text=f"R$ {total_revenue:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.expense_label.configure(
            text=f"R$ {total_expense:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.profit_label.configure(text=f"R$ {net_profit:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # Atualiza o gráfico
        self._plot_expenses_by_category(start_date, end_date)

    def _get_ctk_color_for_matplotlib(self, ctk_color_value, current_theme):
        """
        Adapta o valor de cor do CustomTkinter para um formato compatível com Matplotlib.
        CustomTkinter pode retornar uma string simples ou uma tupla (light_color, dark_color).
        """
        if isinstance(ctk_color_value, tuple):
            return ctk_color_value[1] if current_theme == "Dark" else ctk_color_value[0]
        elif isinstance(ctk_color_value, str):
            # Se for uma string, tenta usá-la diretamente. Matplotlib é robusto com nomes de cores e hex.
            return ctk_color_value
        return "gray"  # Fallback color

    def _plot_expenses_by_category(self, start_date, end_date):
        """Gera e exibe um gráfico de barras das despesas por categoria."""
        # Limpa o gráfico anterior, se houver
        if self.chart_canvas:
            self.chart_canvas.get_tk_widget().destroy()
            self.chart_canvas = None
            plt.close('all')  # Fecha todas as figuras matplotlib para evitar vazamento de memória

        if not MATPLOTLIB_AVAILABLE:
            self.chart_message_label.configure(
                text="A biblioteca 'matplotlib' não está instalada. Gráfico não disponível.")
            return

        self.chart_message_label.configure(text="Gerando gráfico...")

        expenses_data = obter_despesas_por_categoria(start_date, end_date)

        if not expenses_data:
            self.chart_message_label.configure(
                text="Nenhuma despesa para exibir no gráfico para o período selecionado.")
            return

        categories = [item["categoria"] for item in expenses_data]
        values = [item["valor"] for item in expenses_data]

        # Cria a figura e o eixo do gráfico
        fig, ax = plt.subplots(figsize=(8, 5))  # Ajuste o tamanho da figura conforme necessário

        # Define o tema do Matplotlib para combinar com o CustomTkinter (aproximado)
        current_theme = ctk.get_appearance_mode()  # "Light" ou "Dark"

        # Usando a nova função auxiliar para obter cores compatíveis
        bg_color = self._get_ctk_color_for_matplotlib(ctk.ThemeManager.theme["CTkFrame"]["fg_color"], current_theme)
        text_color = self._get_ctk_color_for_matplotlib(ctk.ThemeManager.theme["CTkLabel"]["text_color"], current_theme)
        bar_color = self._get_ctk_color_for_matplotlib(ctk.ThemeManager.theme["CTkButton"]["fg_color"], current_theme)

        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        ax.tick_params(axis='x', colors=text_color)
        ax.tick_params(axis='y', colors=text_color)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color(text_color)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['top'].set_color(text_color)
        ax.spines['right'].set_color(text_color)
        ax.spines['left'].set_color(text_color)

        bars = ax.bar(categories, values, color=bar_color)  # Cor das barras

        ax.set_title(f"Despesas por Categoria ({start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')})",
                     fontsize=14)
        ax.set_xlabel("Categoria", fontsize=12)
        ax.set_ylabel("Valor (R$)", fontsize=12)
        plt.xticks(rotation=45, ha='right')  # Rotaciona os rótulos do eixo X para melhor legibilidade
        plt.tight_layout()  # Ajusta o layout para evitar sobreposição

        # Incorpora o gráfico no CustomTkinter
        self.chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.chart_canvas_widget = self.chart_canvas.get_tk_widget()
        self.chart_canvas_widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chart_canvas.draw()
        self.chart_message_label.configure(text="")  # Limpa a mensagem de carregamento

    def _create_expense_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Frame de formulário para adicionar/editar despesa
        self.expense_form_frame = ctk.CTkFrame(tab)
        self.expense_form_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.expense_form_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.expense_form_frame, text="Descrição:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.expense_desc_entry = ctk.CTkEntry(self.expense_form_frame, placeholder_text="Descrição da despesa")
        self.expense_desc_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(self.expense_form_frame, text="Valor:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.expense_value_entry = ctk.CTkEntry(self.expense_form_frame, placeholder_text="0.00")
        self.expense_value_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(self.expense_form_frame, text="Data (DD-MM-YYYY):").grid(row=2, column=0, padx=5, pady=5,
                                                                              sticky="w")
        self.expense_date_entry = ctk.CTkEntry(self.expense_form_frame,
                                               placeholder_text=datetime.now().strftime("%d-%m-%Y"))
        self.expense_date_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.expense_date_entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self.expense_date_entry.bind("<KeyRelease>", self._format_date_entry)  # Vínculo do evento

        ctk.CTkLabel(self.expense_form_frame, text="Categoria:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.expense_category_combobox = ctk.CTkComboBox(self.expense_form_frame, values=["Carregando..."])
        self.expense_category_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        # _load_expense_categories_to_combobox será chamado no reset do formulário/população da tabela

        ctk.CTkLabel(self.expense_form_frame, text="Observações:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.expense_obs_entry = ctk.CTkEntry(self.expense_form_frame, placeholder_text="Observações (opcional)")
        self.expense_obs_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        button_frame = ctk.CTkFrame(self.expense_form_frame, fg_color="transparent")
        button_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=10)
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.add_expense_button = ctk.CTkButton(button_frame, text="Adicionar Despesa",
                                                command=self._add_or_update_expense)
        self.add_expense_button.grid(row=0, column=0, padx=5)

        self.edit_expense_button = ctk.CTkButton(button_frame, text="Editar Despesa",
                                                 command=self._set_edit_mode_expense, state="disabled")
        self.edit_expense_button.grid(row=0, column=1, padx=5)

        self.cancel_expense_edit_button = ctk.CTkButton(button_frame, text="Cancelar Edição",
                                                        command=self._reset_expense_form, state="disabled")
        self.cancel_expense_edit_button.grid(row=0, column=2, padx=5)

        # Frame da tabela de despesas
        self.expense_table_frame = ctk.CTkFrame(tab)
        self.expense_table_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.expense_table_frame.grid_columnconfigure(0, weight=1)
        self.expense_table_frame.grid_rowconfigure(1, weight=1)

        # Filtro de data para a tabela de despesas
        filter_frame = ctk.CTkFrame(self.expense_table_frame)
        filter_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        filter_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(filter_frame, text="Filtrar por Data: De").grid(row=0, column=0, padx=(0, 5), pady=5)
        self.expense_filter_start_date_entry = ctk.CTkEntry(filter_frame, placeholder_text="DD-MM-YYYY")
        self.expense_filter_start_date_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.expense_filter_start_date_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime("%d-%m-%Y"))
        self.expense_filter_start_date_entry.bind("<KeyRelease>", self._format_date_entry)  # Vínculo do evento

        ctk.CTkLabel(filter_frame, text="Até").grid(row=0, column=2, padx=(0, 5), pady=5)
        self.expense_filter_end_date_entry = ctk.CTkEntry(filter_frame, placeholder_text="DD-MM-YYYY")
        self.expense_filter_end_date_entry.grid(row=0, column=3, padx=(0, 10), pady=5, sticky="ew")
        self.expense_filter_end_date_entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self.expense_filter_end_date_entry.bind("<KeyRelease>", self._format_date_entry)  # Vínculo do evento

        filter_button = ctk.CTkButton(filter_frame, text="Filtrar Despesas", command=self._populate_expense_table)
        filter_button.grid(row=0, column=4, padx=(10, 0), pady=5)

        # Tabela (Treeview) para exibir despesas
        self.expense_table = ctk.CTkScrollableFrame(self.expense_table_frame, height=300)
        self.expense_table.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.expense_table_columns = {
            "ID": 50,
            "Descrição": 250,
            "Valor": 100,
            "Data": 120,
            "Categoria": 150,
            "Observações": 200
        }
        self._create_table_header(self.expense_table, self.expense_table_columns)

        # Botões de ação da tabela (garantido que existem antes de _populate_expense_table)
        action_button_frame = ctk.CTkFrame(self.expense_table_frame, fg_color="transparent")
        action_button_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        action_button_frame.grid_columnconfigure((0, 1), weight=1)

        self.delete_expense_button = ctk.CTkButton(action_button_frame, text="Excluir Despesa",
                                                   command=self._delete_selected_expense, state="disabled")
        self.delete_expense_button.grid(row=0, column=0, padx=5, sticky="e")

        self.select_expense_button = ctk.CTkButton(action_button_frame, text="Selecionar para Editar",
                                                   command=self._select_expense_for_edit, state="disabled")
        self.select_expense_button.grid(row=0, column=1, padx=5, sticky="w")

        self._populate_expense_table()  # Popula a tabela após a criação dos widgets

    def _create_reports_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(tab, text="Relatórios Financeiros", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Frame de seleção de período para relatórios
        period_frame = ctk.CTkFrame(tab)
        period_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        period_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        ctk.CTkLabel(period_frame, text="Relatório:").grid(row=0, column=0, padx=(0, 5), pady=5)
        self.report_type_combobox = ctk.CTkComboBox(period_frame, values=["Demonstrativo de Resultado (P&L)",
                                                                          "Despesas por Categoria"])
        self.report_type_combobox.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.report_type_combobox.set("Demonstrativo de Resultado (P&L)")

        ctk.CTkLabel(period_frame, text="De:").grid(row=1, column=0, padx=(0, 5), pady=5)
        self.report_start_date_entry = ctk.CTkEntry(period_frame, placeholder_text="DD-MM-YYYY")
        self.report_start_date_entry.grid(row=1, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.report_start_date_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime("%d-%m-%Y"))
        self.report_start_date_entry.bind("<KeyRelease>", self._format_date_entry)  # Vínculo do evento

        ctk.CTkLabel(period_frame, text="Até:").grid(row=1, column=2, padx=(0, 5), pady=5)
        self.report_end_date_entry = ctk.CTkEntry(period_frame, placeholder_text="DD-MM-YYYY")
        self.report_end_date_entry.grid(row=1, column=3, padx=(0, 10), pady=5, sticky="ew")
        self.report_end_date_entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self.report_end_date_entry.bind("<KeyRelease>", self._format_date_entry)  # Vínculo do evento

        generate_button = ctk.CTkButton(period_frame, text="Gerar Relatório", command=self._generate_report)
        generate_button.grid(row=0, column=4, rowspan=2, padx=(10, 0), pady=5, sticky="ns")

        # Frame para exibir o relatório gerado
        self.report_display_frame = ctk.CTkScrollableFrame(tab)
        self.report_display_frame.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        self.report_display_frame.grid_columnconfigure(0, weight=1)

        self.report_text_area = ctk.CTkLabel(self.report_display_frame,
                                             text="Selecione um tipo de relatório e um período para gerar.",
                                             font=ctk.CTkFont(size=14), wraplength=700, justify="left", anchor="nw")
        self.report_text_area.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Botão para exportar PDF
        self.export_pdf_button = ctk.CTkButton(tab, text="Exportar para PDF", command=self._export_report_to_pdf)
        self.export_pdf_button.grid(row=3, column=0, padx=20, pady=10, sticky="e")
        if FPDF is None:  # Disable if fpdf is not installed
            self.export_pdf_button.configure(state="disabled", text="Exportar para PDF (fpdf não instalado)")

    def _generate_report(self):
        """Gera o conteúdo do relatório financeiro com base no tipo e período selecionados."""
        report_type = self.report_type_combobox.get()
        start_date_str = self.report_start_date_entry.get()
        end_date_str = self.report_end_date_entry.get()

        try:
            # Converte de DD-MM-YYYY para o formato aceito pelo banco (YYYY-MM-DD)
            start_date = datetime.strptime(start_date_str, "%d-%m-%Y").date()
            end_date = datetime.strptime(end_date_str, "%d-%m-%Y").date()
        except ValueError:
            messagebox.showerror("Erro de Data", "Formato de data inválido. Use DD-MM-YYYY.")
            self.report_text_area.configure(text="Erro: Formato de data inválido.")
            return

        report_content = ""
        if report_type == "Demonstrativo de Resultado (P&L)":
            revenue = obter_receita_total(start_date, end_date)
            expenses = obter_despesa_total(start_date, end_date)
            profit = revenue - expenses

            report_content = (f"DEMONSTRATIVO DE RESULTADO (P&L)\n"
                              f"Período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}\n\n"
                              f"RECEITAS:\n"
                              f"  Vendas de Pedidos: R$ {revenue:,.2f}\n\n"
                              f"DESPESAS:\n"
                              f"  Despesas Operacionais: R$ {expenses:,.2f}\n\n"
                              f"LUCRO LÍQUIDO:\n"
                              f"  Total: R$ {profit:,.2f}\n\n"
                              f"{'Parabéns! Resultados positivos.' if profit >= 0 else 'Atenção: Resultado negativo.'}")
        elif report_type == "Despesas por Categoria":
            expenses_by_category = obter_despesas_por_categoria(start_date, end_date)
            report_content = (f"RELATÓRIO DE DESPESAS POR CATEGORIA\n"
                              f"Período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}\n\n"
                              f"DETALHES DAS DESPESAS:\n")
            if expenses_by_category:
                for item in expenses_by_category:
                    report_content += f"  {item['categoria']}: R$ {item['valor']:,.2f}\n"
            else:
                report_content += "  Nenhuma despesa encontrada para as categorias no período.\n"

        # Formata os números no texto do relatório para o padrão brasileiro (virgula como decimal)
        self.report_text_area.configure(text=report_content.replace(",", "X").replace(".", ",").replace("X", "."))

    def _export_report_to_pdf(self):
        """Exporta o relatório financeiro atual para um arquivo PDF."""
        if FPDF is None:
            messagebox.showerror("Erro",
                                 "A biblioteca 'fpdf' não está instalada. A geração de PDF não está disponível.")
            return

        report_content = self.report_text_area.cget("text")
        if "Selecione um tipo de relatório" in report_content or not report_content.strip():
            messagebox.showwarning("Aviso", "Nenhum relatório gerado para exportar.")
            return

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Adicionar cabeçalho personalizado
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Fogueiro Burger - Relatório Financeiro", 0, 1, "C")
        pdf.set_font("Arial", "", 12)
        pdf.ln(10)  # Quebra de linha

        # Quebrar o texto do relatório em linhas e adicionar ao PDF
        lines = report_content.split('\n')
        for line in lines:
            # Codifica para latin-1 e decodifica para latin-1 para lidar com caracteres especiais
            # que podem não ser padrão em Arial sem fontes adicionais.
            pdf.multi_cell(0, 8, line.encode('latin-1', 'replace').decode('latin-1'))

        # Obter o diretório de trabalho atual do script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "relatorios_financeiros")
        os.makedirs(output_dir, exist_ok=True)

        filename_base = "relatorio_financeiro_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".pdf"
        output_path = os.path.join(output_dir, filename_base)

        try:
            pdf.output(output_path)
            messagebox.showinfo("Sucesso", f"Relatório exportado para:\n{output_path}")

            # Abrir o PDF automaticamente após a exportação
            if platform.system() == "Windows":
                os.startfile(output_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", output_path])
            else:  # Linux
                subprocess.call(["xdg-open", output_path])

        except Exception as e:
            messagebox.showerror("Erro de Exportação", f"Não foi possível exportar o relatório para PDF: {e}")

    def _create_category_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Frame de formulário para adicionar/editar categoria
        self.category_form_frame = ctk.CTkFrame(tab)
        self.category_form_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.category_form_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.category_form_frame, text="Nome da Categoria:").grid(row=0, column=0, padx=5, pady=5,
                                                                               sticky="w")
        self.category_name_entry = ctk.CTkEntry(self.category_form_frame, placeholder_text="Ex: Ingredientes, Salários")
        self.category_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        button_frame = ctk.CTkFrame(self.category_form_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=10)
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.add_category_button = ctk.CTkButton(button_frame, text="Adicionar Categoria",
                                                 command=self._add_or_update_category)
        self.add_category_button.grid(row=0, column=0, padx=5)

        self.edit_category_button = ctk.CTkButton(button_frame, text="Editar Categoria",
                                                  command=self._set_edit_mode_category, state="disabled")
        self.edit_category_button.grid(row=0, column=1, padx=5)

        self.cancel_category_edit_button = ctk.CTkButton(button_frame, text="Cancelar Edição",
                                                         command=self._reset_category_form, state="disabled")
        self.cancel_category_edit_button.grid(row=0, column=2, padx=5)

        # Frame da tabela de categorias
        self.category_table_frame = ctk.CTkFrame(tab)
        self.category_table_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.category_table_frame.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)  # Ajuste para que a tabela expanda verticalmente

        self.category_table = ctk.CTkScrollableFrame(self.category_table_frame)
        self.category_table.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.category_table_columns_def = {"ID": 50, "Nome da Categoria": 200}
        self._create_table_header(self.category_table, self.category_table_columns_def)
        self.category_table_widgets = []

        # Botões de ação da tabela de categorias
        category_action_button_frame = ctk.CTkFrame(self.category_table_frame, fg_color="transparent")
        category_action_button_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        category_action_button_frame.grid_columnconfigure((0, 1), weight=1)

        self.delete_category_button = ctk.CTkButton(category_action_button_frame, text="Excluir Categoria",
                                                    command=self._delete_selected_category, state="disabled")
        self.delete_category_button.grid(row=0, column=0, padx=5, sticky="e")

        self.select_category_button = ctk.CTkButton(category_action_button_frame, text="Selecionar para Editar",
                                                    command=self._select_category_for_edit, state="disabled")
        self.select_category_button.grid(row=0, column=1, padx=5, sticky="w")

        self._populate_category_table()  # Popula a tabela após a criação dos widgets


# Para teste standalone (opcional, pode ser removido no projeto final)
if __name__ == "__main__":
    # Certifique-se que db_config.py está configurado para um DB de teste
    # e que as tabelas financeiras foram criadas (execute main_system.py uma vez)
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Teste do Módulo Financeiro")
    app.geometry("1200x800")
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    finance_module = FinanceModule(app)
    finance_module.grid(row=0, column=0, sticky="nsew")

    app.mainloop()

