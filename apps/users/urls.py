"""dailyfresh URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin

from apps.users import views

urlpatterns = [
    # 视图函数
    # url(r'^register$', views.register, name='register'),
    # url(r'^do_register$', views.do_register, name='do_register'),

    # 类视图
    url(r'^register$', views.RegisterView.as_view(), name='register'),

    url(r'^active/(.+)$', views.ActiveView.as_view(), name='active'),

    url(r'^login$', views.LoginView.as_view(), name='login'),
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),

    url(r'^address$', views.UserAddressView.as_view(), name='address'),
    url(r'^orders/(\d+)$', views.UserOrderView.as_view(), name='orders'),
    url(r'^$', views.UserInfoView.as_view(), name='info'),
]
