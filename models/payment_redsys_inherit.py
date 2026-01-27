# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.

import json
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

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
                # Idempotencia: Verificar si ya se creó lead para esta transacción
                if self.booking_created:
                    _logger.warning(
                        f"REDSYS: Webhook duplicado detectado | TX:{self.id} | "
                        f"Lead ya fue creado"
                    )
                    return

                # Obtener datos de booking desde la sesión o del campo JSON
                booking_data = self._get_booking_data()

                if not booking_data:
                    _logger.error(
                        f"REDSYS: Datos de booking no encontrados | TX:{self.id}"
                    )
                    return

                # Crear el booking
                self._create_lead_from_payment(booking_data)
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
    
    def _create_and_pay_deposit_invoice(self, lead, partner, deposit_amount):
        """
        Crear automáticamente una factura de depósito y marcarla como pagada usando register_payment().
        Se ejecuta cuando el pago de Redsys se completa.
        """
        try:
            # Obtener el producto de depósito
            deposit_product = self.env.ref('vehicle_rental.vehicle_rent_deposit')
            
            # Obtener el diario de ventas
            sale_journal = self.env['account.journal'].sudo().search([
                ('type', '=', 'sale'),
                ('company_id', '=', lead.company_id.id)
            ], limit=1)
            
            if not sale_journal:
                sale_journal = self.env['account.journal'].sudo().search([
                    ('type', '=', 'sale')
                ], limit=1)
            
            if not sale_journal:
                _logger.warning(f"REDSYS: No sale journal found para crear factura de depósito")
                return None
            
            # Crear la factura de depósito
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'journal_id': sale_journal.id,
                'invoice_date': fields.Date.today(),
                'company_id': lead.company_id.id,
                'ref': f"Depósito para reserva TX:{self.reference}",
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': deposit_product.id,
                        'name': f"Depósito de seguridad - {lead.name}",
                        'quantity': 1,
                        'price_unit': deposit_amount,
                    })
                ]
            }
            
            deposit_invoice = self.env['account.move'].sudo().create(invoice_vals)
            _logger.info(f"REDSYS: Factura de depósito creada - Invoice ID:{deposit_invoice.id}")
            
            # Obtener el diario de banco para Redsys
            bank_journal = self.env['account.journal'].sudo().search([
                ('type', '=', 'bank'),
                ('name', 'ilike', 'redsys')
            ], limit=1)
            
            if not bank_journal:
                bank_journal = self.env['account.journal'].sudo().search([
                    ('type', '=', 'bank')
                ], limit=1)
            
            if bank_journal:
                # Crear el pago usando el método oficial de Odoo
                payment_vals = {
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': partner.id,
                    'amount': deposit_amount,
                    'currency_id': deposit_invoice.currency_id.id,
                    'journal_id': bank_journal.id,
                    'company_id': deposit_invoice.company_id.id,
                    'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                    'ref': f"Pago Redsys TX:{self.reference}",
                    'communication': f"Depósito {deposit_invoice.name}",
                }
                
                payment = self.env['account.payment'].sudo().create(payment_vals)
                payment.action_post()
                _logger.info(f"REDSYS: Payment creado y posted - Payment ID:{payment.id}")
                
                # Usar register_payment() - método oficial de Odoo para marcar factura como pagada
                try:
                    deposit_invoice.register_payment(payment.move_id)
                    _logger.info(f"REDSYS: Factura de depósito reconciliada exitosamente usando register_payment()")
                except Exception as e:
                    _logger.warning(f"REDSYS: register_payment() falló, intentando reconciliación manual: {e}")
                    # Fallback a reconciliación manual
                    self._reconcile_payment_manual(payment, deposit_invoice)
            else:
                _logger.warning(f"REDSYS: No bank journal found, factura de depósito quedará sin pago")
            
            return deposit_invoice
            
        except Exception as e:
            _logger.error(f"REDSYS: Error creando factura de depósito: {str(e)}", exc_info=True)
            return None
    
    def _reconcile_payment_manual(self, payment, invoice):
        """
        Reconciliación manual como fallback si register_payment() falla.
        """
        try:
            payment_line = payment.move_id.line_ids.filtered(
                lambda x: x.account_id.internal_type == 'receivable'
            )
            invoice_line = invoice.line_ids.filtered(
                lambda x: x.account_id.internal_type == 'receivable'
            )
            
            if payment_line and invoice_line:
                (payment_line + invoice_line).reconcile()
                _logger.info(f"REDSYS: Reconciliación manual completada")
            else:
                _logger.warning(f"REDSYS: No se encontraron líneas receivable para reconciliación manual")
        except Exception as e:
            _logger.error(f"REDSYS: Error en reconciliación manual: {str(e)}", exc_info=True)
    
    def _create_payment_for_invoice(self, invoice, amount, payment_method_name='Redsys'):
        """
        Crear un pago (account.payment) para reconciliar una factura.
        Esto marca la factura como "Pagado" automáticamente.
        """
        try:
            # Buscar el diario de banco para Redsys
            bank_journal = self.env['account.journal'].sudo().search([
                ('type', '=', 'bank'),
                ('name', 'ilike', 'redsys')
            ], limit=1)
            
            if not bank_journal:
                # Usar el diario de banco por defecto
                bank_journal = self.env['account.journal'].sudo().search([
                    ('type', '=', 'bank')
                ], limit=1)
            
            if not bank_journal:
                _logger.warning(f"REDSYS: No bank journal found para crear payment")
                return None
            
            # Crear el pago
            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': invoice.partner_id.id,
                'amount': amount,
                'currency_id': invoice.currency_id.id,
                'journal_id': bank_journal.id,
                'company_id': invoice.company_id.id,
                'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                'ref': f"Pago Redsys TX:{self.reference}",
                'communication': f"Depósito para {invoice.name}",
            }
            
            payment = self.env['account.payment'].sudo().create(payment_vals)
            _logger.info(f"REDSYS: Payment creado para invoice {invoice.id} - Payment ID:{payment.id}")
            
            # Marcar como enviado (posted)
            payment.action_post()
            _logger.info(f"REDSYS: Payment posted - Payment ID:{payment.id}")
            
            # Reconciliar el pago con la factura
            payment_line = payment.move_id.line_ids.filtered(
                lambda x: x.account_id.internal_type == 'receivable'
            )
            invoice_line = invoice.line_ids.filtered(
                lambda x: x.account_id.internal_type == 'receivable'
            )
            
            if payment_line and invoice_line:
                (payment_line + invoice_line).reconcile()
                _logger.info(f"REDSYS: Invoice {invoice.id} reconciliada con Payment {payment.id}")
            
            return payment
            
        except Exception as e:
            _logger.error(f"REDSYS: Error creando payment para invoice {invoice.id}: {str(e)}", exc_info=True)
            return None

    def _create_lead_from_payment(self, booking_data):
        """
        Crear SOLO el Lead después de pago exitoso.
        El contrato se crea manualmente desde CRM al marcar como "Ganado".
        """
        with open('/tmp/method_execution.log', 'a') as me:
            me.write(f"[METHOD_ENTRY] _create_lead_from_payment called with TX:{self.id}\n")
        
        # Validar datos obligatorios
        required_fields = ['customer_name', 'customer_email', 'start_date', 'end_date', 'category_id']
        for field in required_fields:
            if field not in booking_data or not booking_data[field]:
                raise ValidationError(f"Falta datos obligatorio: {field}")

        try:
            # 1. Encontrar o crear partner (cliente)
            partner = self._find_or_create_partner(
                booking_data.get('customer_name'),
                booking_data.get('customer_email'),
                booking_data.get('customer_phone'),
                booking_data.get('company_id')
            )
            with open('/tmp/method_execution.log', 'a') as me:
                me.write(f"[PARTNER_OK] TX:{self.id} - Partner ID={partner.id}\n")

            # 2. Verificar que existen vehículos en la categoría (NO asignar uno específico)
            category_id = booking_data.get('category_id')
            company_id = booking_data.get('company_id')
            
            available_count = self.env['fleet.vehicle'].sudo().search_count([
                ('model_id.category_id', '=', int(category_id)),
                ('status', '=', 'available'),
                ('company_id', '=', company_id),
            ])
            
            if available_count == 0:
                _logger.warning(
                    f"REDSYS: No hay vehículos disponibles | TX:{self.id} | "
                    f"Category:{category_id}"
                )
                raise ValidationError(
                    "No hay vehículos disponibles en esta categoría. "
                    "Se procesará un reembolso automático."
                )

            # 3. Crear CRM Lead (FUERA del bloque if not vehicle)
            # Buscar stage 1 (que es el que busca la vista "Consulta de Reserva")
            lead_stage_id = 1  # Por defecto, usar stage 1
            try:
                # Verificar que el stage 1 existe
                lead_stage = self.env['crm.stage'].search([('id', '=', 1)], limit=1)
                if lead_stage:
                    lead_stage_id = lead_stage.id
                else:
                    # Si no existe stage 1, usar el primer stage disponible
                    lead_stage = self.env['crm.stage'].search([], limit=1)
                    if lead_stage:
                        lead_stage_id = lead_stage.id
            except:
                pass
            
            # Construir descripción con validación de seguridad
            total_price = float(booking_data.get('total_price', 0.0))
            deposit_amount = float(booking_data.get('deposit_amount', 0.0))
            total_with_deposit = float(booking_data.get('total_with_deposit', 0.0))
            card_type = booking_data.get('card_type', 'N/A')
            card_bin = booking_data.get('card_bin', 'N/A')
            
            # Validación de seguridad: Comparar BIN y tipo de tarjeta validados vs los usados en pago
            # TODO PRODUCCIÓN: Verificar si Redsys devuelve BIN del pago para comparar
            security_note = f"✅ BIN validado: {card_bin} | Tipo: {card_type}"
            
            description = (
                f"Reserva procesada vía web | TX:{self.id}<br/><br/>"
                f"--- RESUMEN DEL ALQUILER ---<br/>"
                f"- Tarifa: {float(booking_data.get('selected_price', 0.0)):.2f} €/día<br/>"
                f"- Precio total alquiler: {total_price:.2f} €<br/>"
                f"- Depósito de seguridad: {deposit_amount:.2f} € ({card_type})<br/>"
                f"- TOTAL PAGADO: {total_with_deposit:.2f} €<br/>"
                f"- Fechas: {booking_data.get('start_date')} {booking_data.get('start_time')} → {booking_data.get('end_date')} {booking_data.get('end_time')}<br/>"
                f"- Ubicación: {booking_data.get('location')}<br/>"
                f"- Transacción Redsys: {self.reference}<br/><br/>"
                f"--- SEGURIDAD ---<br/>"
                f"{security_note}"
            )
            
            lead_vals = {
                'name': f"Consulta de Reserva - {booking_data.get('customer_name')}",
                'partner_id': partner.id,
                'company_id': company_id,
                'type': 'opportunity',
                'email_from': booking_data.get('customer_email'),
                'phone': booking_data.get('customer_phone'),
                'description': description,
                'stage_id': lead_stage_id,
                'vehicle_id': False,
                'start_date': booking_data.get('start_date'),
                'end_date': booking_data.get('end_date'),
                'selected_category_id': int(booking_data.get('category_id')),
                'customer_dni': booking_data.get('customer_dni'),
                'customer_dni_expiry_date': (booking_data.get('customer_dni_expiry_date') + '-01') if booking_data.get('customer_dni_expiry_date') and len(booking_data.get('customer_dni_expiry_date', '')) == 7 else booking_data.get('customer_dni_expiry_date'),
                'location': booking_data.get('location'),
                'start_time': booking_data.get('start_time'),
                'end_time': booking_data.get('end_time'),
            }
            
            with open('/tmp/lead_creation.log', 'a') as lf:
                lf.write(f"[CREATE] TX:{self.id} - Creando lead con vals: {lead_vals}\n")
            
            try:
                lead = self.env['crm.lead'].sudo().create(lead_vals)
                with open('/tmp/lead_creation.log', 'a') as lf:
                    lf.write(f"[SUCCESS] TX:{self.id} - Lead creado: ID={lead.id}\n")
            except Exception as e:
                with open('/tmp/lead_creation.log', 'a') as lf:
                    lf.write(f"[LEAD_ERROR] TX:{self.id} - Error: {str(e)}\n")
                raise

            _logger.info(
                f"REDSYS: Lead creado exitosamente (SIN vehículo asignado) | TX:{self.id} | "
                f"Lead:{lead.id} | "
                f"Category:{category_id}"
            )

            # 7. Crear factura de depósito automáticamente y marcarla como pagada
            try:
                deposit_amount = float(booking_data.get('deposit_amount', 0.0))
                if deposit_amount > 0:
                    self._create_and_pay_deposit_invoice(lead, partner, deposit_amount)
            except Exception as e:
                _logger.warning(f"REDSYS: Error creando factura de depósito automático: {e}")
                # No fallar el flujo si falla la factura de depósito
            
            # 8. Limpiar sesión si es posible
            try:
                from odoo.http import request
                if request and hasattr(request, 'session'):
                    request.session.pop('booking_data', None)
                    request.session.pop('payment_tx_id', None)
                    request.session.modified = True
            except Exception:
                pass

            return lead

        except Exception as e:
            _logger.error(
                f"REDSYS: Error creando booking | TX:{self.id} | "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise

    def _find_or_create_partner(self, name, email, phone, company_id=None):
        """Encontrar o crear partner (cliente)"""
        Partner = self.env['res.partner']

        # Buscar por email si existe
        if email:
            partner = Partner.sudo().search([('company_id', '=', company_id),
                ('email', '=', email.strip().lower())
            ], limit=1)
            if partner:
                _logger.info(f"REDSYS: Partner encontrado por email: {partner.name}")
                return partner

        # Buscar por teléfono si existe
        if phone:
            clean_phone = phone.replace(' ', '').replace('-', '').replace('+', '')
            partners = Partner.sudo().search([('company_id', '=', company_id),
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
            'company_id': company_id,
            'comment': f'Contacto creado vía reserva web | Fecha: {datetime.now()}',
        })
        _logger.info(f"REDSYS: Nuevo partner creado: {partner.name} ({partner.id})")
        return partner

    def _find_available_vehicle(self, company_id, category_id, start_date, end_date):
        """Encontrar vehículo disponible para la categoría y fechas"""
        try:
            # Usar la compañía del booking (pasada desde el website)
            target_company = self.env['res.company'].sudo().browse(company_id) if company_id else None
            if not target_company or not target_company.exists():
                # Fallback a Sunset (compatibilidad)
                target_company = self.env['res.company'].sudo().search([('name', 'ilike', 'sunset')], limit=1) or self.env.company
            
            # Buscar vehículos de la categoría en la compañía correcta
            vehicles = self.env['fleet.vehicle'].sudo().search([
                ('category_id', '=', int(category_id)),
                ('status', '=', 'available'),
                ('company_id', '=', target_company.id),
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
                    tx._create_lead_from_payment(booking_data)
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
