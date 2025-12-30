# Configuração do Ambiente

Este documento descreve como configurar o ambiente de desenvolvimento para o projeto SGE.

## Requisitos

- Python >= 3.14
- Gerenciador de pacotes: uv (ou pip)

## Instalação

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd SGE
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate  # No Linux/Mac
# ou
.venv\Scripts\activate     # No Windows
```

### 3. Instale as dependências

O projeto utiliza o gerenciador de pacotes `uv`, mas também pode ser configurado com `pip`:

#### Com uv (recomendado):
```bash
uv sync
```

#### Com pip:
```bash
pip install -r requirements.txt
```

### 4. Execute as migrações iniciais

```bash
python manage.py migrate
```

### 5. Inicie o servidor de desenvolvimento

```bash
python manage.py runserver
```

## Dependências

O projeto utiliza as seguintes bibliotecas principais:

- Django >= 6.0
- Django Rest Framework >= 3.16.1
- Django Rest Framework Simple JWT >= 5.5.1
- Flake8 >= 7.3.0
- Pylint >= 4.0.4

## Banco de Dados

O projeto utiliza SQLite como banco de dados padrão, com o arquivo `db.sqlite3` na raiz do projeto.

## Linting

O projeto utiliza Flake8 para verificação de estilo de código. Para executar o linting:

```bash
flake8 .
```