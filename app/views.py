import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
# from ai.models import AIResult  <-- Mantenha comentado se não for usar agora
from . import metrics


def health(request):
    return JsonResponse({"status": "ok"})


def landing(request):
    if request.user.is_authenticated:
        return redirect('home')

    context = {
        'landing_metrics': metrics.get_dashboard_metrics(),
    }
    return render(request, 'landing.html', context)


@login_required(login_url='login')
def home(request):
    product_metrics = metrics.get_product_metrics()
    # print("DEBUG METRICS:", product_metrics)
    sales_metrics = metrics.get_sales_metrics()
    graphic_product_category_metric = metrics.get_graphic_product_category_metric()
    graphic_product_brand_metric = metrics.get_graphic_product_brand_metric()
    daily_sales_data = metrics.get_daily_sales_data()
    daily_sales_quantity_data = metrics.get_daily_sales_quantity_data()
    dashboard_metrics = metrics.get_dashboard_metrics()
    stock_status_data = metrics.get_stock_status_data()
    category_inventory_value_data = metrics.get_category_inventory_value_data()
    low_stock_products = metrics.get_low_stock_products()
    recent_movements = metrics.get_recent_movements()

    # CORREÇÃO AQUI:
    # Como você comentou a busca no banco, precisamos definir a variavel como vazia manualmente
    # ai_result = AIResult.objects.first()
    # ai_result = ai_result.result if ai_result else ''
    ai_result = ''

    context = {
        'product_metrics': product_metrics,
        'sales_metrics': sales_metrics,
        'product_count_by_category': json.dumps(graphic_product_category_metric),
        'product_count_by_brand': json.dumps(graphic_product_brand_metric),
        'daily_sales_data': json.dumps(daily_sales_data),
        'daily_sales_quantity_data': json.dumps(daily_sales_quantity_data),
        'dashboard_metrics': dashboard_metrics,
        'stock_status_data': json.dumps(stock_status_data),
        'category_inventory_value_data': json.dumps(category_inventory_value_data),
        'low_stock_products': low_stock_products,
        'recent_movements': recent_movements,
        'ai_result': ai_result,
    }

    return render(request, 'home.html', context)
