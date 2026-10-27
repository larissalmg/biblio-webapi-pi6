from collections import defaultdict
from datetime import date, datetime

from django.db.models import Count, Max, Min, Sum
from django.db.models.functions import ExtractYear, TruncMonth
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


@extend_schema(
    parameters=FILTER_PARAMETERS,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    description=(
        "Retorna indicadores agregados do acervo, sem dados pessoais. "
        "O período informado se refere ao ano de publicação."
    ),
)
@api_view(["GET"])
def dashboard_livros(request):
    books, filters, error_response = _get_filtered_books(request)
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

    today = timezone.localdate()
    current_month_index = today.year * 12 + today.month - 1
    first_month = _month_start(current_month_index - 11)
    month_counts = {
        _month_key(row["mes"]): row["total"]
        for row in loans.filter(
            data_emprestimo__gte=first_month,
            data_emprestimo__lte=today,
        )
        .annotate(mes=TruncMonth("data_emprestimo"))
        .values("mes")
        .annotate(total=Count("id"))
    }
    returns_counts = {
        _month_key(row["mes"]): row["total"]
        for row in loans.filter(
            data_devolucao__gte=first_month,
            data_devolucao__lte=today,
        )
        .annotate(mes=TruncMonth("data_devolucao"))
        .values("mes")
        .annotate(total=Count("id"))
    }
    circulacao_mensal = []
    for month_index in range(current_month_index - 11, current_month_index + 1):
        month = _month_start(month_index)
        key = month.strftime("%Y-%m")
        circulacao_mensal.append({
            "mes": key,
            "emprestimos_iniciados": month_counts.get(key, 0),
            "devolucoes": returns_counts.get(key, 0),
        })

    emprestimos_recentes = [
        {
            "id": row["id"],
            "titulo": row["livro__titulo"],
            "autor": row["livro__autor"],
            "unidade": row["unidade__nome"],
            "data_emprestimo": row["data_emprestimo"],
            "data_prevista_devolucao": row["data_prevista_devolucao"],
            "data_devolucao": row["data_devolucao"],
            "status": row["status"],
        }
        for row in loans.order_by("-data_emprestimo", "-id").values(
            "id",
            "livro__titulo",
            "livro__autor",
            "unidade__nome",
            "data_emprestimo",
            "data_prevista_devolucao",
            "data_devolucao",
            "status",
        )[:10]
    ]

    return Response({
        "meta": {
            "escopo": "indicadores agregados de livros e circulação",
            "contem_dados_pessoais": False,
            "filtros_aplicados": filters,
            "tendencia_de_cadastro_disponivel": False,
            "reservas_disponiveis": False,
            "observacao": (
                "O modelo não registra a data de cadastro do livro nem reservas. "
                "A evolução apresentada é de empréstimos e devoluções mensais; "
                "a distribuição temporal do acervo usa a data de publicação."
            ),
        },
        "indicadores": {
            "titulos": books.count(),
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
        "circulacao_mensal": circulacao_mensal,
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