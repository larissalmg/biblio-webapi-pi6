from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from gestor.domain.entities.emprestimo import Emprestimo
from gestor.domain.entities.genero import Genero
from gestor.domain.entities.livro import Livro
from gestor.domain.entities.livro_unidade import LivroUnidade
from gestor.domain.entities.unidade import Unidade
from gestor.domain.entities.usuario import Usuario


class AnalyticsLivrosTests(APITestCase):
    def setUp(self):
        Emprestimo.objects.all().delete()
        LivroUnidade.objects.all().delete()
        Livro.objects.all().delete()
        Unidade.objects.all().delete()
        Usuario.objects.all().delete()

        staff_user = get_user_model().objects.create_user(
            username="analytics_staff",
            password="SenhaForte123!",
            is_staff=True,
        )
        self.client.force_authenticate(user=staff_user)
        self.categoria = Genero.objects.create(nome="Ficção")
        self.unidade = Unidade.objects.create(nome="Biblioteca Central")
        self.leitor = Usuario.objects.create(
            nome="Leitor de teste",
            email="leitor@example.com",
            ativo=True,
        )

    def _livro(self, *, isbn, **fields):
        return Livro.objects.create(
            titulo=fields.pop("titulo", "Livro de teste"),
            autor=fields.pop("autor", "Autora de teste"),
            isbn=isbn,
            genero=fields.pop("genero", self.categoria),
            data_publicacao=fields.pop("data_publicacao", date(2000, 1, 1)),
            capa=fields.pop("capa", "https://example.com/capa.jpg"),
            **fields,
        )

    def test_dashboard_returns_period_comparison_quality_and_highlights(self):
        livro = self._livro(isbn="9780000000101")
        LivroUnidade.objects.create(
            livro=livro,
            unidade=self.unidade,
            exemplares=4,
        )
        livro_incompleto = self._livro(
            isbn="9780000000102",
            titulo="Livro incompleto",
            autor="   ",
            genero=None,
            data_publicacao=None,
            capa=None,
        )

        Emprestimo.objects.create(
            livro=livro,
            unidade=self.unidade,
            usuario=self.leitor,
            data_emprestimo=date(2026, 3, 15),
            data_devolucao=date(2026, 3, 20),
            status=Emprestimo.STATUS_DEVOLVIDO,
        )
        Emprestimo.objects.create(
            livro=livro,
            unidade=self.unidade,
            usuario=self.leitor,
            data_emprestimo=date(2026, 4, 10),
            status=Emprestimo.STATUS_ABERTO,
        )
        Emprestimo.objects.create(
            livro=livro,
            unidade=self.unidade,
            usuario=self.leitor,
            data_emprestimo=date(2026, 4, 20),
            data_devolucao=date(2026, 4, 22),
            status=Emprestimo.STATUS_DEVOLVIDO,
        )

        response = self.client.get(
            "/gestor/analytics/gestao-livros/",
            {
                "circulacao_data_inicio": "2026-04-01",
                "circulacao_data_fim": "2026-04-30",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["meta"]["periodo_circulacao"],
            {"data_inicio": "2026-04-01", "data_fim": "2026-04-30"},
        )
        self.assertEqual(
            response.data["comparativo_circulacao"]["periodo_anterior"],
            {
                "data_inicio": "2026-03-02",
                "data_fim": "2026-03-31",
                "emprestimos_iniciados": 1,
                "devolucoes": 1,
            },
        )
        self.assertEqual(
            response.data["comparativo_circulacao"]["variacao_percentual"],
            {"emprestimos_iniciados": 100.0, "devolucoes": 0.0},
        )
        self.assertEqual(len(response.data["circulacao_mensal"]), 1)
        self.assertEqual(response.data["circulacao_mensal"][0]["mes"], "2026-04")
        self.assertEqual(response.data["circulacao_mensal"][0]["emprestimos_iniciados"], 2)

        quality = response.data["qualidade_acervo"]
        self.assertEqual(quality["titulos_total"], 2)
        self.assertEqual(quality["campos_avaliados_por_titulo"], 6)
        self.assertEqual(quality["percentual_campos_preenchidos"], 58.3)
        self.assertEqual(quality["titulos_sem_autor"], 1)
        self.assertEqual(quality["titulos_sem_categoria"], 1)
        self.assertEqual(quality["titulos_sem_data_publicacao"], 1)
        self.assertEqual(quality["titulos_sem_capa"], 1)
        self.assertEqual(quality["titulos_sem_unidade"], 1)
        self.assertEqual(
            response.data["insights_acervo"]["categoria_mais_representada"]["categoria"],
            "Ficção",
        )
        self.assertEqual(
            response.data["insights_acervo"]["categoria_mais_representada"][
                "participacao_percentual"
            ],
            100.0,
        )
        self.assertIsNone(
            response.data["insights_acervo"]["categoria_menor_representacao"]
        )

        highlight = response.data["livros_em_destaque"][0]
        self.assertEqual(highlight["livro_id"], livro.id)
        self.assertEqual(highlight["capa"], "https://example.com/capa.jpg")
        self.assertEqual(highlight["emprestimos_total"], 2)
        self.assertEqual(
            response.data["meta"]["filtros_aplicados"]["circulacao_data_inicio"],
            "2026-04-01",
        )
        self.assertEqual(highlight["exemplares"], 4)
        self.assertEqual(highlight["emprestimos_abertos"], 1)
        self.assertEqual(highlight["exemplares_disponiveis"], 3)
        self.assertEqual(livro_incompleto.genero_id, None)

    def test_dashboard_rejects_invalid_circulation_period(self):
        response = self.client.get(
            "/gestor/analytics/gestao-livros/",
            {
                "circulacao_data_inicio": "2026-05-01",
                "circulacao_data_fim": "2026-04-30",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("circulacao_data_inicio", response.data["detail"])

    def test_dashboard_rejects_invalid_circulation_date_format(self):
        response = self.client.get(
            "/gestor/analytics/gestao-livros/",
            {
                "circulacao_data_inicio": "2026-4-01",
                "circulacao_data_fim": "2026-04-30",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("AAAA-MM-DD", response.data["detail"])

    def test_dashboard_rejects_circulation_period_longer_than_36_months(self):
        response = self.client.get(
            "/gestor/analytics/gestao-livros/",
            {
                "circulacao_data_inicio": "2020-01-01",
                "circulacao_data_fim": "2026-04-30",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("36 meses", response.data["detail"])

    def test_dashboard_accepts_circulation_period_of_exactly_36_months(self):
        response = self.client.get(
            "/gestor/analytics/gestao-livros/",
            {
                "circulacao_data_inicio": "2023-05-01",
                "circulacao_data_fim": "2026-04-30",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["circulacao_mensal"]), 36)
        self.assertEqual(
            response.data["meta"]["periodo_circulacao"],
            {"data_inicio": "2023-05-01", "data_fim": "2026-04-30"},
        )

    def test_dashboard_handles_empty_catalog_and_missing_comparison_baseline(self):
        response = self.client.get(
            "/gestor/analytics/gestao-livros/",
            {
                "circulacao_data_inicio": "2026-04-01",
                "circulacao_data_fim": "2026-04-30",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["indicadores"]["titulos"], 0)
        self.assertEqual(
            response.data["qualidade_acervo"]["percentual_campos_preenchidos"],
            0,
        )
        self.assertIsNone(
            response.data["insights_acervo"]["categoria_mais_representada"]
        )
        self.assertIsNone(
            response.data["insights_acervo"]["categoria_menor_representacao"]
        )
        self.assertEqual(response.data["livros_em_destaque"], [])
        self.assertEqual(response.data["emprestimos_recentes"], [])
        self.assertEqual(
            response.data["comparativo_circulacao"]["variacao_percentual"],
            {"emprestimos_iniciados": None, "devolucoes": None},
        )

    def test_open_loan_without_unit_reduces_available_copies(self):
        livro = self._livro(isbn="9780000000103")
        LivroUnidade.objects.create(
            livro=livro,
            unidade=self.unidade,
            exemplares=2,
        )
        Emprestimo.objects.create(
            livro=livro,
            unidade=None,
            usuario=self.leitor,
            data_emprestimo=date(2026, 4, 10),
            status=Emprestimo.STATUS_ABERTO,
        )

        response = self.client.get("/gestor/analytics/gestao-livros/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["situacao_exemplares"]["emprestados"], 1)
        self.assertEqual(response.data["situacao_exemplares"]["disponiveis"], 1)
        self.assertEqual(response.data["emprestimos_recentes"][0]["capa"], livro.capa)