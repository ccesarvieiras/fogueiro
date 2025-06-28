import customtkinter as ctk
import os
import sys
from PIL import Image
import importlib
import psycopg2
from tkinter import messagebox
from psycopg2 import sql
import subprocess
from datetime import datetime

# Importar configurações do banco de dados de um arquivo externo
from db_config import DB_CONFIG

# Importar os módulos do sistema
from login import LoginWindow
from clients_module import ClientsModule
from products_module import ProductsModule
from employees_module import EmployeesModule
from orders_module import OrdersModule
from inventory_module import InventoryModule
from delivery_module import DeliveryModule
from reports_module import ReportsModule
from cadastros_module import CadastrosModule
from relatorio_module import CustomReportsModule
from finance_module import FinanceModule # <-- NOVA IMPORTAÇÃO


# --- Funções de Banco de Dados para Parâmetros e Criação de Tabelas Essenciais ---

def _verificar_e_criar_tabelas_essenciais():
    """
    Verifica se as tabelas e colunas essenciais do sistema existem no banco de dados.
    Se não existirem, as cria com valores padrão.
    Garanti que o registro de parâmetros com id=1 exista.
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # --- Criação da Tabela 'parametros' e suas colunas ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS parametros (
                id SERIAL PRIMARY KEY,
                modo_visualizacao VARCHAR(1) DEFAULT 'S', -- 'E'=Escuro, 'C'=Claro, 'S'=Sistema
                cor_acentuacao VARCHAR(20) DEFAULT 'blue',
                escala_fonte DECIMAL(3,2) DEFAULT 1.0,
                densidade_ui VARCHAR(10) DEFAULT 'Normal'
            );
        """)
        conn.commit()

        # Adicionar colunas se não existirem (para retrocompatibilidade)
        col_checks = {
            'cor_acentuacao': "VARCHAR(20) DEFAULT 'blue'",
            'escala_fonte': "DECIMAL(3,2) DEFAULT 1.0",
            'densidade_ui': "VARCHAR(10) DEFAULT 'Normal'",
            'modo_visualizacao': "VARCHAR(1) DEFAULT 'S'" # Adicionando verificação para modo_visualizacao também
        }
        for col, definition in col_checks.items():
            try:
                cur.execute(sql.SQL(f"ALTER TABLE parametros ADD COLUMN IF NOT EXISTS {col} {definition};"))
                conn.commit()
                print(f"Coluna '{col}' verificada/criada com sucesso na tabela 'parametros'.")
            except psycopg2.Error as e:
                conn.rollback()
                print(f"Erro ao adicionar coluna '{col}' à tabela 'parametros': {e}")


        # Garantir que o registro com ID 1 na tabela 'parametros' exista com valores padrão
        try:
            cur.execute("""
                INSERT INTO parametros (id, modo_visualizacao, cor_acentuacao, escala_fonte, densidade_ui)
                VALUES (1, 'S', 'blue', 1.0, 'Normal')
                ON CONFLICT (id) DO NOTHING;
            """)
            conn.commit()
            print("Registro de parâmetros com ID 1 garantido.")
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Erro ao garantir registro de parâmetros: {e}")

        # --- NOVAS TABELAS PARA O MÓDULO FINANCEIRO ---

        # Tabela para Categorias de Despesas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categoria_despesa (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL UNIQUE
            );
        """)
        conn.commit()
        print("Tabela 'categoria_despesa' verificada/criada com sucesso.")

        # Tabela para Despesas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS despesas (
                id SERIAL PRIMARY KEY,
                descricao VARCHAR(255) NOT NULL,
                valor DECIMAL(10, 2) NOT NULL,
                data DATE NOT NULL DEFAULT CURRENT_DATE,
                categoria_id INTEGER,
                observacoes TEXT,
                FOREIGN KEY (categoria_id) REFERENCES categoria_despesa(id) ON DELETE SET NULL
            );
        """)
        conn.commit()
        print("Tabela 'despesas' verificada/creada com sucesso.")

    except psycopg2.Error as e:
        print(f"Erro de conexão ou operação de banco de dados ao verificar/criar tabelas essenciais: {e}")
        messagebox.showerror("Erro de Banco de Dados",
                             f"Não foi possível conectar ao banco de dados ou criar tabelas essenciais: {e}")
        sys.exit(1) # Sai do aplicativo se houver um erro crítico de banco de dados na inicialização
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def obter_todos_parametros():
    """
    Obtém todos os parâmetros de configuração do sistema da tabela 'parametros'.
    Retorna um dicionário com os parâmetros, ou valores padrão em caso de erro/não encontrado.
    """
    conn = None
    cur = None
    # Valores padrão
    parametros = {
        "modo_visualizacao": 'S',  # 'E' = Escuro, 'C' = Claro, 'S' = Sistema
        "cor_acentuacao": 'blue',  # 'blue', 'green', 'dark-blue'
        "escala_fonte": 1.0,  # e.g., 0.9, 1.0, 1.1 (multiplicador)
        "densidade_ui": 'Normal'  # 'Compacta', 'Normal', 'Espaçosa'
    }

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT modo_visualizacao, cor_acentuacao, escala_fonte, densidade_ui FROM parametros WHERE id = 1")
        result = cur.fetchone()

        if result:
            parametros["modo_visualizacao"] = result[0] if result[0] in ['E', 'C', 'S'] else 'S'
            parametros["cor_acentuacao"] = result[1] if result[1] in ['blue', 'green', 'dark-blue'] else 'blue'
            try:
                parametros["escala_fonte"] = float(result[2])
            except (ValueError, TypeError):
                parametros["escala_fonte"] = 1.0
            parametros["densidade_ui"] = result[3] if result[3] in ['Compacta', 'Normal', 'Espaçosa'] else 'Normal'

    except psycopg2.Error as e:
        print(f"Erro ao obter parâmetros do DB: {e}")
        # Retorna os valores padrão definidos no início da função em caso de erro.
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return parametros


def salvar_parametros(modo_visualizacao, cor_acentuacao, escala_fonte, densidade_ui):
    """
    Salva todos os parâmetros de configuração na tabela 'parametros' (para o registro com ID 1).
    """
    conn = None
    cur = None
    success = False
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO parametros (id, modo_visualizacao, cor_acentuacao, escala_fonte, densidade_ui)
            VALUES (1, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                modo_visualizacao = EXCLUDED.modo_visualizacao,
                cor_acentuacao = EXCLUDED.cor_acentuacao,
                escala_fonte = EXCLUDED.escala_fonte,
                densidade_ui = EXCLUDED.densidade_ui;
        """, (modo_visualizacao, cor_acentuacao, escala_fonte, densidade_ui))
        conn.commit()
        success = True
    except psycopg2.Error as e:
        print(f"Erro ao salvar parâmetros no DB: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return success


class FogueiroBurgerSystem(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração da janela principal
        self.title("Fogueiro Burger - Sistema de Gestão")
        self.geometry("1200x700")
        self.minsize(1000, 600)

        # Variáveis para armazenar as configurações atuais
        self.current_theme = 'S' # 'S' for System, 'E' for Dark, 'C' for Light
        self.current_accent_color = 'blue'
        self.current_font_scale = 1.0
        self.current_ui_density = 'Normal'

        # Carregar e aplicar configurações do banco de dados na inicialização
        self.load_and_apply_system_parameters()

        # Variáveis de estado do sistema
        self.current_user = None
        self.current_module = None

        # Iniciar com a tela de login
        self.show_login()

    def load_and_apply_system_parameters(self):
        """Carrega todos os parâmetros do banco de dados e os aplica."""
        params = obter_todos_parametros()

        # Atualiza as variáveis de instância com os valores carregados do DB
        self.current_theme = params["modo_visualizacao"]
        self.current_accent_color = params["cor_acentuacao"]
        self.current_font_scale = params["escala_fonte"]
        self.current_ui_density = params["densidade_ui"]

        # Aplica as configurações do CustomTkinter
        self._apply_theme_setting(self.current_theme)
        self._apply_accent_color(self.current_accent_color)

        # A escala da fonte e densidade da UI são aplicadas na recriação dos widgets
        # ao chamar setup_main_interface() ou show_settings().

    def _apply_theme_setting(self, modo):
        """Aplica a configuração de tema (claro/escuro/sistema) do CustomTkinter."""
        if modo == "E":  # Escuro
            ctk.set_appearance_mode("Dark")
        elif modo == "C":  # Claro
            ctk.set_appearance_mode("Light")
        else:  # Sistema (S) ou qualquer outro valor padrão/inválido
            ctk.set_appearance_mode("System")

    def _apply_accent_color(self, color_name):
        """Aplica a cor de acentuação (tema de cor) do CustomTkinter."""
        try:
            ctk.set_default_color_theme(color_name)
        except ValueError:
            print(f"Aviso: Cor de acentuação '{color_name}' inválida. Usando 'blue'.")
            ctk.set_default_color_theme("blue")
            self.current_accent_color = 'blue'  # Atualiza a variável interna se for inválida

    def _get_density_multiplier(self):
        """Retorna o fator multiplicador para espaçamento da UI com base na densidade selecionada."""
        if self.current_ui_density == 'Compacta':
            return 0.8
        elif self.current_ui_density == 'Espaçosa':
            return 1.2
        return 1.0  # Normal

    def show_login(self):
        """Exibe a tela de login, destruindo widgets anteriores."""
        for widget in self.winfo_children():
            widget.destroy()

        login_window = LoginWindow(self, self.on_login_success)
        login_window.pack(fill="both", expand=True)

    def on_login_success(self, user):
        """Chamado após um login bem-sucedido."""
        self.current_user = user
        self.setup_main_interface()

    def setup_main_interface(self):
        """Configura a interface principal do sistema após o login."""
        for widget in self.winfo_children():
            widget.destroy()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame do menu lateral
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        # Ajuste para acomodar o novo botão de backup e manter o espaçamento
        self.sidebar_frame.grid_rowconfigure(10, weight=1)  # Aumenta a linha flexível para o novo botão de finanças

        # Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Fogueiro Burger",
            font=ctk.CTkFont(size=int(20 * self.current_font_scale), weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=int(20 * self._get_density_multiplier()),
                             pady=int(20 * self._get_density_multiplier()))

        # Usuário logado
        self.user_label = ctk.CTkLabel(
            self.sidebar_frame,
            text=f"Usuário: {self.current_user.get("nome", "Admin")}",
            font=ctk.CTkFont(size=int(12 * self.current_font_scale))
        )
        self.user_label.grid(row=1, column=0, padx=int(20 * self._get_density_multiplier()),
                             pady=int(5 * self._get_density_multiplier()))

        # Botões do menu
        button_font = ctk.CTkFont(size=int(14 * self.current_font_scale))
        button_pady = int(10 * self._get_density_multiplier())
        button_padx = int(20 * self._get_density_multiplier())

        # Iniciar a contagem da linha para os botões do menu
        current_row = 2

        self.dashboard_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Dashboard",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.show_dashboard
        )
        self.dashboard_button.grid(row=current_row, column=0, padx=button_padx, pady=button_pady, sticky="ew")
        current_row += 1

        self.clients_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Clientes",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.show_clients
        )
        self.clients_button.grid(row=current_row, column=0, padx=button_padx, pady=button_pady, sticky="ew")
        current_row += 1

        self.products_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Produtos",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.show_products
        )
        self.products_button.grid(row=current_row, column=0, padx=button_padx, pady=button_pady, sticky="ew")
        current_row += 1

        self.cadastros_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Cadastros",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.show_cadastros
        )
        self.cadastros_button.grid(row=current_row, column=0, padx=button_padx, pady=button_pady, sticky="ew")
        current_row += 1

        self.orders_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Pedidos",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.show_orders
        )
        self.orders_button.grid(row=current_row, column=0, padx=button_padx, pady=button_pady, sticky="ew")
        current_row += 1

        self.inventory_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Estoque",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.show_inventory
        )
        self.inventory_button.grid(row=current_row, column=0, padx=button_padx, pady=button_pady, sticky="ew")
        current_row += 1

        self.delivery_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Entregas",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.show_delivery
        )
        self.delivery_button.grid(row=current_row, column=0, padx=button_padx, pady=button_pady, sticky="ew")
        current_row += 1

        self.reports_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Relatórios",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.open_reports_window
        )
        self.reports_button.grid(row=current_row, column=0, padx=button_padx, pady=button_pady, sticky="ew")
        current_row += 1

        self.finance_button = ctk.CTkButton( # <-- NOVO BOTÃO FINANCEIRO
            self.sidebar_frame,
            text="Financeiro",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.show_finance # <-- NOVA CHAMADA
        )
        self.finance_button.grid(row=current_row, column=0, padx=button_padx, pady=button_pady, sticky="ew")
        current_row += 1

        self.settings_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Configurações",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.show_settings
        )
        self.settings_button.grid(row=current_row, column=0, padx=button_padx, pady=button_pady, sticky="ew")
        current_row += 1

        self.logout_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Sair",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=button_font,
            command=self.logout
        )
        self.logout_button.grid(row=current_row, column=0, padx=button_padx,
                                pady=int(20 * self._get_density_multiplier()), sticky="ew")
        # current_row += 1 # Não precisa, é o último

        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.show_dashboard()

    def reset_menu_buttons(self):
        """Reseta a cor de fundo dos botões do menu lateral."""
        for button in [
            self.dashboard_button,
            self.clients_button,
            self.products_button,
            self.cadastros_button,
            self.orders_button,
            self.inventory_button,
            self.delivery_button,
            self.reports_button,
            self.finance_button, # <-- NOVO BOTÃO NO RESET
            self.settings_button,
        ]:
            button.configure(fg_color="transparent")

    # Métodos de exibição dos módulos (sem alterações significativas na lógica,
    # mas a fonte e densidade serão aplicadas ao recriar a interface principal)
    def show_dashboard(self):
        self.reset_menu_buttons()
        self.dashboard_button.configure(fg_color=("gray75", "gray25"))
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.current_module = ReportsModule(self.main_frame)
        self.current_module.grid(row=0, column=0, sticky="nsew")

    def show_clients(self):
        self.reset_menu_buttons()
        self.clients_button.configure(fg_color=("gray75", "gray25"))
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.current_module = ClientsModule(self.main_frame)
        self.current_module.grid(row=0, column=0, sticky="nsew")

    def show_products(self):
        self.reset_menu_buttons()
        self.products_button.configure(fg_color=("gray75", "gray25"))
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.current_module = ProductsModule(self.main_frame)
        self.current_module.grid(row=0, column=0, sticky="nsew")

    def show_cadastros(self):
        self.reset_menu_buttons()
        self.cadastros_button.configure(fg_color=("gray75", "gray25"))
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        is_admin = self.current_user.get("admin", False)
        self.current_module = CadastrosModule(self.main_frame, is_admin=is_admin)
        self.current_module.grid(row=0, column=0, sticky="nsew")

    def show_orders(self):
        self.reset_menu_buttons()
        self.orders_button.configure(fg_color=("gray75", "gray25"))
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.current_module = OrdersModule(self.main_frame)
        self.current_module.grid(row=0, column=0, sticky="nsew")

    def show_inventory(self):
        self.reset_menu_buttons()
        self.inventory_button.configure(fg_color=("gray75", "gray25"))
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.current_module = InventoryModule(self.main_frame)
        self.current_module.grid(row=0, column=0, sticky="nsew")

    def show_delivery(self):
        self.reset_menu_buttons()
        self.delivery_button.configure(fg_color=("gray75", "gray25"))
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.current_module = DeliveryModule(self.main_frame)
        self.current_module.grid(row=0, column=0, sticky="nsew")

    def open_reports_window(self):
        self.reset_menu_buttons()
        self.reports_button.configure(fg_color=("gray75", "gray25"))
        reports_window = ctk.CTkToplevel(self)
        reports_window.title("Relatórios Personalizados")
        reports_window.geometry("1000x700")
        reports_window.transient(self)
        reports_window.grab_set()
        reports_window.grid_columnconfigure(0, weight=1)
        reports_window.grid_rowconfigure(0, weight=1)
        reports_module_instance = CustomReportsModule(reports_window)
        reports_module_instance.grid(row=0, column=0, sticky="nsew")

    def show_finance(self): # <-- NOVO MÉTODO PARA MOSTRAR O MÓDULO FINANCEIRO
        self.reset_menu_buttons()
        self.finance_button.configure(fg_color=("gray75", "gray25"))
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.current_module = FinanceModule(self.main_frame)
        self.current_module.grid(row=0, column=0, sticky="nsew")

    def show_settings(self):
        """Exibe a tela de configurações do sistema com opções de aparência e backup."""
        self.reset_menu_buttons()
        self.settings_button.configure(fg_color=("gray75", "gray25"))

        # Limpar o frame principal
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        settings_frame = ctk.CTkFrame(self.main_frame)
        settings_frame.grid(row=0, column=0, sticky="nsew", padx=int(20 * self._get_density_multiplier()),
                            pady=int(20 * self._get_density_multiplier()))
        settings_frame.grid_columnconfigure(0, weight=0)  # Labels
        settings_frame.grid_columnconfigure(1, weight=1)  # Controles
        settings_frame.grid_rowconfigure(0, weight=0)  # Title

        # Título da seção de configurações
        title_label = ctk.CTkLabel(
            settings_frame,
            text="Configurações do Sistema",
            font=ctk.CTkFont(size=int(24 * self.current_font_scale), weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, padx=int(20 * self._get_density_multiplier()),
                         pady=int(20 * self._get_density_multiplier()), sticky="w")

        # --- Seção de Aparência ---
        appearance_section_label = ctk.CTkLabel(
            settings_frame,
            text="Aparência",
            font=ctk.CTkFont(size=int(18 * self.current_font_scale), weight="bold")
        )
        appearance_section_label.grid(row=1, column=0, columnspan=2, padx=int(20 * self._get_density_multiplier()),
                                      pady=int(20 * self._get_density_multiplier()), sticky="w")

        # 1. Opção de Tema (Modo Escuro/Claro/Sistema)
        theme_label = ctk.CTkLabel(
            settings_frame,
            text="Tema Visual:",
            font=ctk.CTkFont(size=int(16 * self.current_font_scale))
        )
        theme_label.grid(row=2, column=0, padx=int(20 * self._get_density_multiplier()),
                         pady=int(10 * self._get_density_multiplier()), sticky="w")

        self.theme_combo = ctk.CTkComboBox(
            settings_frame,
            values=["Claro", "Escuro", "Sistema"],
            command=self.change_theme
        )
        self.theme_combo.grid(row=2, column=1, padx=int(20 * self._get_density_multiplier()),
                              pady=int(10 * self._get_density_multiplier()), sticky="ew")
        # Definir o valor atual no combobox
        ctk_current_theme_mode = ctk.get_appearance_mode()
        if ctk_current_theme_mode == "Light":
            self.theme_combo.set("Claro")
        elif ctk_current_theme_mode == "Dark":
            self.theme_combo.set("Escuro")
        else:
            self.theme_combo.set("Sistema")

        # 2. Opção de Cor de Acentuação
        accent_color_label = ctk.CTkLabel(
            settings_frame,
            text="Cor de Destaque:",
            font=ctk.CTkFont(size=int(16 * self.current_font_scale))
        )
        accent_color_label.grid(row=3, column=0, padx=int(20 * self._get_density_multiplier()),
                                pady=int(10 * self._get_density_multiplier()), sticky="w")

        self.accent_color_combo = ctk.CTkComboBox(
            settings_frame,
            values=["blue", "green", "dark-blue"],  # Cores padrão do CustomTkinter
            command=self.change_accent_color
        )
        self.accent_color_combo.grid(row=3, column=1, padx=int(20 * self._get_density_multiplier()),
                                     pady=int(10 * self._get_density_multiplier()), sticky="ew")
        self.accent_color_combo.set(self.current_accent_color)

        # 3. Opção de Tamanho da Fonte
        font_size_label = ctk.CTkLabel(
            settings_frame,
            text="Tamanho da Fonte:",
            font=ctk.CTkFont(size=int(16 * self.current_font_scale))
        )
        font_size_label.grid(row=4, column=0, padx=int(20 * self._get_density_multiplier()),
                             pady=int(10 * self._get_density_multiplier()), sticky="w")

        self.font_size_combo = ctk.CTkComboBox(
            settings_frame,
            values=["Pequena", "Normal", "Grande"],
            command=self.change_font_size
        )
        self.font_size_combo.grid(row=4, column=1, padx=int(20 * self._get_density_multiplier()),
                                  pady=int(10 * self._get_density_multiplier()), sticky="ew")
        # Definir o valor atual no combobox
        if self.current_font_scale == 0.9:
            self.font_size_combo.set("Pequena")
        elif self.current_font_scale == 1.1:
            self.font_size_combo.set("Grande")
        else:
            self.font_size_combo.set("Normal")

        # 4. Opção de Densidade da UI
        ui_density_label = ctk.CTkLabel(
            settings_frame,
            text="Densidade da UI:",
            font=ctk.CTkFont(size=int(16 * self.current_font_scale))
        )
        ui_density_label.grid(row=5, column=0, padx=int(20 * self._get_density_multiplier()),
                              pady=int(10 * self._get_density_multiplier()), sticky="w")

        self.ui_density_combo = ctk.CTkComboBox(
            settings_frame,
            values=["Compacta", "Normal", "Espaçosa"],
            command=self.change_ui_density
        )
        self.ui_density_combo.grid(row=5, column=1, padx=int(20 * self._get_density_multiplier()),
                                   pady=int(10 * self._get_density_multiplier()), sticky="ew")
        self.ui_density_combo.set(self.current_ui_density)

        # --- Seção de Gestão de Dados (para Administradores) ---
        data_management_section_label = ctk.CTkLabel(
            settings_frame,
            text="Gestão de Dados",
            font=ctk.CTkFont(size=int(18 * self.current_font_scale), weight="bold")
        )
        data_management_section_label.grid(row=6, column=0, columnspan=2, padx=int(20 * self._get_density_multiplier()),
                                           pady=int(40 * self._get_density_multiplier()), sticky="w")

        # Botão de Backup do Banco de Dados (apenas para admins)
        is_admin = self.current_user.get("admin", False)
        self.backup_db_button_in_settings = ctk.CTkButton(
            settings_frame,
            text="Realizar Backup do Banco de Dados (.tar)",
            font=ctk.CTkFont(size=int(16 * self.current_font_scale)),
            command=self.perform_database_backup
        )
        if is_admin:
            self.backup_db_button_in_settings.grid(row=7, column=0, columnspan=2,
                                                   padx=int(20 * self._get_density_multiplier()),
                                                   pady=int(10 * self._get_density_multiplier()), sticky="ew")
        else:
            self.backup_db_button_in_settings.grid_forget()  # Remove do layout

        # --- Informações do sistema ---
        system_info_label = ctk.CTkLabel(
            settings_frame,
            text="Informações do Sistema",
            font=ctk.CTkFont(size=int(18 * self.current_font_scale), weight="bold")
        )
        system_info_label.grid(row=8, column=0, columnspan=2, padx=int(20 * self._get_density_multiplier()),
                               pady=int(40 * self._get_density_multiplier()), sticky="w")

        version_label = ctk.CTkLabel(
            settings_frame,
            text="Versão: 1.0.0",
            font=ctk.CTkFont(size=int(14 * self.current_font_scale))
        )
        version_label.grid(row=9, column=0, columnspan=2, padx=int(20 * self._get_density_multiplier()),
                           pady=int(5 * self._get_density_multiplier()), sticky="w")

        developer_label = ctk.CTkLabel(
            settings_frame,
            text="Desenvolvido por: Cesar AI",
            font=ctk.CTkFont(size=int(14 * self.current_font_scale))
        )
        developer_label.grid(row=10, column=0, columnspan=2, padx=int(20 * self._get_density_multiplier()),
                             pady=int(5 * self._get_density_multiplier()), sticky="w")

        date_label = ctk.CTkLabel(
            settings_frame,
            text="Data de lançamento: 08/06/2025",
            font=ctk.CTkFont(size=int(14 * self.current_font_scale))
        )
        date_label.grid(row=11, column=0, columnspan=2, padx=int(20 * self._get_density_multiplier()),
                        pady=int(5 * self._get_density_multiplier()), sticky="w")

    def _save_all_current_parameters(self):
        """Salva todas as configurações atuais (tema, cor, fonte, densidade) no DB."""
        if salvar_parametros(self.current_theme, self.current_accent_color,
                             self.current_font_scale, self.current_ui_density):
            messagebox.showinfo("Configurações",
                                "Configurações salvas com sucesso! Algumas alterações podem precisar de reinício do aplicativo.")
            # Ao salvar, é bom recriar a interface principal para aplicar as novas configurações
            # Se já estiver logado, reconstruir a interface
            if self.current_user:
                self.setup_main_interface()
            # Senão, se estiver na tela de login, o tema já foi aplicado no __init__
        else:
            messagebox.showerror("Erro", "Não foi possível salvar as configurações no banco de dados.")

    def change_theme(self, selected_theme_name):
        """Altera o tema visual do aplicativo e o salva no banco de dados."""
        theme_map = {
            "Claro": "C",  # Código para o DB
            "Escuro": "E",
            "Sistema": "S"
        }
        ctk_mode_map = {
            "Claro": "Light",
            "Escuro": "Dark",
            "Sistema": "System"
        }

        if selected_theme_name in theme_map:
            self.current_theme = theme_map[selected_theme_name]
            ctk.set_appearance_mode(ctk_mode_map[selected_theme_name])
            self._save_all_current_parameters()
        else:
            print(f"Aviso: Tema desconhecido '{selected_theme_name}'.")

    def change_accent_color(self, selected_color):
        """Altera a cor de acentuação do aplicativo e a salva no banco de dados."""
        valid_colors = ["blue", "green", "dark-blue"]  # Cores CustomTkinter
        if selected_color in valid_colors:
            self.current_accent_color = selected_color
            ctk.set_default_color_theme(selected_color)
            self._save_all_current_parameters()
        else:
            messagebox.showerror("Erro", "Cor de destaque inválida selecionada.")
            self.accent_color_combo.set(self.current_accent_color)  # Reverte para a cor válida anterior

    def change_font_size(self, selected_size_name):
        """Altera o fator de escala da fonte e o salva no banco de dados."""
        font_scale_map = {
            "Pequena": 0.9,
            "Normal": 1.0,
            "Grande": 1.1
        }
        if selected_size_name in font_scale_map:
            self.current_font_scale = font_scale_map[selected_size_name]
            self._save_all_current_parameters()
        else:
            print(f"Aviso: Tamanho de fonte desconhecido '{selected_size_name}'.")

    def change_ui_density(self, selected_density_name):
        """Altera o nível de densidade da UI e o salva no banco de dados."""
        valid_densities = ["Compacta", "Normal", "Espaçosa"]
        if selected_density_name in valid_densities:
            self.current_ui_density = selected_density_name
            self._save_all_current_parameters()
        else:
            print(f"Aviso: Densidade da UI desconhecida '{selected_density_name}'.")

    def perform_database_backup(self):
        """
        Executa um backup completo do banco de dados PostgreSQL usando pg_dump.
        Salva o backup automaticamente na pasta 'bkp_bd' no diretório do executável.
        Apenas para usuários administradores.
        """
        if not self.current_user.get("admin", False):
            messagebox.showerror("Acesso Negado", "Você não tem permissão para realizar o backup do banco de dados.")
            return

        db_host = DB_CONFIG.get("host")
        db_port = DB_CONFIG.get("port")
        db_user = DB_CONFIG.get("user")
        db_password = DB_CONFIG.get("password")
        db_name = DB_CONFIG.get("dbname")

        if not all([db_host, db_port, db_user, db_password, db_name]):
            messagebox.showerror("Erro de Configuração",
                                 "As configurações do banco de dados (host, porta, usuário, senha, nome do DB) não estão completas em db_config.txt.")
            return

        # Determina o diretório base da aplicação (para .py ou .exe)
        if getattr(sys, 'frozen', False):
            # Se a aplicação estiver 'congelada' (compilada com PyInstaller)
            base_dir = os.path.dirname(sys.executable)
        else:
            # Se estiver executando como um script Python normal
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # Cria o diretório de backup 'bkp_bd' se não existir
        backup_dir = os.path.join(base_dir, "bkp_bd")
        try:
            os.makedirs(backup_dir, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Erro", f"Não foi possível criar o diretório de backup: {backup_dir}\nErro: {e}")
            return

        # Gerar nome de arquivo padrão com timestamp e extensão .tar
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(backup_dir, f"fogueiro_burger_backup_{timestamp}.tar")

        # Construir o comando pg_dump
        command = [
            "pg_dump",
            f"--host={db_host}",
            f"--port={db_port}",
            f"--username={db_user}",
            f"--dbname={db_name}",
            f"--file={file_path}",
            "-Ft",  # Formato de saída tar
        ]

        # Definir a variável de ambiente PGPASSWORD
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password

        try:
            messagebox.showinfo("Backup em Andamento",
                                "Iniciando o backup do banco de dados. Isso pode levar alguns segundos...")

            # Executar o comando pg_dump
            result = subprocess.run(command, env=env, check=True, capture_output=True, text=True)

            if result.returncode == 0:
                messagebox.showinfo("Backup Concluído", f"Backup do banco de dados salvo com sucesso em:\n{file_path}")
            else:
                messagebox.showerror("Erro no Backup",
                                     f"Ocorreu um erro durante o backup. Código de saída: {result.returncode}\n{result.stderr}")

        except FileNotFoundError:
            messagebox.showerror("Erro",
                                 "O comando 'pg_dump' não foi encontrado.\nCertifique-se de que o PostgreSQL está instalado e 'pg_dump' está no seu PATH.")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Erro no Backup", f"Erro ao executar pg_dump:\n{e.stderr}")
            print(f"Erro ao executar pg_dump: {e}")
            print(f"Saída STDERR: {e.stderr}")
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Ocorreu um erro inesperado durante o backup: {e}")
            print(f"Erro inesperado no backup: {e}")

        # Limpar a variável de ambiente da senha após o uso
        if "PGPASSWORD" in env:
            del env["PGPASSWORD"]

    def logout(self):
        """Redireciona para a tela de login ao fazer logout."""
        self.current_user = None
        self.show_login()


if __name__ == "__main__":
    # Garante que as colunas de parâmetros e tabelas essenciais existam antes de iniciar o aplicativo
    _verificar_e_criar_tabelas_essenciais() # <-- NOME DA FUNÇÃO ATUALIZADO
    app = FogueiroBurgerSystem()
    app.mainloop()

