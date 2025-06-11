from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import *
from django.contrib.auth.models import User
import pandas as pd
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import *
from django.contrib.auth.models import User
import pandas as pd
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Q
from datetime import datetime, timedelta, date
from collections import defaultdict

# Superuser check function
def is_superuser(user):
    """Check if user is superuser"""
    return user.is_authenticated and user.is_superuser

@login_required
def custom_logout(request):
    username = request.user.username
    logout(request)
    messages.success(request, f'คุณ {username} ได้ออกจากระบบเรียบร้อยแล้ว')
    return redirect('login')



@login_required
def home(request):
    # Base queryset
    orders = MaterialOrder.objects.all().order_by('-created_at')
    
    # Admin user list
    admin_list = ['admin', 'admin2', 'area_manager', 'coo', 'ceo','KITCHEN_CENTRAL']
    
    # Get filter parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    delivery_round_id = request.GET.get('delivery_round')
    ordered_by_id = request.GET.get('ordered_by')
    status_filter = request.GET.get('status')
    
    # Build active filters list for display
    active_filters = []
    
    # Apply date filters
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__gte=from_date)
            active_filters.append(f'จากวันที่: {from_date.strftime("%d/%m/%Y")}')
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__lte=to_date)
            active_filters.append(f'ถึงวันที่: {to_date.strftime("%d/%m/%Y")}')
        except ValueError:
            pass
    
    # Apply delivery round filter
    if delivery_round_id:
        try:
            delivery_round = DeliveryRound.objects.get(pk=delivery_round_id)
            orders = orders.filter(delivery_round=delivery_round)
            active_filters.append(f'รอบจัดส่ง: {delivery_round.name}')
        except DeliveryRound.DoesNotExist:
            pass
    
    # Apply user filter (only for admin users)
    if ordered_by_id and request.user.username in admin_list:
        try:
            ordered_by_user = User.objects.get(pk=ordered_by_id)
            orders = orders.filter(ordered_by=ordered_by_user)
            active_filters.append(f'ผู้สั่ง: {ordered_by_user.username}')
        except User.DoesNotExist:
            pass
    
    # Apply status filter
    if status_filter:
        orders = orders.filter(approval_status=status_filter)
        status_names = {
            'pending': 'รออนุมัติ',
            'approved': 'อนุมัติแล้ว',
            'rejected': 'ไม่อนุมัติ'
        }
        active_filters.append(f'สถานะ: {status_names.get(status_filter, status_filter)}')
    
    # Apply user access control (filter by user unless admin)
    filter_order = []
    all_cost = []
    
    for o in orders:
        if request.user.username in admin_list:
            filter_order.append(o)
            all_cost.append(o.total_cost or 0)
        elif o.ordered_by.username == request.user.username:
            filter_order.append(o)
            all_cost.append(o.total_cost or 0)
    
    # Calculate totals
    sumtotal = len(filter_order)
    total_cost = sum(all_cost)
    
    # Get status counts for the filtered results
    filtered_order_ids = [order.id for order in filter_order]
    status_counts = MaterialOrder.objects.filter(id__in=filtered_order_ids).aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(approval_status='pending')),
        approved=Count('id', filter=Q(approval_status='approved')),
        rejected=Count('id', filter=Q(approval_status='rejected'))
    )
    
    # Get data for filter dropdowns
    delivery_rounds = DeliveryRound.objects.filter(is_active=True).order_by('name')
    
    # Get users for admin filter (only show users who have created orders)
    users = []
    if request.user.username in admin_list:
        users = User.objects.filter(
            materialorder__isnull=False
        ).distinct().order_by('username')
    
    context = {
        'orders': filter_order,
        'status_counts': status_counts,
        'total_order': sumtotal,
        'total_cost': total_cost,
        'delivery_rounds': delivery_rounds,
        'users': users,
        'admin_list': admin_list,
        'active_filters': active_filters,
    }
    
    return render(request, 'inventory/home.html', context)



# หน้าอัปโหลด Excel
@login_required
def import_excel(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        df = pd.read_excel(request.FILES['excel_file'])

        for _, row in df.iterrows():
            def safe_value(val, default='-'):
                if pd.isna(val):
                    return default
                return val

            MaterialStock.objects.update_or_create(
                code=safe_value(row['รหัสสินค้า']),
                defaults={
                    'name': safe_value(row['ชื่อสินค้า']),
                    'barcode': safe_value(row['Barcode']),
                    'cost': safe_value(row['ต้นทุน'], 0.0),
                    'avg_cost': safe_value(row['ต้นทุนเฉลี่ย'], 0.0),
                    'unit': safe_value(row['หน่วยนับ']),
                    'sale_price': safe_value(row['ราคาขายสำหรับสาขา'], 0.0),
                    'reorder_point': safe_value(row['จุดสั่งซื้อ'], 0),
                    'max_stock': safe_value(row['จุดสูงสุด'], 0),
                    'category': safe_value(row['ประเภทสินค้า']),
                }
            )
        return redirect('material_list')
    return render(request, 'inventory/import_excel.html')


# รายการสต็อก
@login_required
def material_list(request):
    materials = MaterialStock.objects.all()
    return render(request, 'inventory/material_list.html', {'materials': materials})


# ค้นหาสินค้าแบบ real-time
@login_required
def search_materials(request):
    query = request.GET.get('q', '')
    results = MaterialStock.objects.filter(name__icontains=query)[:10]  # จำกัด 10 รายการ
    data = [
        {
            'id': m.id,
            'code': m.code,
            'name': m.name,
            'cost': m.cost
        }
        for m in results
    ]
    return JsonResponse(data, safe=False)


# dashboard
@login_required
def dashboard(request):
    materials = MaterialStock.objects.all()
    orders = MaterialOrder.objects.all()
    return render(request, 'inventory/dashboard.html', {'stocks': materials, 'orders': orders})


@login_required
def material_create(request):
    if request.method == 'POST':
        MaterialStock.objects.create(
            code=request.POST['code'],
            name=request.POST['name'],
            barcode=request.POST.get('barcode', ''),
            cost=request.POST.get('cost', 0),
            avg_cost=request.POST.get('avg_cost', 0),
            unit=request.POST.get('unit', ''),
            sale_price=request.POST.get('sale_price', 0),
            reorder_point=request.POST.get('reorder_point', 0),
            max_stock=request.POST.get('max_stock', 0),
            category=request.POST.get('category', '')
        )
        return redirect('material_list')
    return render(request, 'inventory/material_form.html', {'title': 'เพิ่มวัตถุดิบ'})

@login_required
def material_edit(request, pk):
    material = get_object_or_404(MaterialStock, pk=pk)
    if request.method == 'POST':
        for field in ['code', 'name', 'barcode', 'cost', 'avg_cost', 'unit', 'sale_price', 'reorder_point', 'max_stock', 'category']:
            setattr(material, field, request.POST.get(field, getattr(material, field)))
        material.save()
        return redirect('material_list')
    return render(request, 'inventory/material_form.html', {'title': 'แก้ไขวัตถุดิบ', 'material': material})

@login_required
def material_delete(request, pk):
    material = get_object_or_404(MaterialStock, pk=pk)
    if request.method == 'POST':
        material.delete()
        return redirect('material_list')
    return render(request, 'inventory/material_confirm_delete.html', {'material': material})



@login_required
def order_edit(request, pk):
    """Enhanced order edit with full functionality"""
    order = get_object_or_404(MaterialOrder, pk=pk)
    
    # Check permissions - only order owner or staff can edit
    if not (request.user == order.ordered_by or request.user.is_staff):
        messages.error(request, 'คุณไม่มีสิทธิ์แก้ไขออร์เดอร์นี้')
        return redirect('home')
    
    if request.method == 'POST':
        try:
            # Get form data
            note = request.POST.get('note', '').strip()
            delivery_round_id = request.POST.get('delivery_round')
            approval_status = request.POST.get('approval_status')
            
            # Update basic order info
            order.note = note
            
            # Update delivery round
            if delivery_round_id:
                try:
                    delivery_round = DeliveryRound.objects.get(pk=delivery_round_id)
                    order.delivery_round = delivery_round
                except DeliveryRound.DoesNotExist:
                    pass
            else:
                order.delivery_round = None
            
            # Update approval status (only for staff)
            if request.user.is_staff and approval_status:
                old_status = order.approval_status
                order.approval_status = approval_status
                
                # Set approval info based on status change
                if approval_status == 'approved' and old_status != 'approved':
                    order.approved_by = request.user
                    order.approved_at = timezone.now()
                elif approval_status == 'rejected' and old_status != 'rejected':
                    order.approved_by = request.user
                    order.approved_at = timezone.now()
                elif approval_status == 'pending':
                    order.approved_by = None
                    order.approved_at = None
            
            # Handle removed items
            removed_items = request.POST.getlist('removed_items')
            for item_id in removed_items:
                try:
                    item = MaterialOrderItem.objects.get(id=item_id, order=order)
                    item.delete()
                except MaterialOrderItem.DoesNotExist:
                    pass
            
            # Update existing items
            total_cost = 0
            for item in order.items.all():
                qty_key = f'qty_{item.id}'
                cost_key = f'cost_{item.id}'
                note_key = f'note_{item.id}'
                
                if qty_key in request.POST and cost_key in request.POST:
                    try:
                        quantity = int(request.POST[qty_key])
                        unit_cost = float(request.POST[cost_key])
                        item_note = request.POST.get(note_key, '').strip()
                        
                        if quantity > 0 and unit_cost >= 0:
                            item.quantity = quantity
                            item.unit_cost = unit_cost
                            item.total_cost = quantity * unit_cost
                            
                            # Add note field to MaterialOrderItem if it doesn't exist
                            # You might need to add this field to your model
                            if hasattr(item, 'note'):
                                item.note = item_note
                            
                            item.save()
                            total_cost += item.total_cost
                        else:
                            messages.warning(request, f'ข้อมูลไม่ถูกต้องสำหรับรายการ {item.material.name}')
                    except (ValueError, TypeError):
                        messages.warning(request, f'ข้อมูลไม่ถูกต้องสำหรับรายการ {item.material.name}')
            
            # Add new items
            new_item_counter = 1
            while f'new_material_{new_item_counter}' in request.POST:
                try:
                    material_id = request.POST[f'new_material_{new_item_counter}']
                    quantity = int(request.POST[f'new_qty_{new_item_counter}'])
                    unit_cost = float(request.POST[f'new_cost_{new_item_counter}'])
                    item_note = request.POST.get(f'new_note_{new_item_counter}', '').strip()
                    
                    if quantity > 0 and unit_cost >= 0:
                        material = MaterialStock.objects.get(pk=material_id)
                        item_total = quantity * unit_cost
                        
                        new_item = MaterialOrderItem.objects.create(
                            order=order,
                            material=material,
                            quantity=quantity,
                            unit_cost=unit_cost,
                            total_cost=item_total
                        )
                        
                        # Add note if the field exists
                        if hasattr(new_item, 'note'):
                            new_item.note = item_note
                            new_item.save()
                        
                        total_cost += item_total
                    
                except (ValueError, TypeError, MaterialStock.DoesNotExist):
                    messages.warning(request, f'ไม่สามารถเพิ่มรายการใหม่ลำดับที่ {new_item_counter} ได้')
                
                new_item_counter += 1
            
            # Update order total
            order.total_cost = total_cost
            order.save()
            
            messages.success(request, f'แก้ไขออร์เดอร์ MOD-{order.id:05d} เรียบร้อยแล้ว')
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    # Get delivery rounds for the form
    delivery_rounds = DeliveryRound.objects.filter(is_active=True).order_by('name')
    
    context = {
        'order': order,
        'delivery_rounds': delivery_rounds,
    }
    
    return render(request, 'inventory/order_edit.html', context)

@login_required
def order_delete(request, pk):
    order = get_object_or_404(MaterialOrder, pk=pk)
    if request.method == 'POST':
        order.delete()
        return redirect('home')
    return render(request, 'inventory/order_confirm_delete.html', {'order': order})




# views.py - อัปเดต order_material view



# อัปเดต order_material view
@login_required
def order_material(request):
    if request.method == 'POST':
        note = request.POST.get('note', '')
        delivery_round_id = request.POST.get('delivery_round')
        material_ids = request.POST.getlist('material_id')
        qtys = request.POST.getlist('qty')
        costs = request.POST.getlist('cost')

        print(f"Material IDs: {material_ids}")
        print(f"Quantities: {qtys}")
        print(f"Costs: {costs}")
        print(f"Delivery Round ID: {delivery_round_id}")

        # ตรวจสอบว่ามีข้อมูลหรือไม่
        if not material_ids:
            messages.error(request, 'กรุณาเลือกวัตถุดิบอย่างน้อย 1 รายการ')
            return redirect('order_material')

        try:
            # ดึงรอบจัดส่ง
            delivery_round = None
            if delivery_round_id:
                delivery_round = DeliveryRound.objects.get(pk=delivery_round_id)

            # สร้าง order
            order = MaterialOrder.objects.create(
                ordered_by=request.user,
                note=note,
                delivery_round=delivery_round,
                total_cost=0,
                approval_status='approved'  # ตั้งค่าเริ่มต้นเป็นรออนุมัติ
            )

            print('Order created successfully')

            total_cost = 0
            items_created = 0

            for mid, qty, cost in zip(material_ids, qtys, costs):
                try:
                    if not mid or not qty or not cost:
                        continue  # ข้ามถ้าข้อมูลว่าง

                    mid = int(mid)
                    quantity = int(qty)
                    cost_value = float(cost)

                    if quantity <= 0:
                        continue

                    material = MaterialStock.objects.get(pk=mid)
                    item_total = quantity * cost_value

                    MaterialOrderItem.objects.create(
                        order=order,
                        material=material,
                        quantity=quantity,
                        unit_cost=cost_value,
                        total_cost=item_total,
                    )
                    total_cost += item_total
                    items_created += 1

                except (ValueError, MaterialStock.DoesNotExist):
                    continue  # ข้ามรายการที่ผิดพลาด

            if items_created == 0:
                order.delete()
                messages.error(request, 'ไม่สามารถสร้างรายการสั่งซื้อได้')
                return redirect('order_material')

            order.total_cost = total_cost
            order.save()
            
            messages.success(request, f'สร้างรายการสั่งซื้อ MOD-{order.id:05d} เรียบร้อยแล้ว (สถานะ: อนุมัติแล้ว)')
            return redirect('home')

        except DeliveryRound.DoesNotExist:
            messages.error(request, 'ไม่พบรอบจัดส่งที่เลือก')
            return redirect('order_material')
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
            return redirect('order_material')

    # ดึงข้อมูลรอบจัดส่งที่เปิดใช้งาน
    delivery_rounds = DeliveryRound.objects.filter(is_active=True).order_by('name')
    
    today = timezone.now()
    next_id = MaterialOrder.objects.count() + 1
    return render(request, 'inventory/order_form.html', {
        'today': today,
        'order_id': f"{next_id:05d}",
        'delivery_rounds': delivery_rounds
    })





# Staff check function
def is_staff_user(user):
    """Check if user is staff"""
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(is_staff_user, login_url='home')
def material_summary(request):
    """
    Summary page for MaterialOrderItems grouped by material
    Only accessible by staff users
    """
    
    # Get filter parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    selected_round_ids = request.GET.getlist('delivery_rounds')
    
    # Set default dates (last 7 days)
    if not date_from:
        date_from = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = date.today().strftime('%Y-%m-%d')
    
    # Get all delivery rounds
    delivery_rounds = DeliveryRound.objects.filter(is_active=True).order_by('name')
    
    # If no delivery rounds selected, select all
    if not selected_round_ids:
        selected_round_ids = [str(round.id) for round in delivery_rounds]
    
    # Convert to integers
    selected_round_ids = [int(id) for id in selected_round_ids if id.isdigit()]
    
    # Build active filters list
    active_filters = []
    summary_data = []
    total_materials = 0
    total_quantity = 0
    total_cost = 0
    total_users = 0
    
    try:
        # Parse dates
        from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        active_filters.append(f'ช่วงวันที่: {from_date.strftime("%d/%m/%Y")} - {to_date.strftime("%d/%m/%Y")}')
        
        # Add delivery round filter info
        if len(selected_round_ids) == delivery_rounds.count():
            active_filters.append('รอบจัดส่ง: ทั้งหมด')
        else:
            selected_rounds = delivery_rounds.filter(id__in=selected_round_ids)
            round_names = [round.name for round in selected_rounds]
            active_filters.append(f'รอบจัดส่ง: {", ".join(round_names)}')
        
        # Base queryset for MaterialOrderItems
        items = MaterialOrderItem.objects.select_related(
            'material', 'order__ordered_by', 'order__delivery_round'
        ).filter(
            order__created_at__date__gte=from_date,
            order__created_at__date__lte=to_date,
            order__approval_status='approved'  # Only approved orders
        )
        
        # Filter by delivery rounds
        if selected_round_ids:
            items = items.filter(order__delivery_round_id__in=selected_round_ids)
        
        # Group data by material
        material_data = defaultdict(lambda: {
            'total_quantity': 0,
            'total_cost': 0,
            'users': defaultdict(lambda: {'quantity': 0, 'cost': 0}),
            'material_info': None
        })
        
        # Process each item
        for item in items:
            material_id = item.material.id
            username = item.order.ordered_by.username
            
            # Store material info
            if not material_data[material_id]['material_info']:
                material_data[material_id]['material_info'] = {
                    'code': item.material.code,
                    'name': item.material.name,
                    'unit': item.material.unit,
                }
            
            # Aggregate quantities and costs
            material_data[material_id]['total_quantity'] += item.quantity
            material_data[material_id]['total_cost'] += item.total_cost
            material_data[material_id]['users'][username]['quantity'] += item.quantity
            material_data[material_id]['users'][username]['cost'] += item.total_cost
        
        # Convert to list format for template
        for material_id, data in material_data.items():
            user_details = []
            for username, user_data in data['users'].items():
                user_details.append({
                    'username': username,
                    'quantity': user_data['quantity'],
                    'cost': user_data['cost']
                })
            
            # Sort users by quantity (descending)
            user_details.sort(key=lambda x: x['quantity'], reverse=True)
            
            summary_data.append({
                'material_code': data['material_info']['code'],
                'material_name': data['material_info']['name'],
                'unit': data['material_info']['unit'],
                'total_quantity': data['total_quantity'],
                'total_cost': data['total_cost'],
                'user_count': len(data['users']),
                'user_details': user_details
            })
        
        # Sort by total quantity (descending)
        summary_data.sort(key=lambda x: x['total_quantity'], reverse=True)
        
        # Calculate totals
        total_materials = len(summary_data)
        total_quantity = sum(item['total_quantity'] for item in summary_data)
        total_cost = sum(item['total_cost'] for item in summary_data)
        
        # Count unique users
        all_users = set()
        for data in material_data.values():
            all_users.update(data['users'].keys())
        total_users = len(all_users)
        
    except ValueError as e:
        messages.error(request, 'รูปแบบวันที่ไม่ถูกต้อง')
    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    context = {
        'summary_data': summary_data,
        'delivery_rounds': delivery_rounds,
        'selected_rounds': selected_round_ids,
        'active_filters': active_filters,
        'default_date_from': date_from,
        'default_date_to': date_to,
        'total_materials': total_materials,
        'total_quantity': total_quantity,
        'total_cost': total_cost,
        'total_users': total_users,
    }
    
    return render(request, 'inventory/material_summary.html', context)







# ============================================================================
# DELIVERY ROUND CRUD VIEWS (Superuser only)
# ============================================================================

@login_required
@user_passes_test(is_superuser, login_url='home')
def delivery_round_list(request):
    """List all delivery rounds - Superuser only"""
    
    delivery_rounds = DeliveryRound.objects.all().order_by('-created_at')
    
    # Calculate statistics
    total_rounds = delivery_rounds.count()
    active_rounds = delivery_rounds.filter(is_active=True).count()
    inactive_rounds = total_rounds - active_rounds
    
    # Count total orders using delivery rounds
    total_orders = MaterialOrder.objects.filter(delivery_round__isnull=False).count()
    
    context = {
        'delivery_rounds': delivery_rounds,
        'total_rounds': total_rounds,
        'active_rounds': active_rounds,
        'inactive_rounds': inactive_rounds,
        'total_orders': total_orders,
    }
    
    return render(request, 'inventory/delivery_round_list.html', context)


@login_required
@user_passes_test(is_superuser, login_url='home')
def delivery_round_create(request):
    """Create new delivery round - Superuser only"""
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation
        if not name:
            messages.error(request, 'กรุณาระบุชื่อรอบจัดส่ง')
            return render(request, 'inventory/delivery_round_form.html', {
                'title': 'เพิ่มรอบจัดส่งใหม่'
            })
        
        if len(name) < 3:
            messages.error(request, 'ชื่อรอบจัดส่งต้องมีอย่างน้อย 3 ตัวอักษร')
            return render(request, 'inventory/delivery_round_form.html', {
                'title': 'เพิ่มรอบจัดส่งใหม่'
            })
        
        if len(name) > 100:
            messages.error(request, 'ชื่อรอบจัดส่งต้องไม่เกิน 100 ตัวอักษร')
            return render(request, 'inventory/delivery_round_form.html', {
                'title': 'เพิ่มรอบจัดส่งใหม่'
            })
        
        # Check for duplicate name
        if DeliveryRound.objects.filter(name=name).exists():
            messages.error(request, f'รอบจัดส่งชื่อ "{name}" มีอยู่แล้ว กรุณาใช้ชื่ออื่น')
            return render(request, 'inventory/delivery_round_form.html', {
                'title': 'เพิ่มรอบจัดส่งใหม่'
            })
        
        try:
            # Create delivery round
            delivery_round = DeliveryRound.objects.create(
                name=name,
                description=description,
                is_active=is_active
            )
            
            messages.success(request, f'สร้างรอบจัดส่ง "{delivery_round.name}" เรียบร้อยแล้ว')
            return redirect('delivery_round_list')
            
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    return render(request, 'inventory/delivery_round_form.html', {
        'title': 'เพิ่มรอบจัดส่งใหม่'
    })


@login_required
@user_passes_test(is_superuser, login_url='home')
def delivery_round_edit(request, pk):
    """Edit delivery round - Superuser only"""
    
    delivery_round = get_object_or_404(DeliveryRound, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation
        if not name:
            messages.error(request, 'กรุณาระบุชื่อรอบจัดส่ง')
            return render(request, 'inventory/delivery_round_form.html', {
                'title': 'แก้ไขรอบจัดส่ง',
                'delivery_round': delivery_round
            })
        
        if len(name) < 3:
            messages.error(request, 'ชื่อรอบจัดส่งต้องมีอย่างน้อย 3 ตัวอักษร')
            return render(request, 'inventory/delivery_round_form.html', {
                'title': 'แก้ไขรอบจัดส่ง',
                'delivery_round': delivery_round
            })
        
        if len(name) > 100:
            messages.error(request, 'ชื่อรอบจัดส่งต้องไม่เกิน 100 ตัวอักษร')
            return render(request, 'inventory/delivery_round_form.html', {
                'title': 'แก้ไขรอบจัดส่ง',
                'delivery_round': delivery_round
            })
        
        # Check for duplicate name (excluding current record)
        if DeliveryRound.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, f'รอบจัดส่งชื่อ "{name}" มีอยู่แล้ว กรุณาใช้ชื่ออื่น')
            return render(request, 'inventory/delivery_round_form.html', {
                'title': 'แก้ไขรอบจัดส่ง',
                'delivery_round': delivery_round
            })
        
        try:
            # Update delivery round
            delivery_round.name = name
            delivery_round.description = description
            delivery_round.is_active = is_active
            delivery_round.save()
            
            messages.success(request, f'แก้ไขรอบจัดส่ง "{delivery_round.name}" เรียบร้อยแล้ว')
            return redirect('delivery_round_list')
            
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    return render(request, 'inventory/delivery_round_form.html', {
        'title': 'แก้ไขรอบจัดส่ง',
        'delivery_round': delivery_round
    })


@login_required
@user_passes_test(is_superuser, login_url='home')
def delivery_round_delete(request, pk):
    """Delete delivery round - Superuser only"""
    
    delivery_round = get_object_or_404(DeliveryRound, pk=pk)
    
    # Check if delivery round is being used by any orders
    related_orders = MaterialOrder.objects.filter(delivery_round=delivery_round)
    order_count = related_orders.count()
    
    if request.method == 'POST':
        if order_count > 0:
            messages.error(request, f'ไม่สามารถลบรอบจัดส่ง "{delivery_round.name}" ได้ เนื่องจากมี {order_count} ออร์เดอร์ที่อ้างอิงถึงรอบนี้')
            return redirect('delivery_round_delete', pk=pk)
        
        try:
            delivery_round_name = delivery_round.name
            delivery_round.delete()
            messages.success(request, f'ลบรอบจัดส่ง "{delivery_round_name}" เรียบร้อยแล้ว')
            return redirect('delivery_round_list')
            
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    return render(request, 'inventory/delivery_round_delete.html', {
        'delivery_round': delivery_round,
        'order_count': order_count,
        'related_orders': related_orders
    })


@login_required
@user_passes_test(is_superuser, login_url='home')
def delivery_round_toggle(request, pk):
    """Toggle active status of delivery round - Superuser only"""
    
    delivery_round = get_object_or_404(DeliveryRound, pk=pk)
    
    if request.method == 'POST':
        try:
            # Toggle active status
            delivery_round.is_active = not delivery_round.is_active
            delivery_round.save()
            
            status = 'เปิดใช้งาน' if delivery_round.is_active else 'ปิดใช้งาน'
            messages.success(request, f'{status}รอบจัดส่ง "{delivery_round.name}" เรียบร้อยแล้ว')
            
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
    
    return redirect('delivery_round_list')