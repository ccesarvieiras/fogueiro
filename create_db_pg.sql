-- Tabela de Clientes
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    endereco TEXT,
    telefone VARCHAR(20),
    email VARCHAR(255)
);

-- Tabela de Produtos
CREATE TABLE IF NOT EXISTS produtos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    preco NUMERIC(10, 2) NOT NULL,
    categoria VARCHAR(100)
);

-- Tabela de Pedidos
CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER,
    data_pedido TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total NUMERIC(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

-- Tabela de Itens do Pedido
CREATE TABLE IF NOT EXISTS itens_pedido (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    quantidade INTEGER NOT NULL,
    preco_unitario NUMERIC(10, 2) NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);

-- Tabela de Estoque (para ingredientes/materiais)
CREATE TABLE IF NOT EXISTS estoque (
    id SERIAL PRIMARY KEY,
    nome_item VARCHAR(255) NOT NULL UNIQUE,
    quantidade INTEGER NOT NULL,
    unidade VARCHAR(50),
    estoque_minimo INTEGER
);

-- Tabela de Funcionários
CREATE TABLE IF NOT EXISTS funcionarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cargo VARCHAR(100),
    telefone VARCHAR(20),
    email VARCHAR(255),
    senha VARCHAR(255) NOT NULL
);

-- Tabela de Entregas
CREATE TABLE IF NOT EXISTS entregas (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL,
    funcionario_id INTEGER,
    status VARCHAR(50) NOT NULL,
    data_saida TIMESTAMP,
    data_entrega TIMESTAMP,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
    FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id)
);


