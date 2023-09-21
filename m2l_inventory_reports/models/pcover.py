# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
import pytz
from datetime import timedelta
import logging
_log = logging.getLogger("\n =====[%s]===" % __name__)


class PcoverReportHistory(models.Model):
    _name = "pcover.report.history"
    _description = "Historial de portadas"
    _sql_constraints = [
        ('folio_name_uniq', 'unique (name)', "Ya existe un registro con este folio !"),
    ]

    name = fields.Char(string="Folio")
    folio = fields.Integer(string="Folio")
    carrier_id = fields.Many2one('res.partner', string="Transportista relacionado") #  Manual
    carrier_name = fields.Char(string="Transportista")
    remition_qty = fields.Integer(string="Número de bultos")
    hr_driver_id = fields.Many2one('hr.employee', string="Chofer relacionado") # Manual
    hr_driver_name = fields.Char(string="Chofer")
    supervisor_id = fields.Many2one('hr.employee', string="Supervisor")
    vehicle_tag_id = fields.Many2one('l10n_mx_edi.vehicle', string="Placas relacionadas") # Manual 
    vehicle_tag_name = fields.Char(string="Placas")
    dest_location_id = fields.Many2one('res.partner', string="Destino")
    line_ids = fields.One2many('pcover.report.history.line', 'pcover_id', string="Remisiones")
    cover_type = fields.Selection([('in', 'Entrada'),('out', 'Salida')], string="Tipo de portada")
    
    is_critical = fields.Boolean(string="Embarque crítico")
    retrab_transpa_descr = fields.Char(string="Flejes", help="Detalle flejes")
    tarimas_m2l_descr = fields.Char(string="Tarimas M2L", help="Detalles de tarimas M2L")
    out_date = fields.Datetime(string="Entrega estimada", required=True)

    def generate_pdf(self):
        # report = self.env.ref('account.account_invoices')._render_qweb_pdf(self.account_move.ids[0])

        lines = []
        for line in self.line_ids:
            lines.append({
                'remision_id': line.remision_id.name,
            })
        if len(lines)<1:
            raise UserError("Necesitas agregar lineas para generar la portada")

        user_tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
        date_out = pytz.utc.localize(self.out_date).astimezone(user_tz)
        createdate = pytz.utc.localize(self.create_date).astimezone(user_tz)

        data = {
            'name': self.name,
            'createdate': createdate.strftime('%d/%m/%Y %I:%M %p'),
            'carrier': self.carrier_name,
            'box_name': self.vehicle_tag_id.vehicle_name,
            'bl': self.remition_qty,
            'driver': self.hr_driver_name,
            'vehicle_tag': self.vehicle_tag_name,
            'destination': self.dest_location_id.display_name,
            'supervisor': self.supervisor_id.name.upper(),
            'is_critical': 'Si' if self.is_critical else 'No',
            'retrab_transpa_descr': self.retrab_transpa_descr,
            'tarimas_m2l_descr': self.tarimas_m2l_descr,
            'out_date': date_out.strftime('%d/%m/%Y %I:%M %p'),
            'cover_type': self.cover_type,
            'lines': lines
        }
        report_action = self.env.ref('m2l_inventory_reports.report_pcover_pdf').report_action(self.ids, data=data)
        report_action.update({
            'close_on_report_download': True,
        })
        return report_action

    @api.onchange('line_ids')
    def m2lcount_lines(self):
        self.remition_qty = len(self.line_ids)


class PcoverReportHistoryLine(models.Model):
    _name = "pcover.report.history.line"

    pcover_id = fields.Many2one('pcover.report.history', string="Portada")
    remision_id = fields.Many2one('stock.picking', string="Remision")
