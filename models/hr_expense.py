# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from ..utils import _display_rental_notification


class HrExpense(models.Model):
    """Hr Expense"""
    _inherit = 'hr.expense'
    _description = __doc__

    fleet_vehicle_id = fields.Many2one('fleet.vehicle', ondelete='cascade')
    vehicle_contract_id = fields.Many2one('vehicle.contract', ondelete='cascade')
    driver_id = fields.Many2one('res.partner', string="Driver")
    employee_ids = fields.Many2many('hr.employee', compute='_compute_employee_ids',
                                    string="Employees")

    @api.model
    def default_get(self, fields_list):
        """Default get method"""
        res = super().default_get(fields_list)
        driver_id = res.get('driver_id')
        if driver_id:
            driver = self.env['res.partner'].browse(driver_id)
            if len(driver.employee_ids) == 1:
                res['employee_id'] = driver.employee_ids.id
            else:
                res['employee_id'] = False
        return res

    @api.depends('driver_id', 'driver_id.employee_ids')
    def _compute_employee_ids(self):
        """Compute employee(s) linked to the driver (partner)"""
        for rec in self:
            rec.employee_ids = rec.driver_id.employee_ids.ids

    def action_view_expense_details(self):
        """View expanse details"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('My Expenses'),
            'res_model': 'hr.expense',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'create': False,
            }
        }


# HrExpenseSheet hereda de hr.expense.sheet
# Comentado temporalmente para evitar errores si hr_expense no está instalado
# Descomentar cuando hr_expense esté instalado y funcionando
"""
class HrExpenseSheet(models.Model):
    '''Hr Expense Sheet'''
    _inherit = 'hr.expense.sheet'
    _description = __doc__

    def action_submit_sheet(self):
        '''Submit expense sheet with validation for assigned manager.'''
        for sheet in self:
            if not sheet.user_id:
                message = _display_rental_notification(
                    message='''Please choose a Manager before proceeding.''',
                    message_type='warning')
                return message
        return super().action_submit_sheet()
"""
