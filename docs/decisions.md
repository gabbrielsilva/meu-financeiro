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
