# Validação da Etapa 1

Executada em 29/09/2026 com Python 3.12.14, Django 5.2.17, DRF 3.16.1 e PostgreSQL
portátil 17.11, usando banco e papel dedicados ao desenvolvimento.

- `manage.py migrate --noinput`: todas as migrações aplicadas.
- `manage.py test --verbosity 2`: 12 testes aprovados em 3,614 segundos.
- `manage.py check`: nenhum problema identificado.
- `manage.py makemigrations --check --dry-run`: nenhuma alteração pendente.
- `pip check`: nenhuma dependência incompatível.
- `.env`, `.venv` e `.local` confirmados como ignorados pelo Git.

O banco de testes foi criado e removido pelo Django. O banco de desenvolvimento
permanece com o esquema inicial, sem dados financeiros e sem usuários cadastrados.
Não foram implementadas funcionalidades da Etapa 2 nem realizadas validações
de uma implantação em produção.

## Etapa 2 — 30/09/2026

- Migrações de categorias, subcategorias e movimentações aplicadas no PostgreSQL 17.11.
- `manage.py test --verbosity 1`: **45 testes aprovados**, incluindo os 12 da Etapa 1,
  em 7,490 segundos. Banco de testes criado e removido pelo Django.
- Primeira rodada identificou e corrigiu: filtro booleano omitido interpretado como
  falso em QueryDict, formulário vazio não vinculado durante throttling e comparação
  sem suporte Unicode no locale C. A suíte completa passou após os ajustes.
- Verificação pelo navegador com conta fictícia isolada: cadastro (incluindo erro
  de senha semelhante ao e-mail), login, padrões iniciais, categoria e subcategoria,
  receita, despesa, edição, confirmação de exclusão, logout e persistência após login.
- Layout verificado em desktop 1366×900 e viewport móvel 390×844. Tabelas usam
  rolagem horizontal em telas estreitas. Assets são locais.
- O banco e o servidor foram mantidos em execução para revisão do usuário.
- Verificações finais: `manage.py check` sem problemas, `makemigrations --check
  --dry-run` sem alterações e `pip check` sem dependências incompatíveis. `.env`,
  `.venv` e `.local` continuam ignorados pelo Git.
- Os registros fictícios do teste de navegador pertencem somente à conta
  `verificacao.etapa2.0930@example.test`, sem acesso a dados de outras contas.

## Etapa 3 — Redesign e dashboard

- Suíte completa: **62 testes aprovados em 9,976 segundos**, incluindo os 45
  anteriores e 17 testes novos. Banco de testes PostgreSQL criado e removido.
- `manage.py check`: nenhum problema; `makemigrations --check --dry-run`: nenhuma
  alteração; `pip check`: nenhuma incompatibilidade. Migrações já aplicadas.
- `.env`, `.venv` e `.local` continuam ignorados pelo Git. Nenhuma dependência nova.
- Navegador: login, dashboard, troca para mês vazio, Ver todas mantendo período,
  histórico, formulário, categorias integradas, configurações e logout verificados.
- Revisão visual desktop (1440×1000), tablet (820×1000), celular (390×844).
  Dimensões do DOM também verificadas em notebook (1366×900). A captura do navegador
  apresentou artefato ao alternar viewport; restaurar o tamanho padrão normalizou
  a imagem, enquanto as dimensões reais do DOM permaneceram corretas.
- Foram utilizados os registros já existentes da conta isolada de QA da Etapa 2.
  Nenhuma movimentação fictícia adicional foi inserida no banco de desenvolvimento.
  Totais, distribuição com despesas e mutações foram cobertos no banco de testes.
- Sessão de QA encerrada; login disponível para revisão. PostgreSQL e Django ativos.
- Sem bloqueios conhecidos. Verificação de produção não faz parte desta etapa.
