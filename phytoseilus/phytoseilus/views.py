from django.conf import settings
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.models import ReceivedPredator
from .serializer import ReceivedPredatorSerializer


class ReceivedPredatorViewSet(viewsets.ModelViewSet):
    queryset = ReceivedPredator.objects.all()
    serializer_class = ReceivedPredatorSerializer

    @action(detail=True, methods=["get"])
    def quality_report(self, request, pk=None):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.utils import ImageReader, simpleSplit
            from reportlab.pdfgen import canvas
        except ImportError:
            return Response(
                {"detail": "ReportLab is not installed. Run: pip install reportlab"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        received = self.get_object()
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="quality-report-{received.batch_number}.pdf"'
        )

        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        # Company logo
        logo_path = settings.BASE_DIR.parent / "src" / "images" / "company logo.jpg"
        if logo_path.exists():
            pdf.drawImage(
                ImageReader(str(logo_path)),
                50,
                height - 120,
                width=82,
                height=82,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )

        # Company letterhead
        pdf.setFillColorRGB(0.118, 0.420, 0.271)
        pdf.setStrokeColorRGB(0.118, 0.420, 0.271)
        pdf.setLineWidth(1.5)
        pdf.line(50, height - 130, width - 50, height - 130)

        pdf.setFillColorRGB(0.118, 0.420, 0.271)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(145, height - 72, "REAL IPM")

        pdf.setFillColorRGB(0, 0, 0)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(145, height - 94, "QUALITY CONTROL")

        pdf.setFont("Helvetica", 10)
        pdf.drawString(145, height - 108, "Phytoseiulus Quality Report")

        pdf.setFont("Helvetica", 9)
        pdf.drawString(
            145,
            height - 122,
            f"Batch: {received.batch_number}  |  {received.received_at.strftime('%Y-%m-%d')}",
        )

        # Phytoseiulus-style insect emoji and legacy title removed to keep letterhead clean.

        # Keep report details in the default/black text color
        pdf.setFillColorRGB(0, 0, 0)

        pdf.setFont("Helvetica", 11)
        rows = [
            ("Batch number", received.batch_number),
            ("Supplier", received.supplier_name),
            ("Supplier reference", received.supplier_reference or "-"),
            ("Received", received.received_at.strftime("%Y-%m-%d %H:%M")),
            ("Number of tubs", received.number_of_tubs),
            ("Live predators", received.live_predators),
            ("Live preys", received.live_preys),
            ("Dead predators", received.dead_predators),
            ("Dead preys", received.dead_preys),
            ("Mortality rate", f"{received.mortality_rate}%"),
            ("Prey mortality rate", f"{received.prey_mortality_rate}%"),
            ("Status", received.get_status_display()),
            ("Comments", received.comments or "-"),
        ]

        y = height - 160
        for label, value in rows:
            if y < 115:
                pdf.showPage()
                pdf.setFillColorRGB(0, 0, 0)
                y = height - 60

            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(50, y, f"{label}: ")
            pdf.setFont("Helvetica", 11)
            if label == "Comments":
                comment_lines = simpleSplit(str(value), "Helvetica", 11, width - 220)
                for line in comment_lines:
                    if y < 50:
                        pdf.showPage()
                        pdf.setFillColorRGB(0, 0, 0)
                        y = height - 60
                    pdf.drawString(170, y, line)
                    y -= 16
            else:
                pdf.drawString(170, y, str(value))
                y -= 28

        # Footer divider and signature area
        pdf.setStrokeColorRGB(0.118, 0.420, 0.271)
        pdf.setLineWidth(1)
        pdf.line(50, 95, width - 50, 95)

        pdf.setStrokeColorRGB(0, 0, 0)
        pdf.setLineWidth(0.8)
        pdf.line(50, 55, 250, 55)

        pdf.setFillColorRGB(0, 0, 0)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(50, 42, "Date")

        pdf.setFont("Helvetica", 9)

        signature_name = received.signature_name or "________________"
        pdf.drawString(50, 58, signature_name)

        signature_date = (
            received.signature_date.strftime("%Y-%m-%d")
            if received.signature_date
            else "________________"
        )
        pdf.drawString(50, 42, f"Date: {signature_date}")

        designation = (
            received.get_signature_designation_display()
            if received.signature_designation
            else ""
        )
        if designation:
            pdf.drawString(50, 26, f"Designation: {designation}")

        pdf.save()
        return response