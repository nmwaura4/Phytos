from datetime import timedelta
from io import BytesIO

from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from .forms import EmailLoginForm, RegistrationForm
from .models import ReceivedPredator


def register(request):
    if request.user.is_authenticated:
        return redirect("api_dashboard")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except (ValidationError, ValueError) as error:
            form.add_error(None, error)
        else:
            auth_login(request, user)
            return redirect("api_dashboard")

    return render(request, "api/auth.html", {"form": form, "mode": "register"})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("api_dashboard")

    form = EmailLoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("api_dashboard")

    return render(
        request,
        "api/auth.html",
        {
            "form": form,
            "mode": "login",
            "next_url": request.GET.get("next", ""),
        },
    )


@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect("login")


@login_required(login_url="login")
def dashboard(request):
    records = ReceivedPredator.objects.all()
    status = request.GET.get("status")
    search = request.GET.get("supplier", "").strip()
    period = request.GET.get("period", "")

    today = timezone.localdate()
    if period == "daily":
        records = records.filter(received_at__date=today)
    elif period == "weekly":
        records = records.filter(
            received_at__date__gte=today - timedelta(days=6),
            received_at__date__lte=today,
        )
    elif period == "monthly":
        records = records.filter(
            received_at__date__gte=today.replace(day=1),
            received_at__date__lte=today,
        )

    if status:
        records = records.filter(status=status)
    if search:
        records = records.filter(
            Q(supplier_name__icontains=search)
            | Q(batch_number__icontains=search)
        )

    summary = records.aggregate(
        total=Count("id"),
        tubs=Sum("number_of_tubs"),
        average_mortality=Avg("mortality_rate"),
    )

    recent_records = records.order_by("-received_at")[:5]

    context = {
        "records": recent_records,
        "summary": summary,
        "accepted_count": ReceivedPredator.objects.filter(status="accepted").count(),
        "pending_count": ReceivedPredator.objects.filter(status="pending").count(),
        "rejected_count": ReceivedPredator.objects.filter(status="rejected").count(),
        "status_filter": status or "",
        "supplier_filter": search,
        "period_filter": period,
    }
    return render(request, "api/dashboard.html", context)


@login_required(login_url="login")
def create_received_predator(request):
    if request.method == "POST":
        try:
            record = ReceivedPredator(
                supplier_name=request.POST["supplier_name"],
                supplier_reference=request.POST.get("supplier_reference", ""),
                number_of_tubs=request.POST["number_of_tubs"],
                batch_number=request.POST["batch_number"],
                live_predators=request.POST["live_predators"],
                live_preys=request.POST["live_preys"],
                dead_predators=request.POST.get("dead_predators", 0),
                dead_preys=request.POST.get("dead_preys", 0),
                contaminant=request.POST.get("contaminant", ""),
                contamination_level=request.POST.get("contamination_level", 0),
                status=request.POST.get("status", "pending"),
                comments=request.POST.get("comments", ""),
            )
            record.full_clean()
            record.save()
            messages.success(request, "Received batch saved successfully.")
            return redirect("api_dashboard")
        except Exception as exc:
            messages.error(request, str(exc))

    return render(request, "api/create.html")


@login_required(login_url="login")
def received_predator_detail(request, pk):
    record = get_object_or_404(ReceivedPredator, pk=pk)

    if request.method == "POST":
        record.status = request.POST.get("status", record.status)
        record.comments = request.POST.get("comments", record.comments)
        record.signature_name = request.POST.get("signature_name", "").strip()
        record.signature_designation = request.POST.get("signature_designation", "")
        signature_date = request.POST.get("signature_date", "")
        record.signature_date = signature_date or None
        record.save()
        messages.success(request, "Quality status updated.")
        return redirect("received_predator_detail", pk=record.pk)

    return render(request, "api/detail.html", {"record": record})


@login_required(login_url="login")
def edit_received_predator(request, pk):
    record = get_object_or_404(ReceivedPredator, pk=pk)

    if request.method == "POST":
        try:
            record.supplier_name = request.POST["supplier_name"]
            record.supplier_reference = request.POST.get("supplier_reference", "")
            record.number_of_tubs = request.POST["number_of_tubs"]
            record.batch_number = request.POST["batch_number"]
            record.live_predators = request.POST["live_predators"]
            record.live_preys = request.POST["live_preys"]
            record.dead_predators = request.POST.get("dead_predators", 0)
            record.dead_preys = request.POST.get("dead_preys", 0)
            record.contaminant = request.POST.get("contaminant", "")
            record.contamination_level = request.POST.get("contamination_level", 0)
            record.status = request.POST.get("status", record.status)
            record.comments = request.POST.get("comments", "")
            record.save()
            messages.success(request, "Reception updated successfully.")
            return redirect("received_predator_detail", pk=record.pk)
        except Exception as exc:
            messages.error(request, str(exc))

    return render(request, "api/edit.html", {"record": record})


@login_required(login_url="login")
def delete_received_predator(request, pk):
    record = get_object_or_404(ReceivedPredator, pk=pk)

    if request.method == "POST":
        record.delete()
        messages.success(request, "Reception deleted successfully.")
        return redirect("api_dashboard")

    return render(request, "api/delete.html", {"record": record})


@login_required(login_url="login")
def report(request):
    records = ReceivedPredator.objects.all()
    status = request.GET.get("status")
    supplier = request.GET.get("supplier", "").strip()

    if status:
        records = records.filter(status=status)
    if supplier:
        records = records.filter(supplier_name__icontains=supplier)

    summary = ReceivedPredator.objects.aggregate(
        total=Count("id"),
        tubs=Sum("number_of_tubs"),
        average_mortality=Avg("mortality_rate"),
    )

    context = {
        "records": records,
        "summary": summary,
        "accepted_count": ReceivedPredator.objects.filter(status="accepted").count(),
        "pending_count": ReceivedPredator.objects.filter(status="pending").count(),
        "rejected_count": ReceivedPredator.objects.filter(status="rejected").count(),
        "status_filter": status or "",
        "supplier_filter": supplier,
    }
    return render(request, "api/report.html", context)


@login_required(login_url="login")
def download_qc_workbook(request, period):
    today = timezone.localdate()
    if period == "daily":
        start_date = end_date = today
    elif period == "weekly":
        start_date = today - timedelta(days=6)
        end_date = today
    elif period == "monthly":
        start_date = today.replace(day=1)
        end_date = today
    else:
        raise Http404("Unknown QC report period.")

    records = ReceivedPredator.objects.filter(
        received_at__date__gte=start_date,
        received_at__date__lte=end_date,
    )
    summary = records.aggregate(
        total=Count("id"),
        tubs=Sum("number_of_tubs"),
        average_mortality=Avg("mortality_rate"),
    )

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    summary_sheet.append([f"{period.title()} QC Report"])
    summary_sheet.append(["Period", start_date.isoformat(), end_date.isoformat()])
    summary_sheet.append(["Generated", timezone.localtime().strftime("%Y-%m-%d %H:%M")])
    summary_sheet.append(["Total batches", summary["total"] or 0])
    summary_sheet.append(["Total tubs", summary["tubs"] or 0])
    summary_sheet.append(["Average mortality (%)", summary["average_mortality"] or 0])
    for status_value, status_label in ReceivedPredator.Status.choices:
        summary_sheet.append([
            f"{status_label} batches",
            records.filter(status=status_value).count(),
        ])
    summary_sheet["A1"].font = Font(bold=True, size=16, color="FFFFFF")
    summary_sheet["A1"].fill = PatternFill("solid", fgColor="1E6B45")
    summary_sheet.column_dimensions["A"].width = 28
    summary_sheet.column_dimensions["B"].width = 24
    summary_sheet.column_dimensions["C"].width = 24

    details_sheet = workbook.create_sheet("Batches")
    headers = [
        "Batch number", "Supplier", "Supplier reference", "Received at",
        "Tubs", "Live predators", "Live preys", "Dead predators",
        "Dead preys", "Mortality (%)", "Contaminant", "Contamination level",
        "Status", "Comments",
    ]
    details_sheet.append(headers)
    for cell in details_sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1E6B45")

    for record in records:
        details_sheet.append([
            record.batch_number,
            record.supplier_name,
            record.supplier_reference,
            timezone.localtime(record.received_at).replace(tzinfo=None),
            record.number_of_tubs,
            record.live_predators,
            record.live_preys,
            record.dead_predators,
            record.dead_preys,
            float(record.mortality_rate),
            record.contaminant,
            float(record.contamination_level),
            record.get_status_display(),
            record.comments,
        ])
    details_sheet.freeze_panes = "A2"
    details_sheet.auto_filter.ref = details_sheet.dimensions
    for column in details_sheet.columns:
        column_letter = column[0].column_letter
        details_sheet.column_dimensions[column_letter].width = min(
            max(max(len(str(cell.value or "")) for cell in column) + 2, 14), 36
        )

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{period}_QC_Report.xlsx"'
    return response
