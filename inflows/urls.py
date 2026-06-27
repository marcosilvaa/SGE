from django.urls import path
from . import views


urlpatterns = [
    path('inflows/list/', views.InflowListView.as_view(), name='inflow_list'),
    path('inflows/create/', views.InflowCreateView.as_view(), name='inflow_create'),
    path('inflows/<int:pk>/detail/', views.InflowDetailView.as_view(), name='inflow_detail'),
    path('inflows/<int:pk>/update/', views.InflowUpdateView.as_view(), name='inflow_update'),
    path('inflows/<int:pk>/delete/', views.InflowDeleteView.as_view(), name='inflow_delete'),
    path('api/v1/inflows/', views.InflowCreateListAPIView.as_view(), name='inflow-create-list-api-view'),
    path('api/v1/inflows/<int:pk>/', views.InflowRetrieveAPIView.as_view(), name='inflow-detail-api-view')
]
