# Guia de Estilo

Este documento descreve os padrões de codificação e estilo usados no projeto SGE.

## PEP 8

O projeto segue as diretrizes da [PEP 8](https://pep8.org/), o guia oficial de estilo para código Python.

## Linting com Flake8

O projeto usa [Flake8](https://flake8.pycqa.org/en/latest/) para verificação de estilo de código. A configuração está no arquivo `.flake8` na raiz do projeto.

### Configuração do Flake8

A configuração específica do projeto está definida no arquivo `.flake8`, que define regras como:

- Limites de comprimento de linha
- Verificações de estilo específicas
- Exceções a regras específicas

## Nomenclatura

### Módulos e Pacotes
- Nomes em minúsculas com sublinhados se necessário (ex: `products`, `inflows`)

### Classes
- Nomes em PascalCase (ex: `ProductView`, `SupplierModel`)

### Funções e Variáveis
- Nomes em snake_case (ex: `get_product`, `calculate_total`)

### Constantes
- Nomes em maiúsculas com sublinhados (ex: `MAX_QUANTITY`)

## Imports

- Imports devem ser organizados em seções: bibliotecas padrão, bibliotecas de terceiros e imports locais
- Cada seção deve ser separada por uma linha em branco
- Imports devem ser colocados no topo do arquivo

## Comentários

- Comentários devem ser claros e objetivos
- Use comentários para explicar decisões complexas ou não óbvias
- Use docstrings para documentar módulos, classes e funções