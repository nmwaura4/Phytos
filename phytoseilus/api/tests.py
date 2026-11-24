import base64
from io import BytesIO
import re
import zlib

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from .models import ReceivedPredator


class QCWorkbookDownloadTests(TestCase):
	def setUp(self):
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


class DashboardRateIndicatorTests(TestCase):
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


class QCPdfReportTests(TestCase):
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
