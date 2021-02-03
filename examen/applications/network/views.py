import os
# Python Local Moducles
from datetime import datetime
from django.core.files import File

# Django Modules
from django.shortcuts import render, get_object_or_404, HttpResponseRedirect
from django.urls import reverse_lazy, reverse

# Importamos las funciones propias
from .utils import (
    searchTopology, 
    drawTopologyDiagram, 
    registerSSHUser, 
    make_ssh_conexion, 
    updateHostNames,
    createPlot,
    createPlots
)

from .snmp import snmp_query
# Importamos el formulario que creamos en el archivo forms.py
from .forms import RouterForm
from django.views.generic import (
    TemplateView, 
    ListView,
    UpdateView,
    CreateView,
    DeleteView,
    View
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
        system_name     = '1.3.6.1.2.1.1.5.0' # SysName     OID
        system_location = '1.3.6.1.2.1.1.6.0' # SysLocation OID
        system_contact  = '1.3.6.1.2.1.1.4.0' # SysContact  OID
        system_descr    = '1.3.6.1.2.1.1.1.0' # SysDescr    OID

        print(' ======== FORM VALID ========')
        # Eliminamos los elementos dentro la base de datos
        Router.objects.all().delete()
        Interface.objects.all().delete()
        SSHUser.objects.all().delete()
        # Registramos todos los routers con sus interfaces
        routers_db    = list()
        interfaces_db = list()
        routers = searchTopology()
        # Creating the topology diagram
        drawTopologyDiagram(routers)
        now = datetime.now()
        # Register all the router information in the Database
        for router in routers.keys():
            oid_count = 1
            # Retreiving all the interfaces 
            interfaces = routers[router].get('router_interfaces')
            # Router model instance
            router_id = routers[router].get('router_id')
            router_db = Router(
                ip        = router_id,
                host_name = routers[router].get('router_hostname'),
                brand     = 'Cisco',
                os        = 'Software Version 12.4(25g)',
                interfaces_on = len( interfaces.keys() ),
                sysName     = snmp_query( router_id, system_name ),
                sysLocation = snmp_query( router_id, system_location ),
                sysContact  = snmp_query( router_id, system_contact ),
                sysDescr    = snmp_query( router_id, system_descr )
            )
            routers_db.append(router_db)
            # Defining all the fields for the SNMP Interface
            fa_in_oct       = '1.3.6.1.2.1.2.2.1.10.'
            fa_in_uPackets  = '1.3.6.1.2.1.2.2.1.11.'
            fa_out_oct      = '1.3.6.1.2.1.2.2.1.16.'
            fa_out_uPackets = '1.3.6.1.2.1.2.2.1.17.'

            # Interface model instance
            for interface in interfaces.keys():
                interface_db = Interface(
                    name   = routers[router].get('router_hostname')+'-'+interface,
                    ip     = interfaces[interface].get('ip'),
                    mask   = interfaces[interface].get('mask'),
                    router = routers[router].get('router_hostname')+':'+routers[router].get('router_id'),
                    oid    = str(oid_count),
                    in_oct       = snmp_query( router_id, fa_in_oct+str(oid_count) ) + ',', 
                    in_uPackets  = snmp_query( router_id, fa_in_uPackets+str(oid_count) ) + ',',
                    out_oct      = snmp_query( router_id, fa_out_oct+str(oid_count) ) + ',',
                    out_uPackets = snmp_query( router_id, fa_out_uPackets+str(oid_count) ) + ',',
                    times        = now.strftime('%H:%M:%S') + ','
                )
                interfaces_db.append(interface_db)
                oid_count += 1

            
        # Registramos todos los datos obtenidos en la tabla Router dentro la BD
        Router.objects.bulk_create(
            routers_db
        )
        # Registramos todos los datos obtenidos en la tabla Interface dentro la BD
        Interface.objects.bulk_create(
            interfaces_db
        )
        # Creating the plots for every single interface
        valid = createPlots()
        if valid == 1:
            print('Everything went well')
        else:
            print('Internal Server Error :(')

        print('Todos los registros han sido almacenados correctamente dentro de la Base de Datos')
        return super(RegisterRouterView,self).form_valid(form)

# Vistas para mostrar registros de la Base de Datos

class RouterListView(ListView):
    template_name = "network/list_routers.html"
    context_object_name = 'routers'
    # Al no tener queryset necesitamos especificar el modelo de la BD
    model = Router
    # Ordenamos los datos por id
    ordering = 'id'


class SnmpListView(ListView):
    template_name = 'network/list_snmp.html'
    model = Router
    context_object_name = 'routers'
    ordering = 'host_name'

class SnmpInterfacesListView(ListView):
    template_name = 'network/list_interfaces_snmp.html'
    model = Interface
    ordering = 'router'
    # This function is executed every time that this url is reloaded
    def get_context_data(self, **kwargs):
        context = super(SnmpInterfacesListView, self).get_context_data(**kwargs)
        # Retrieving only the fields in_oct, in_uPackets, out_oct, out_uPackets for all the interfaces in the database
        query_result1 = Interface.objects.values_list('in_oct', 'in_uPackets', 'out_oct', 'out_uPackets')
        # When you retrieve more than one field the following function returns a list of tuples
        query_result2 = Interface.objects.values_list('name', 'times')
        query_result3 = Interface.objects.values_list('id', flat = True)
        
        interfaces_names = []
        for tupla in query_result2:
            name, _ = tupla
            interfaces_names.append( name ) 
        
        inOC_list  = []
        inPA_list  = []
        outOC_list = []
        outPA_list = []

        for tupla in query_result1:
            flat_tuple = tuple(map( lambda number: number.rstrip(',').split(',')[-1], tupla))
            inOC, inPA, outOC, outPA = flat_tuple
            inOC_list.append(inOC) 
            inPA_list.append(inPA) 
            outOC_list.append(outOC)
            outPA_list.append(outPA)
        
        path = '/media/'
        #print(f'Path: {path}')
        query_result4 = Interface.objects.values_list('image', flat=True)
        images = [ f'{path}{image_url}' for image_url in query_result4 ]
        # print(images)
        context['interfaces'] = zip(interfaces_names, inOC_list, inPA_list, outOC_list, outPA_list, images, query_result3)

        return context


    def post( self, request, *args, **kargs ):
        # Recuperamos el id del router que se enviará por la url
        print(f'Entre al método POST en la URL: {self.kwargs}')
        # Defining all the fields for the SNMP Interface
        fa_in_oct       = '1.3.6.1.2.1.2.2.1.10.'
        fa_in_uPackets  = '1.3.6.1.2.1.2.2.1.11.'
        fa_out_oct      = '1.3.6.1.2.1.2.2.1.16.'
        fa_out_uPackets = '1.3.6.1.2.1.2.2.1.17.'
        now = datetime.now()
        interfaces = []
        for interface in Interface.objects.all():
            router = interface.router.split(':')[1]
            oid    = interface.oid
            interface.in_oct       += snmp_query( router, fa_in_oct+str(oid) ) + ','
            interface.in_uPackets  += snmp_query( router, fa_in_uPackets+str(oid) ) + ','
            interface.out_oct      += snmp_query( router, fa_out_oct+str(oid) ) + ','
            interface.out_uPackets += snmp_query( router, fa_out_uPackets+str(oid) ) + ','
            interface.times        += now.strftime('%H:%M:%S') + ','
            interfaces.append(interface)
        
        # Updating all the interfaces
        Interface.objects.bulk_update(
            # Model instances
            interfaces,
            # Fields will be updated
            fields = ['in_oct', 'in_uPackets', 'out_oct', 'out_uPackets', 'times' ]
        )

        valid = createPlots()
        if valid == 1:
            print('Everything went well')
        else:
            print('Internal Server Error :(')

        print('All the interfaces were updated')
        return HttpResponseRedirect(
            reverse(
                'network_app:interfaces_snmp'
            )
        )


class InterfaceLossView(ListView):
    template_name = 'network/list_packets_loss.html'
    model = Interface
    
    def get_context_data(self, **kwargs):
        context = super(InterfaceLossView, self).get_context_data(**kwargs)
        router_4 = Interface.objects.get( name = 'R4-Fa1/1')
        router_6 = Interface.objects.get( name = 'R6-Fa1/0')
        routers = []
        routers.append(router_4)
        routers.append(router_6)
    
        inPA_list  = []
        outPA_list = []
        
        inPA_router_4  = int(router_4.in_uPackets.rstrip(',').split(',')[-1])
        outPA_router_4 = int(router_4.out_uPackets.rstrip(',').split(',')[-1])
        inPA_router_6  = int(router_6.in_uPackets.rstrip(',').split(',')[-1])
        outPA_router_6 = int(router_6.out_uPackets.rstrip(',').split(',')[-1])

        inPA_list.append( inPA_router_4 )
        outPA_list.append( outPA_router_4 )
        inPA_list.append( inPA_router_6 )
        outPA_list.append( outPA_router_6 )

        # Calculating the difference
        difference_4 = (outPA_router_4 - inPA_router_6) 
        difference_6 = (outPA_router_6 - inPA_router_4)

        percentage_4 = 0
        percentage_6 = 0

        
        percentage_4 = (difference_4*100)/outPA_router_4
        percentage_6 = (difference_6*100)/outPA_router_6
         
        context['difference_4'] = difference_4 
        context['difference_6'] = difference_6

        context['percentage_4'] = percentage_4
        context['percentage_6'] = percentage_6
        
        context['umbral_1'] = outPA_router_4 
        context['umbral_2'] = outPA_router_6
        context['routers'] = zip(routers, inPA_list, outPA_list)

        return context




class UpdateRouterSNMPView(View):
    # Recuperamos lo que se envía a través del método POST 
    def post( self, request, *args, **kargs ):
        # Recuperamos el id del router que se enviará por la url
        print(f' Data sended via URL: {self.kwargs}')
        router_id = self.kwargs['pk']
        # Retrieving the Router according to the 'pk' that was sended via the URL
        router = Router.objects.get( id = router_id )
        
        system_name     = '1.3.6.1.2.1.1.5.0' # SysName     OID
        system_location = '1.3.6.1.2.1.1.6.0' # SysLocation OID
        system_contact  = '1.3.6.1.2.1.1.4.0' # SysContact  OID
        system_descr    = '1.3.6.1.2.1.1.1.0' # SysDescr    OID
        # Updating the router information
        router.sysName     = snmp_query( router.ip, system_name)
        router.sysLocation = snmp_query( router.ip, system_location)
        router.sysContact  = snmp_query( router.ip, system_contact)
        router.sysDescr    = snmp_query( router.ip, system_descr) 
        # Saving the changes
        router.save()
        print('The SNMP Router Information was updated successfully')
        # When the process finish, we gotta reload the previous page
        return HttpResponseRedirect(
            reverse(
                'network_app:routers_snmp'
            )
        )
         


class InterfaceListView(ListView):
    template_name = "network/list_interfaces.html"
    context_object_name = 'interfaces'
    # Al no tener queryset necesitamos especificar el modelo de la BD
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
    fields = (
        'ip',
        'host_name',
        'brand',
        'os',
        'interfaces_on'
    )
    # URL a la cual será redireccionado
    success_url = reverse_lazy('network_app:routers_network')

    def form_valid(self, form):
        host_name = form.cleaned_data['host_name']
        print(f'Updating the hostname in GNS3: {host_name}')
        session = make_ssh_conexion( form.cleaned_data['ip'] )
        updateHostNames( session, host_name )
        return super(RouterUpdateView,self).form_valid(form) 


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
        sshuser   = form.save( commit = False )
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
    

    
