# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.

import json
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    """Override payment.transaction para crear bookings automáticamente"""
    _inherit = 'payment.transaction'

    # Campo para almacenar datos de booking
    booking_data_json = fields.Text(
        string="Booking Data (JSON)",
        help="Datos de la reserva guardados como JSON"
    )
    booking_created = fields.Boolean(
        string="Booking Created",
        default=False,
        help="Indica si el booking fue creado exitosamente"
    )

    def _apply_updates(self, payment_data):
        """
        Override para crear lead + contract automáticamente después de pago exitoso.
        Este método se ejecuta cuando Redsys envía el webhook de confirmación.
        """
        # Llamar al método padre primero
        super()._apply_updates(payment_data)

        # Si la transacción está en estado 'done' (pago exitoso)
        if self.state == 'done':
            _logger.info(
                f"REDSYS: Pago exitoso procesado | TX:{self.id} | "
                f"Amount:{self.amount} {self.currency_id.symbol} | "
                f"Ref:{self.reference} | Company:{self.company_id.name}"
            )

            try:
                # Idempotencia: Verificar si ya existe contrato para esta transacción
                existing_contract = self.env['vehicle.contract'].search([
                    ('payment_transaction_id', '=', self.id),
                ])

                if existing_contract:
                    _logger.warning(
                        f"REDSYS: Webhook duplicado detectado | TX:{self.id} | "
                        f"Contract ya existe: {existing_contract.id}"
                    )
                    self.booking_created = True
                    return

                # Obtener datos de booking desde la sesión o del campo JSON
                booking_data = self._get_booking_data()

                if not booking_data:
                    _logger.error(
                        f"REDSYS: Datos de booking no encontrados | TX:{self.id}"
                    )
                    return

                # Crear el booking
                self._create_booking_from_payment(booking_data)
                self.booking_created = True

            except Exception as e:
                _logger.error(
                    f"REDSYS: Error crítico creando booking | TX:{self.id} | "
                    f"Error: {str(e)}",
                    exc_info=True
                )
                # NO fallar la transacción, el cron lo reintentará
                raise

    def _get_booking_data(self):
        """
        Obtener datos de booking. Primero intenta desde sesión,
        luego desde el campo JSON guardado en la transacción.
        """
        try:
            from odoo.http import request
            # Intentar obtener desde sesión
            if request and hasattr(request, 'session'):
                booking_data = request.session.get('booking_data')
                if booking_data:
                    return booking_data
        except Exception:
            pass

        # Si no está en sesión, intentar desde campo JSON
        if self.booking_data_json:
            try:
                return json.loads(self.booking_data_json)
            except json.JSONDecodeError:
                return None

        return None

    def _create_booking_from_payment(self, booking_data):
        """
        Crear lead + vehicle.contract automáticamente después de pago exitoso.
        """
        # Validar datos obligatorios
        required_fields = ['customer_name', 'customer_email', 'start_date', 'end_date', 'category_id']
        for field in required_fields:
            if field not in booking_data or not booking_data[field]:
                raise ValidationError(f"Falta datos obligatorio: {field}")

        try:
            with self.env.cr.savepoint():
                # 1. Encontrar o crear partner (cliente)
                partner = self._find_or_create_partner(
                    booking_data.get('customer_name'),
                    booking_data.get('customer_email'),
                    booking_data.get('customer_phone')
                )

                # 2. Encontrar vehículo disponible
                vehicle = self._find_available_vehicle(
                    booking_data.get('category_id'),
                    booking_data.get('start_date'),
                    booking_data.get('end_date')
                )

                if not vehicle:
                    # Si el vehículo se agotó, crear reembolso
                    _logger.warning(
                        f"REDSYS: Vehículo no disponible | TX:{self.id} | "
                        f"Category:{booking_data.get('category_id')}"
                    )
                    # TODO: Implementar reembolso automático
                    raise ValidationError(
                        "El vehículo seleccionado ya no está disponible. "
                        "Se procesará un reembolso automático."
                    )

                # 3. Crear CRM Lead
                # Buscar stage sin depender de un nombre específico
                lead_stage_id = False
                try:
                    # Intentar encontrar stage "Ganado" primero
                    lead_stage = self.env['crm.stage'].search([('name', 'ilike', '%Ganado%')], limit=1)
                    if lead_stage:
                        lead_stage_id = lead_stage.id
                    else:
                        # Si no, usar el primer stage disponible
                        lead_stage = self.env['crm.stage'].search([], limit=1)
                        if lead_stage:
                            lead_stage_id = lead_stage.id
                except:
                    pass
                
                lead_vals = {
                    'name': f"Reserva Confirmada - {booking_data.get('customer_name')}",
                    'partner_id': partner.id,
                    'type': 'opportunity',
                    'email_from': booking_data.get('customer_email'),
                    'phone': booking_data.get('customer_phone'),
                    'description': f"Reserva procesada vía web | TX:{self.id}",
                }
                if lead_stage_id:
                    lead_vals['stage_id'] = lead_stage_id
                
                lead = self.env['crm.lead'].sudo().create(lead_vals)

                # 4. Crear Vehicle Contract
                contract = self.env['vehicle.contract'].sudo().create({
                    'customer_id': partner.id,
                    'vehicle_id': vehicle.id,
                    'start_date': booking_data.get('start_date'),
                    'end_date': booking_data.get('end_date'),
                    'rent_type': 'days',  # Por defecto
                    'rent': self.amount,
                    'currency_id': self.currency_id.id,
                    'status': 'a_draft',
                    'responsible_id': self.env.user.id,
                    'company_id': self.company_id.id,
                })

                # 5. Transicionar automáticamente a in_progress
                contract.a_draft_to_b_in_progress()

                _logger.info(
                    f"REDSYS: Booking creado exitosamente | TX:{self.id} | "
                    f"Lead:{lead.id} | Contract:{contract.id} | "
                    f"Vehicle:{vehicle.name}"
                )

                # 6. Limpiar sesión si es posible
                try:
                    from odoo.http import request
                    if request and hasattr(request, 'session'):
                        request.session.pop('booking_data', None)
                        request.session.pop('payment_tx_id', None)
                        request.session.modified = True
                except Exception:
                    pass

                return contract

        except Exception as e:
            _logger.error(
                f"REDSYS: Error creando booking | TX:{self.id} | "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise

    def _find_or_create_partner(self, name, email, phone):
        """Encontrar o crear partner (cliente)"""
        Partner = self.env['res.partner']

        # Buscar por email si existe
        if email:
            partner = Partner.sudo().search([
                ('email', '=', email.strip().lower())
            ], limit=1)
            if partner:
                _logger.info(f"REDSYS: Partner encontrado por email: {partner.name}")
                return partner

        # Buscar por teléfono si existe
        if phone:
            clean_phone = phone.replace(' ', '').replace('-', '').replace('+', '')
            partners = Partner.sudo().search([
                ('phone', '!=', False)
            ])
            for partner in partners:
                partner_phone = (partner.phone or '').replace(' ', '').replace('-', '').replace('+', '')
                if partner_phone and partner_phone == clean_phone:
                    _logger.info(f"REDSYS: Partner encontrado por teléfono: {partner.name}")
                    return partner

        # Crear nuevo partner
        partner = Partner.sudo().create({
            'name': name or 'Cliente Web',
            'email': email,
            'phone': phone,
            'customer_rank': 1,
            'comment': f'Contacto creado vía reserva web | Fecha: {datetime.now()}',
        })
        _logger.info(f"REDSYS: Nuevo partner creado: {partner.name} ({partner.id})")
        return partner

    def _find_available_vehicle(self, category_id, start_date, end_date):
        """Encontrar vehículo disponible para la categoría y fechas"""
        try:
            # Buscar vehículos de la categoría
            vehicles = self.env['fleet.vehicle'].sudo().search([
                ('category_id', '=', int(category_id)),
                ('status', '=', 'available'),
                ('company_id', '=', self.company_id.id),
            ])

            # Verificar disponibilidad (sin solapamientos)
            for vehicle in vehicles:
                overlapping = self.env['vehicle.contract'].search([
                    ('vehicle_id', '=', vehicle.id),
                    ('status', 'in', ['b_in_progress', 'c_return']),
                    ('start_date', '<=', end_date),
                    ('end_date', '>=', start_date),
                ])

                if not overlapping:
                    _logger.info(
                        f"REDSYS: Vehículo disponible encontrado: {vehicle.name} "
                        f"(ID:{vehicle.id})"
                    )
                    return vehicle

            _logger.warning(
                f"REDSYS: No hay vehículos disponibles | "
                f"Category:{category_id} | Company:{self.company_id.name}"
            )
            return None

        except Exception as e:
            _logger.error(f"REDSYS: Error buscando vehículo | Error: {str(e)}")
            return None

    @api.model
    def _cron_process_orphaned_transactions(self):
        """
        Cron job para procesar transacciones 'done' sin booking creado.
        Ejecutar cada 30 minutos.
        """
        orphaned_txs = self.search([
            ('state', '=', 'done'),
            ('provider_code', '=', 'redsys'),
            ('booking_created', '=', False),
            ('create_date', '>', datetime.now() - timedelta(hours=24)),
        ])

        _logger.info(f"REDSYS CRON: Procesando {len(orphaned_txs)} transacciones huérfanas")

        for tx in orphaned_txs:
            try:
                booking_data = tx._get_booking_data()
                if booking_data:
                    tx._create_booking_from_payment(booking_data)
                else:
                    _logger.warning(
                        f"REDSYS CRON: Datos de booking no encontrados | TX:{tx.id}"
                    )
            except Exception as e:
                _logger.error(
                    f"REDSYS CRON: Error procesando TX {tx.id} | Error: {str(e)}",
                    exc_info=True
                )

        return True
