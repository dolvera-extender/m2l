# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
import logging

_log = logging.getLogger(__name__)


class PcoverReportWizard(models.TransientModel):
    _name = "pcover.report.wizard"
    _description = "Generador de etiquetas cover para transpasos"

    name = fields.Char(string="Filename")
    carrier_id = fields.Many2one('res.partner', string="Transportista")
    # box_num_id = fields.Many2one('l10n_mx_edi.vehicle', string="No. de caja") # Es el año, en la placa
    remition_qty = fields.Integer(string="B/L")
    hr_driver_id = fields.Many2one('hr.employee', string="Chofer")
    vehicle_tag_id = fields.Many2one('l10n_mx_edi.vehicle', string="Placas")
    dest_location_id = fields.Many2one('res.partner', string="Destino")

    line_ids = fields.One2many('pcover.report.wizard.line', 'pcover_id', string="Remisiones")

    def process_pcover_report(self):
        _log.info(" CREANDO REGISTRO EN HISTORIAL ")
        pcover_data = {
            'name': self.name or "",
            'remition_qty': self.remition_qty
        }
        if self.carrier_id:
            pcover_data['carrier_id'] = self.carrier_id.id
        if self.hr_driver_id:
            pcover_data['hr_driver_id'] = self.hr_driver_id.id
        if self.vehicle_tag_id:
            pcover_data['vehicle_tag_id'] = self.vehicle_tag_id.id
        if self.dest_location_id:
            pcover_data['dest_location_id'] = self.dest_location_id.id

        cover_obj = self.env['pcover.report.history'].create(pcover_data)
        return cover_obj.generate_pdf()


class PcoverReportWizardLine(models.TransientModel):
    _name = "pcover.report.wizard.line"
    _description = "Lineas de reporte"

    pcover_id = fields.Many2one('pcover.report.wizard', string="Portada")

    remision_id = fields.Many2one('stock.picking', string="Remision")
    is_critical = fields.Boolean(string="Embarque crítico", default=False)
    retrab_transpa = fields.Boolean(string="Retrabajos o Transpapeleos", default=False)
    retrab_transpa_descr = fields.Char(string="Detalles RT")
    tarimas_m2l = fields.Boolean(string="Tarimas M2L", default=False)
    tarimas_m2l_descr = fields.Char(string="Detalles Tarimas M2L")
    out_date = fields.Datetime(string="Entrega estimada")
