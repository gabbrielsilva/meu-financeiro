# Meu Financeiro

Controle financeiro pessoal em Django 5.2 LTS, Django REST Framework e PostgreSQL.
Interface com Templates Django, Bootstrap 5.3.8 local e JavaScript para os seletores
de categoria/subcategoria. Etapas 1, 2 e 3 implementadas, com CSS próprio e gráficos SVG locais.

## Abrir nesta máquina

O ambiente virtual, `.env`, PostgreSQL portátil e banco local já foram preparados.
As migrações foram aplicadas. Não sobrescreva o `.env` existente.

Acesse **http://127.0.0.1:8000/**. Crie sua própria conta em `/cadastro/`.
O PostgreSQL e o Django foram deixados em execução ao concluir a Etapa 3.

Se precisar iniciar novamente, execute da raiz do projeto:

```powershell
& .\.local\postgres\pgsql\bin\pg_ctl.exe -D .local\pgdata status
```

Se o banco estiver parado:

```powershell
& .\.local\postgres\pgsql\bin\pg_ctl.exe -D .local\pgdata -l .local\postgres.log -o '-h 127.0.0.1 -p 55432' -w start
```

Depois:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Se a porta 8000 já estiver ocupada pelo servidor deste projeto, use o servidor
existente ou pare-o no terminal antes de iniciar outro. Para encerrar o banco,
pare primeiro o Django com Ctrl+C e execute:

```powershell
& .\.local\postgres\pgsql\bin\pg_ctl.exe -D .local\pgdata -m fast -w stop
```

A porta do banco local é **55432**, não 5432. O banco portátil não é um serviço
Windows. `.local/`, `.env` e `.venv/` ficam fora do Git. O ambiente virtual atual
usa Python 3.12 fornecido pelo ambiente do Codex; para uso independente, instale
Python 3.12 e recrie o ambiente virtual.

## Instalar em outra máquina

Requisitos: Python 3.12 e PostgreSQL 17 ou 18 com suporte ICU (collation
`und-x-icu`, disponível na distribuição oficial utilizada no Windows).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
Copy-Item .env.example .env
```

Crie um papel PostgreSQL dedicado com login e um banco pertencente a ele usando
pgAdmin ou psql. Não use o superusuário na aplicação. O papel de desenvolvimento
precisa de `CREATEDB` para executar testes; produção não deve ter essa permissão.
Preencha seu `.env`:

| Variável | Conteúdo |
|---|---|
| DJANGO_SECRET_KEY | Chave aleatória exclusiva |
| DJANGO_DEBUG | `true` para desenvolvimento HTTP local |
| DJANGO_ALLOWED_HOSTS | `localhost,127.0.0.1` |
| DJANGO_CSRF_TRUSTED_ORIGINS | Vazia para acesso pela mesma origem |
| POSTGRES_DB | Nome do banco dedicado |
| POSTGRES_USER | Papel proprietário do banco |
| POSTGRES_PASSWORD | Senha local desse papel |
| POSTGRES_HOST | Host do banco, normalmente `127.0.0.1` |
| POSTGRES_PORT | Porta do seu servidor PostgreSQL |

Gere uma chave e copie a saída apenas para o `.env`:

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

`requirements.txt` contém intervalos aceitos; `requirements.lock.txt` fixa as
versões verificadas. O CSS Bootstrap é servido localmente, sem CDN em runtime.

## Funcionalidades e páginas

| Página | Caminho |
|---|---|
| Cadastro | `/cadastro/` |
| Login | `/entrar/` |
| Dashboard autenticado | `/` |
| Configurações (consulta da conta) | `/configuracoes/` |
| Logout (botão Sair, POST) | `/sair/` |
| Categorias | `/categorias/` |
| Nova categoria / edição | `/categorias/nova/`, `/categorias/<id>/editar/` |
| Subcategorias integradas a Categorias (rota compatível) | `/subcategorias/` |
| Nova subcategoria / edição | `/subcategorias/nova/`, `/subcategorias/<id>/editar/` |
| Histórico e filtros | `/movimentacoes/` |
| Nova movimentação / edição | `/movimentacoes/nova/`, `/movimentacoes/<id>/editar/` |
| Confirmar exclusão | `/movimentacoes/<id>/excluir/` |

No cadastro são criadas 6 categorias e 20 subcategorias individuais. A migração
também fornece os padrões às contas anteriores. Receitas/despesas exigem categoria,
subcategoria válida, valor positivo, forma e data não futura. Use vírgula decimal
na interface, por exemplo `85,90`. A API recebe strings decimais com ponto.

Categorias e subcategorias podem ser renomeadas, desativadas e reativadas na edição.
Tipo de categoria e categoria-pai da subcategoria não podem mudar. Desativar uma
categoria bloqueia suas subcategorias para novos lançamentos, sem apagar histórico.
Na edição de um lançamento antigo, é possível manter a classificação inativa já
existente para corrigir valor, data ou descrição. Uma troca exige classificação ativa.
Renomeações aparecem também no histórico. Exclusões de movimentações são lógicas.

O histórico oferece busca por descrição/categoria/subcategoria, mês e ano, período
inicial/final inclusivo, tipo, categoria, subcategoria e paginação de 20 registros.
Os filtros são combinados. Nenhum dado é zerado na virada do mês.

O dashboard mostra receitas, despesas e resultado do mês (receitas menos despesas),
evolução diária, despesas por categoria e as seis movimentações mais recentes do
período. Os cálculos usam Decimal no backend, exclusivamente com movimentações
do usuário autenticado não excluídas. Resultado mensal não representa saldo bancário.
O mês atual é o padrão; meses sem dados apresentam totais zero e estados vazios.
Não foram implementados orçamento, cartões, contas bancárias ou contas pendentes.

## API REST

Prefixo `/api/v1`, sem barra final. Autenticação por sessão e CSRF.

| Método | Rota | Função |
|---|---|---|
| GET | `/auth/csrf` | Obter token e cookie CSRF |
| POST | `/auth/register` | Cadastro com padrões individuais |
| POST | `/auth/login` | Iniciar sessão |
| POST | `/auth/logout` | Encerrar sessão |
| GET | `/auth/me` | Usuário autenticado |
| GET | `/dashboard` | Resumo mensal, séries diárias, categorias e recentes |
| GET, POST | `/categories` | Listar/criar |
| GET, PATCH | `/categories/<id>` | Consultar/renomear/ativar/desativar |
| GET, POST | `/subcategories` | Listar/criar |
| GET, PATCH | `/subcategories/<id>` | Consultar/renomear/ativar/desativar |
| GET, POST | `/transactions` | Histórico paginado/criar |
| GET, PATCH, DELETE | `/transactions/<id>` | Consultar/editar/excluir logicamente |
| GET | `/payment-methods` | Formas permitidas |

Todas as rotas financeiras exigem sessão. O cliente deve preservar cookies e enviar
`X-CSRFToken` nos métodos de escrita. Obtenha novo token após login (rotação CSRF).
Cadastro recebe `email` e `password`, não autentica automaticamente.

Categoria recebe `name`, `type` e opcionalmente `is_active`. Subcategoria recebe
`name`, `category` (ID) e opcionalmente `is_active`. Movimentação recebe `type`,
`amount`, `category`, `subcategory`, `payment_method`, `transaction_date` e
`description` opcional. Datas no formato `AAAA-MM-DD`. Não enviar `user_id`.
Campos desconhecidos ou de leitura são rejeitados nas escritas.

Tipos: `RECEITA`, `DESPESA`. Formas: `PIX`, `DINHEIRO`, `TRANSFERENCIA`, `DEBITO`,
`BOLETO`, `OUTRO`.

Filtros: categorias (`type`, `is_active`); subcategorias (`category`, `type`,
`is_active`); movimentações (`date_from`, `date_to`, `type`, `category`, `subcategory`,
`q`, `month`, `year`, `page`). Em movimentações, `month` e `year` devem ser enviados
juntos; datas inicial/final continuam válidas e restringem também o mês selecionado.
Dashboard aceita `month` (1–12) e `year` (1–9998), com padrões do mês/ano atual;
valores financeiros são strings decimais. Não aceita `user_id`.
`is_active` indica o estado próprio da subcategoria; `effective_active`
na resposta considera também o estado da categoria-pai.

Respostas: 201 criação, 200 consulta/edição/login, 204 exclusão/logout, 400 validação,
403 sessão ausente/CSRF, 404 registro de terceiro/inexistente/excluído, 429 limite de
requisições. Não há DELETE para categorias/subcategorias.

## Testes

Com PostgreSQL em execução e `.env` configurado:

```powershell
.\.venv\Scripts\python.exe manage.py test --verbosity 2
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m pip check
```

O Django cria e remove `test_<POSTGRES_DB>`. Os 62 testes cobrem autenticação,
CSRF, páginas privadas, padrões individuais, cadastro atômico, isolamento de
usuários, vínculos e unicidade no PostgreSQL, validação financeira, filtros,
paginação, edição histórica, soft delete e dashboard mensal (totais, calendário,
isolamento, vazios, agrupamentos, recentes e atualização após edição). Veja `docs/validation.md` e execute
`docs/manual-test.md` no navegador.

## Estrutura e decisões

```text
apps/
  accounts/       # Usuários, serviços de cadastro, API e telas de autenticação
  categories/     # Modelos, padrões, serializers, API, formulários, telas e testes
  transactions/   # Modelos, serializers, API, consultas, formulários, telas e testes
  reports/        # Dashboard: cálculos, período, API, tela e testes
config/           # Configurações e rotas
static/           # CSS próprio, ícones SVG, navegação, seletores e Bootstrap local
templates/        # Base e páginas Django
docs/             # Decisões, validação e checklist
```

As páginas e a API usam os mesmos serializers para validar/salvar as regras de
negócio. Consultas sempre limitam pelo usuário autenticado. Constraints compostas
no PostgreSQL reforçam proprietário, tipo e vínculo da subcategoria; dinheiro usa
NUMERIC(14,2). Senhas usam Argon2. Logout exige POST e CSRF. Consulte
`docs/decisions.md` para limites e decisões históricas.

O projeto continua sendo um ambiente de desenvolvimento. Antes de publicação,
revise HTTPS/proxy, `check --deploy`, limitação de tentativas compartilhada,
monitoramento e backups. Não há integração bancária nem armazenamento de cartões.
