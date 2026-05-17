from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from brands.models import Brand
from categories.models import Category
from outflows.models import Outflow
from products.models import Product


class PortfolioExperienceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="portfolio",
            password="portfolio-pass",
        )
        self.category = Category.objects.create(name="Eletronicos")
        self.brand = Brand.objects.create(name="CoreStock")
        self.product = Product.objects.create(
            title="Leitor de codigo",
            category=self.category,
            brand=self.brand,
            description="Equipamento para conferencia de estoque.",
            serie_number="LC-001",
            cost_price=Decimal("120.00"),
            selling_price=Decimal("210.00"),
            quantity=3,
        )
        Outflow.objects.create(
            product=self.product,
            quantity=2,
            description="Venda balcão",
        )

    def test_landing_page_is_public_root(self):
        response = self.client.get(reverse("landing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Controle de estoque")
        self.assertContains(response, "Entrar")
        self.assertTemplateUsed(response, "landing.html")

    def test_dashboard_route_requires_login(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_authenticated_root_redirects_to_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("landing"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("home"))

    def test_authenticated_dashboard_exposes_operational_visualizations(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("dashboard_metrics", response.context)
        self.assertIn("stock_status_data", response.context)
        self.assertIn("recent_movements", response.context)
        self.assertGreaterEqual(response.context["dashboard_metrics"]["low_stock_products"], 1)
