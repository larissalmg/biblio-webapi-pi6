from collections import defaultdict
from datetime import date, datetime, timedelta

from django.db.models import Count, Max, Min, Q, Sum
from django.db.models.functions import ExtractYear, Trim, TruncMonth
from django.utils import timezone
from django.urls import path
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from gestor.domain.entities.emprestimo import Emprestimo
from gestor.domain.entities.genero import Genero
from gestor.domain.entities.livro import Livro
from gestor.domain.entities.livro_unidade import LivroUnidade
from gestor.domain.entities.unidade import Unidade


MAX_CIRCULATION_MONTHS = 36
ASSESSED_FIELDS_PER_TITLE = 6

FILTER_PARAMETERS = [
    OpenApiParameter(
        "unidade_id",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description="Filtra o acervo por unidade.",
    ),
    OpenApiParameter(
        "genero_id",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description="Filtra o acervo por categoria/gênero.",
    ),
    OpenApiParameter(
        "ano_inicio",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description="Ano inicial da publicação (inclusive).",
    ),
    OpenApiParameter(
        "ano_fim",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description="Ano final da publicação (inclusive).",
    ),
    OpenApiParameter(
        "circulacao_data_inicio",
        OpenApiTypes.DATE,
        OpenApiParameter.QUERY,
        description="Data inicial da circulação (inclusive, formato AAAA-MM-DD).",
    ),
    OpenApiParameter(
        "circulacao_data_fim",
        OpenApiTypes.DATE,
        OpenApiParameter.QUERY,
        description="Data final da circulação (inclusive, formato AAAA-MM-DD).",
    ),
]


def _optional_positive_int(query_params, name):
    raw_value = (query_params.get(name) or "").strip()
    if not raw_value:
        return None

    try:
        value = int(raw_value)
    except ValueError:
        raise ValueError(f"O parâmetro {name} deve ser um número inteiro.") from None

    if value < 1:
        raise ValueError(f"O parâmetro {name} deve ser maior que zero.")
    return value


def _get_filtered_books(request):
    try:
        filters = {
            "unidade_id": _optional_positive_int(request.query_params, "unidade_id"),
            "genero_id": _optional_positive_int(request.query_params, "genero_id"),
            "ano_inicio": _optional_positive_int(request.query_params, "ano_inicio"),
            "ano_fim": _optional_positive_int(request.query_params, "ano_fim"),
        }
    except ValueError as error:
        return None, None, Response({"detail": str(error)}, status=400)

    if (
        filters["ano_inicio"]
        and filters["ano_fim"]
        and filters["ano_inicio"] > filters["ano_fim"]
    ):
        return None, None, Response(
            {"detail": "ano_inicio não pode ser maior que ano_fim."},
            status=400,
        )

    books = Livro.objects.all()
    if filters["unidade_id"]:
        books = books.filter(livrounidade__unidade_id=filters["unidade_id"])
    if filters["genero_id"]:
        books = books.filter(genero_id=filters["genero_id"])
    if filters["ano_inicio"]:
        books = books.filter(data_publicacao__year__gte=filters["ano_inicio"])
    if filters["ano_fim"]:
        books = books.filter(data_publicacao__year__lte=filters["ano_fim"])

    return books.distinct(), filters, None


def _month_start(month_index):
    year, month_zero_based = divmod(month_index, 12)
    return date(year, month_zero_based + 1, 1)


def _month_key(value):
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%Y-%m")


def _optional_date(query_params, name):
    raw_value = (query_params.get(name) or "").strip()
    if not raw_value:
        return None

    try:
        parsed = date.fromisoformat(raw_value)
    except ValueError:
        raise ValueError(f"O parâmetro {name} deve usar o formato AAAA-MM-DD.") from None

    if parsed.isoformat() != raw_value:
        raise ValueError(f"O parâmetro {name} deve usar o formato AAAA-MM-DD.")
    return parsed


def _circulation_period(query_params, today):
    try:
        start = _optional_date(query_params, "circulacao_data_inicio")
        end = _optional_date(query_params, "circulacao_data_fim")
    except ValueError as error:
        return None, None, None, None, Response({"detail": str(error)}, status=400)

    end = end or today
    if start is None:
        end_month_index = end.year * 12 + end.month - 1
        start = _month_start(end_month_index - 11)

    if start > end:
        return None, None, None, None, Response(
            {"detail": "circulacao_data_inicio não pode ser maior que circulacao_data_fim."},
            status=400,
        )

    month_span = (end.year - start.year) * 12 + (end.month - start.month) + 1
    if month_span > MAX_CIRCULATION_MONTHS:
        return None, None, None, None, Response(
            {
                "detail": (
                    "O período de circulação pode ter no máximo "
                    f"{MAX_CIRCULATION_MONTHS} meses."
                )
            },
            status=400,
        )

    duration_days = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=duration_days - 1)
    return start, end, previous_start, previous_end, None


def _percentage_change(current, previous):
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def _blank_text(field_name):
    trimmed = f"{field_name}_normalizado"
    return (
        {trimmed: Trim(field_name)},
        Q(**{f"{trimmed}__isnull": True}) | Q(**{trimmed: ""}),
    )


@extend_schema(
    parameters=FILTER_PARAMETERS,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    description=(
        "Retorna indicadores agregados do acervo, sem dados pessoais. "
        "Os anos filtram a data de publicação. "
        "circulacao_data_inicio e circulacao_data_fim filtram a circulação, "
        f"com no máximo {MAX_CIRCULATION_MONTHS} meses."
    ),
)
@api_view(["GET"])
def dashboard_livros(request):
    books, filters, error_response = _get_filtered_books(request)
    if error_response:
        return error_response

    today = timezone.localdate()
    (
        circulation_start,
        circulation_end,
        previous_start,
        previous_end,
        error_response,
    ) = _circulation_period(request.query_params, today)
    if error_response:
        return error_response

    inventory = LivroUnidade.objects.filter(livro__in=books)
    if filters["unidade_id"]:
        inventory = inventory.filter(unidade_id=filters["unidade_id"])

    category_titles = books.values(
        "genero_id",
        "genero__nome",
    ).annotate(
        titulos=Count("id", distinct=True),
    ).order_by("genero__nome")
    category_copies = {
        row["livro__genero_id"]: row["exemplares"] or 0
        for row in inventory.values("livro__genero_id").annotate(
            exemplares=Sum("exemplares")
        )
    }
    acervo_por_categoria = [
        {
            "genero_id": row["genero_id"],
            "categoria": row["genero__nome"] or "Não informada",
            "titulos": row["titulos"],
            "exemplares": category_copies.get(row["genero_id"], 0),
        }
        for row in category_titles
    ]
    categorized_categories = [
        row for row in acervo_por_categoria if row["genero_id"] is not None
    ]
    categorized_title_count = sum(
        row["titulos"] for row in categorized_categories
    )

    def category_insight(row):
        return {
            "genero_id": row["genero_id"],
            "categoria": row["categoria"],
            "titulos": row["titulos"],
            "participacao_percentual": round(
                row["titulos"] / categorized_title_count * 100, 1
            ) if categorized_title_count else 0,
        }

    most_represented = (
        min(categorized_categories, key=lambda row: (-row["titulos"], row["categoria"]))
        if categorized_categories
        else None
    )
    least_represented = (
        min(categorized_categories, key=lambda row: (row["titulos"], row["categoria"]))
        if categorized_categories
        else None
    )
    if (
        least_represented is None
        or most_represented is None
        or least_represented["titulos"] == most_represented["titulos"]
    ):
        least_represented = None

    insights_acervo = {
        "base_calculo": "títulos com categoria informada",
        "titulos_categorizados": categorized_title_count,
        "categoria_mais_representada": (
            category_insight(most_represented) if most_represented else None
        ),
        "categoria_menor_representacao": (
            category_insight(least_represented) if least_represented else None
        ),
    }

    acervo_por_unidade = list(
        inventory.values("unidade_id", "unidade__nome")
        .annotate(
            titulos=Count("livro_id", distinct=True),
            exemplares=Sum("exemplares"),
        )
        .order_by("unidade__nome")
    )
    acervo_por_unidade = [
        {
            "unidade_id": row["unidade_id"],
            "unidade": row["unidade__nome"],
            "titulos": row["titulos"],
            "exemplares": row["exemplares"] or 0,
        }
        for row in acervo_por_unidade
    ]

    total_exemplares = inventory.aggregate(total=Sum("exemplares"))["total"] or 0
    category_count = books.exclude(genero_id__isnull=True).values(
        "genero_id"
    ).distinct().count()
    unit_count = inventory.values("unidade_id").distinct().count()
    authors = books.exclude(autor__isnull=True).exclude(autor__exact="")

    top_authors = list(
        authors.values("autor")
        .annotate(titulos=Count("id", distinct=True))
        .order_by("-titulos", "autor")[:10]
    )

    decade_counts = defaultdict(int)
    for row in (
        books.exclude(data_publicacao__isnull=True)
        .annotate(ano=ExtractYear("data_publicacao"))
        .values("ano")
        .annotate(titulos=Count("id", distinct=True))
        .order_by("ano")
    ):
        decade = (row["ano"] // 10) * 10
        decade_counts[decade] += row["titulos"]

    publicacoes_por_decada = [
        {
            "ano_inicio": decade,
            "ano_fim": decade + 9,
            "faixa": f"{decade}-{decade + 9}",
            "titulos": decade_counts[decade],
        }
        for decade in sorted(decade_counts)
    ]
    sem_data_publicacao = books.filter(data_publicacao__isnull=True).count()
    total_titles = books.count()
    author_annotation, author_is_blank = _blank_text("autor")
    cover_annotation, cover_is_blank = _blank_text("capa")
    isbn_annotation, isbn_is_blank = _blank_text("isbn")
    titles_without_author = books.annotate(**author_annotation).filter(
        author_is_blank
    ).distinct().count()
    titles_without_category = books.filter(genero_id__isnull=True).distinct().count()
    titles_without_isbn = books.annotate(**isbn_annotation).filter(
        isbn_is_blank
    ).distinct().count()
    titles_without_cover = books.annotate(**cover_annotation).filter(
        cover_is_blank
    ).distinct().count()
    titles_without_unit = books.filter(
        livrounidade__isnull=True
    ).distinct().count()
    assessed_fields_per_title = ASSESSED_FIELDS_PER_TITLE
    assessed_field_values = total_titles * assessed_fields_per_title
    missing_field_values = (
        titles_without_author
        + titles_without_category
        + sem_data_publicacao
        + titles_without_isbn
        + titles_without_cover
        + titles_without_unit
    )
    qualidade_acervo = {
        "titulos_total": total_titles,
        "campos_avaliados_por_titulo": assessed_fields_per_title,
        "percentual_campos_preenchidos": round(
            (assessed_field_values - missing_field_values)
            / assessed_field_values
            * 100,
            1,
        ) if assessed_field_values else 0,
        "titulos_sem_autor": titles_without_author,
        "titulos_sem_categoria": titles_without_category,
        "titulos_sem_data_publicacao": sem_data_publicacao,
        "titulos_sem_isbn": titles_without_isbn,
        "titulos_sem_capa": titles_without_cover,
        "titulos_sem_unidade": titles_without_unit,
    }

    loans = Emprestimo.objects.filter(livro__in=books)
    if filters["unidade_id"]:
        loans = loans.filter(unidade_id=filters["unidade_id"])

    stock_by_book_unit = {
        (row["livro_id"], row["unidade_id"]): row["exemplares"]
        for row in inventory.values("livro_id", "unidade_id", "exemplares")
    }
    open_by_book_unit = defaultdict(int)
    open_loans = loans.filter(
        status=Emprestimo.STATUS_ABERTO,
        unidade__isnull=False,
    )
    for row in open_loans.values("livro_id", "unidade_id").annotate(
        total=Count("id")
    ):
        open_by_book_unit[(row["livro_id"], row["unidade_id"])] = row["total"]

    exemplares_emprestados = 0
    exemplares_disponiveis = 0
    for key, stock in stock_by_book_unit.items():
        borrowed = open_by_book_unit.get(key, 0)
        exemplares_emprestados += borrowed
        exemplares_disponiveis += max(0, stock - borrowed)
    emprestimos_sem_unidade = loans.filter(
        status=Emprestimo.STATUS_ABERTO,
        unidade__isnull=True,
    ).count()
    exemplares_emprestados += emprestimos_sem_unidade
    exemplares_disponiveis = max(
        0,
        exemplares_disponiveis - emprestimos_sem_unidade,
    )

    livros_em_destaque = []
    highlighted_rows = loans.filter(
        data_emprestimo__range=(circulation_start, circulation_end),
    ).values(
        "livro_id",
        "livro__titulo",
        "livro__autor",
        "livro__genero__nome",
        "livro__data_publicacao",
        "livro__capa",
        "unidade_id",
        "unidade__nome",
    ).annotate(
        emprestimos_total=Count("id")
    ).order_by(
        "-emprestimos_total",
        "livro__titulo",
        "unidade__nome",
    )[:10]
    for row in highlighted_rows:
        stock_key = (row["livro_id"], row["unidade_id"])
        exemplares = stock_by_book_unit.get(stock_key, 0)
        emprestimos_abertos = open_by_book_unit.get(stock_key, 0)
        publication_date = row["livro__data_publicacao"]
        livros_em_destaque.append({
            "livro_id": row["livro_id"],
            "titulo": row["livro__titulo"],
            "autor": row["livro__autor"],
            "categoria": row["livro__genero__nome"] or "Não informada",
            "ano_publicacao": publication_date.year if publication_date else None,
            "capa": row["livro__capa"],
            "unidade_id": row["unidade_id"],
            "unidade": row["unidade__nome"] or "Sem unidade",
            "emprestimos_total": row["emprestimos_total"],
            "exemplares": exemplares,
            "emprestimos_abertos": emprestimos_abertos,
            "exemplares_disponiveis": max(0, exemplares - emprestimos_abertos),
        })

    first_month_index = circulation_start.year * 12 + circulation_start.month - 1
    last_month_index = circulation_end.year * 12 + circulation_end.month - 1
    month_counts = {
        _month_key(row["mes"]): row["total"]
        for row in loans.filter(
            data_emprestimo__range=(circulation_start, circulation_end),
        )
        .annotate(mes=TruncMonth("data_emprestimo"))
        .values("mes")
        .annotate(total=Count("id"))
    }
    returns_counts = {
        _month_key(row["mes"]): row["total"]
        for row in loans.filter(
            data_devolucao__range=(circulation_start, circulation_end),
        )
        .annotate(mes=TruncMonth("data_devolucao"))
        .values("mes")
        .annotate(total=Count("id"))
    }
    circulacao_mensal = []
    for month_index in range(first_month_index, last_month_index + 1):
        month = _month_start(month_index)
        key = month.strftime("%Y-%m")
        circulacao_mensal.append({
            "mes": key,
            "emprestimos_iniciados": month_counts.get(key, 0),
            "devolucoes": returns_counts.get(key, 0),
        })

    current_period_loans = loans.filter(
        data_emprestimo__range=(circulation_start, circulation_end)
    ).count()
    previous_period_loans = loans.filter(
        data_emprestimo__range=(previous_start, previous_end)
    ).count()
    current_period_returns = loans.filter(
        data_devolucao__range=(circulation_start, circulation_end)
    ).count()
    previous_period_returns = loans.filter(
        data_devolucao__range=(previous_start, previous_end)
    ).count()
    comparativo_circulacao = {
        "periodo_atual": {
            "data_inicio": circulation_start.isoformat(),
            "data_fim": circulation_end.isoformat(),
            "emprestimos_iniciados": current_period_loans,
            "devolucoes": current_period_returns,
        },
        "periodo_anterior": {
            "data_inicio": previous_start.isoformat(),
            "data_fim": previous_end.isoformat(),
            "emprestimos_iniciados": previous_period_loans,
            "devolucoes": previous_period_returns,
        },
        "variacao_percentual": {
            "emprestimos_iniciados": _percentage_change(
                current_period_loans, previous_period_loans
            ),
            "devolucoes": _percentage_change(
                current_period_returns, previous_period_returns
            ),
        },
    }

    emprestimos_recentes = [
        {
            "id": row["id"],
            "livro_id": row["livro_id"],
            "titulo": row["livro__titulo"],
            "autor": row["livro__autor"],
            "capa": row["livro__capa"],
            "unidade": row["unidade__nome"],
            "data_emprestimo": row["data_emprestimo"],
            "data_prevista_devolucao": row["data_prevista_devolucao"],
            "data_devolucao": row["data_devolucao"],
            "status": row["status"],
        }
        for row in loans.order_by("-data_emprestimo", "-id").values(
            "id",
            "livro_id",
            "livro__titulo",
            "livro__autor",
            "livro__capa",
            "unidade__nome",
            "data_emprestimo",
            "data_prevista_devolucao",
            "data_devolucao",
            "status",
        )[:10]
    ]
    filters = {
        **filters,
        "circulacao_data_inicio": circulation_start.isoformat(),
        "circulacao_data_fim": circulation_end.isoformat(),
    }

    return Response({
        "meta": {
            "escopo": "indicadores agregados de livros e circulação",
            "contem_dados_pessoais": False,
            "filtros_aplicados": filters,
            "tendencia_de_cadastro_disponivel": False,
            "comparativo_circulacao_disponivel": True,
            "reservas_disponiveis": False,
            "periodo_circulacao": {
                "data_inicio": circulation_start.isoformat(),
                "data_fim": circulation_end.isoformat(),
            },
            "observacao": (
                "O modelo não registra a data de cadastro do livro nem reservas. "
                "A evolução e a comparação apresentadas são de empréstimos e "
                "devoluções; a distribuição temporal do acervo usa a data de publicação."
            ),
        },
        "indicadores": {
            "titulos": total_titles,
            "autores_distintos": authors.values("autor").distinct().count(),
            "categorias": category_count,
            "unidades_com_acervo": unit_count,
            "exemplares": total_exemplares,
            "emprestimos_abertos": loans.filter(
                status=Emprestimo.STATUS_ABERTO
            ).count(),
        },
        "situacao_exemplares": {
            "total": total_exemplares,
            "emprestados": exemplares_emprestados,
            "disponiveis": exemplares_disponiveis,
            "reservados": None,
        },
        "acervo_por_categoria": acervo_por_categoria,
        "acervo_por_unidade": acervo_por_unidade,
        "top_autores": top_authors,
        "publicacoes_por_decada": publicacoes_por_decada,
        "titulos_sem_data_publicacao": sem_data_publicacao,
        "qualidade_acervo": qualidade_acervo,
        "insights_acervo": insights_acervo,
        "livros_em_destaque": livros_em_destaque,
        "circulacao_mensal": circulacao_mensal,
        "comparativo_circulacao": comparativo_circulacao,
        "emprestimos_recentes": emprestimos_recentes,
    })


@extend_schema(
    responses={200: OpenApiTypes.OBJECT},
    description="Retorna as opções disponíveis para os filtros da dashboard de livros.",
)
@api_view(["GET"])
def filtros_livros(_request):
    publication_years = Livro.objects.aggregate(
        primeiro=Min("data_publicacao"),
        ultimo=Max("data_publicacao"),
    )
    first_publication = publication_years["primeiro"]
    last_publication = publication_years["ultimo"]

    return Response({
        "unidades": list(
            Unidade.objects.order_by("nome").values("id", "nome")
        ),
        "categorias": list(
            Genero.objects.order_by("nome").values("id", "nome")
        ),
        "anos_publicacao": {
            "inicio": first_publication.year if first_publication else None,
            "fim": last_publication.year if last_publication else None,
        },
    })


app_name = "analytics_livros"
urlpatterns = [
    path("", dashboard_livros, name="dashboard"),
    path("filtros/", filtros_livros, name="filtros"),
]