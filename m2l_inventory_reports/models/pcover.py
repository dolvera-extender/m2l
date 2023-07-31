# -*- coding: utf-8 -*-

from odoo import api, fields, models
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
    carrier_id = fields.Many2one('res.partner', string="Transportista")
    # box_num_id= fields.Many2one('l10n_mx_edi.vehicle', string="No. de caja") # Es el año.
    remition_qty = fields.Integer(string="B/L")
    hr_driver_id = fields.Many2one('hr.employee', string="Chofer")
    supervisor_id = fields.Many2one('hr.employee', string="Supervisor")
    vehicle_tag_id = fields.Many2one('l10n_mx_edi.vehicle', string="Placas")
    dest_location_id = fields.Many2one('res.partner', string="Destino")
    line_ids = fields.One2many('pcover.report.history.line', 'pcover_id', string="Remisiones")

    def generate_pdf(self):
        _log.info("Generando PDF")
        # report = self.env.ref('account.account_invoices')._render_qweb_pdf(self.account_move.ids[0])
        lines = []
        for line in self.line_ids:
            lines.append({
                'remision_id': line.remision_id.name,
                'is_critical': 1 if line.is_critical else 0,
                'retrab_transpa': line.retrab_transpa,
                'retrab_transpa_descr': line.retrab_transpa_descr,
                'tarimas_m2l': line.tarimas_m2l,
                'tarimas_m2l_descr': line.tarimas_m2l_descr,
                'out_date': line.out_date.strftime('%d/%m/%Y'),
            })

        data = {
            'name': self.name,
            'createdate': self.create_date.strftime('%d/%m/%Y %I:%M %p'),
            'carrier': self.carrier_id.name,
            'box_name': self.vehicle_tag_id.vehicle_name,
            'bl': len(self.line_ids),
            'driver': self.hr_driver_id.name,
            'vehicle_tag': self.vehicle_tag_id.vehicle_licence,
            'destination': self.dest_location_id.display_name,
            'supervisor': self.supervisor_id.name.upper(),
            'lines': lines
        }
        report_action = self.env.ref('m2l_inventory_reports.report_pcover_pdf').report_action(self.ids, data=data)
        report_action.update({
            'close_on_report_download': True,
        })
        return report_action

    @api.onchange('line_ids')
    def m2lcount_lines(self):
        _log.info(" CONTANDO LINEAS ")
        self.remition_qty = len(self.line_ids)


class PcoverReportHistoryLine(models.Model):
    _name = "pcover.report.history.line"

    pcover_id = fields.Many2one('pcover.report.history', string="Portada")
    remision_id = fields.Many2one('stock.picking', string="Remision")
    is_critical = fields.Boolean(string="Embarque crítico", default=False)
    retrab_transpa = fields.Boolean(string="Retrabajos o Transpapeleos", default=False)
    retrab_transpa_descr = fields.Char(string="Detalles RT")
    tarimas_m2l = fields.Boolean(string="Tarimas M2L", default=False)
    tarimas_m2l_descr = fields.Char(string="Detalles Tarimas M2L")
    out_date = fields.Datetime(string="Entrega estimada")
