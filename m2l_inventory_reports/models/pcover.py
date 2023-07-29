# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
_log = logging.getLogger("\n =====[%s]===" % __name__)


class PcoverReportHistory(models.Model):
    _name = "pcover.report.history"

    name = fields.Char(string="Filename")
    carrier_id = fields.Many2one('res.partner', string="Transportista")
    # box_num_id= fields.Many2one('l10n_mx_edi.vehicle', string="No. de caja") # Es el año.
    remition_qty = fields.Integer(string="B/L")
    hr_driver_id = fields.Many2one('hr.employee', string="Chofer")
    vehicle_tag_id = fields.Many2one('l10n_mx_edi.vehicle', string="Placas")
    dest_location_id = fields.Many2one('res.partner', string="Destino")
    line_ids = fields.One2many('pcover.report.history.line', 'pcover_id', string="Remisiones")

    def generate_pdf(self):
        _log.info("Generando PDF")
        # report = self.env.ref('account.account_invoices')._render_qweb_pdf(self.account_move.ids[0])
        data = {
            'location_ids': "location_ids_list.ids",
        }
        report_action = self.env.ref('m2l_inventory_reports.report_pcover_pdf').report_action([], data=data)
        report_action.update({
            'close_on_report_download': True
        })
        return report_action


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
