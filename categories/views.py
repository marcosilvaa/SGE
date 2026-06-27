from rest_framework import generics
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from . import models, forms, serializers
from app.demo import DemoAPIViewMixin, DemoDeleteSimulationMixin, DemoWriteSimulationMixin


class CategoryListView(ListView):
    model = models.Category
    template_name = 'category_list.html'
    context_object_name = 'categories'
    paginate_by = 5
    permission_required = 'categories.view_category'

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.GET.get('name')

        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class CategoryCreateView(DemoWriteSimulationMixin, CreateView):
    model = models.Category
    template_name = 'category_create.html'
    form_class = forms.CategoryForm
    success_url = reverse_lazy('category_list')
    permission_required = 'categories.add_category'


class CategoryDetailView(DetailView):
    model = models.Category
    template_name = 'category_detail.html'
    permission_required = 'categories.view_category'


class CategoryUpdateView(DemoWriteSimulationMixin, UpdateView):
    model = models.Category
    template_name = 'category_update.html'
    form_class = forms.CategoryForm
    success_url = reverse_lazy('category_list')
    permission_required = 'categories.change_category'


class CategoryDeleteView(DemoDeleteSimulationMixin, DeleteView):
    model = models.Category
    template_name = 'category_delete.html'
    success_url = reverse_lazy('category_list')
    permission_required = 'categories.delete_category'


class CategoryCreateListAPIView(DemoAPIViewMixin, generics.ListCreateAPIView):
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer


class CategoryRetrieveUpdateDestroyAPIView(DemoAPIViewMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer
