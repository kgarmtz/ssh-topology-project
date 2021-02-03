from django.db import models

class Router(models.Model):    
    """ Router Model """
    
    ip = models.CharField(
        'IP ID',
         max_length = 20
    )

    host_name = models.CharField(
        'Host Name', 
        max_length = 20
    )

    brand = models.CharField(
        'Brand', 
        max_length = 20
    )

    os = models.CharField(
        'Operative System', 
        max_length = 50
    )

    interfaces_on = models.PositiveIntegerField(null = True)

    # SNMP Fields
    sysName = models.CharField(
        'System Name', 
        max_length = 100, 
        blank = True
    )

    sysLocation = models.CharField(
        'System Location', 
        max_length=50, 
        blank = True
    )

    sysContact  = models.CharField(
        'System Contact', 
        max_length=50, 
        blank = True
    )

    sysDescr = models.CharField(
        'System Description', 
        max_length = 300, 
        blank = True
    )  
    
    def __str__(self):
        return self.host_name


class Interface(models.Model):
    """ Interfaces Model """
    name = models.CharField(
        'Interface Name',
        max_length = 40
    )

    ip = models.CharField(
        'IP',
        max_length = 20
    )

    mask = models.CharField(
        'Mask',
        max_length = 20
    )

    router = models.CharField(
        'Router',
        max_length = 50
    )
    
    # SNMP Fields
    oid = models.CharField(
        'OID Identifier', 
        max_length = 1,
        blank = True
    )

    in_oct = models.CharField(
        'Octetos de Entrada', 
        max_length = 300,
        blank = True
    )

    in_uPackets = models.CharField(
        'Paquetes de Entrada', 
        max_length = 300,
        blank = True
    )

    out_oct = models.CharField(
        'Octetos de Salida', 
        max_length = 300,
        blank = True
    )

    out_uPackets = models.CharField(
        'Paquetes de Salida', 
        max_length = 300,
        blank = True
    )

    times = models.CharField(
        'Time of Last Modification', 
        max_length = 500,
        blank = True
    )

    image = models.ImageField(
        'Image', 
        upload_to ='Interfaces', 
        blank = True
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return str(self.id) + '. ' + self.router+' - '+self.name

class SSHUser(models.Model):
    """ SSH User Model """
    username = models.CharField(
        'SSH User Name',
        max_length = 40,
        unique = True
    )

    password = models.CharField(
        'Password',
        max_length = 40
    )
    
    # La llave foránea será el Router
    router = models.ForeignKey( Router, on_delete=models.CASCADE)

    def __str__(self):
        return self.username
