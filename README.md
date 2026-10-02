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

O Django cria e remove `test_<POSTGRES_DB>`. Os 91 testes cobrem autenticação,
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

## Preparação para produção (sem deploy)

A aplicação mantém um único módulo de configuração, com dois contextos explícitos.
`DJANGO_ENV` é lido **do ambiente do processo antes de qualquer arquivo**:

- Ausente ou `development`: lê o `.env` local, sem substituir variáveis externas.
  Continue usando os comandos locais acima; seu `.env` existente não precisa mudar.
- `production`: não lê `.env`, exige secrets externos, hosts explícitos e decisão
  explícita de TLS do PostgreSQL. `DJANGO_DEBUG=true` impede a inicialização.
  `DEBUG` é False quando omitido ou definido como `false`.

No serviço futuro, configure obrigatoriamente `DJANGO_ENV=production` no ambiente
externo. Definir essa variável somente em um `.env` não seleciona produção.
Nunca copie o `.env` local para a hospedagem nem reutilize sua chave de desenvolvimento.

### Variáveis de ambiente

| Variável | Desenvolvimento | Produção |
|---|---|---|
| `DJANGO_ENV` | Ausente ou `development` no processo | `production`, obrigatório no processo |
| `DJANGO_DEBUG` | `true` no `.env` para HTTP local | Ausente/`false`; `true` é rejeitado |
| `DJANGO_SECRET_KEY` | Obrigatória no `.env` ou processo | Externa, aleatória e exclusiva; mínimo 50 caracteres |
| `DJANGO_ALLOWED_HOSTS` | Hosts locais existentes | Obrigatória, hosts exatos separados por vírgula, sem protocolo/curingas |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Pode ficar vazia | Vazia na mesma origem; se necessário, origens HTTPS exatas com protocolo |
| `POSTGRES_DB` | Nome do banco local | Banco dedicado externo |
| `POSTGRES_USER` | Papel local | Papel dedicado, não superusuário |
| `POSTGRES_PASSWORD` | Secret local | Secret externo |
| `POSTGRES_HOST` | Host local | Host fornecido pela infraestrutura |
| `POSTGRES_PORT` | Porta local | Porta fornecida pela infraestrutura |
| `POSTGRES_SSLMODE` | Ausente/vazio usa `prefer` | Obrigatório; preferir `verify-full` para banco remoto |
| `POSTGRES_SSLROOTCERT` | Opcional | Caminho da CA exigida pelo provedor, especialmente em `verify-full` |
| `DJANGO_TRUST_PROXY_HEADERS` | Não utilizado | `false` por padrão; `true` somente com proxy confiável validado |
| `DJANGO_HSTS_SECONDS` | Não utilizado | `0` inicialmente; ampliar gradualmente após validar HTTPS |

`require` cifra sem verificar a identidade como `verify-full`; `disable` só deve
ser uma decisão documentada para conexão local/rede privada protegida da futura
plataforma. A aplicação exige a escolha, sem presumir a topologia. Certificados e
chaves devem ser provisionados externamente. Não habilitar `CREATEDB` no papel de
runtime em produção; essa permissão é usada somente pelo ambiente de testes.

### HTTPS, proxy e sessões

Produção força redirecionamento HTTPS, cookies de sessão/CSRF Secure, sessão
HttpOnly e SameSite=Lax, proteção CSRF, validação de hosts, nosniff e bloqueio de
frames. Autenticação, Argon2 e isolamento por usuário foram preservados.

Se o proxy termina TLS, habilite `DJANGO_TRUST_PROXY_HEADERS=true` **somente** quando
esse proxy remove o `X-Forwarded-Proto` recebido do cliente e define seu próprio
valor, e o servidor Django não pode ser acessado diretamente pela internet.
Sem essa configuração, um proxy que encaminha HTTP pode gerar ciclos de redirect.
Não há confiança automática em cabeçalhos enviados pelo cliente.

HSTS começa desativado para não comprometer um domínio antes da validação de TLS.
Após validar, comece com um prazo curto (por exemplo, 3600 segundos) e aumente.
Subdomínios e preload permanecem desabilitados até uma revisão de domínio própria.

### Estáticos e processo de publicação futuro

WhiteNoise 6.12.0 serve os arquivos locais coletados, com nomes versionados por hash
e compressão, após SecurityMiddleware. Não exige CDN ou serviço adicional.
`STATIC_URL=/static/`, `STATIC_ROOT=staticfiles/` (ignorado pelo Git).
Desenvolvimento mantém o serviço de estáticos do `runserver`.

Com as variáveis **de produção já injetadas externamente**:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py check --deploy
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --check
```

No deploy futuro, aplicar migrações pendentes com `migrate --noinput` após backup,
antes de liberar tráfego. Não executar migrações de produção contra o banco local.
O artefato publicado deve conter `staticfiles/` gerado com a configuração de produção.
Use servidor WSGI de produção apontando para `config.wsgi:application`, escolhido
conforme a plataforma; **não use runserver em produção**. Nenhum servidor/plataforma
externa foi contratado ou configurado nesta etapa.

### Logs e páginas de erro

Logs de produção vão para stderr em JSON: data/hora, nível, logger, local de origem,
status HTTP e tipo/locais da exceção. Não incluem mensagens livres, mensagens de
exceção, SQL, parâmetros, corpos, cookies, variáveis locais ou dados de requisição.
Essa escolha mantém a localização dos erros e evita que mensagens de bibliotecas
exponham credenciais ou valores financeiros. Não há arquivo local de log obrigatório.
Logs de acesso do futuro proxy/servidor WSGI precisam de revisão separada (URLs e
query strings podem conter dados). Retenção/acesso aos logs cabem à plataforma.
As páginas 400/403/404/500 são genéricas, independentes de banco e de CSS. A resposta
CSRF existente continua genérica. `DEBUG=True` permanece restrito ao desenvolvimento.

### Verificação segura de produção

```powershell
.\.venv\Scripts\python.exe manage.py test config --verbosity 2
.\.venv\Scripts\python.exe manage.py test --verbosity 1
```

Os testes de configuração criam secrets aleatórios apenas na memória, usam processo
isolado com `DJANGO_ENV=production`, banco inacessível e coletam estáticos em diretório
temporário. Conferem inicialização, guardas de configuração, HTTPS, CSRF, conteúdo
estático e erros sem debug. Não alteram `.env` nem acessam o banco de desenvolvimento.
A suíte completa usa o banco temporário de testes PostgreSQL, como anteriormente.

`check --deploy` no ambiente local HTTP acusa DEBUG, redirect e cookies Secure,
além de HSTS: são diferenças esperadas, não devem ser corrigidas ativando HTTPS local.
Em produção, HSTS desabilitado gera W004; após habilitá-lo, W005/W021 permanecem por
subdomínios/preload ainda não aprovados. Nenhum aviso foi silenciado no código.

### Checklist antes do deploy

- Escolher plataforma, domínio e servidor WSGI; configurar explicitamente o modo produção.
- Provisionar secrets exclusivos e banco PostgreSQL com ICU, privilégios mínimos e TLS.
- Definir backup e testar restauração; revisar migrações antes da publicação.
- Configurar HTTPS, hosts, proxy confiável e bloqueio de acesso direto ao Django.
- Validar HSTS, domínio e subdomínios antes de aumentar sua abrangência.
- Validar IPs dos proxies e limitação adicional de tráfego na borda; os limites de
  autenticação da aplicação agora são atômicos e compartilhados pelo PostgreSQL.
- Executar testes/checks, coletar estáticos e verificar assets no artefato final.
- Definir supervisão/reinício do serviço, logs, retenção, monitoramento e limpeza
  periódica de sessões expiradas (`clearsessions`).
- Testar login, logout, CSRF, isolamento, erros, dashboard e mobile na URL HTTPS real.

Referências: [checklist Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/),
[proxy HTTPS](https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header),
[WhiteNoise](https://whitenoise.readthedocs.io/en/stable/django.html).


## Correções da revisão técnica

- Escritas de categorias, subcategorias e movimentações bloqueiam o registro no
  PostgreSQL e comparam `updated_at` com a versão lida pela solicitação. Se outra
  solicitação já gravou/excluiu, a operação retorna erro de validação e pede recarga.
  O controle cobre requisições sobrepostas e, para movimentações, a versão enviada
  pelo formulário protege também telas abertas antes de outro salvamento.
- A exclusão usa UPDATE restrito a `deleted_at`/`updated_at`, preservando valores
  financeiros mesmo quando a instância recebida é antiga.
- Listas, strings e números no lugar de objetos JSON geram 400, não TypeError/500.
- Conflitos de integridade agora são registrados. Logs de produção preservam tipo,
  local da exceção e SQLSTATE quando disponível, sem mensagens ou dados pessoais.
- O template antigo de subcategorias sem uso foi removido; a rota antiga segue válida.

### Limites de autenticação

HTML e API compartilham contadores no PostgreSQL: login 5 tentativas/minuto e cadastro
10/hora por IP, em janelas fixas. Uma transação com bloqueio de linha serializa as
atualizações entre processos. A chave é HMAC com a SECRET_KEY; não guardamos IP em
texto. Limites não são zerados ao reiniciar workers nem ao alternar HTML/API.
Janelas fixas podem permitir dois lotes perto de uma virada; não são mitigação de DDoS.
Uma falha no banco bloqueia a autenticação com 503, sem ignorar a proteção.

`DJANGO_TRUSTED_PROXY_IPS` é opcional (vazio por padrão) e contém IPs exatos separados
por vírgula. Sem ela, X-Forwarded-For é ignorado. Com ela, a conexão precisa vir de um
proxy autorizado e a cadeia é percorrida da direita para a esquerda até o primeiro
IP não confiável. Configure somente proxies controlados que sanitizam/acrescentam
corretamente esse cabeçalho. Esta opção é separada de DJANGO_TRUST_PROXY_HEADERS,
que trata apenas HTTPS. O backend não deve ser exposto diretamente pela hospedagem.
Usuários na mesma rede compartilham o limite; aguarde a janela expirar se o atingir.

A migração `accounts.0002_authratebucket` apenas cria a tabela técnica dos contadores.
Aplicar `manage.py migrate --noinput` antes de iniciar os workers com esta versão.
Agendar diariamente na futura plataforma, junto à limpeza de sessões:

```powershell
.\.venv\Scripts\python.exe manage.py clear_auth_limits
.\.venv\Scripts\python.exe manage.py clearsessions
```

`clear_auth_limits` remove apenas contadores expirados, preservando bloqueios ativos.
Não foi configurado agendamento nesta máquina nem na hospedagem.

Continuam pendentes de decisões futuras: backup/restauração, servidor WSGI, domínio,
TLS e proxy reais, recuperação de senha e política de cadastro. Idempotência de
movimentações e controle de formulários antigos foram acrescentados na etapa abaixo.


## Proteção de reenvios e formulários antigos

Novas movimentações exigem `request_id` (UUID). O formulário gera e transporta esse
identificador em campo oculto; não exige nenhuma entrada adicional do usuário.
O mesmo envio válido repetido com a mesma chave e os mesmos dados retorna o mesmo
registro (API mantém 201), sem somar novamente no dashboard. Duas compras legítimas
iguais usam chaves diferentes. A chave é limitada ao usuário e persistida junto ao
registro, com constraint única e serialização das criações por usuário no PostgreSQL.

Reutilizar uma chave com dados diferentes ou de movimentação já excluída retorna 400.
A validação de categorias/valores continua ocorrendo antes da recuperação do envio;
se a classificação ficou inativa, o reenvio pode ser rejeitado, mas não gera duplicata.
O registro retornado é a versão atual: uma repetição não desfaz edições posteriores.
Registros antigos permanecem com chave nula, sem alteração nos valores ou datas.

PATCH e DELETE de movimentações exigem `expected_version`, contendo exatamente o
`updated_at` recebido na última consulta. Ausência ou versão ultrapassada não grava.
A interface envia esse valor em campo oculto e preserva os campos digitados em um
conflito de edição. O link de reabertura faz GET dos dados atuais e descarta os campos
não salvos somente após a ação do usuário. Uma confirmação de exclusão antiga volta
à confirmação atualizada e exige outra ação explícita, sem excluir automaticamente.

Estes campos atualizam o contrato da API de movimentações: clientes devem gerar uma
chave por criação e reutilizá-la apenas nos retries; devem consultar a versão antes
de editar/excluir. Categoria/subcategoria não ganharam controle de formulário antigo
nesta etapa (mantêm a proteção contra requisições simultâneas).

Aplicar `manage.py migrate --noinput` para a migração
`transactions.0003_transaction_request_fingerprint_and_more`. Ela acrescenta dois
campos técnicos e uma constraint, preservando movimentações existentes. Não há nova
biblioteca. A proteção depende do backend, não de desabilitar o botão no navegador.
