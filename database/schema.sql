-- Schema do Sistema de Controle de Locação de Carros
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    papel TEXT NOT NULL DEFAULT 'admin', -- admin, operador
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expira_em TEXT NOT NULL,
    usado INTEGER NOT NULL DEFAULT 0,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS proprietarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    documento TEXT, -- CPF/CNPJ
    telefone TEXT,
    email TEXT,
    chave_pix TEXT,
    percentual_repasse REAL, -- % que fica com o proprietário, se aplicável
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS veiculos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    placa TEXT NOT NULL UNIQUE,
    renavam TEXT,
    chassi TEXT,
    marca TEXT,
    modelo TEXT,
    ano_fabricacao TEXT,
    ano_modelo TEXT,
    cor TEXT,
    km_atual INTEGER NOT NULL DEFAULT 0,
    valor_diaria_padrao REAL DEFAULT 0,
    proprietario_id INTEGER,
    rastreador_link TEXT,
    rastreador_login TEXT,
    seguradora_nome TEXT,
    seguradora_apolice TEXT,
    seguradora_telefone_24h TEXT,
    status TEXT NOT NULL DEFAULT 'disponivel', -- disponivel, alugado, manutencao, inativo
    foto_path TEXT,
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (proprietario_id) REFERENCES proprietarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cpf TEXT UNIQUE,
    rg TEXT,
    cnh TEXT,
    cnh_validade TEXT,
    telefone TEXT,
    email TEXT,
    endereco TEXT,
    antecedentes_verificado INTEGER NOT NULL DEFAULT 0, -- 0/1
    antecedentes_link TEXT,
    antecedentes_observacao TEXT,
    antecedentes_data TEXT,
    score_manual TEXT, -- bom, regular, ruim, NULL = automático
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS locacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    veiculo_id INTEGER NOT NULL,
    data_inicio TEXT NOT NULL,
    data_fim_prevista TEXT,
    data_fim_real TEXT,
    km_inicial INTEGER,
    km_final INTEGER,
    valor_diaria REAL NOT NULL DEFAULT 0,
    valor_total_previsto REAL DEFAULT 0,
    caucao_valor REAL DEFAULT 0,
    caucao_status TEXT NOT NULL DEFAULT 'sem_caucao', -- sem_caucao, retido, devolvido, parcial, retido_para_danos
    status TEXT NOT NULL DEFAULT 'ativa', -- ativa, finalizada, atrasada, cancelada
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
);

CREATE TABLE IF NOT EXISTS contratos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    locacao_id INTEGER NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'gerado', -- gerado, upload
    arquivo_path TEXT NOT NULL,
    nome_original TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (locacao_id) REFERENCES locacoes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS financeiro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    locacao_id INTEGER,
    cliente_id INTEGER NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'aluguel', -- aluguel, caucao, multa, dano, outro
    descricao TEXT,
    valor REAL NOT NULL DEFAULT 0,
    vencimento TEXT NOT NULL,
    data_pagamento TEXT,
    forma_pagamento TEXT,
    status TEXT NOT NULL DEFAULT 'pendente', -- pendente, pago, atrasado, cancelado
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (locacao_id) REFERENCES locacoes(id) ON DELETE SET NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE TABLE IF NOT EXISTS vistorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    veiculo_id INTEGER NOT NULL,
    locacao_id INTEGER,
    tipo TEXT NOT NULL DEFAULT 'semanal', -- semanal, entrada, saida, avulsa
    data TEXT NOT NULL,
    km INTEGER,
    condicao_geral TEXT, -- ok, atencao, problema
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (veiculo_id) REFERENCES veiculos(id),
    FOREIGN KEY (locacao_id) REFERENCES locacoes(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS vistoria_fotos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vistoria_id INTEGER NOT NULL,
    arquivo_path TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (vistoria_id) REFERENCES vistorias(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vistoria_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    locacao_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (locacao_id) REFERENCES locacoes(id) ON DELETE CASCADE
);

-- Configurações da empresa/locadora que usa este sistema (linha única, id sempre 1).
-- Permite personalizar o contrato (cláusulas, texto extra, rodapé) e os dados
-- exibidos sem precisar alterar código -- essencial quando o sistema é vendido
-- para diferentes clientes/locadoras, cada um com sua própria instância.
CREATE TABLE IF NOT EXISTS configuracoes (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    nome_empresa TEXT,
    cnpj TEXT,
    endereco TEXT,
    telefone TEXT,
    email TEXT,
    logo_path TEXT,
    contrato_clausulas TEXT, -- uma cláusula por linha
    contrato_texto_extra TEXT, -- condições específicas adicionais (opcional)
    contrato_rodape TEXT, -- nota de rodapé do contrato
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_veiculos_status ON veiculos(status);
CREATE INDEX IF NOT EXISTS idx_locacoes_status ON locacoes(status);
CREATE INDEX IF NOT EXISTS idx_financeiro_status ON financeiro(status);
CREATE INDEX IF NOT EXISTS idx_financeiro_cliente ON financeiro(cliente_id);
CREATE INDEX IF NOT EXISTS idx_vistorias_veiculo ON vistorias(veiculo_id);
CREATE INDEX IF NOT EXISTS idx_vistoria_links_locacao ON vistoria_links(locacao_id);
