# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
import logging

_log = logging.getLogger(__name__)


class PcoverReportWizard(models.TransientModel):
    _name = "pcover.report.wizard"
    _description = "Generador de etiquetas cover para transpasos"

    # name = fields.Char(string="Filename")
    carrier_id = fields.Many2one('res.partner', string="Transportista", required=True)
    # box_num_id = fields.Many2one('l10n_mx_edi.vehicle', string="No. de caja") # Es el año, en la placa
    remition_qty = fields.Integer(string="B/L", required=True)
    hr_driver_id = fields.Many2one('hr.employee', string="Chofer", required=True)
    vehicle_tag_id = fields.Many2one('l10n_mx_edi.vehicle', string="Placas", required=True)
    dest_location_id = fields.Many2one('res.partner', string="Destino", required=True)
    supervisor_id = fields.Many2one('hr.employee', string="Supervisor", required=True)


    line_ids = fields.One2many('pcover.report.wizard.line', 'pcover_id', string="Remisiones")

    def process_pcover_report(self):
        _log.info(" CREANDO REGISTRO EN HISTORIAL ")

        cover_obj = self.env['pcover.report.history']
        last_cover = cover_obj.search([], order="folio asc")[-1:]
        last_folio = last_cover.folio + 1 if last_cover else 1

        lines = []
        for line in self.line_ids:
            lines.append((0, 0, {
                'remision_id': line.remision_id.id,
                'is_critical': line.is_critical,
                'retrab_transpa': line.retrab_transpa,
                'retrab_transpa_descr': line.retrab_transpa_descr,
                'tarimas_m2l': line.tarimas_m2l,
                'tarimas_m2l_descr': line.tarimas_m2l_descr,
                'out_date': line.out_date,

            }))

        pcover_data = {
            'name': str(last_folio).zfill(6),
            'remition_qty': self.remition_qty,
            'folio': last_folio,
            'line_ids': lines,
            'supervisor_id': self.supervisor_id.id
        }

        if self.carrier_id:
            pcover_data['carrier_id'] = self.carrier_id.id
        if self.hr_driver_id:
            pcover_data['hr_driver_id'] = self.hr_driver_id.id
        if self.vehicle_tag_id:
            pcover_data['vehicle_tag_id'] = self.vehicle_tag_id.id
        if self.dest_location_id:
            pcover_data['dest_location_id'] = self.dest_location_id.id
        cover = cover_obj.create(pcover_data)
        return cover.generate_pdf()


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
    out_date = fields.Date(string="Entrega estimada", required=True)
