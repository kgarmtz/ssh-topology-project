from django import forms

# Los Formularios Simples no trabajan con un modelo en particular
class RouterForm(forms.Form):
    # Validación de la opción elegida 
    valid = forms.BooleanField(
        # El campo debe ser requerido 
        required = True
    )
