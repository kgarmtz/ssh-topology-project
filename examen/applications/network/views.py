from django.shortcuts import render, get_object_or_404, HttpResponseRedirect
from django.urls import reverse_lazy

# Importamos las funciones propias
from .utils import searhTopology, drawTopologyDiagram, registerSSHUser
# Importamos el formulario que creamos en el archivo forms.py
from .forms import RouterForm
from django.views.generic import (
    TemplateView, 
    ListView,
    UpdateView,
    CreateView,
    DeleteView
)
from django.views.generic.edit import FormView
# ---> Importamos los modelos necesarios <---
# Importamos el modelo Router y Interface que se encuentra en esta misma aplicación
from .models import Router, Interface, SSHUser

class NetworkMainPageView(TemplateView):
    template_name = "network/home.html"

class RegisterRouterView(FormView):
    """ RegisterRouter """
    template_name = 'network/search.html'
    form_class = RouterForm
    # Lo redirigimos a la página principal
    success_url = reverse_lazy('network_app:main_network')
    # Una vez que los datos ingresados en los inputs del formulario hayan sido validados
    def form_valid(self, form):
        print(' ======== FORM VALID ========')
        # Eliminamos los elementos dentro la base de datos
        Router.objects.all().delete()
        Interface.objects.all().delete()
        SSHUser.objects.all().delete()
        # Registramos todos los routers con sus interfaces
        routers_db    = list()
        interfaces_db = list()
        routers = searhTopology()
        # Creating the topology diagram
        drawTopologyDiagram(routers)
        # Register all the router information in the Database
        for router in routers.keys():
            # Retreiving all the interfaces 
            interfaces = routers[router].get('router_interfaces')
            # Router model instance
            router_db = Router(
                ip        = routers[router].get('router_id'),
                host_name = routers[router].get('router_hostname'),
                brand     = 'Cisco',
                os        = 'Cisco IOS Software - 7200',
                interfaces_on = len( interfaces.keys() )
            )
            routers_db.append(router_db)
            # Interface model instance
            for interface in interfaces.keys():
                interface_db = Interface(
                    name   = interface,
                    ip     = interfaces[interface].get('ip'),
                    mask   = interfaces[interface].get('mask'),
                    router = routers[router].get('router_hostname')+' : '+routers[router].get('router_id') 
                )
                interfaces_db.append(interface_db)
            
        # Registramos todos los datos obtenidos en la tabla Router dentro la BD
        Router.objects.bulk_create(
            routers_db
        )
        # Registramos todos los datos obtenidos en la tabla Interface dentro la BD
        Interface.objects.bulk_create(
            interfaces_db
        )
        print('Todos los registros han sido almacenados correctamente dentro de la Base de Datos')
        return super(RegisterRouterView,self).form_valid(form)

# Vistas para mostrar registros de la Base de Datos

class RouterListView(ListView):
    template_name = "network/list_routers.html"
    context_object_name = 'routers'
    # Al no tener queryset necesitamos especificar el modelo 
    model = Router
    # Ordenamos los datos por id
    ordering = 'id'

class InterfaceListView(ListView):
    template_name = "network/list_interfaces.html"
    context_object_name = 'interfaces'
    # Al no tener queryset necesitamos especificar el modelo 
    model = Interface
    # Tamaño de bloque de paginación
    paginate_by = 4
    # Ordenamos los datos por id
    ordering = 'id'


class SSHUserListView(ListView):
    template_name = "network/list_users.html"
    context_object_name = 'sshusers'
    model = SSHUser
    # Ordenamos los datos por id
    ordering = 'id'

# Actualización de los Datos de los Routers e Interfaces, necesitamos mandar el índice
# del registro en la Base de Datos que seamos actualizar

class RouterUpdateView(UpdateView):
    template_name = "network/update_router.html"
    # Asignamos el modelo para esta vista
    model = Router
    # Campos que deseamos actualizar, para acceder a estos campos lo haremos
    # con la palabra reservada 'form' en el HTML
    fields = ('__all__')
    # URL a la cual será redireccionado
    success_url = reverse_lazy('network_app:routers_network')


class InterfaceUpdateView(UpdateView):
    template_name = "network/update_interface.html"
    # Asignamos el modelo para esta vista
    model = Interface
    # Campos que deseamos actualizar, para acceder a estos campos lo haremos
    # con la palabra reservada 'form' en el HTML
    fields = ('__all__')
    # Especificamos la URL a la cual será redireccionado 
    success_url = reverse_lazy('network_app:interfaces_network')


class SSHUserUpdateView(UpdateView):
    template_name = "network/update_user.html"
    # Asignamos el modelo para esta vista
    model = SSHUser
    # Campos mostrador en el HTML
    fields = ('__all__')
    # Especificamos la URL a la cual será redireccionado 
    success_url = reverse_lazy('network_app:users_network')

# Vistas para añadir nuevos registros en la Base de Datos

class SSHUserCreateView(CreateView):
    template_name = "network/add_user.html"
    # Asignamos el modelo para esta vista
    model = SSHUser
    # Campos a llenar para crear el usuario ssh
    fields = ('__all__')
    # Especificamos la URL a la cual será redireccionado 
    success_url = reverse_lazy('network_app:users_network')
    # Una vez que los datos ingresados en los inputs del formulario hayan sido validados
    def form_valid(self, form):
        print(' ======== FORM VALID ========')
        # Registramos al usuario en los usuarios del router 
        sshuser   = form.save( commit=False )
        username  = sshuser.username
        password  = sshuser.password
        router_id = sshuser.router.ip
        # Creamos el usuario ssh 
        print(f'Setting up user \'{username}\' in router {router_id}')
        registerSSHUser(username, password, router_id)
        print(f'User {username} successfully configured in router {sshuser.router.host_name}')
        # Registramos al usuario en la base de datos
        sshuser.save()
        return super(SSHUserCreateView,self).form_valid(form)

# Vistas para eliminar registros en la Base de Datos

class SSHUserDeleteView(DeleteView):
    template_name = "network/delete_user.html"
    model = SSHUser
    success_url = reverse_lazy('network_app:users_network')

    # Recuperamos el objeto que al que se hace referencia en la URL
    def get_object(self):
        #Obtenemos el 'id' que se manda en la URL a través del diccionario kwargs
        id_ = self.kwargs.get('pk')
        return get_object_or_404( SSHUser, id = id_ )

    def delete(self,request,*args,**kwargs):
        # Obtenemos el objeto que se especifica en la url
        self.object = self.get_object()
        # Realizamos algún proceso antes de eliminar el registro
        username  = self.object.username
        password  = self.object.password
        router_id = self.object.router.ip
        # Eliminamos el usuario ssh 
        print(f'Eliminating user \'{username}\' in router {router_id}')
        registerSSHUser(username, password, router_id, 'no')
        print(f'User {username} successfully eliminated in router {self.object.router.host_name}')
        # Eliminamos el objeto del modelo de la BD
        self.object.delete()
        return HttpResponseRedirect(self.success_url)
    

    
