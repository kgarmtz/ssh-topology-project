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

    def __str__(self):
        return self.router+' - '+self.name

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
