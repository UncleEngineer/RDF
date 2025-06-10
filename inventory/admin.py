from django.contrib import admin
from .models import *


# admin.site.register(MaterialStock)
# admin.site.register(MaterialOrder)
# admin.site.register(MaterialOrderItem)

# admin.py - เพิ่มการจัดการใน Django Admin

from django.contrib import admin
from django.utils import timezone
from .models import UserProfile, MaterialStock, MaterialOrder, MaterialOrderItem, DeliveryRound

@admin.register(DeliveryRound)
class DeliveryRoundAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']


class MaterialOrderItemInline(admin.TabularInline):
    model = MaterialOrderItem
    extra = 0
    readonly_fields = ['total_cost']


@admin.register(MaterialOrder)
class MaterialOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 
        'ordered_by', 
        'delivery_round',
        'approval_status', 
        'approved_by',
        'total_cost', 
        'created_at'
    ]
    list_filter = [
        'approval_status', 
        'delivery_round',
        'created_at', 
        'approved_at'
    ]
    search_fields = [
        'ordered_by__username', 
        'note',
        'delivery_round__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'total_cost']
    inlines = [MaterialOrderItemInline]
    
    fieldsets = (
        ('ข้อมูลทั่วไป', {
            'fields': ('ordered_by', 'delivery_round', 'note', 'total_cost')
        }),
        ('การอนุมัติ', {
            'fields': ('approval_status', 'approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        ('ข้อมูลระบบ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def order_number(self, obj):
        return f"MOD-{obj.id:05d}"
    order_number.short_description = "รหัสออร์เดอร์"
    
    def save_model(self, request, obj, form, change):
        # ถ้าเปลี่ยนสถานะเป็น approved และยังไม่มีผู้อนุมัติ
        if obj.approval_status == 'approved' and not obj.approved_by:
            obj.approved_by = request.user
            obj.approved_at = timezone.now()
        # ถ้าเปลี่ยนสถานะเป็น pending หรือ rejected ให้ล้างข้อมูลการอนุมัติ
        elif obj.approval_status in ['pending', 'rejected']:
            if obj.approval_status == 'rejected':
                obj.approved_by = request.user
                obj.approved_at = timezone.now()
            else:
                obj.approved_by = None
                obj.approved_at = None
        
        super().save_model(request, obj, form, change)


@admin.register(MaterialStock)
class MaterialStockAdmin(admin.ModelAdmin):
    list_display = [
        'code', 
        'name', 
        'category', 
        'cost', 
        'sale_price', 
        'reorder_point', 
        'max_stock',
        'unit'
    ]
    list_filter = ['category', 'unit']
    search_fields = ['code', 'name', 'barcode']
    list_editable = ['cost', 'sale_price', 'reorder_point', 'max_stock']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type']
    list_filter = ['user_type']
    search_fields = ['user__username', 'user__email']