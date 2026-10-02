# Decisões da Etapa 1

> Registro histórico. As decisões da Etapa 2, abaixo, substituem as referências a módulos vazios e ausência de padrões.

- Monólito Django com API DRF e PostgreSQL, inclusive nos testes.
- Login por e-mail normalizado em letras minúsculas; unicidade também protegida no banco.
- Usuário próprio na primeira migração. `date_joined` representa a criação.
- Sessões persistidas no banco, Argon2 e CSRF em todos os POSTs, inclusive anônimos.
- Cadastro não inicia sessão automaticamente. Login é uma operação separada.
- Endpoint auxiliar GET `/api/v1/auth/csrf` fornece o token para clientes de mesma origem.
- Rotas privadas por padrão. Resposta anônima 403 segue a autenticação por sessão do DRF.
- Throttling local por IP serve ao desenvolvimento com um processo. Antes de publicação,
  adotar limitação compartilhada no proxy/cache; throttling do DRF não garante proteção
  contra força bruta em múltiplos processos.
- Módulos futuros são apenas pacotes vazios. Não há classificações padrão nesta etapa.
- Regra aprovada para etapa futura: categoria e subcategoria obrigatórias para toda
  movimentação, com vínculo válido entre elas; nunca usar “Sem subcategoria”.

## Etapa 2

- Templates Django e Bootstrap 5.3.8 servido localmente. Não existe outro frontend.
- Páginas e API reutilizam serializers de escrita, consulta de histórico e serviço
  de soft delete. Formulários Django tratam apresentação e conversão de valores locais.
- Cadastro, categorias e subcategorias padrão são criados em uma transação atômica.
  A migração preenche padrões para contas da Etapa 1. Seu reverso não apaga dados.
- Cada conta nova recebe exatamente 6 categorias e 20 subcategorias.
- Categorias têm tipo imutável; subcategorias têm categoria-pai imutável na API/UI.
- Unicidade de nomes considera caixa e espaços nas extremidades. Campos de nome
  usam collation Unicode ICU `und-x-icu`, evitando diferenças com acentos em bancos
  criados com locale C. Acentos continuam significativos: “Agua” e “Água” são nomes distintos.
- FKs compostas impedem vínculos entre usuários diferentes, categoria de outro tipo
  e subcategoria incompatível mesmo em escritas diretas no banco.
- Categoria e subcategoria são obrigatórias. Somente classificações ativas podem
  ser selecionadas. Um registro histórico pode manter sua classificação inativa
  enquanto valor, data ou descrição são corrigidos.
- Dinheiro usa Decimal/NUMERIC(14,2), valores positivos, sem arredondamento silencioso
  de entradas com mais de duas casas. Data futura é validada contra America/Sao_Paulo.
- Exclusão lógica define `deleted_at` e atualiza `updated_at`. Listagem, leitura,
  edição e nova exclusão não acessam registros já excluídos. Sem restauração nesta etapa.
- Histórico: datas inclusivas, filtros por tipo/categoria/subcategoria, 20 registros
  por página e ordenação estável por data decrescente e ID decrescente.
- Exclusão visual exige confirmação e POST com CSRF; logout também exige POST.
- Relatórios e dashboard financeiro continuam fora do escopo.

## Etapa 3 — Interface e dashboard

- Templates Django e Bootstrap local preservados; CSS próprio, sprite SVG e JavaScript
  pequeno para navegação móvel. Nenhuma dependência ou migração adicionada.
- Dashboard usa uma consulta filtrada por usuário, mês e soft delete. Os registros
  desse mês formam um único snapshot para totais, agrupamentos e recentes. Agregação
  em Python com Decimal é simples para o volume pessoal previsto; se o volume crescer,
  medir antes de substituir por agregações SQL. Não há tabela de resumo mensal.
- Gráficos SVG renderizados no servidor: evolução diária (não acumulada) e distribuição
  de despesas. Valores também acessíveis em texto/tabela. Frontend não calcula totais.
- Resultado do mês significa receitas menos despesas, sem representar saldo bancário.
- Nova movimentação permanece página própria, reutilizando validações e seletores.
- Subcategorias integradas visualmente às categorias; rota antiga e APIs preservadas.
- Configurações apenas consulta informações da conta. Sem nova edição de perfil.
- Busca textual e mês/ano complementam os filtros existentes, combinados por interseção.

## Preparação para produção — 01/10/2026

- Dois contextos via DJANGO_ENV externo, sem mudar os comandos locais existentes.
  Produção não lê .env; DEBUG=True, chave fraca/ausente, hosts não explícitos e
  configuração TLS ausente para PostgreSQL impedem a inicialização.
- WhiteNoise 6.12.0 é a única dependência nova: estáticos locais com manifesto,
  compressão e cache. Demais versões preservadas. Removido somente o comentário
  sourceMappingURL do Bootstrap, pois o mapa não distribuído impedia collectstatic.
- Proxy HTTPS exige opt-in após validar sanitização do cabeçalho e isolamento de rede.
  HSTS/subdomínios/preload aguardam domínio e HTTPS reais. Avisos não são silenciados.
- Logs JSON em stderr conservam tipo e locais de exceção sem mensagens/payloads
  potencialmente sensíveis. Páginas genéricas 400/403/404/500 não dependem de banco
  ou estáticos para informar o erro.
- Sem mudanças financeiras, migrações, plataforma externa, deploy, commit ou push.

## Correções após revisão técnica — 01/10/2026

- Controle de concorrência no salvamento compartilhado: bloqueio de linha e comparação
  de updated_at, rejeitando snapshots ultrapassados/excluídos. Soft delete faz UPDATE
  limitado aos campos de exclusão. Sem reintroduzir valores financeiros antigos.
- Limites de autenticação atômicos no PostgreSQL, compartilhados entre workers e entre
  HTML/API. Proxy IP explícito, X-Forwarded-For não confiável ignorado, HMAC nas chaves,
  indisponibilidade do contador retorna 503. Sem nova dependência externa.
- Entrada JSON de tipo inesperado retorna 400. Erros de integridade são registrados,
  com SQLSTATE seguro em produção. Removido template legado sem uso.
- Migração aditiva accounts.0002_authratebucket, sem alteração de dados financeiros.
- Recuperação de senha, idempotência de criação e novas funcionalidades seguem fora
  desta correção. Infraestrutura e backup/restauração dependem da hospedagem futura.

## Reenvio e formulários antigos — 01/10/2026

- request_id UUID obrigatório na criação, único por usuário; hash dos campos validados
  identifica reenvio compatível. Criações concorrentes da mesma conta são serializadas
  com bloqueio de linha do usuário, sem dependência adicional. Reenvio válido retorna
  o registro atual existente; não recria excluídos nem reaplica dados de criação.
- expected_version obrigatório em edição e exclusão de movimentações, baseado no
  updated_at consultado. Campos ocultos na interface; contrato explícito na API.
- Conflito mantém dados digitados e oferece reabertura por GET. Confirmação de exclusão
  desatualizada exige nova confirmação com dados atuais. Nenhuma mesclagem automática.
- Migração aditiva transactions.0003: campos técnicos nulos/vazios nos dados anteriores
  e constraint de unicidade, sem modificar valores financeiros ou datas existentes.
- Escopo de formulários antigos: movimentações. Categorias/subcategorias mantêm somente
  a proteção de requisições simultâneas da etapa anterior.
