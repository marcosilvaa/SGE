# Convenções de Commit

Este documento descreve os padrões para mensagens de commit no projeto SGE.

## Formato Geral

As mensagens de commit seguem o formato convencional para manter consistência e facilitar a geração de changelogs:

```
<tipo>[escopo opcional]: <descrição curta>

[corpo opcional]

[rodapé opcional]
```

## Tipos de Commit

- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Atualizações na documentação
- `style`: Mudanças que não afetam o significado do código (espaços em branco, formatação, falta de ponto e vírgula, etc.)
- `refactor`: Mudança que não corrige um bug nem adiciona uma funcionalidade
- `perf`: Mudança de código que melhora o desempenho
- `test`: Adicionando testes ausentes ou corrigindo testes existentes
- `chore`: Outras mudanças que não modificam o código-fonte ou os testes, como atualizações de build, configurações de administrador, etc.

## Escopo

O escopo é opcional e deve referenciar o módulo ou componente afetado (por exemplo: `auth`, `products`, `categories`, etc.).

## Exemplos

```
feat(products): adicionar validação de SKU único

Adiciona validação para garantir que cada produto tenha um SKU único
no sistema de gestão de estoque.
```

```
fix(categories): corrigir erro de permissão

Corrige erro onde usuários sem permissão adequada conseguiam
editar categorias existentes.
```

```
docs: atualizar documentação de configuração do ambiente

Atualiza o arquivo README com instruções mais claras para
configurar o ambiente de desenvolvimento.
```

```
refactor(auth): refatorar sistema de autenticação

Refatora o módulo de autenticação para seguir melhores práticas
Django REST Framework.
```