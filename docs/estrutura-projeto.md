# Estrutura do Projeto

Este documento descreve a organização dos arquivos e pastas do projeto SGE (Sistema de Gestão de Estoque).

## Visão Geral

```
SGE/
├── .flake8          # Configuração do linter Flake8
├── .gitignore       # Arquivos e diretórios ignorados pelo Git
├── .python-version  # Versão do Python usada no projeto
├── db.sqlite3       # Banco de dados SQLite (arquivo binário)
├── manage.py        # Ponto de entrada para comandos Django
├── pyproject.toml   # Configurações do projeto Python
├── README.md        # Documentação principal do projeto
├── requirements-dev.txt  # Dependências de desenvolvimento
├── requirements.txt # Dependências de produção
├── uv.lock          # Lock file do gerenciador de pacotes uv
├── app/            # Código principal da aplicação
├── authentication/ # Módulo de autenticação
├── brands/         # Módulo de marcas
├── categories/     # Módulo de categorias
├── inflows/        # Módulo de entradas
├── outflows/       # Módulo de saídas
├── products/       # Módulo de produtos
├── suppliers/      # Módulo de fornecedores
└── .venv/          # Ambiente virtual Python
```

## Descrição dos Módulos

### app/
Aplicação principal do Django que pode conter configurações gerais do projeto.

### authentication/
Módulo responsável pela autenticação de usuários e controle de acesso.

### brands/
Módulo que gerencia as marcas dos produtos.

### categories/
Módulo que gerencia as categorias dos produtos.

### inflows/
Módulo que gerencia as entradas de estoque (compras, devoluções, etc.).

### outflows/
Módulo que gerencia as saídas de estoque (vendas, devoluções de clientes, etc.).

### products/
Módulo que gerencia os produtos no sistema.

### suppliers/
Módulo que gerencia os fornecedores.