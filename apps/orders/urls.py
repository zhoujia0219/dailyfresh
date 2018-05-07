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

from apps.orders import views

urlpatterns = [
    url(r'^place$', views.PlaceOrderView.as_view(), name='place'),
    url(r'^commit$', views.CommitOrderView.as_view(), name='commit'),
    # 支付: /orders/pay
    url(r'^pay$', views.OrderPayView.as_view(), name='pay'),
    # 查询支付结果: /orders/check
    url(r'^check$', views.CheckPayView.as_view(), name='check'),
]
# 2016091500513483