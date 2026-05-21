from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Bill, Budget, CustomUser, Expense, Income


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    ordering = ("email",)
    search_fields = ("email", "name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2", "is_staff", "is_active"),
        }),
    )


admin.site.register(Income)
admin.site.register(Expense)
admin.site.register(Bill)
admin.site.register(Budget)
