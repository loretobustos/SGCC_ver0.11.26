
import csv

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from .models import Cajero, PersonalJefatura, BitacoraAuditoria
from .forms import CajeroForm, SupervisorForm


def registrar_log(request, accion, detalle, id_cajero=0, supervisor_id=None):
    responsable = supervisor_id or request.session.get('id_admin')

    if responsable:
        BitacoraAuditoria.objects.create(
            id_admin_responsable=responsable,
            id_cajero=id_cajero,
            accion=accion,
            detalle=detalle
        )


def requiere_supervisor(request):
    return bool(request.session.get('id_admin'))


# INICIO DE SESIÓN
def login_jefatura(request):
    if request.method == 'POST':
        raw_id = request.POST.get('id_admin', '').strip()
        password = request.POST.get('password', '')

        try:
            sid = int(raw_id)
        except (TypeError, ValueError):
            messages.error(request, 'Ingrese un ID numérico válido.')
            return render(request, 'cajeros/login.html')

        if not password:
            messages.error(request, 'Ingrese su contraseña.')
            return render(request, 'cajeros/login.html')

        # Buscar al usuario sin restringirlo al cargo SUPERVISOR.
        supervisor = PersonalJefatura.objects.filter(
            pk=sid
        ).first()

        # Primer acceso: crear supervisor inicial si la tabla está vacía.
        if (
            supervisor is None
            and not PersonalJefatura.objects.exists()
            and sid == 1120
            and password == 'admin123'
        ):
            supervisor = PersonalJefatura(
                nombre='Supervisor',
                apellido='Administrador',
                cargo='SUPERVISOR',
                password=make_password(password)
            )
            supervisor.save()

        # Validar contraseña y permitir acceso a cualquier cargo registrado.
        if supervisor and check_password(password, supervisor.password):
            request.session.cycle_key()
            request.session['id_admin'] = supervisor.id_jefatura

            messages.success(
                request,
                f'Bienvenido/a {supervisor.nombre}.'
            )

            registrar_log(
                request,
                'INICIO_SESION',
                'Inicio de sesión del personal de jefatura.',
                supervisor_id=supervisor.id_jefatura
            )

            return redirect('listado_cajeros')

        messages.error(
            request,
            'Credenciales incorrectas. Verifique su ID y contraseña.'
        )

    return render(request, 'cajeros/login.html')


def logout_jefatura(request):
    sid = request.session.get('id_admin')

    if sid:
        registrar_log(
            request,
            'CIERRE_SESION',
            'Cierre de sesión del personal de jefatura.',
            supervisor_id=sid
        )

    request.session.flush()
    messages.info(request, 'Sesión cerrada correctamente.')

    return redirect('login_jefatura')


# LISTADO DE CAJEROS
def listado_cajeros(request):
    if not requiere_supervisor(request):
        messages.error(request, 'Debe iniciar sesión para continuar.')
        return redirect('login_jefatura')

    cajeros = Cajero.objects.all()

    context = {
        'cajeros': cajeros,
        'total_cajas': 70,
        'activas': cajeros.filter(estado='ACTIVO').count(),
        'colacion': cajeros.filter(estado='COLACION').count(),
        'inactivas': cajeros.filter(estado='INACTIVO').count(),
        'supervisor_actual': PersonalJefatura.objects.filter(
            pk=request.session['id_admin']
        ).first()
    }

    return render(request, 'cajeros/listado_cajeros.html', context)


# CREAR CAJERO
def crear_cajero(request):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    form = CajeroForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        cajero = form.save()

        registrar_log(
            request,
            'CREAR_CAJERO',
            f'Registro de cajero {cajero.nombre} / {cajero.nombre_cajero}.',
            cajero.id_cajero
        )

        messages.success(request, 'Cajero registrado correctamente.')
        return redirect('listado_cajeros')

    return render(
        request,
        'cajeros/form_cajero.html',
        {'form': form, 'titulo': 'Registrar cajero'}
    )


# EDITAR CAJERO
def editar_cajero(request, pk):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    cajero = get_object_or_404(Cajero, pk=pk)
    form = CajeroForm(request.POST or None, instance=cajero)

    if request.method == 'POST' and form.is_valid():
        form.save()

        registrar_log(
            request,
            'EDITAR_CAJERO',
            f'Se actualizaron los datos del cajero {cajero.nombre}.',
            cajero.id_cajero
        )

        messages.success(request, 'Datos actualizados.')
        return redirect('listado_cajeros')

    return render(
        request,
        'cajeros/form_cajero.html',
        {'form': form, 'titulo': 'Editar cajero'}
    )


# ELIMINAR / CERRAR CAJERO
def eliminar_cajero(request, pk):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    cajero = get_object_or_404(Cajero, pk=pk)

    if request.method == 'POST':
        cajero.estado = 'INACTIVO'
        cajero.save(update_fields=['estado'])

        registrar_log(
            request,
            'CIERRE_CAJA',
            f'Cierre de turno de caja {cajero.id_cajero}.',
            cajero.id_cajero
        )

        messages.success(request, f'Caja {cajero.id_cajero} cerrada.')
        return redirect('listado_cajeros')

    return render(
        request,
        'cajeros/eliminar_cajero.html',
        {'cajero': cajero}
    )


# CAMBIAR CAJERO A COLACIÓN
@require_POST
def cambiar_colacion(request, pk):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    cajero = get_object_or_404(Cajero, pk=pk)

    if cajero.estado == 'ACTIVO':
        cajero.estado = 'COLACION'
        cajero.save(update_fields=['estado'])

        registrar_log(
            request,
            'COLACION',
            f'Caja {pk} enviada a colación.',
            pk
        )

        messages.warning(request, f'Caja {pk} en colación.')

    return redirect('listado_cajeros')


# REANUDAR TURNO
@require_POST
def reanudar_turno(request, pk):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    cajero = get_object_or_404(Cajero, pk=pk)

    if cajero.estado == 'COLACION':
        cajero.estado = 'ACTIVO'
        cajero.save(update_fields=['estado'])

        registrar_log(
            request,
            'REANUDAR_TURNO',
            f'Caja {pk} volvió a estado activo.',
            pk
        )

        messages.success(request, f'Caja {pk} reanudada.')

    return redirect('listado_cajeros')


# CIERRE GENERAL DE JORNADA
def cierre_general_jornada(request):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    if request.method == 'POST':
        cajas = Cajero.objects.filter(
            estado__in=['ACTIVO', 'COLACION']
        )

        cantidad = cajas.count()
        cajas.update(estado='INACTIVO')

        registrar_log(
            request,
            'CIERRE_GENERAL',
            f'Cierre general ejecutado. Se cerraron {cantidad} cajas.'
        )

        messages.success(
            request,
            f'Cierre general realizado. Cajas cerradas: {cantidad}.'
        )

        return redirect('listado_cajeros')

    return render(request, 'cajeros/cierre_general.html')


# HISTORIAL DE AUDITORÍA
def historial_auditoria(request):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    logs = BitacoraAuditoria.objects.all()

    caja = request.GET.get('caja', '').strip()
    accion = request.GET.get('accion', '').strip()
    supervisor = request.GET.get('supervisor', '').strip()

    if caja.isdigit():
        logs = logs.filter(id_cajero=int(caja))

    if accion:
        logs = logs.filter(accion=accion)

    if supervisor.isdigit():
        logs = logs.filter(id_admin_responsable=int(supervisor))

    return render(
        request,
        'cajeros/historial_auditoria.html',
        {
            'logs': logs[:500],
            'caja_filtro': caja,
            'accion_filtro': accion,
            'supervisor_filtro': supervisor,
            'acciones': BitacoraAuditoria.objects.values_list(
                'accion',
                flat=True
            ).distinct()
        }
    )


# EXPORTAR AUDITORÍA A CSV
def exportar_csv(request):
    if not requiere_supervisor(request):
        return HttpResponse('No autorizado', status=403)

    response = HttpResponse(
        content_type='text/csv; charset=utf-8-sig'
    )

    response['Content-Disposition'] = (
        'attachment; filename="bitacora_sgcc.csv"'
    )

    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'Fecha y hora',
        'ID supervisor',
        'Caja',
        'Acción',
        'Detalle'
    ])

    for log in BitacoraAuditoria.objects.all():
        writer.writerow([
            log.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
            log.id_admin_responsable,
            log.id_cajero or 'General',
            log.accion,
            log.detalle
        ])

    return response


# LISTADO DE PERSONAL DE JEFATURA
def listado_supervisores(request):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    personal = PersonalJefatura.objects.all()

    busqueda = request.GET.get('q', '').strip()
    cargo = request.GET.get('cargo', '').strip()

    if busqueda:
        filtros = (
            Q(nombre__icontains=busqueda)
            | Q(apellido__icontains=busqueda)
        )

        if busqueda.isdigit():
            filtros |= Q(id_jefatura=int(busqueda))

        personal = personal.filter(filtros)

    if cargo in dict(PersonalJefatura.CARGOS):
        personal = personal.filter(cargo=cargo)

    contexto = {
        'supervisores': personal,
        'total_personal': PersonalJefatura.objects.count(),
        'busqueda': busqueda,
        'cargo_filtro': cargo,
        'cargos': PersonalJefatura.CARGOS,
    }

    return render(
        request,
        'cajeros/listado_supervisores.html',
        contexto
    )


# CREAR PERSONAL
def crear_supervisor(request):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    form = SupervisorForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        persona = form.save()

        registrar_log(
            request,
            'CREAR_PERSONAL',
            f'Se creó {persona.get_cargo_display()}: '
            f'{persona.nombre} {persona.apellido} '
            f'(ID {persona.id_jefatura}).'
        )

        messages.success(
            request,
            f'Registro creado correctamente. '
            f'ID asignado: {persona.id_jefatura}.'
        )

        return redirect('listado_supervisores')

    return render(
        request,
        'cajeros/form_supervisor.html',
        {'form': form, 'titulo': 'Agregar personal'}
    )


# EDITAR PERSONAL
def editar_supervisor(request, pk):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    persona = get_object_or_404(PersonalJefatura, pk=pk)

    form = SupervisorForm(
        request.POST or None,
        instance=persona
    )

    if request.method == 'POST' and form.is_valid():
        persona = form.save()

        registrar_log(
            request,
            'EDITAR_PERSONAL',
            f'Se actualizaron los datos de '
            f'{persona.get_cargo_display()} '
            f'ID {persona.id_jefatura}.'
        )

        messages.success(
            request,
            'Registro actualizado correctamente.'
        )

        return redirect('listado_supervisores')

    return render(
        request,
        'cajeros/form_supervisor.html',
        {
            'form': form,
            'titulo': 'Editar registro',
            'supervisor': persona
        }
    )


# ELIMINAR PERSONAL
def eliminar_supervisor(request, pk):
    if not requiere_supervisor(request):
        return redirect('login_jefatura')

    persona = get_object_or_404(
        PersonalJefatura,
        pk=pk
    )

    if request.method == 'POST':

        if pk == request.session.get('id_admin'):
            messages.error(
                request,
                'No puedes eliminar la cuenta con la que '
                'tienes la sesión iniciada.'
            )

            return redirect('listado_supervisores')

        nombre = f'{persona.nombre} {persona.apellido}'
        cargo = persona.get_cargo_display()
        identificador = persona.id_jefatura

        registrar_log(
            request,
            'ELIMINAR_PERSONAL',
            f'Se eliminó {cargo}: {nombre} '
            f'(ID {identificador}).'
        )

        persona.delete()

        messages.success(
            request,
            f'{cargo} {nombre} '
            f'(ID {identificador}) eliminado correctamente.'
        )

        return redirect('listado_supervisores')

    return render(
        request,
        'cajeros/confirmar_eliminar_supervisor.html',
        {'supervisor': persona}
    )
