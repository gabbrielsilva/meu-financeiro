# Checklist de teste manual — Etapa 2

Abra http://127.0.0.1:8000/ com PostgreSQL e Django em execução.

- [ ] Crie sua conta em “Criar conta”, usando senha de pelo menos 12 caracteres.
- [ ] Faça login; confirme a página inicial e o botão “Sair”.
- [ ] Confira as 6 categorias e 20 subcategorias padrão.
- [ ] Crie uma categoria de despesa “Saúde” e uma subcategoria “Consulta”.
- [ ] Registre despesa de R$ 85,90, usando Saúde / Consulta, Pix e a data atual.
- [ ] Registre receita de R$ 600,00, usando Trabalho / Serviço.
- [ ] Confira os dois lançamentos no histórico. Filtre por tipo, datas e categoria.
- [ ] Edite um valor e confira a alteração no histórico.
- [ ] Abra a exclusão; cancele primeiro. Depois confirme e verifique que o registro saiu da lista.
- [ ] Renomeie uma categoria e confira o nome atualizado no histórico.
- [ ] Desative uma categoria/subcategoria pela edição; confira que não está disponível em um novo lançamento.
- [ ] Edite um lançamento antigo dessa classificação inativa, mantendo-a e corrigindo apenas a descrição.
- [ ] Reative a classificação e confira que voltou a aparecer.
- [ ] Tente salvar valor zero/negativo, omitir subcategoria ou usar data futura; verifique o erro.
- [ ] Saia e entre novamente; confirme que os dados permanecem.
- [ ] Em uma janela privada, crie outra conta e confirme que ela não vê seus lançamentos nem suas categorias personalizadas.
- [ ] Em tela estreita, confira a navegação e os formulários; o histórico permite rolagem horizontal da tabela.

Todos os dados devem representar apenas exemplos durante o teste. A conta fictícia
utilizada na verificação automatizada pelo navegador está isolada das suas contas.

## Etapa 3 — Redesign e dashboard

1. Entre em sua conta e confira Dashboard: receitas, despesas e resultado do mês.
2. Troque mês/ano e confira um período vazio; valores devem ser zero, sem dados fictícios.
3. Confira evolução diária, despesas por categoria e detalhes por subcategoria.
4. Clique Ver todas: o histórico deve manter mês/ano. Combine busca, tipo e categoria;
   abra Mais filtros para intervalo de datas/subcategoria e depois limpe os filtros.
5. Crie receita e despesa: categoria deve acompanhar o tipo e subcategoria deve ser
   obrigatória e pertencer à categoria. Confira reflexo nos totais do dashboard.
6. Edite valor/data e confira o mês correto. Exclua uma movimentação de teste pela
   confirmação: ela deve sumir do histórico, dos recentes e dos totais.
7. Em Categorias, crie/edite/desative/reative categoria e subcategoria, verificando
   os vínculos e a restrição de classificações inativas nos novos lançamentos.
8. Abra Configurações e confira os dados da própria conta. Saia e tente abrir o
   dashboard: deve solicitar login.
9. Reduza a janela para celular: teste menu, formulários, filtros e cartões do
   histórico; volte para tablet/notebook/desktop e confira gráficos e tabelas.

## Correções de integridade e autenticação

- Salve/edite/exclua uma movimentação de teste e confira os totais; os testes
  automatizados cobrem a sobreposição de requisições que é difícil simular manualmente.
- Caso receba mensagem de conflito, recarregue e confira a versão mais recente antes
  de reenviar. Formulários de movimentação agora também carregam sua versão original.
- Faça cinco tentativas de login de teste: a próxima deve ser limitada. Alterne
  HTML/API e confira que o contador é compartilhado. Aguarde um minuto para liberar.
- Confirme IPs e cabeçalhos do proxy no ambiente de hospedagem antes de publicá-lo.


## Reenvios e formulários antigos

1. Abra uma nova movimentação, preencha e envie. Reenvie o mesmo POST pelo histórico
   do navegador: deve continuar existindo apenas uma movimentação e um valor no total.
2. Abra outra nova movimentação e registre intencionalmente os mesmos dados: deve
   ser aceita, pois é outro envio com outra chave.
3. Abra a mesma edição em duas abas. Salve um valor na primeira. Na segunda, tente
   salvar outro valor: deve mostrar conflito e manter o valor salvo pela primeira.
4. Na tela de conflito, confira que o digitado continua visível; clique Reabrir o
   formulário com os dados atuais para carregar a versão atual antes de editar.
5. Abra uma confirmação de exclusão, altere a movimentação em outra aba e confirme
   a tela antiga: deve exigir nova confirmação, exibindo os dados atuais.
6. Confira dashboard e histórico após os testes. Subcategoria continua obrigatória.
