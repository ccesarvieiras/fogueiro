import customtkinter as ctk
import psycopg2
from datetime import datetime, timedelta

# Importar configurações do banco de dados de um arquivo externo
from db_config import DB_CONFIG


def get_total_pedidos():
    """Retorna o número total de pedidos."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(id) FROM pedidos")
        total = cur.fetchone()[0]
        return total if total is not None else 0
    except psycopg2.Error as e:
        print(f"Erro ao obter total de pedidos: {e}")
        return 0
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_receita_total():
    """Retorna a soma total dos pedidos concluídos/entregues."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Considera pedidos com status 'Entregue' ou 'Concluída'
        cur.execute("SELECT SUM(total) FROM pedidos WHERE status IN ('Entregue', 'Concluída')")
        receita = cur.fetchone()[0]
        return float(receita) if receita is not None else 0.0
    except psycopg2.Error as e:
        print(f"Erro ao obter receita total: {e}")
        return 0.0
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_pedidos_por_status():
    """Retorna a contagem de pedidos por status."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(id) FROM pedidos GROUP BY status")
        results = cur.fetchall()
        # Inicializa todos os status para garantir que apareçam, mesmo com 0 pedidos
        status_counts = {
            "Pendente": 0,
            "Em preparo": 0,
            "Pronto": 0,
            "Em entrega": 0,
            "Entregue": 0,
            "Concluída": 0,
            "Cancelado": 0
        }
        for status, count in results:
            if status in status_counts:
                status_counts[status] = count
            else:
                status_counts[status] = count  # Captura status não mapeados também
        return status_counts
    except psycopg2.Error as e:
        print(f"Erro ao obter pedidos por status: {e}")
        return {}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_pedidos_por_tipo():
    """Retorna a contagem de pedidos por tipo (Balcão, Delivery)."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT tipo, COUNT(id) FROM pedidos GROUP BY tipo")
        results = cur.fetchall()
        tipo_counts = {
            "Balcão": 0,
            "Delivery": 0
        }
        for tipo, count in results:
            if tipo in tipo_counts:
                tipo_counts[tipo] = count
            else:
                tipo_counts[tipo] = count  # Captura tipos não mapeados também
        return tipo_counts
    except psycopg2.Error as e:
        print(f"Erro ao obter pedidos por tipo: {e}")
        return {}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_produtos_mais_vendidos(limit=5):
    """Retorna os produtos mais vendidos por quantidade."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT
                p.nome,
                SUM(ip.quantidade) as total_vendido
            FROM itens_pedidos ip
            JOIN produtos p ON ip.produto_id = p.id
            GROUP BY p.nome
            ORDER BY total_vendido DESC
            LIMIT {limit}
        """)
        results = cur.fetchall()
        return [{"produto_nome": row[0], "quantidade_vendida": row[1]} for row in results]
    except psycopg2.Error as e:
        print(f"Erro ao obter produtos mais vendidos: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_receita_mensal():
    """Retorna a receita total por mês."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                TO_CHAR(data_pedido, 'YYYY-MM') as ano_mes,
                SUM(total) as receita_mensal
            FROM pedidos
            WHERE status IN ('Entregue', 'Concluída')
            GROUP BY ano_mes
            ORDER BY ano_mes
        """)
        results = cur.fetchall()
        return [{"mes": row[0], "receita": float(row[1])} for row in results]
    except psycopg2.Error as e:
        print(f"Erro ao obter receita mensal: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


class ReportsModule(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Ajustando a configuração das colunas e linhas para um layout mais compacto e esteticamente agradável
        # As colunas e linhas não precisam ser 'uniform' para dar flexibilidade no tamanho de cada widget
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)  # 4 colunas para mais flexibilidade
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)  # 4 linhas

        self.title_label = ctk.CTkLabel(
            self,
            text="Relatórios e Estatísticas do Negócio",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w",
                              columnspan=4)  # Ocupa todas as 4 colunas

        # Botão de atualização - Inicializado ANTES de load_reports()
        self.refresh_button = ctk.CTkButton(
            self,
            text="Atualizar Relatórios",
            command=self.load_reports
        )
        self.refresh_button.grid(row=0, column=3, padx=20, pady=(20, 10),
                                 sticky="e")  # Posicionado no canto superior direito

        self.load_reports()  # Agora pode ser chamado com segurança

    def load_reports(self):
        """Carrega e exibe todos os relatórios e gráficos na interface."""
        # Limpa o frame antes de carregar novos relatórios
        for widget in self.winfo_children():
            # Não destroi o título e o botão de atualização
            if widget not in [self.title_label, self.refresh_button]:
                widget.destroy()

        # Visão Geral (Total de Pedidos e Receita Total)
        total_pedidos = get_total_pedidos()
        receita_total = get_receita_total()
        self._create_info_card(
            parent_frame=self,
            title="Total de Pedidos",
            value=str(total_pedidos),
            description="Pedidos registrados",
            row=1, column=0
        )
        self._create_info_card(
            parent_frame=self,
            title="Receita Gerada",
            value=f"R$ {receita_total:.2f}".replace(".", ","),
            description="Receita total de pedidos",
            row=1, column=1
        )

        # Pedidos por Status (Informação Analítica)
        pedidos_status = get_pedidos_por_status()
        status_data_formatted = []
        for status, count in pedidos_status.items():
            status_data_formatted.append(f"{status}: {count} pedidos")
        self._create_analytic_card(
            parent_frame=self,
            title="Pedidos por Status",
            data_list=status_data_formatted,
            row=1, column=2, columnspan=2  # Ocupa duas colunas
        )

        # Pedidos por Tipo (Informação Analítica)
        pedidos_tipo = get_pedidos_por_tipo()
        tipo_data_formatted = []
        for tipo, count in pedidos_tipo.items():
            tipo_data_formatted.append(f"{tipo}: {count} pedidos")
        self._create_analytic_card(
            parent_frame=self,
            title="Pedidos por Tipo",
            data_list=tipo_data_formatted,
            row=2, column=0, columnspan=2  # Ocupa duas colunas
        )

        # Produtos Mais Vendidos (Informação Analítica)
        produtos_vendidos = get_produtos_mais_vendidos(limit=5)
        produtos_data_formatted = []
        if produtos_vendidos:
            for item in produtos_vendidos:
                produtos_data_formatted.append(f"{item['produto_nome']}: {item['quantidade_vendida']} unidades")
        else:
            produtos_data_formatted.append("Nenhum produto vendido ainda.")
        self._create_analytic_card(
            parent_frame=self,
            title="Produtos Mais Vendidos (Top 5)",
            data_list=produtos_data_formatted,
            row=2, column=2, columnspan=2  # Ocupa duas colunas
        )

        # Receita Mensal (Informação Analítica)
        receita_mensal = get_receita_mensal()
        receita_mensal_formatted = []
        if receita_mensal:
            for entry in receita_mensal:
                receita_mensal_formatted.append(f"{entry['mes']}: R$ {entry['receita']:.2f}".replace(".", ","))
        else:
            receita_mensal_formatted.append("Nenhum dado de receita mensal.")
        self._create_analytic_card(
            parent_frame=self,
            title="Receita Mensal",
            data_list=receita_mensal_formatted,
            row=3, column=0, columnspan=4  # Ocupa todas as 4 colunas
        )

    def _create_info_card(self, parent_frame, title, value, description, row, column):
        """Cria um card de informações simples (KPI)."""
        card_frame = ctk.CTkFrame(parent_frame, corner_radius=10, fg_color=("gray85", "gray15"))
        card_frame.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")
        card_frame.grid_columnconfigure(0, weight=1)
        card_frame.grid_rowconfigure((0, 1, 2), weight=1)  # Permite o conteúdo centralizar/expandir

        title_label = ctk.CTkLabel(
            card_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("gray20", "gray80")
        )
        title_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        value_label = ctk.CTkLabel(
            card_frame,
            text=value,
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#1f77b4"  # Usando uma cor fixa da paleta anterior para valores
        )
        value_label.grid(row=1, column=0, padx=15, pady=5, sticky="w")

        description_label = ctk.CTkLabel(
            card_frame,
            text=description,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        description_label.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="w")

    def _create_analytic_card(self, parent_frame, title, data_list, row, column, columnspan):
        """Cria um card para exibir informações analíticas em formato de lista."""
        card_frame = ctk.CTkFrame(parent_frame, corner_radius=10, fg_color=("gray85", "gray15"))
        card_frame.grid(row=row, column=column, padx=10, pady=10, sticky="nsew", columnspan=columnspan)
        card_frame.grid_columnconfigure(0, weight=1)
        card_frame.grid_rowconfigure(1, weight=1)  # O conteúdo dos dados expandirá

        card_title = ctk.CTkLabel(
            card_frame,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("gray20", "gray80")
        )
        card_title.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        # Usar um CTkScrollableFrame para a lista de dados, caso seja muito longa
        data_scroll_frame = ctk.CTkScrollableFrame(card_frame, fg_color="transparent")
        data_scroll_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        data_scroll_frame.grid_columnconfigure(0, weight=1)

        if not data_list:
            no_data_label = ctk.CTkLabel(data_scroll_frame, text="Nenhum dado disponível.", font=ctk.CTkFont(size=14))
            no_data_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        else:
            for i, item_text in enumerate(data_list):
                item_label = ctk.CTkLabel(
                    data_scroll_frame,
                    text=item_text,
                    anchor="w",
                    font=ctk.CTkFont(size=12)
                )
                item_label.grid(row=i, column=0, padx=5, pady=2, sticky="w")


# Para teste standalone
if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")  # Definir modo escuro para o teste standalone
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Teste do Módulo de Relatórios")
    app.geometry("1200x800")  # Mantém o tamanho da janela de teste para visualização
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    reports_module = ReportsModule(app)
    reports_module.grid(row=0, column=0, sticky="nsew")

    app.mainloop()
