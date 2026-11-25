import base64
from io import BytesIO
import re
import zlib

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from phytoseilus.auth import create_user, get_user_by_email, require_authentication
from .models import ReceivedPredator


class AuthenticationHelperTests(TestCase):
	def test_create_user_stores_a_hashed_password(self):
		password = "cT9#vQ2!mL7@pR4"
		user = create_user("user@example.com", password)

		self.assertNotEqual(user.password, password)
		self.assertTrue(user.check_password(password))
		self.assertEqual(get_user_by_email(" USER@example.com "), user)

	def test_authentication_returns_tokens_only_for_valid_credentials(self):
		create_user("user@example.com", "cT9#vQ2!mL7@pR4")

		tokens = require_authentication("user@example.com", "cT9#vQ2!mL7@pR4")

		self.assertIsNotNone(tokens)
		assert tokens is not None
		self.assertTrue(tokens["access"])
		self.assertTrue(tokens["refresh"])
		self.assertIsNone(require_authentication("user@example.com", "wrong-password"))

	def test_create_user_rejects_duplicate_email_and_invalid_password(self):
		create_user("user@example.com", "cT9#vQ2!mL7@pR4")

		with self.assertRaises(ValueError):
			create_user("USER@example.com", "cT9#vQ2!mL7@pR4")
		with self.assertRaises(ValidationError):
			create_user("other@example.com", "123")

	def test_email_lookup_rejects_ambiguous_matches(self):
		User.objects.create_user(
			username="legacy-one", email="duplicate@example.com", password="password"
		)
		User.objects.create_user(
			username="legacy-two", email="DUPLICATE@example.com", password="password"
		)

		self.assertIsNone(get_user_by_email("duplicate@example.com"))


class AuthenticationPageTests(TestCase):
	def test_registration_creates_account_and_starts_session(self):
		password = "cT9#vQ2!mL7@pR4"
		response = self.client.post(
			reverse("register"),
			{
				"email": "web-user@example.com",
				"password": password,
				"password_confirm": password,
			},
		)

		self.assertRedirects(response, reverse("api_dashboard"))
		user = User.objects.get(email="web-user@example.com")
		self.assertTrue(user.check_password(password))
		self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

	def test_login_accepts_email_and_password(self):
		password = "cT9#vQ2!mL7@pR4"
		User.objects.create_user(
			username="login-user@example.com",
			email="login-user@example.com",
			password=password,
		)

		response = self.client.post(
			reverse("login"),
			{"email": "login-user@example.com", "password": password},
		)

		self.assertRedirects(response, reverse("api_dashboard"))
		self.assertIn("_auth_user_id", self.client.session)

	def test_dashboard_redirects_anonymous_users_to_login(self):
		response = self.client.get(reverse("api_dashboard"))

		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse("login"), response.url)


class AuthenticatedTestCase(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="test-user@example.com",
			email="test-user@example.com",
			password="test-password",
		)
		self.client.force_login(self.user)


class QCWorkbookDownloadTests(AuthenticatedTestCase):
	def setUp(self):
		super().setUp()
		self.record = ReceivedPredator.objects.create(
			supplier_name="Test supplier",
			number_of_tubs=3,
			batch_number="TEST-001",
			live_predators=90,
			live_preys=10,
			dead_predators=10,
			received_at=timezone.now(),
		)

	def test_daily_weekly_and_monthly_workbooks_download(self):
		for period in ("daily", "weekly", "monthly"):
			with self.subTest(period=period):
				response = self.client.get(
					reverse("qc_report_download", args=[period])
				)

				self.assertEqual(response.status_code, 200)
				self.assertEqual(
					response["Content-Type"],
					"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				)
				self.assertIn(f'{period}_QC_Report.xlsx', response["Content-Disposition"])

				workbook = load_workbook(BytesIO(response.content), read_only=True)
				self.assertEqual(workbook.sheetnames, ["Summary", "Batches"])
				rows = list(workbook["Batches"].values)
				self.assertEqual(rows[1][0], self.record.batch_number)
				workbook.close()

	def test_unknown_period_returns_404(self):
		response = self.client.get(reverse("qc_report_download", args=["yearly"]))
		self.assertEqual(response.status_code, 404)


class DashboardRateIndicatorTests(AuthenticatedTestCase):
	def test_dashboard_search_finds_batch_number_and_supplier(self):
		ReceivedPredator.objects.create(
			supplier_name="K2A",
			number_of_tubs=1,
			batch_number="K0010112026",
			live_predators=97,
			dead_predators=3,
			live_preys=10,
		)

		response = self.client.get(
			reverse("api_dashboard"), {"supplier": "K0010112026"}
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "K0010112026")
		self.assertContains(response, "K2A")
		self.assertEqual(response.context["summary"]["total"], 1)

	def test_dashboard_average_uses_filtered_batches(self):
		ReceivedPredator.objects.create(
			supplier_name="Selected supplier",
			number_of_tubs=1,
			batch_number="SELECTED-001",
			live_predators=90,
			dead_predators=10,
			live_preys=10,
		)
		ReceivedPredator.objects.create(
			supplier_name="Other supplier",
			number_of_tubs=1,
			batch_number="OTHER-001",
			live_predators=100,
			dead_predators=0,
			live_preys=10,
		)

		response = self.client.get(
			reverse("api_dashboard"), {"supplier": "Selected supplier"}
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(float(response.context["summary"]["average_mortality"]), 9.09)
		self.assertEqual(response.context["summary"]["total"], 1)

	def test_dashboard_applies_requested_rate_thresholds(self):
		ReceivedPredator.objects.create(
			supplier_name="High mortality supplier",
			number_of_tubs=1,
			batch_number="HIGH-001",
			live_predators=90,
			dead_predators=10,
			live_preys=10,
			dead_preys=1,
		)
		ReceivedPredator.objects.create(
			supplier_name="Medium mortality supplier",
			number_of_tubs=1,
			batch_number="MEDIUM-001",
			live_predators=95,
			dead_predators=5,
			live_preys=16,
			dead_preys=1,
		)

		response = self.client.get(reverse("api_dashboard"))
		content = response.content.decode()

		self.assertEqual(response.status_code, 200)
		self.assertEqual(content.count('class="rate-red"'), 0)
		self.assertEqual(content.count('class="rate-yellow"'), 1)
		self.assertContains(response, "Prey mortality")


class QCPdfReportTests(AuthenticatedTestCase):
	def test_pdf_includes_saved_comment(self):
		comment = "Saved QC comment for this batch"
		record = ReceivedPredator.objects.create(
			supplier_name="Test supplier",
			number_of_tubs=1,
			batch_number="PDF-001",
			live_predators=100,
			live_preys=10,
			comments=comment,
		)

		response = self.client.get(
			f"/api/received-predators/{record.pk}/quality_report/"
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Content-Type"], "application/pdf")
		stream = re.search(rb"stream\r?\n(.*?)endstream", response.content, re.S)
		self.assertIsNotNone(stream)
		assert stream is not None
		compressed = base64.a85decode(stream.group(1).removesuffix(b"~>"))
		pdf_text = zlib.decompress(compressed)
		self.assertIn(b"Comments:", pdf_text)
		self.assertIn(comment.encode(), pdf_text)
