from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, PerfumeriaEsenciaGlobal, PerfumeriaEnvase, PerfumeriaLista, PerfumeriaMovimiento, obtener_hora_bogota

perfumeria_bp = Blueprint('perfumeria_bp', __name__)

@perfumeria_bp.route('/')
@login_required
def index():
    esencia = PerfumeriaEsenciaGlobal.obtener_registro()
    envases = PerfumeriaEnvase.query.filter_by(activo=True).order_by(PerfumeriaEnvase.capacidad_ml.asc()).all()
    lociones = PerfumeriaLista.query.filter_by(activo=True).order_by(PerfumeriaLista.nombre.asc()).all()
    movimientos = PerfumeriaMovimiento.query.order_by(PerfumeriaMovimiento.id.desc()).limit(150).all()

    total_envases_stock = sum(e.stock_unidades or 0 for e in envases)
    total_lociones_stock = sum(l.stock_unidades or 0 for l in lociones)

    return render_template(
        'perfumeria/index.html',
        esencia=esencia,
        envases=envases,
        lociones=lociones,
        movimientos=movimientos,
        total_envases_stock=total_envases_stock,
        total_lociones_stock=total_lociones_stock
    )

# ----------------- GESTIÓN DE ESENCIA GLOBAL (GRAMOS) -----------------

@perfumeria_bp.route('/esencia/ingresar', methods=['POST'])
@login_required
def ingresar_esencia():
    try:
        gramos = Decimal(request.form.get('gramos', '0').strip().replace(',', '.'))
        motivo = request.form.get('motivo', '').strip()

        if gramos <= 0:
            flash('La cantidad de gramos a ingresar debe ser mayor a 0.', 'danger')
            return redirect(url_for('perfumeria_bp.index'))

        esencia = PerfumeriaEsenciaGlobal.obtener_registro()
        saldo_anterior = esencia.stock_gramos_disponibles or Decimal('0.00')
        saldo_nuevo = saldo_anterior + gramos
        esencia.stock_gramos_disponibles = saldo_nuevo

        mov = PerfumeriaMovimiento(
            tipo_insumo='esencia',
            referencia_id=None,
            tipo_movimiento='entrada_manual',
            cantidad=gramos,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=saldo_nuevo,
            motivo=motivo or 'Ingreso manual de gramos de esencia',
            user_id=current_user.id
        )
        db.session.add(mov)
        db.session.commit()
        flash(f'Se ingresaron {gramos:,.2f} gramos a la bolsa global de esencia con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar el ingreso de esencia: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


@perfumeria_bp.route('/esencia/ajustar', methods=['POST'])
@login_required
def ajustar_esencia():
    try:
        nuevo_stock = Decimal(request.form.get('nuevo_stock', '0').strip().replace(',', '.'))
        motivo = request.form.get('motivo', '').strip()

        if nuevo_stock < 0:
            flash('El nuevo valor de stock no puede ser negativo.', 'danger')
            return redirect(url_for('perfumeria_bp.index'))

        if not motivo:
            flash('Debes especificar un motivo para justificar el ajuste de stock.', 'warning')
            return redirect(url_for('perfumeria_bp.index'))

        esencia = PerfumeriaEsenciaGlobal.obtener_registro()
        saldo_anterior = esencia.stock_gramos_disponibles or Decimal('0.00')
        diferencia = nuevo_stock - saldo_anterior
        esencia.stock_gramos_disponibles = nuevo_stock

        mov = PerfumeriaMovimiento(
            tipo_insumo='esencia',
            referencia_id=None,
            tipo_movimiento='ajuste',
            cantidad=diferencia,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=nuevo_stock,
            motivo=f"Ajuste manual: {motivo}",
            user_id=current_user.id
        )
        db.session.add(mov)
        db.session.commit()
        flash(f'Bolsa global de esencia ajustada a {nuevo_stock:,.2f} gramos correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al ajustar la esencia: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


# ----------------- GESTIÓN DE ENVASES -----------------

@perfumeria_bp.route('/envases/nuevo', methods=['POST'])
@login_required
def nuevo_envase():
    try:
        nombre = request.form.get('nombre', '').strip()
        capacidad_ml = int(request.form.get('capacidad_ml', 0))
        gramos_consumo = Decimal(request.form.get('gramos_consumo', '0').strip().replace(',', '.'))
        stock_unidades = int(request.form.get('stock_unidades', 0))
        precio_venta = Decimal(request.form.get('precio_venta', '0').strip().replace(',', '.'))

        if not nombre or capacidad_ml <= 0 or gramos_consumo <= 0:
            flash('Por favor diligencia nombre, capacidad (ml) y gramos de consumo válidos.', 'danger')
            return redirect(url_for('perfumeria_bp.index'))

        envase = PerfumeriaEnvase(
            nombre=nombre,
            capacidad_ml=capacidad_ml,
            gramos_consumo=gramos_consumo,
            stock_unidades=max(0, stock_unidades),
            precio_venta=max(Decimal('0.00'), precio_venta),
            activo=True
        )
        db.session.add(envase)
        db.session.flush()

        if stock_unidades > 0:
            mov = PerfumeriaMovimiento(
                tipo_insumo='envase',
                referencia_id=envase.id,
                tipo_movimiento='entrada_manual',
                cantidad=Decimal(stock_unidades),
                saldo_anterior=Decimal('0'),
                saldo_nuevo=Decimal(stock_unidades),
                motivo='Stock inicial al crear el tipo de envase',
                user_id=current_user.id
            )
            db.session.add(mov)

        db.session.commit()
        flash(f'Tipo de envase "{nombre}" registrado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar envase: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


@perfumeria_bp.route('/envases/<int:id>/editar', methods=['POST'])
@login_required
def editar_envase(id):
    try:
        envase = PerfumeriaEnvase.query.get_or_404(id)
        nombre = request.form.get('nombre', '').strip()
        capacidad_ml = int(request.form.get('capacidad_ml', envase.capacidad_ml))
        gramos_consumo = Decimal(request.form.get('gramos_consumo', str(envase.gramos_consumo)).strip().replace(',', '.'))
        precio_venta = Decimal(request.form.get('precio_venta', str(envase.precio_venta)).strip().replace(',', '.'))

        if not nombre or capacidad_ml <= 0 or gramos_consumo <= 0:
            flash('Datos del envase inválidos.', 'danger')
            return redirect(url_for('perfumeria_bp.index'))

        envase.nombre = nombre
        envase.capacidad_ml = capacidad_ml
        envase.gramos_consumo = gramos_consumo
        envase.precio_venta = precio_venta

        db.session.commit()
        flash(f'Envase "{nombre}" actualizado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al editar envase: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


@perfumeria_bp.route('/envases/<int:id>/sumar-stock', methods=['POST'])
@login_required
def sumar_stock_envase(id):
    try:
        envase = PerfumeriaEnvase.query.get_or_404(id)
        cantidad = int(request.form.get('cantidad', 0))
        motivo = request.form.get('motivo', '').strip()

        if cantidad <= 0:
            flash('La cantidad a sumar debe ser mayor a 0.', 'danger')
            return redirect(url_for('perfumeria_bp.index'))

        saldo_anterior = envase.stock_unidades or 0
        saldo_nuevo = saldo_anterior + cantidad
        envase.stock_unidades = saldo_nuevo

        mov = PerfumeriaMovimiento(
            tipo_insumo='envase',
            referencia_id=envase.id,
            tipo_movimiento='entrada_manual',
            cantidad=Decimal(cantidad),
            saldo_anterior=Decimal(saldo_anterior),
            saldo_nuevo=Decimal(saldo_nuevo),
            motivo=motivo or f"Ingreso de {cantidad} unidades de {envase.nombre}",
            user_id=current_user.id
        )
        db.session.add(mov)
        db.session.commit()
        flash(f'Se sumaron {cantidad} unidades al stock de "{envase.nombre}". Total: {saldo_nuevo} u.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al sumar stock: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


@perfumeria_bp.route('/envases/<int:id>/ajustar-stock', methods=['POST'])
@login_required
def ajustar_stock_envase(id):
    try:
        envase = PerfumeriaEnvase.query.get_or_404(id)
        nuevo_stock = int(request.form.get('nuevo_stock', 0))
        motivo = request.form.get('motivo', '').strip()

        if nuevo_stock < 0:
            flash('El nuevo stock no puede ser negativo.', 'danger')
            return redirect(url_for('perfumeria_bp.index'))

        saldo_anterior = envase.stock_unidades or 0
        diferencia = nuevo_stock - saldo_anterior
        envase.stock_unidades = nuevo_stock

        mov = PerfumeriaMovimiento(
            tipo_insumo='envase',
            referencia_id=envase.id,
            tipo_movimiento='ajuste',
            cantidad=Decimal(diferencia),
            saldo_anterior=Decimal(saldo_anterior),
            saldo_nuevo=Decimal(nuevo_stock),
            motivo=f"Ajuste manual ({envase.nombre}): {motivo or 'Sin motivo'}",
            user_id=current_user.id
        )
        db.session.add(mov)
        db.session.commit()
        flash(f'Stock de "{envase.nombre}" ajustado a {nuevo_stock} unidades.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al ajustar stock de envase: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


@perfumeria_bp.route('/envases/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_envase(id):
    try:
        envase = PerfumeriaEnvase.query.get_or_404(id)
        envase.activo = False
        db.session.commit()
        flash(f'Envase "{envase.nombre}" deshabilitado.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al deshabilitar envase: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


# ----------------- GESTIÓN DE LOCIONES YA PREPARADAS (LISTAS) -----------------

@perfumeria_bp.route('/listas/nueva', methods=['POST'])
@login_required
def nueva_locion_lista():
    try:
        nombre = request.form.get('nombre', '').strip()
        stock_unidades = int(request.form.get('stock_unidades', 0))
        precio_venta = Decimal(request.form.get('precio_venta', '0').strip().replace(',', '.'))

        if not nombre:
            flash('El nombre de la loción es obligatorio.', 'danger')
            return redirect(url_for('perfumeria_bp.index'))

        locion = PerfumeriaLista(
            nombre=nombre,
            stock_unidades=max(0, stock_unidades),
            precio_venta=max(Decimal('0.00'), precio_venta),
            activo=True
        )
        db.session.add(locion)
        db.session.flush()

        if stock_unidades > 0:
            mov = PerfumeriaMovimiento(
                tipo_insumo='locion_lista',
                referencia_id=locion.id,
                tipo_movimiento='entrada_manual',
                cantidad=Decimal(stock_unidades),
                saldo_anterior=Decimal('0'),
                saldo_nuevo=Decimal(stock_unidades),
                motivo='Stock inicial de loción terminada',
                user_id=current_user.id
            )
            db.session.add(mov)

        db.session.commit()
        flash(f'Loción "{nombre}" registrada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar loción: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


@perfumeria_bp.route('/listas/<int:id>/editar', methods=['POST'])
@login_required
def editar_locion_lista(id):
    try:
        locion = PerfumeriaLista.query.get_or_404(id)
        nombre = request.form.get('nombre', '').strip()
        precio_venta = Decimal(request.form.get('precio_venta', str(locion.precio_venta)).strip().replace(',', '.'))

        if not nombre:
            flash('El nombre es obligatorio.', 'danger')
            return redirect(url_for('perfumeria_bp.index'))

        locion.nombre = nombre
        locion.precio_venta = precio_venta
        db.session.commit()
        flash(f'Loción "{nombre}" actualizada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al editar loción: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


@perfumeria_bp.route('/listas/<int:id>/sumar-stock', methods=['POST'])
@login_required
def sumar_stock_locion(id):
    try:
        locion = PerfumeriaLista.query.get_or_404(id)
        cantidad = int(request.form.get('cantidad', 0))
        motivo = request.form.get('motivo', '').strip()

        if cantidad <= 0:
            flash('La cantidad debe ser mayor a 0.', 'danger')
            return redirect(url_for('perfumeria_bp.index'))

        saldo_anterior = locion.stock_unidades or 0
        saldo_nuevo = saldo_anterior + cantidad
        locion.stock_unidades = saldo_nuevo

        mov = PerfumeriaMovimiento(
            tipo_insumo='locion_lista',
            referencia_id=locion.id,
            tipo_movimiento='entrada_manual',
            cantidad=Decimal(cantidad),
            saldo_anterior=Decimal(saldo_anterior),
            saldo_nuevo=Decimal(saldo_nuevo),
            motivo=motivo or f"Ingreso de {cantidad} unidades de {locion.nombre}",
            user_id=current_user.id
        )
        db.session.add(mov)
        db.session.commit()
        flash(f'Se sumaron {cantidad} unidades a "{locion.nombre}". Total: {saldo_nuevo} u.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al sumar stock: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


@perfumeria_bp.route('/listas/<int:id>/ajustar-stock', methods=['POST'])
@login_required
def ajustar_stock_locion(id):
    try:
        locion = PerfumeriaLista.query.get_or_404(id)
        nuevo_stock = int(request.form.get('nuevo_stock', 0))
        motivo = request.form.get('motivo', '').strip()

        if nuevo_stock < 0:
            flash('El nuevo stock no puede ser negativo.', 'danger')
            return redirect(url_for('perfumeria_bp.index'))

        saldo_anterior = locion.stock_unidades or 0
        diferencia = nuevo_stock - saldo_anterior
        locion.stock_unidades = nuevo_stock

        mov = PerfumeriaMovimiento(
            tipo_insumo='locion_lista',
            referencia_id=locion.id,
            tipo_movimiento='ajuste',
            cantidad=Decimal(diferencia),
            saldo_anterior=Decimal(saldo_anterior),
            saldo_nuevo=Decimal(nuevo_stock),
            motivo=f"Ajuste manual ({locion.nombre}): {motivo or 'Sin motivo'}",
            user_id=current_user.id
        )
        db.session.add(mov)
        db.session.commit()
        flash(f'Stock de "{locion.nombre}" ajustado a {nuevo_stock} unidades.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al ajustar stock de loción: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


@perfumeria_bp.route('/listas/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_locion(id):
    try:
        locion = PerfumeriaLista.query.get_or_404(id)
        locion.activo = False
        db.session.commit()
        flash(f'Loción "{locion.nombre}" deshabilitada.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al deshabilitar loción: {str(e)}', 'danger')

    return redirect(url_for('perfumeria_bp.index'))


# ----------------- API EN TIEMPO REAL PARA EL POS (CAJA) -----------------

@perfumeria_bp.route('/api/estado', methods=['GET'])
@login_required
def api_estado():
    """
    Retorna el estado en vivo de:
    - Bolsa global de esencia en gramos disponibles
    - Catálogo de envases (con stock de unidades, gramos de consumo y precio)
    - Catálogo de lociones listas (con stock de unidades y precio)
    """
    esencia = PerfumeriaEsenciaGlobal.obtener_registro()
    envases = PerfumeriaEnvase.query.filter_by(activo=True).order_by(PerfumeriaEnvase.capacidad_ml.asc()).all()
    lociones = PerfumeriaLista.query.filter_by(activo=True).order_by(PerfumeriaLista.nombre.asc()).all()

    return jsonify({
        'esencia_gramos': float(esencia.stock_gramos_disponibles or 0),
        'envases': [e.to_dict() for e in envases],
        'listas': [l.to_dict() for l in lociones]
    })
