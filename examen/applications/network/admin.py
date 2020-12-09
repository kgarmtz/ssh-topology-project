from django.contrib import admin
from .models import Router, Interface, SSHUser

# Register your models here.
admin.site.register(Router)
admin.site.register(Interface)
admin.site.register(SSHUser)