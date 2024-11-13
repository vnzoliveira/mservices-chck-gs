# 🎓 Diploma Generator PDF

Um gerador de diplomas em PDF utilizando tecnologias modernas de microsserviços.

## 🚀 Tecnologias

- Python
- RabbitMQ
- Redis
- MinIO

## 🛠️ Primeiros Passos

### Pré-requisitos

- Docker instalado em sua máquina

### Instalação

1. Clone o repositório
2. Navegue até o diretório do projeto
3. Execute o comando:
```bash
docker-compose up --build
```

## 📌 Como Usar

### Testando a API

Acesse a documentação interativa da API em:
```
http://localhost:8000/docs
```

#### Exemplos de Requisições

##### POST - Gerar Diploma
```bash
curl -X 'POST' \
  'http://localhost:8000/diplomas' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "data_conclusao": "2024-11-13",
    "curso": "Economia",
    "carga_horaria": 2000,
    "aluno": {
      "nome": "Larissa Andrade",
      "nacionalidade": "Russa",
      "estado": "RS",
      "data_nascimento": "2004-11-01",
      "documento": "52576967940"
    },
    "assinatura": {
      "nome_assinatura": "Dr.PHD Marco Silveira",
      "cargo": "Reitor Líder de Economia & RI"
    }
  }'
```

##### GET - Consultar Diploma
```
http://localhost:8000/diplomas/{id_do_diploma_gerado}
```

## 📊 Monitoramento

### RabbitMQ Dashboard
- URL: `http://localhost:15672`
- Usuário: `admin`
- Senha: `admin_password`

### MinIO Console
- URL: `http://localhost:9001`
- Usuário: `minio_admin`
- Senha: `minio_password`

## 📄 Acessando os PDFs

Os diplomas gerados podem ser acessados através do console do MinIO na porta 9001.
