from django.contrib import admin

from apps.users.models import TestModel, Address

admin.site.register(TestModel)
admin.site.register(Address)
