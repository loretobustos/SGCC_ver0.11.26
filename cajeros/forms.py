
import re
from django import forms
from django.contrib.auth.hashers import make_password
from .models import Cajero, PersonalJefatura


class CajeroForm(forms.ModelForm):
    class Meta:
        model = Cajero
        fields = ['id_cajero', 'rut', 'nombre', 'nombre_cajero', 'estado']
        widgets = {
            'id_cajero': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 70
            }),
            'rut': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '12.123.123-1'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'nombre_cajero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre o empresa'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def clean_id_cajero(self):
        value = self.cleaned_data['id_cajero']

        if not 1 <= value <= 70:
            raise forms.ValidationError(
                'El número de caja debe estar entre 1 y 70.'
            )

        return value

    def clean_rut(self):
        raw = self.cleaned_data.get('rut', '')
        clean = re.sub(r'[^0-9kK]', '', raw).upper()

        if len(clean) < 7 or len(clean) > 9 or not clean[:-1].isdigit():
            raise forms.ValidationError('Ingrese un RUT válido.')

        suma = 0
        mult = 2

        for digit in reversed(clean[:-1]):
            suma += int(digit) * mult
            mult = 2 if mult == 7 else mult + 1

        dv = 11 - suma % 11
        esperado = '0' if dv == 11 else 'K' if dv == 10 else str(dv)

        if clean[-1] != esperado:
            raise forms.ValidationError(
                'El dígito verificador del RUT no es válido.'
            )

        return f"{int(clean[:-1]):,}".replace(',', '.') + '-' + clean[-1]


class SupervisorForm(forms.ModelForm):
    password = forms.CharField(
        label='Contraseña',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        }),
        help_text='Obligatoria al crear; déjela vacía para conservar la actual al editar.'
    )

    class Meta:
        model = PersonalJefatura
        fields = ['nombre', 'apellido', 'cargo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'cargo': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['password'].required = self.instance.pk is None

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if password and len(password) < 6:
            raise forms.ValidationError(
                'La contraseña debe tener al menos 6 caracteres.'
            )

        return password

    def save(self, commit=True):
        obj = super().save(commit=False)

        password = self.cleaned_data.get('password')

        if password:
            obj.password = make_password(password)

        if commit:
            obj.save()

        return obj
