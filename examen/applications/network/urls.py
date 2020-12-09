from django.urls import path
# Importamos las vistas 
from . import views

app_name = "network_app"

urlpatterns = [
     # URL página principal
    path(
         '', 
         views.NetworkMainPageView.as_view(),
         name='main_network',
    ), 
    # URL buscar topología
    path(
         'searchTopology/', 
         views.RegisterRouterView.as_view(),
         name='topology_network',
    ), 
    # URLS para listar datos
    path(
         'listRouters/', 
         views.RouterListView.as_view(),
         name='routers_network',
    ), 
    path(
         'listInterfaces/', 
         views.InterfaceListView.as_view(),
         name='interfaces_network',
    ),
    path(
         'listUsers/', 
         views.SSHUserListView.as_view(),
         name='users_network',
    ),
    # URLS para actualizar datos en la Base de Datos
    path(
        'updateRouter/<int:pk>/',
        views.RouterUpdateView.as_view(),
        name='update_router'
    ),
    path(
        'updateInterface/<int:pk>/',
        views.InterfaceUpdateView.as_view(),
        name='update_interface'
    ),
    path(
        'updateUser/<int:pk>/',
        views.SSHUserUpdateView.as_view(),
        name='update_user'
    ),
    # URLS para añadir nuevos registros en la Base de Datos
    path(
        'addUser/',
        views.SSHUserCreateView.as_view(),
        name='add_user'
    ),
    # URLS para eliminar registros en la Base de Datos
    path(
        'deleteUser/<int:pk>/',
        views.SSHUserDeleteView.as_view(),
        name='delete_user'
    ),
]