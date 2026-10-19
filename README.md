# Bibliotecas Conectadas — API

Backend da plataforma **Bibliotecas Conectadas**, voltada à gestão das bibliotecas
públicas municipais de Santos/SP.

Este repositório é utilizado pelo **Grupo 1 do Projeto Integrador em Computação VI
(PJI610 — DRP02)** da Universidade Virtual do Estado de São Paulo, no desenvolvimento
do módulo analítico de apoio à gestão.

A aplicação usa Django 5, Django REST Framework e PostgreSQL.

---

## Créditos e origem

A base deste sistema foi desenvolvida em projetos integradores anteriores:

- **PI III** — construção da plataforma de gestão de unidades, acervo e empréstimos,
  por Cláudio Alexandre dos Santos, Julian Geiger Nunes, Larissa Martins Gonçalves e equipe.
- **PI IV** — camada analítica territorial com dados do IBGE e integração com Power BI,
  pelo grupo do Projeto Integrador IV.
- **PI VI** — módulo de indicadores de gestão integrado à plataforma, por este grupo.

O repositório de origem é [ClaudioProg/biblio.webapi](https://github.com/ClaudioProg/biblio.webapi).
Esta é uma cópia independente, com banco de dados e hospedagem próprios, para que o
desenvolvimento do PI VI não afete o ambiente em produção dos projetos anteriores.

---

## Arquitetura

| Camada | Tecnologia |
|---|---|
| Backend | Django 5 + Django REST Framework |
| Banco de dados | PostgreSQL (Neon) |
| Hospedagem da API | Render |
| Frontend | Web Components + Vite, hospedado na Vercel |
| Documentação da API | OpenAPI via drf-spectacular |

O código do app `gestor` segue arquitetura em camadas:

```
src/gestor/
├── domain/
│   ├── entities/        → modelos de dados
│   └── repositories/    → acesso a dados
├── application/         → casos de uso
├── infrastructure/      → serviços externos (ISBN, tradução, território)
├── presentation/        → views, serializers e rotas
└── migrations/          → migrações do banco
```

Ao acrescentar funcionalidades, respeite essa separação: entidade em `domain/entities`,
regra de negócio em `application`, endpoint em `presentation`.

---

## Como rodar localmente

### 1. Clonar o repositório

```bash
git clone https://github.com/larissalmg/biblio-webapi-pi6.git
cd biblio-webapi-pi6
```

### 2. Criar o ambiente virtual e instalar as dependências

**Windows (PowerShell):**

```powershell
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar o ambiente

Copie o arquivo de exemplo e preencha os valores:

```bash
cp .env.example .env
```

Para começar, basta deixar a `DATABASE_URL` em branco — a aplicação usa SQLite local
automaticamente. Para trabalhar com o banco compartilhado do grupo, peça a string de
conexão a quem administra o projeto no Neon.

> O arquivo `.env` **nunca** deve ser versionado.

### 4. Aplicar as migrações

```bash
python manage.py migrate
```

As migrações já populam o catálogo inicial: as **6 unidades** do Sistema Municipal de
Bibliotecas de Santos e **100 livros** de exemplo.

### 5. Criar um usuário administrador

```bash
python manage.py createsuperuser
```

### 6. Executar

```bash
python manage.py runserver
```

A API sobe em `http://localhost:8000`.
A documentação interativa fica em `http://localhost:8000/api/docs/`.

---

## Endpoints principais

### Autenticação
```
POST   /gestor/auth/login/
POST   /gestor/auth/logout/
GET    /gestor/auth/me/
POST   /gestor/auth/change-password/
```

### Gestão
```
/gestor/livros/
/gestor/unidades/
/gestor/livro-unidades/
/gestor/usuarios/
/gestor/emprestimos/
/gestor/acessos/
```

### Consulta por ISBN
```
GET /gestor/livros/isbn-lookup/?isbn={isbn}
```

### Analytics
```
GET /gestor/analytics/resumo/        indicadores operacionais agregados
GET /gestor/analytics/territorio/    indicadores territoriais do IBGE (Santos/SP)
GET /gestor/analytics/powerbi/       dataset agregado, sem identificadores pessoais
```

---

## Modelo de dados

| Entidade | Descrição |
|---|---|
| `Unidade` | Biblioteca ou equipamento de leitura, com dados territoriais do IBGE |
| `Livro` | Obra do acervo, com gênero, tipo de obra e idioma |
| `LivroUnidade` | Relação entre obra e unidade, com o número de exemplares |
| `Usuario` | Leitor cadastrado |
| `Emprestimo` | Movimentação de empréstimo e devolução |
| `Genero`, `TipoObra`, `Autor`, `Editora` | Tabelas auxiliares de classificação |

---

## Fluxo de trabalho no repositório

O ramo `main` é protegido. Nenhuma alteração entra diretamente nele.

```bash
git checkout main
git pull
git checkout -b feat/nome-da-funcionalidade
# ... desenvolve, testa ...
git add .
git commit -m "feat: descrição curta do que foi feito"
git push -u origin feat/nome-da-funcionalidade
```

Depois, abra um **Pull Request** no GitHub descrevendo o que foi alterado.

**Convenção de nomes de ramo:**

| Prefixo | Uso |
|---|---|
| `feat/` | nova funcionalidade |
| `fix/` | correção de defeito |
| `docs/` | documentação |
| `chore/` | manutenção, configuração, limpeza |

---

## Segurança e privacidade

- Rotas operacionais protegidas por autenticação por token.
- CORS restrito às origens previstas.
- Credenciais e segredos apenas em variáveis de ambiente, nunca versionados.
- O painel analítico opera exclusivamente com **dados agregados**: os registros de
  empréstimo vinculam pessoas identificadas às obras que consultam, e esse vínculo
  não é exposto, em observância à Lei Geral de Proteção de Dados Pessoais
  (Lei nº 13.709/2018).
- Dados territoriais provenientes de fontes públicas oficiais do IBGE.

---

## Documentação complementar

| Caminho | Conteúdo |
|---|---|
| `docs/pi4/` | documentação da camada territorial e do Power BI (PI IV) |
| `powerbi/` | projeto PBIP, modelo semântico e consultas (PI IV) |
| `/api/docs/` | documentação interativa da API, gerada automaticamente |
