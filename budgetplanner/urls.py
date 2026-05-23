from django.contrib import admin
from django.urls import path

from planner import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.landing, name="landing"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("auth/google/", views.google_login, name="google_login"),
    path("auth/google/callback/", views.google_callback, name="google_callback"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("reports/monthly/", views.monthly_report, name="monthly_report"),
    path("income/", views.income_page, name="income"),
    path("income/<int:pk>/edit/", views.income_edit, name="income_edit"),
    path("income/<int:pk>/delete/", views.income_delete, name="income_delete"),
    path("expenses/", views.expenses_page, name="expenses"),
    path("expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),
    path("budgets/", views.budgets_page, name="budgets"),
    path("budgets/<int:pk>/delete/", views.budget_delete, name="budget_delete"),
    path("bills/", views.bills_page, name="bills"),
    path("bills/add/", views.bill_add_page, name="bill_add"),
    path("bills/<int:pk>/edit/", views.bill_edit, name="bill_edit"),
    path("bills/<int:pk>/delete/", views.bill_delete, name="bill_delete"),
    path("bills/<int:pk>/paid/", views.bill_mark_paid, name="bill_mark_paid"),
    path("gmail/connect/", views.gmail_connect, name="gmail_connect"),
    path("gmail/callback/", views.gmail_callback, name="gmail_callback"),
    path("gmail/import/", views.gmail_import_page, name="gmail_import"),
    path("trends/", views.trends_page, name="trends"),
    path("profile/", views.profile_page, name="profile"),
    path("service-worker.js", views.service_worker, name="service_worker"),
    path("privacy/", views.privacy_page, name="privacy"),
    path("terms/", views.terms_page, name="terms"),
]
