# Teste das rotas da API

O script `test_api_routes.py` faz um smoke test das principais rotas HTTP da API.
Ele solicita as credenciais, autentica pelo endpoint de login e só então consulta
as rotas protegidas usando o token recebido.

## Pré-requisitos

- Python 3 instalado. O script usa apenas a biblioteca padrão do Python, sem pacotes adicionais.
- API em execução e acessível pela máquina. Com a configuração Docker deste projeto, a URL padrão é `http://localhost:8000`.
- Usuário e senha válidos para acessar a API.

## Como executar

Na raiz do repositório, rode:

```bash
python3 -m tests_route.test_api_routes
```

O script solicitará o usuário e a senha. A senha é digitada sem aparecer na tela e não é gravada pelo script.

Para usar outra URL base:

```bash
python3 -m tests_route.test_api_routes --base-url http://localhost:8000
```

Também é possível consultar as opções com:

```bash
python3 -m tests_route.test_api_routes --help
```

## Rotas verificadas

Antes do login, o script verifica `GET /`, `GET /healthz` e `GET /admin/`. Após
autenticar, verifica:

- `GET /api/schema/`, `GET /api/docs/` e `GET /api/redoc/`
- `GET /gestor/` e `GET /gestor/auth/me/`
- `GET /gestor/livros/`, `/gestor/unidades/`, `/gestor/livro-unidades/`, `/gestor/usuarios/` e `/gestor/emprestimos/`
- `GET /gestor/acessos/`, somente quando a conta autenticada é administradora
- `GET /gestor/dados-iniciais/`
- `GET /gestor/analytics/resumo/`, `/gestor/analytics/territorio/`, `/gestor/analytics/powerbi/`, `/gestor/analytics/gestao-livros/` e `/gestor/analytics/gestao-livros/filtros/`
- `GET /gestor/livros/isbn-lookup/?isbn=1234567890123`, verificando a rejeição de entrada sem chamar o serviço externo
- `POST /gestor/auth/change-password/` com payload vazio, verificando a validação sem alterar a senha
- `POST /gestor/auth/logout/`, executado por último para invalidar o token após os demais checks

Para cada coleção com registros, também consulta o detalhe do primeiro item. O resultado
mostra status e contagens sem imprimir registros de usuários ou empréstimos. Operações
de criação, edição, exclusão e reset de senha não são executadas pelo smoke test.

## Estrutura JSON das rotas analíticas

Os exemplos abaixo foram capturados da API em 2026-10-27. Listas longas foram
abreviadas para até dois itens; os totais indicam a quantidade completa retornada.

### `GET /gestor/analytics/resumo/`

```json
{
  "meta": {
    "escopo": "dados agregados da plataforma Bibliotecas Conectadas",
    "contém_dados_pessoais": false,
    "observacao": "Estes indicadores descrevem o acervo e a circulação registrada na plataforma. Não representam, por si só, a demanda sociodemográfica."
  },
  "resumo": {
    "titulos": 100,
    "exemplares": 965,
    "unidades": 6,
    "usuarios_ativos": 0,
    "emprestimos_total": 0,
    "emprestimos_abertos": 0,
    "emprestimos_devolvidos": 0
  },
  "acervo_por_genero": [
    {
      "genero": "Clássico",
      "titulos": 14,
      "exemplares": 136
    }
  ],
  "acervo_por_tipo": [
    {
      "tipo_obra": "Livro",
      "titulos": 100,
      "exemplares": 965
    }
  ],
  "por_unidade": [
    {
      "unidade_id": 1,
      "unidade": "Biblioteca Alberto Sousa",
      "ibge_bairro_codigo": "3548500017",
      "ibge_bairro_nome": "Centro",
      "latitude": null,
      "longitude": null,
      "titulos": 49,
      "exemplares": 170,
      "emprestimos_total": 0,
      "emprestimos_abertos": 0,
      "emprestimos_devolvidos": 0
    }
  ]
}
```

`resumo` contém totais operacionais. `acervo_por_genero` e `acervo_por_tipo`
agrupam títulos e exemplares; `por_unidade` acrescenta localização territorial e
quantidades de empréstimos. Coordenadas e dados territoriais podem ser `null` quando
não cadastrados.

### `GET /gestor/analytics/territorio/`

```json
{
  "meta": {
    "fonte": "IBGE — Censo Demográfico 2022",
    "municipio": "Santos",
    "uf": "SP",
    "codigo_municipio_ibge": "3548500",
    "nivel_territorial": "bairro",
    "gerado_de_fontes_oficiais_em": "2026-10-07",
    "contem_dados_pessoais": false,
    "observacao": "Os dados caracterizam o território e não constituem, isoladamente, evidência de preferência ou demanda literária."
  },
  "cobertura": {
    "bairros_total": 55,
    "bairros_com_demografia": 55,
    "bairros_com_alfabetizacao": 55,
    "bairros_com_renda": 55,
    "bairros_com_faixas_etarias_completas": 55,
    "bairros_com_taxa_alfabetizacao": 55,
    "bairros_sem_renda": 0
  },
  "validacao": {
    "diferencas_total_basico_demografia": 8,
    "diferencas_total_demografia_faixas_etarias": 22,
    "renda_ausente_eh_zero": false
  },
  "bairros": [
    {
      "cd_bairro": "3548500001",
      "bairro": "José Menino",
      "area_km2": 0.6800466,
      "populacao_total": 11209,
      "populacao_demografia": 11209,
      "idade_0_14": 1280,
      "idade_15_29": 1683,
      "idade_30_59": 4871,
      "idade_60_mais": 3359,
      "populacao_idade_classificada": 11193,
      "populacao_15_mais_alfabetizacao": 9908,
      "alfabetizados_15_mais": 9828,
      "taxa_alfabetizacao_15_mais_pct": 99.19,
      "responsaveis_dpp_ocupados": 5292,
      "renda_responsavel_media": 7220.24,
      "renda_responsavel_mediana": 5000.0,
      "renda_disponivel": true
    }
  ]
}
```

`cobertura` resume quantos bairros possuem cada conjunto de indicadores; `validacao`
registra diferenças entre universos e informa que renda ausente não significa zero.
Cada item de `bairros` contém população, faixas etárias, alfabetização e rendimento
da pessoa responsável pelo domicílio. Valores suprimidos ou indisponíveis são `null`.
Filtros opcionais: `?codigo=<código IBGE>` e `?bairro=<trecho do nome>`.

### `GET /gestor/analytics/powerbi/`

```json
{
  "meta": {
    "dataset": "Bibliotecas Conectadas — PI4 — Power BI",
    "municipio": "Santos",
    "codigo_municipio_ibge": "3548500",
    "nivel_territorial": "bairro",
    "contem_dados_pessoais": false,
    "observacao": "Dataset agregado sem identificadores de leitores."
  },
  "periodo": {
    "primeiro_emprestimo": null,
    "ultimo_emprestimo": null,
    "ultima_devolucao": null
  },
  "qualidade_ibge": {
    "bairros_total": 55,
    "bairros_com_renda": 55,
    "bairros_sem_renda": 0,
    "diferencas_total_basico_demografia": 8,
    "diferencas_total_demografia_faixas_etarias": 22
  },
  "dim_bairro": [
    {
      "cd_bairro": "3548500001",
      "bairro": "José Menino",
      "area_km2": 0.6800466,
      "populacao_total": 11209,
      "populacao_demografia": 11209,
      "idade_0_14": 1280,
      "idade_15_29": 1683,
      "idade_30_59": 4871,
      "idade_60_mais": 3359,
      "populacao_idade_classificada": 11193,
      "populacao_15_mais_alfabetizacao": 9908,
      "alfabetizados_15_mais": 9828,
      "taxa_alfabetizacao_15_mais_pct": 99.19,
      "responsaveis_dpp_ocupados": 5292,
      "renda_responsavel_media": 7220.24,
      "renda_responsavel_mediana": 5000.0,
      "renda_disponivel": true
    }
  ],
  "dim_unidade": [
    {
      "unidade_id": 1,
      "unidade": "Biblioteca Alberto Sousa",
      "endereco": "Praça José Bonifácio, 58 – Centro, Santos/SP",
      "ibge_bairro_codigo": "3548500017",
      "ibge_bairro_nome": "Centro",
      "latitude": null,
      "longitude": null
    }
  ],
  "fato_acervo": [
    {
      "unidade_id": 1,
      "ibge_bairro_codigo": "3548500017",
      "genero": "Clássico",
      "tipo_obra": "Livro",
      "titulos": 7,
      "exemplares": 19,
      "emprestimos_abertos": 0,
      "exemplares_disponiveis": 19
    }
  ],
  "fato_circulacao_mensal": [],
  "fato_devolucoes_mensal": [],
  "fato_titulos": []
}
```

As dimensões são listas de linhas analíticas. Cada objeto de `dim_bairro` tem as chaves
`cd_bairro`, `bairro`, `area_km2`, `populacao_total`, `populacao_demografia`,
`idade_0_14`, `idade_15_29`, `idade_30_59`, `idade_60_mais`,
`populacao_idade_classificada`, `populacao_15_mais_alfabetizacao`,
`alfabetizados_15_mais`, `taxa_alfabetizacao_15_mais_pct`,
`responsaveis_dpp_ocupados`, `renda_responsavel_media`,
`renda_responsavel_mediana` e `renda_disponivel`. Cada objeto de `dim_unidade` tem
`unidade_id`, `unidade`, `endereco`, `ibge_bairro_codigo`, `ibge_bairro_nome`,
`latitude` e `longitude`.

Na consulta real, o dataset tinha 55 bairros, 6 unidades e 108 linhas em `fato_acervo`;
`fato_circulacao_mensal`, `fato_devolucoes_mensal` e `fato_titulos` estavam vazias.

As linhas das tabelas fato têm estes campos:

- `fato_acervo`: `unidade_id`, `ibge_bairro_codigo`, `genero`, `tipo_obra`, `titulos`, `exemplares`, `emprestimos_abertos`, `exemplares_disponiveis`.
- `fato_circulacao_mensal`: `mes`, `unidade_id`, `ibge_bairro_codigo`, `genero`, `tipo_obra`, `emprestimos_iniciados`.
- `fato_devolucoes_mensal`: `mes`, `unidade_id`, `ibge_bairro_codigo`, `genero`, `tipo_obra`, `devolucoes`.
- `fato_titulos`: `unidade_id`, `ibge_bairro_codigo`, `livro_id`, `titulo`, `autor`, `isbn`, `genero`, `tipo_obra`, `emprestimos_total`, `emprestimos_abertos`, `exemplares_atuais`, `exemplares_disponiveis`.

Uma tabela fato pode vir vazia se ainda não houver registros, mas mantém a chave no
JSON. Nenhuma tabela contém nome, e-mail ou documento de leitor.

### `GET /gestor/analytics/gestao-livros/`

```json
{
  "meta": {
    "escopo": "indicadores agregados de livros e circulação",
    "contem_dados_pessoais": false,
    "filtros_aplicados": {
      "unidade_id": null,
      "genero_id": null,
      "ano_inicio": null,
      "ano_fim": null,
      "circulacao_data_inicio": "2025-11-01",
      "circulacao_data_fim": "2026-10-27"
    },
    "comparativo_circulacao_disponivel": true,
    "periodo_circulacao": {
      "data_inicio": "2025-11-01",
      "data_fim": "2026-10-27"
    },
    "tendencia_de_cadastro_disponivel": false,
    "reservas_disponiveis": false,
    "observacao": "O modelo não registra a data de cadastro do livro nem reservas. A evolução e a comparação apresentadas são de empréstimos e devoluções; a distribuição temporal do acervo usa a data de publicação."
  },
  "indicadores": {
    "titulos": 100,
    "autores_distintos": 77,
    "categorias": 24,
    "unidades_com_acervo": 6,
    "exemplares": 965,
    "emprestimos_abertos": 0
  },
  "situacao_exemplares": {
    "total": 965,
    "emprestados": 0,
    "disponiveis": 965,
    "reservados": null
  },
  "acervo_por_categoria": [
    {
      "genero_id": 8,
      "categoria": "Ciência",
      "titulos": 1,
      "exemplares": 13
    }
  ],
  "acervo_por_unidade": [
    {
      "unidade_id": 1,
      "unidade": "Biblioteca Alberto Sousa",
      "titulos": 49,
      "exemplares": 170
    }
  ],
  "top_autores": [
    {
      "autor": "Agatha Christie",
      "titulos": 3
    }
  ],
  "publicacoes_por_decada": [
    {
      "ano_inicio": 1840,
      "ano_fim": 1849,
      "faixa": "1840-1849",
      "titulos": 1
    }
  ],
  "titulos_sem_data_publicacao": 3,
  "qualidade_acervo": {
    "titulos_total": 100,
    "campos_avaliados_por_titulo": 6,
    "percentual_campos_preenchidos": 98.3,
    "titulos_sem_autor": 0,
    "titulos_sem_categoria": 0,
    "titulos_sem_data_publicacao": 3,
    "titulos_sem_isbn": 0,
    "titulos_sem_capa": 7,
    "titulos_sem_unidade": 0
  },
  "insights_acervo": {
    "base_calculo": "títulos com categoria informada",
    "titulos_categorizados": 100,
    "categoria_mais_representada": {
      "genero_id": 18,
      "categoria": "Clássico",
      "titulos": 14,
      "participacao_percentual": 14.0
    },
    "categoria_menor_representacao": {
      "genero_id": 8,
      "categoria": "Ciência",
      "titulos": 1,
      "participacao_percentual": 1.0
    }
  },
  "livros_em_destaque": [],
  "circulacao_mensal": [
    {
      "mes": "2025-11",
      "emprestimos_iniciados": 0,
      "devolucoes": 0
    }
  ],
  "comparativo_circulacao": {
    "periodo_atual": {
      "data_inicio": "2025-11-01",
      "data_fim": "2026-10-27",
      "emprestimos_iniciados": 0,
      "devolucoes": 0
    },
    "periodo_anterior": {
      "data_inicio": "2024-11-05",
      "data_fim": "2025-10-31",
      "emprestimos_iniciados": 0,
      "devolucoes": 0
    },
    "variacao_percentual": {
      "emprestimos_iniciados": null,
      "devolucoes": null
    }
  },
  "emprestimos_recentes": []
}
```

`indicadores` contém os cartões da dashboard; as listas agrupam o acervo por categoria
e unidade, os dez autores com mais títulos, publicações por década, circulação mensal
do período selecionado e até dez empréstimos recentes. Os itens recentes incluem dados
da obra, capa, unidade, datas e status, mas não identificam o leitor. Filtros opcionais:
`unidade_id`, `genero_id`, `ano_inicio` e `ano_fim`; os anos se referem à publicação.
`circulacao_data_inicio` e `circulacao_data_fim` (formato `AAAA-MM-DD`) controlam a
série mensal, a comparação e os livros em destaque; se omitidos, a rota usa os últimos
12 meses. O intervalo pode ter no máximo 36 meses. O percentual de variação é `null`
quando o período anterior não tem registros. A qualidade do acervo avalia seis campos
por título e trata texto só com espaços como ausente. `insights_acervo` compara a
participação das categorias; categorias empatadas não geram uma “menor representação”.
`livros_em_destaque` conta apenas empréstimos do período, mas o estoque exibido é o
atual. O modelo não registra data de cadastro nem reservas, portanto `reservados` é
`null` e a tendência de cadastro não é fornecida.

Campos dos objetos das listas: `acervo_por_categoria` contém `genero_id`, `categoria`,
`titulos` e `exemplares`; `acervo_por_unidade` contém `unidade_id`, `unidade`,
`titulos` e `exemplares`; `top_autores` contém `autor` e `titulos`;
`publicacoes_por_decada` contém `ano_inicio`, `ano_fim`, `faixa` e `titulos`;
`circulacao_mensal` contém `mes`, `emprestimos_iniciados` e `devolucoes`;
`emprestimos_recentes` contém `id`, `livro_id`, `titulo`, `autor`, `capa`, `unidade`,
`data_emprestimo`, `data_prevista_devolucao`, `data_devolucao` e `status`.

### `GET /gestor/analytics/gestao-livros/filtros/`

```json
{
  "unidades": [
    {
      "id": 1,
      "nome": "Biblioteca Alberto Sousa"
    }
  ],
  "categorias": [
    {
      "id": 6,
      "nome": "Biografia"
    }
  ],
  "anos_publicacao": {
    "inicio": 1847,
    "fim": 2026
  }
}
```

`unidades` e `categorias` fornecem ID e nome para preencher os seletores. `inicio` e
`fim` são o menor e o maior ano de publicação cadastrados; ambos podem ser `null` se
nenhum livro tiver data de publicação. A consulta retornou 6 unidades e 27 categorias.

## Viabilidade da dashboard

A tabela compara os componentes do mockup da dashboard com os dados oferecidos pelas
rotas analíticas. “Parcial” indica que é necessário adaptar o componente ou combinar
os dados com outra fonte.

| Componente da dashboard | Rota/dados disponíveis | Viabilidade e limitações |
| --- | --- | --- |
| Totais de livros, autores, categorias e exemplares | `gestao-livros`: `indicadores` | Sim. `unidades_com_acervo` conta apenas unidades com acervo. |
| Acervo por categoria e por biblioteca | `gestao-livros`: `acervo_por_categoria`, `acervo_por_unidade` | Sim. |
| Principais autores | `gestao-livros`: `top_autores` | Sim. Retorna até dez autores e suas quantidades de títulos. |
| Distribuição por ano de publicação | `gestao-livros`: `publicacoes_por_decada` | Parcial. Os dados são agrupados por década, não nas faixas específicas do mockup. |
| Empréstimos recentes | `gestao-livros`: `emprestimos_recentes` | Parcial. Retorna até dez empréstimos e não identifica o leitor; a capa está disponível em `livros_em_destaque`, não nesta lista. |
| Situação dos exemplares | `gestao-livros`: `situacao_exemplares` | Parcial. Informa total, emprestados e disponíveis; reservas não são suportadas e `reservados` é `null`. |
| Evolução do acervo e crescimento percentual | `gestao-livros`: `circulacao_mensal`, `comparativo_circulacao` | Parcial. Período configurável e comparação de empréstimos/devoluções estão disponíveis; ainda não há histórico de novos títulos cadastrados. |
| Insights: categoria mais/menos representada | `gestao-livros`: `insights_acervo` | Sim, calcula participação das categorias entre títulos categorizados; isso não mede demanda. |
| Insights: completude dos registros | `gestao-livros`: `qualidade_acervo` | Sim. Calcula preenchimento e ausências de autor, categoria, data, ISBN, capa e vínculo com unidade; é diferente da cobertura territorial do IBGE. |
| Insights: oportunidade/demanda por categoria | Nenhuma rota oferece demanda literária por categoria | Não diretamente. A API não tem dados para fundamentar uma recomendação de demanda. |
| Tabela de livros em destaque | `gestao-livros`: `livros_em_destaque` | Sim, se os destaques forem definidos pelo total de empréstimos; inclui capa, categoria, unidade e estoque. Títulos sem empréstimos não aparecem. |
| Filtros de biblioteca, categoria e período | `gestao-livros/filtros/` e parâmetros de `gestao-livros` | Sim. Suporta unidade, categoria, ano de publicação e intervalo de circulação de até 36 meses; o padrão continua sendo os últimos 12 meses. |

Assim, as rotas atuais permitem montar mais componentes do mockup diretamente. Ainda
faltam histórico de cadastro de livros, reservas e dados de demanda por categoria.

## Interpretação de erros

- `HTTP 401` ou `HTTP 403`: credenciais inválidas ou conta sem permissão para alguma rota.
- `Falha de conexão`: confirme se os containers estão ativos e se a API está acessível na URL informada.
- `HTTP 5xx`: a API respondeu, mas ocorreu um erro no servidor; confira os logs do container `api`.

O script só faz login e requisições `GET`; não cria, altera ou exclui dados.
