import customtkinter as ctk
from tkinter import messagebox
import psycopg2
import os
import tempfile
import platform
from datetime import datetime
from db_config import DB_CONFIG  # Importa as configurações do banco de dados

# Define o caminho para a pasta de relatórios SQL
REPORTS_FOLDER = "relatorios"


class CustomReportsModule(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Configuração do grid para o próprio CustomReportsModule para preencher o espaço
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Linha para o título do módulo
        self.grid_rowconfigure(1, weight=0)  # Linha para o frame de controles/seleção
        self.grid_rowconfigure(2, weight=1)  # Linha para o frame principal de exibição do relatório

        # Variáveis para controle de redimensionamento de colunas
        self._resizing_column = None
        self._start_x = 0
        self._start_width = 0
        self.column_widths = []  # Lista para armazenar as larguras atuais das colunas

        # Variáveis para armazenar os dados do relatório atualmente exibido para impressão
        self.current_report_title = ""
        self.current_report_columns = []
        self.current_report_data = []

        # 1. Título do Módulo
        self.module_title_label = ctk.CTkLabel(
            self,
            text="Módulo de Relatórios",  # Título geral do módulo
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.module_title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # 2. Frame de Controles e Seleção de Relatórios
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.controls_frame.grid_columnconfigure(0, weight=0)  # Coluna para o label "Selecione o Relatório"
        self.controls_frame.grid_columnconfigure(1, weight=1)  # Coluna para o ComboBox (expansível)
        # self.controls_frame.grid_columnconfigure(2, weight=0)  # Coluna para o botão "Gerar PDF" - REMOVIDA
        self.controls_frame.grid_columnconfigure(2,
                                                 weight=0)  # Coluna para o botão "Imprimir Relatório" (era 3, agora 2)

        self.select_report_label = ctk.CTkLabel(
            self.controls_frame,
            text="Selecione o Relatório:",
            font=ctk.CTkFont(size=16)
        )
        self.select_report_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        self.report_selection_combo = ctk.CTkComboBox(
            self.controls_frame,
            values=[],  # Será preenchido por load_report_list
            command=self.display_report_from_combo,
            width=250  # Ajusta a largura para o combobox
        )
        self.report_selection_combo.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ew")

        # Botão "Gerar PDF" - REMOVIDO
        # self.pdf_button = ctk.CTkButton(
        #     self.controls_frame,
        #     text="Gerar PDF",
        #     command=lambda: messagebox.showinfo("Gerar PDF", "Funcionalidade de geração de PDF em desenvolvimento.")
        # )
        # self.pdf_button.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="e")

        # Botão "Imprimir Relatório"
        self.print_button = ctk.CTkButton(
            self.controls_frame,
            text="Imprimir Relatório",
            command=self._generate_printable_report,
            state="disabled"  # Desabilitado inicialmente, habilitado quando um relatório é carregado
        )
        self.print_button.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="e")  # Coluna ajustada para 2

        # 3. Frame Principal de Exibição do Relatório
        self.report_display_frame = ctk.CTkFrame(self)
        self.report_display_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.report_display_frame.grid_columnconfigure(0, weight=1)  # Coluna para o conteúdo
        self.report_display_frame.grid_rowconfigure(0, weight=1)  # Linha inicial para a mensagem/tabela

        # Mensagem inicial
        self.initial_message = ctk.CTkLabel(
            self.report_display_frame,
            text="Selecione um relatório para visualizá-lo.",
            font=ctk.CTkFont(size=16),
            wraplength=self.report_display_frame._current_width - 40  # Ajusta quebra de linha
        )
        self.initial_message.place(relx=0.5, rely=0.5, anchor="center")  # Centraliza a mensagem

        self.load_report_list()

    def load_report_list(self):
        """
        Carrega a lista de arquivos SQL da pasta REPORTS_FOLDER e popula o ComboBox.
        """
        self.report_files = {}  # Dicionário para mapear nome de exibição para caminho do arquivo
        report_display_names = ["Selecione um relatório..."]

        if not os.path.exists(REPORTS_FOLDER):
            os.makedirs(REPORTS_FOLDER)  # Cria a pasta se não existir
            messagebox.showinfo("Informação",
                                f"Pasta '{REPORTS_FOLDER}' criada. Por favor, adicione seus arquivos .sql nela.")
            self.report_selection_combo.configure(values=report_display_names)
            self.report_selection_combo.set(report_display_names[0])
            return

        sql_files = [f for f in os.listdir(REPORTS_FOLDER) if f.endswith(".sql")]

        if not sql_files:
            self.initial_message.configure(text="Nenhum relatório .sql encontrado na pasta 'relatorios'.")
            self.report_selection_combo.configure(values=report_display_names)
            self.report_selection_combo.set(report_display_names[0])
            # Desabilitar o botão de imprimir se não houver relatórios
            self.print_button.configure(state="disabled")
            return

        for file_name in sorted(sql_files):
            display_name = os.path.splitext(file_name)[0].replace("_", " ").title()
            file_path = os.path.join(REPORTS_FOLDER, file_name)
            self.report_files[display_name] = file_path
            report_display_names.append(display_name)

        self.report_selection_combo.configure(values=report_display_names)
        self.report_selection_combo.set(report_display_names[0])  # Seleciona a primeira opção

        # Se houver relatórios, tenta exibir o primeiro automaticamente
        if len(report_display_names) > 1:
            self.report_selection_combo.set(report_display_names[1])  # Seleciona o primeiro relatório real
            self.display_report_from_combo(report_display_names[1])
            self.print_button.configure(state="normal")  # Habilita o botão de imprimir
        else:
            self.print_button.configure(state="disabled")  # Desabilita se só tiver a opção "Selecione..."

    def display_report_from_combo(self, report_name):
        """
        Método chamado pelo ComboBox para exibir o relatório selecionado.
        """
        if report_name == "Selecione um relatório...":
            for widget in self.report_display_frame.winfo_children():  # Limpa o frame de exibição
                widget.destroy()
            self.initial_message = ctk.CTkLabel(  # Recria a mensagem inicial
                self.report_display_frame,
                text="Selecione um relatório no menu à esquerda para visualizá-lo.",
                font=ctk.CTkFont(size=16),
                wraplength=self.report_display_frame._current_width - 40
            )
            self.initial_message.place(relx=0.5, rely=0.5, anchor="center")
            self.print_button.configure(state="disabled")  # Desabilita o botão de imprimir
            # Limpa os dados do relatório atual
            self.current_report_title = ""
            self.current_report_columns = []
            self.current_report_data = []
            return

        self.display_report(report_name)

    def display_report(self, report_name):
        """
        Lê o arquivo SQL, executa a consulta e exibe os resultados.
        """
        for widget in self.report_display_frame.winfo_children():  # Limpa o frame de exibição
            widget.destroy()

        file_path = self.report_files.get(report_name)
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Erro", "Arquivo de relatório não encontrado.")
            self.print_button.configure(state="disabled")
            # Limpa os dados do relatório atual
            self.current_report_title = ""
            self.current_report_columns = []
            self.current_report_data = []
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                sql_query = f.read()

            conn = None
            cur = None
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                cur = conn.cursor()
                cur.execute(sql_query)
                column_names = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

                # Armazena os dados do relatório para a função de impressão
                self.current_report_title = report_name
                self.current_report_columns = column_names
                self.current_report_data = rows
                self.print_button.configure(state="normal")  # Habilita o botão de imprimir

                self.render_report_table(report_name, column_names, rows)

            except psycopg2.Error as e:
                messagebox.showerror("Erro de Banco de Dados", f"Falha ao executar o relatório:\n{e}")
                print(f"Erro SQL: {e}")  # Imprime o erro detalhado no console
                self.print_button.configure(state="disabled")
                # Limpa os dados do relatório atual em caso de erro
                self.current_report_title = ""
                self.current_report_columns = []
                self.current_report_data = []
            finally:
                if cur:
                    cur.close()
                if conn:
                    conn.close()

        except Exception as e:
            messagebox.showerror("Erro de Leitura", f"Não foi possível ler o arquivo de relatório:\n{e}")
            print(f"Erro ao ler arquivo: {e}")
            self.print_button.configure(state="disabled")
            # Limpa os dados do relatório atual em caso de erro
            self.current_report_title = ""
            self.current_report_columns = []
            self.current_report_data = []

    def render_report_table(self, title, columns, data):
        """
        Renderiza os dados do relatório em uma tabela na tela com colunas redimensionáveis.
        """
        # Limpa qualquer conteúdo anterior do report_display_frame
        for widget in self.report_display_frame.winfo_children():
            widget.destroy()

        # Calcula o número total de colunas no grid para dados e resizers
        total_grid_columns = len(columns) * 2

        # Título do relatório (agora filho de report_display_frame)
        self.report_title_label = ctk.CTkLabel(
            self.report_display_frame,
            text=f"Relatório: {title}",
            font=ctk.CTkFont(size=18, weight="bold"),  # Tamanho da fonte ajustado
            wraplength=self.report_display_frame.winfo_width() - 40
            # Ajusta a quebra de linha com base na largura do frame pai
        )
        # O título irá ocupar todas as colunas disponíveis no report_display_frame
        self.report_title_label.grid(row=0, column=0, padx=10, pady=(10, 20), sticky="w", columnspan=total_grid_columns)

        # Cabeçalho da tabela (agora filho de report_display_frame)
        self.header_frame = ctk.CTkFrame(self.report_display_frame, fg_color=("#EEEEEE", "#333333"))
        self.header_frame.grid(row=1, column=0, sticky="ew", columnspan=total_grid_columns)  # Ocupa todas as colunas

        # Inicializa as larguras das colunas (aproximadas, serão ajustadas)
        default_col_width = 120
        self.column_widths = [default_col_width for _ in columns]

        for i, col_name in enumerate(columns):
            # Célula do cabeçalho
            header_cell_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
            header_cell_frame.grid(row=0, column=i * 2, sticky="nsew")  # Coluna do cabeçalho
            header_cell_frame.grid_columnconfigure(0, weight=1)

            label = ctk.CTkLabel(
                header_cell_frame,
                text=col_name,
                font=ctk.CTkFont(weight="bold")
            )
            label.grid(row=0, column=0, padx=5, pady=5, sticky="w")  # Reduzindo pady para 5

            self.header_frame.grid_columnconfigure(i * 2, minsize=self.column_widths[
                i])  # Define minsize para a coluna do cabeçalho

            # Handle de redimensionamento
            # Removendo a borda lateral (resizer)
            # if i < len(columns) - 0:
            #     resizer = ctk.CTkFrame(self.header_frame, width=5, cursor="sb_h_double_arrow", fg_color="gray50")
            #     resizer.grid(row=0, column=i*2 + 1, sticky="ns", padx=0, pady=0)
            #     resizer.bind("<Button-1>", lambda e, col=i: self._start_resize(e, col))
            #     resizer.bind("<B1-Motion>", self._do_resize)
            #     resizer.bind("<ButtonRelease-1>", self._stop_resize)
            #     self.header_frame.grid_columnconfigure(i*2 + 1, minsize=5)

        # Conteúdo da tabela (ScrollableFrame) (agora filho de report_display_frame)
        self.data_scroll_frame = ctk.CTkScrollableFrame(self.report_display_frame, fg_color="transparent")
        self.data_scroll_frame.grid(row=2, column=0, sticky="nsew", columnspan=total_grid_columns)
        self.report_display_frame.grid_rowconfigure(2, weight=1)  # Permite o scrollable frame expandir

        self._populate_data_rows(data)

    def _populate_data_rows(self, data):
        """Popula as linhas de dados do relatório."""
        for widget in self.data_scroll_frame.winfo_children():
            widget.destroy()

        if not data:
            no_data_label = ctk.CTkLabel(
                self.data_scroll_frame,
                text="Nenhum dado encontrado para este relatório.",
                font=ctk.CTkFont(size=14)
            )
            no_data_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        else:
            for r_idx, row_data in enumerate(data):
                row_frame = ctk.CTkFrame(self.data_scroll_frame, fg_color="transparent")
                row_frame.grid(row=r_idx, column=0, sticky="ew")  # Cada linha é uma moldura para todas as células
                # Configurações de coluna para o row_frame, replicando a estrutura do cabeçalho
                for i in range(len(self.column_widths)):
                    row_frame.grid_columnconfigure(i * 2, minsize=self.column_widths[i])
                    # if i < len(self.column_widths) - 0: # Para incluir as "colunas" vazias do resizer
                    #     row_frame.grid_columnconfigure(i*2 + 1, minsize=5) # Largura do resizer

                for c_idx, cell_value in enumerate(row_data):
                    label = ctk.CTkLabel(
                        row_frame,
                        text=str(cell_value),
                        anchor="w"  # Alinha texto à esquerda
                    )
                    label.grid(row=0, column=c_idx * 2, padx=10, pady=2, sticky="ew")  # Reduzindo pady para 2
                    # Removendo a borda lateral (resizer)
                    # if c_idx < len(row_data) - 0:
                    #    row_frame.grid_columnconfigure(c_idx*2 + 1, minsize=5) # Largura do resizer

    def _start_resize(self, event, col_idx):
        """Inicia o processo de redimensionamento da coluna."""
        self._resizing_column = col_idx
        self._start_x = event.x_root
        # Obtém a largura atual da coluna no cabeçalho
        self._start_width = self.header_frame.grid_columnconfigure(col_idx * 2, "minsize")

    def _do_resize(self, event):
        """Executa o redimensionamento da coluna enquanto o mouse é arrastado."""
        if self._resizing_column is not None:
            delta_x = event.x_root - self._start_x
            new_width = max(50, self._start_width + delta_x)  # Largura mínima de 50 pixels

            # Atualiza a largura da coluna no cabeçalho
            self.header_frame.grid_columnconfigure(self._resizing_column * 2, minsize=new_width)
            self.column_widths[self._resizing_column] = new_width

            # Atualiza a largura da coluna em TODAS as linhas de dados
            for row_frame in self.data_scroll_frame.winfo_children():
                if isinstance(row_frame, ctk.CTkFrame):  # Garante que é um frame de linha de dados
                    row_frame.grid_columnconfigure(self._resizing_column * 2, minsize=new_width)

            self.update_idletasks()  # Atualiza a exibição imediatamente

    def _stop_resize(self, event):
        """Finaliza o processo de redimensionamento da coluna."""
        self._resizing_column = None

    def _generate_printable_report(self):
        """
        Gera uma string com os dados do relatório atualmente exibido e a salva em um arquivo temporário.
        Em seguida, tenta abrir o arquivo com o aplicativo padrão do sistema para impressão.
        """
        if not self.current_report_data:
            messagebox.showinfo("Informação", "Nenhum relatório carregado para impressão.")
            return

        try:
            # Construir o conteúdo para impressão
            content = f"===== Relatório: {self.current_report_title} =====\n\n"

            # Adicionar cabeçalhos
            header_line = ""
            # Encontrar a largura máxima para cada coluna para alinhar
            col_max_widths = [len(col) for col in self.current_report_columns]
            for row_data in self.current_report_data:
                for i, cell_value in enumerate(row_data):
                    col_max_widths[i] = max(col_max_widths[i], len(str(cell_value)))

            # Formatar cabeçalhos e dados com alinhamento
            for i, col_name in enumerate(self.current_report_columns):
                header_line += f"{col_name:<{col_max_widths[i]}}  "
            content += header_line + "\n"
            content += "=" * len(header_line) + "\n"  # Linha separadora

            # Adicionar dados
            for r_idx, row_data in enumerate(self.current_report_data):
                data_line = ""
                for i, cell_value in enumerate(row_data):
                    data_line += f"{str(cell_value):<{col_max_widths[i]}}  "
                content += data_line + "\n"
                # Adiciona uma linha de traços para separar as linhas de dados visualmente
                if r_idx < len(self.current_report_data) - 1:
                    content += "-" * len(header_line) + "\n"

            content += "\n=======================================\n"
            content += f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"

            # Salvar em um arquivo temporário
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

            messagebox.showinfo("Imprimir Relatório", f"Detalhes do relatório abertos para impressão.")

        except Exception as e:
            messagebox.showerror("Erro de Impressão",
                                 f"Ocorreu um erro ao preparar ou abrir o arquivo para impressão: {e}")
            print(f"Erro ao imprimir relatório: {e}")
        finally:
            # O arquivo temporário será excluído automaticamente quando o programa terminar,
            # ou você pode gerenciá-lo manualmente se precisar de um comportamento diferente.
            pass


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Teste do Módulo de Relatórios Personalizados")
    app.geometry("1000x700")
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    reports_module = CustomReportsModule(app)
    reports_module.grid(row=0, column=0, sticky="nsew")

    app.mainloop()
