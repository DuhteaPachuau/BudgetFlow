import json
import os
import urllib.request
from calendar import month_name
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BillForm, BudgetForm, ExpenseForm, IncomeForm, LoginForm, ProfileForm, RegisterForm
from .gmail_import import (
    build_flow,
    credentials_to_dict,
    fetch_suggested_bills,
    gmail_dependencies_ready,
)
from .models import Bill, Budget, CustomUser, Expense, Income


def money(value):
    return float(value or Decimal("0.00"))


def selected_month(request):
    raw = request.GET.get("month")
    today = timezone.localdate()
    if raw:
        try:
            year, month = [int(part) for part in raw.split("-")]
            return date(year, month, 1)
        except ValueError:
            pass
    return date(today.year, today.month, 1)


def month_label(day):
    return f"{month_name[day.month]} {day.year}"


def monthly_queryset(queryset, field, selected):
    return queryset.filter(**{f"{field}__year": selected.year, f"{field}__month": selected.month})


def totals_for(user, selected):
    incomes = monthly_queryset(Income.objects.filter(user=user), "date", selected)
    expenses = monthly_queryset(Expense.objects.filter(user=user), "date", selected)
    bills = monthly_queryset(Bill.objects.filter(user=user), "due_date", selected)
    income_total = incomes.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    expense_total = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    paid_bills_total = bills.filter(is_paid=True).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    pending_bills_total = bills.filter(is_paid=False).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    savings = income_total - expense_total - paid_bills_total
    forecast = savings - pending_bills_total
    savings_rate = (savings / income_total * Decimal("100")) if income_total else Decimal("0")
    return {
        "incomes": incomes,
        "expenses": expenses,
        "bills": bills,
        "income_total": income_total,
        "expense_total": expense_total,
        "paid_bills_total": paid_bills_total,
        "pending_bills_total": pending_bills_total,
        "savings": savings,
        "forecast": forecast,
        "savings_rate": savings_rate,
    }


def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


def service_worker(request):
    content = (settings.BASE_DIR / "static" / "service-worker.js").read_text(encoding="utf-8")
    return HttpResponse(content, content_type="application/javascript")


def build_google_auth_flow():
    from google_auth_oauthlib.flow import Flow

    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_AUTH_REDIRECT_URI],
            }
        },
        scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        redirect_uri=settings.GOOGLE_AUTH_REDIRECT_URI,
    )


def fetch_google_profile(token):
    request = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")
    return render(request, "auth/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.cleaned_data["user"])
        return redirect("dashboard")
    return render(request, "auth/login.html", {"form": form})


def google_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if not gmail_dependencies_ready():
        messages.error(request, "Install Google auth dependencies with: pip install -r requirements.txt")
        return redirect("login")
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        messages.error(request, "Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET before using Google login.")
        return redirect("login")
    if settings.DEBUG:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    flow = build_google_auth_flow()
    authorization_url, state = flow.authorization_url(
        access_type="online",
        include_granted_scopes="false",
        prompt="select_account",
    )
    request.session["google_auth_state"] = state
    if getattr(flow, "code_verifier", None):
        request.session["google_auth_code_verifier"] = flow.code_verifier
    return redirect(authorization_url)


def google_callback(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if not gmail_dependencies_ready():
        messages.error(request, "Google auth dependencies are not installed.")
        return redirect("login")
    state = request.session.get("google_auth_state")
    if state and request.GET.get("state") != state:
        messages.error(request, "Google login failed because the OAuth state did not match.")
        return redirect("login")
    if settings.DEBUG:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    flow = build_google_auth_flow()
    code_verifier = request.session.get("google_auth_code_verifier")
    if code_verifier:
        flow.code_verifier = code_verifier
    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        profile = fetch_google_profile(flow.credentials.token)
    except Exception as exc:
        messages.error(request, f"Google login failed: {exc}")
        return redirect("login")

    email = profile.get("email")
    if not email:
        messages.error(request, "Google did not return an email address.")
        return redirect("login")

    name = profile.get("name") or email.split("@")[0]
    user, created = CustomUser.objects.get_or_create(email=email, defaults={"name": name})
    if created:
        user.set_unusable_password()
        user.save()
    elif not user.name and name:
        user.name = name
        user.save(update_fields=["name", "username"])
    login(request, user)
    messages.success(request, "Signed in with Google.")
    return redirect("dashboard")


def logout_view(request):
    logout(request)
    return redirect("landing")


@login_required
def dashboard(request):
    selected = selected_month(request)
    data = totals_for(request.user, selected)
    category_totals = {}
    expense_rows = data["expenses"].values("category").annotate(total=Sum("amount")).order_by("category")
    bill_rows = data["bills"].filter(is_paid=True).values("category").annotate(total=Sum("amount")).order_by("category")
    for row in expense_rows:
        category_totals[row["category"]] = category_totals.get(row["category"], Decimal("0")) + row["total"]
    for row in bill_rows:
        category_totals[row["category"]] = category_totals.get(row["category"], Decimal("0")) + row["total"]
    labels = list(category_totals.keys())
    values = [money(value) for value in category_totals.values()]
    alerts = data["bills"].filter(is_paid=False).order_by("due_date")
    context = {
        **data,
        "dashboard_expense_total": data["expense_total"] + data["paid_bills_total"],
        "selected_month": selected.strftime("%Y-%m"),
        "selected_label": month_label(selected),
        "category_labels": json.dumps(labels),
        "category_values": json.dumps(values),
        "alerts": alerts,
    }
    return render(request, "planner/dashboard.html", context)


@login_required
def budgets_page(request):
    selected = selected_month(request)
    initial = {"month": selected}
    form = BudgetForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        budget = form.save(commit=False)
        budget.user = request.user
        budget.month = budget.month.replace(day=1)
        existing = Budget.objects.filter(user=request.user, category=budget.category, month=budget.month).first()
        if existing:
            existing.amount = budget.amount
            existing.save()
            messages.success(request, "Budget updated.")
        else:
            budget.save()
            messages.success(request, "Budget saved.")
        return redirect("budgets")
    items = Budget.objects.filter(user=request.user).order_by("-month", "category")
    return render(request, "planner/budgets.html", {
        "form": form,
        "items": items,
        "selected_month": selected.strftime("%Y-%m"),
    })


@login_required
def budget_delete(request, pk):
    get_object_or_404(Budget, pk=pk, user=request.user).delete()
    return redirect("budgets")


@login_required
def monthly_report(request):
    selected = selected_month(request)
    data = totals_for(request.user, selected)
    paid_bills = data["bills"].filter(is_paid=True)
    pending_bills = data["bills"].filter(is_paid=False)
    context = {
        **data,
        "paid_bills": paid_bills,
        "pending_bills": pending_bills,
        "dashboard_expense_total": data["expense_total"] + data["paid_bills_total"],
        "selected_month": selected.strftime("%Y-%m"),
        "selected_label": month_label(selected),
        "generated_at": timezone.localtime(),
    }
    return render(request, "planner/monthly_report.html", context)


@login_required
def income_page(request):
    form = IncomeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        income = form.save(commit=False)
        income.user = request.user
        income.save()
        messages.success(request, "Income saved.")
        return redirect("income")
    return render(request, "planner/income.html", {"form": form, "items": Income.objects.filter(user=request.user)})


@login_required
def income_edit(request, pk):
    item = get_object_or_404(Income, pk=pk, user=request.user)
    form = IncomeForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("income")
    return render(request, "planner/form_page.html", {"form": form, "title": "Edit Income"})


@login_required
def income_delete(request, pk):
    get_object_or_404(Income, pk=pk, user=request.user).delete()
    return redirect("income")


@login_required
def expenses_page(request):
    form = ExpenseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False)
        expense.user = request.user
        expense.save()
        messages.success(request, "Expense saved.")
        return redirect("expenses")
    return render(request, "planner/expenses.html", {"form": form, "items": Expense.objects.filter(user=request.user)})


@login_required
def expense_edit(request, pk):
    item = get_object_or_404(Expense, pk=pk, user=request.user)
    form = ExpenseForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("expenses")
    return render(request, "planner/form_page.html", {"form": form, "title": "Edit Expense"})


@login_required
def expense_delete(request, pk):
    get_object_or_404(Expense, pk=pk, user=request.user).delete()
    return redirect("expenses")


@login_required
def bills_page(request):
    selected = selected_month(request)
    data = totals_for(request.user, selected)
    items = Bill.objects.filter(user=request.user).order_by("is_paid", "due_date", "name")
    return render(request, "planner/bills.html", {"items": items, **data})


@login_required
def bill_add_page(request):
    form = BillForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        bill = form.save(commit=False)
        bill.user = request.user
        bill.source = "manual"
        bill.save()
        messages.success(request, "Bill saved.")
        return redirect("bills")
    return render(request, "planner/bill_add.html", {"form": form})


@login_required
def bill_edit(request, pk):
    item = get_object_or_404(Bill, pk=pk, user=request.user)
    form = BillForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("bills")
    return render(request, "planner/form_page.html", {"form": form, "title": "Edit Bill"})


@login_required
def bill_delete(request, pk):
    get_object_or_404(Bill, pk=pk, user=request.user).delete()
    return redirect("bills")


@login_required
def bill_mark_paid(request, pk):
    bill = get_object_or_404(Bill, pk=pk, user=request.user)
    bill.is_paid = True
    bill.save()
    messages.success(request, f"{bill.name} marked paid.")
    return redirect("bills")


@login_required
def gmail_connect(request):
    if not gmail_dependencies_ready():
        messages.error(request, "Install Gmail dependencies with: pip install -r requirements.txt")
        return redirect("gmail_import")
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        messages.error(request, "Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET before connecting Gmail.")
        return redirect("gmail_import")
    if settings.DEBUG:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    flow = build_flow(settings)
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="false",
        prompt="consent",
    )
    request.session["gmail_oauth_state"] = state
    if getattr(flow, "code_verifier", None):
        request.session["gmail_code_verifier"] = flow.code_verifier
    return redirect(authorization_url)


@login_required
def gmail_callback(request):
    if not gmail_dependencies_ready():
        messages.error(request, "Gmail dependencies are not installed.")
        return redirect("gmail_import")
    state = request.session.get("gmail_oauth_state")
    if state and request.GET.get("state") != state:
        messages.error(request, "Gmail connection failed because the OAuth state did not match.")
        return redirect("gmail_import")
    if settings.DEBUG:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    flow = build_flow(settings)
    code_verifier = request.session.get("gmail_code_verifier")
    if code_verifier:
        flow.code_verifier = code_verifier
    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
    except Exception as exc:
        messages.error(request, f"Gmail connection failed: {exc}")
        return redirect("gmail_import")
    request.session["gmail_credentials"] = credentials_to_dict(flow.credentials)
    messages.success(request, "Gmail connected. Review suggested bills before adding them.")
    return redirect("gmail_import")


@login_required
def gmail_import_page(request):
    credentials = request.session.get("gmail_credentials")
    suggestions = request.session.get("gmail_suggestions", [])
    if request.method == "POST" and request.POST.get("action") == "scan":
        if not credentials:
            messages.error(request, "Connect Gmail first.")
            return redirect("gmail_import")
        existing_ids = set(Bill.objects.filter(user=request.user, source="gmail").values_list("gmail_message_id", flat=True))
        try:
            found = fetch_suggested_bills(credentials, existing_ids)
        except Exception as exc:
            messages.error(request, f"Gmail scan failed: {exc}")
            return redirect("gmail_import")
        suggestions = [
            {
                "message_id": item.message_id,
                "subject": item.subject,
                "service": item.service,
                "amount": str(item.amount),
                "due_date": item.due_date.isoformat(),
                "category": item.category,
                "snippet": item.snippet,
            }
            for item in found
        ]
        request.session["gmail_suggestions"] = suggestions
        messages.success(request, f"Found {len(suggestions)} suggested bill(s).")
        return redirect("gmail_import")
    if request.method == "POST" and request.POST.get("action") == "add":
        selected_ids = set(request.POST.getlist("message_id"))
        added = 0
        for item in suggestions:
            if item["message_id"] not in selected_ids:
                continue
            if Bill.objects.filter(user=request.user, source="gmail", gmail_message_id=item["message_id"]).exists():
                continue
            Bill.objects.create(
                user=request.user,
                name=item["service"],
                service=item["service"],
                amount=Decimal(item["amount"]),
                due_date=date.fromisoformat(item["due_date"]),
                category=item["category"],
                is_recurring=True,
                source="gmail",
                gmail_message_id=item["message_id"],
                email_subject=item["subject"],
            )
            added += 1
        request.session["gmail_suggestions"] = [item for item in suggestions if item["message_id"] not in selected_ids]
        messages.success(request, f"Added {added} bill(s) from Gmail.")
        return redirect("bills")
    return render(request, "planner/gmail_import.html", {
        "is_connected": bool(credentials),
        "is_configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "suggestions": suggestions,
    })


@login_required
def trends_page(request):
    selected = selected_month(request)
    year = int(request.GET.get("year", selected.year))
    labels = [month_name[i][:3] for i in range(1, 13)]
    income_values = []
    expense_values = []
    bill_values = []
    savings_values = []
    for month in range(1, 13):
        point = date(year, month, 1)
        data = totals_for(request.user, point)
        income_values.append(money(data["income_total"]))
        expense_values.append(money(data["expense_total"]))
        bill_values.append(money(data["paid_bills_total"]))
        savings_values.append(money(data["savings"]))
    context = {
        "year": year,
        "selected_month": selected.strftime("%Y-%m"),
        "trend_labels": json.dumps(labels),
        "trend_income": json.dumps(income_values),
        "trend_expenses": json.dumps(expense_values),
        "trend_bills": json.dumps(bill_values),
        "trend_savings": json.dumps(savings_values),
    }
    return render(request, "planner/trends.html", context)


@login_required
def profile_page(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    context = {
        "form": form,
        "income_count": Income.objects.filter(user=request.user).count(),
        "expense_count": Expense.objects.filter(user=request.user).count(),
        "bill_count": Bill.objects.filter(user=request.user).count(),
        "budget_count": Budget.objects.filter(user=request.user).count(),
        "gmail_connected": bool(request.session.get("gmail_credentials")),
        "google_auth_ready": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "joined_label": request.user.date_joined.strftime("%d %b %Y"),
    }
    return render(request, "planner/profile.html", context)
