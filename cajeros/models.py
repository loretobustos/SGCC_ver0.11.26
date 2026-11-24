
from django.db import models
from django.utils import timezone
from django.db.models import Max


class Cajero(models.Model):
    id_cajero = models.IntegerField(primary_key=True)

    rut = models.CharField(
        max_length=15,
        unique=True,
        blank=False,
        null=True
    )

    nombre = models.CharField(max_length=100)
    nombre_cajero = models.CharField(max_length=100)

    estado = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVO', 'Activo (Verde)'),
            ('COLACION', 'En Colación (Amarillo)'),
            ('INACTIVO', 'Inactivo (Rojo)')
        ],
        default='INACTIVO'
    )

    ingreso = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['id_cajero']

    def __str__(self):
        return f"Cajero {self.id_cajero:02d} - {self.nombre_cajero}"


class PersonalJefatura(models.Model):

    CARGOS = [
        ('ENCARGAO', 'Encargado/a de Caja'),
        ('SUPERVISOR', 'Supervisor/a'),
        ('AYUDANTE', 'Primer Ayudante'),
    ]

    id_jefatura = models.IntegerField(
        primary_key=True,
        editable=False
    )

    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)

    cargo = models.CharField(
        max_length=20,
        choices=CARGOS
    )

    # Contraseña almacenada mediante el sistema de hash de Django
    password = models.CharField(
        max_length=128,
        blank=True,
        default=''
    )

    class Meta:
        ordering = ['id_jefatura']

    def save(self, *args, **kwargs):

        if self._state.adding:

            ultimo_id = PersonalJefatura.objects.aggregate(
                mayor=Max('id_jefatura')
            )['mayor']

            if ultimo_id is None:
                nuevo_id = 1120
            else:
                nuevo_id = ultimo_id + 1

            if nuevo_id > 1140:
                raise ValueError(
                    "Se ha alcanzado el límite máximo "
                    "de IDs de Jefatura (1140)."
                )

            self.id_jefatura = nuevo_id

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"ID {self.id_jefatura} - "
            f"{self.nombre} {self.apellido} "
            f"({self.get_cargo_display()})"
        )


class BitacoraAuditoria(models.Model):

    timestamp = models.DateTimeField(default=timezone.now)
    id_admin_responsable = models.IntegerField()
    id_cajero = models.IntegerField()
    accion = models.CharField(max_length=50)
    detalle = models.TextField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return (
            f"[{self.timestamp.strftime('%d/%m/%Y %H:%M')}] "
            f"Admin #{self.id_admin_responsable} - "
            f"{self.accion} (Caja {self.id_cajero})"
        )
