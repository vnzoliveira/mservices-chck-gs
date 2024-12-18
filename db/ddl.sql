CREATE TABLE IF NOT EXISTS alunos(
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    nacionalidade VARCHAR(100) NOT NULL,
    estado VARCHAR(100) NOT NULL,
    data_nascimento DATE NOT NULL,
    documento VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS assinaturas(
    id SERIAL PRIMARY KEY,
    nome_assinatura VARCHAR(255) NOT NULL,
    cargo VARCHAR(100) NOT NULL 
);

CREATE TABLE IF NOT EXISTS diplomas(
    id SERIAL PRIMARY KEY,
    data_conclusao DATE NOT NULL,
    curso VARCHAR(255) NOT NULL,
    carga_horaria INTEGER NOT NULL,
    fk_aluno INTEGER NOT NULL REFERENCES alunos(id),
    fk_assinatura INTEGER NOT NULL REFERENCES assinaturas(id),
    data_emissao DATE NOT NULL DEFAULT CURRENT_DATE,
    pdf_url VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending'
);