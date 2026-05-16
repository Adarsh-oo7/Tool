from django.contrib import admin
from .models import Company, Branch, Segment


class SegmentInline(admin.TabularInline):
    model = Segment
    extra = 0


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display  = ('name', 'phone', 'email', 'created_at')
    search_fields = ('name',)
    inlines       = [BranchInline]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display  = ('name', 'company', 'phone', 'is_active')
    list_filter   = ('company', 'is_active')
    search_fields = ('name',)
    inlines       = [SegmentInline]


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display  = ('name', 'branch', 'is_active')
    list_filter   = ('branch', 'name', 'is_active')
