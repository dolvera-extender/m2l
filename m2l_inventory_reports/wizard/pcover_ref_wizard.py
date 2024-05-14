# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
import logging

_log = logging.getLogger(__name__)


class PcoverReportWizard(models.TransientModel):
    _name = "pcover.report.wizard"
    _description = "Generador de etiquetas cover para transpasos"

    carrier_id = fields.Many2one('res.partner', string="Transportista")
    carrier_name = fields.Char(string="Transportista")
    carrier_manual = fields.Boolean(string="Manual", default=False)
    
    hr_driver_id = fields.Many2one('hr.employee', string="Chofer")
    hr_driver_name = fields.Char(string="Chofer")
    hr_driver_manual = fields.Boolean(string="Entrada manual ", default=False)
    
    vehicle_tag_id = fields.Many2one('l10n_mx_edi.vehicle', string="Placas")
    vehicle_tag_name = fields.Char(string="Placas")
    vehicle_tag_manual = fields.Boolean(string="Entrada manual", default=False)
    
    remition_qty = fields.Integer(string="No. de bultos", compute="_compute_moves_qty", store=False)
    dest_location_id = fields.Many2one('res.partner', string="Destino", required=True)
    supervisor_id = fields.Many2one('hr.employee', string="Lider de Operaciones", required=True)
    montacarguista_id = fields.Many2one('hr.employee', string="Montacarguista")
    auditor_id = fields.Many2one('hr.employee', string="Auditor")

    is_critical = fields.Boolean(string="Embarque crítico")
    retrab_transpa_descr = fields.Char(string="Detalles RT", required=True)
    tarimas_m2l_descr = fields.Char(string="Detalles Tarimas M2L")
    out_date = fields.Datetime(string="Entrega estimada")
    cover_type = fields.Selection([('in', 'Entrada'), ('out', 'Salida')], string="Tipo de portada")
    observations = fields.Text(string="Observaciones")

    line_ids = fields.One2many('pcover.report.wizard.line', 'pcover_id', string="Remisiones")

    def process_pcover_report(self):
        cover_obj = self.env['pcover.report.history']
        last_cover = cover_obj.search([], order="folio asc")[-1:]
        last_folio = last_cover.folio + 1 if last_cover else 1

        lines = []
        for line in self.line_ids:
            lines.append((0, 0, {
                'remision_id': line.remision_id.id
            }))

        pcover_data = {
            'name': "%s-%s" % (self.cover_type.upper() ,str(last_folio).zfill(6)),
            'remition_qty': self.remition_qty,
            'cover_type': self.cover_type,
            'folio': last_folio,
            'line_ids': lines,
            'supervisor_id': self.supervisor_id.id,
            'is_critical': self.is_critical,
            'retrab_transpa_descr': self.retrab_transpa_descr,
            'tarimas_m2l_descr': self.tarimas_m2l_descr,
            'observations':  self.observations if self.observations else "",
        }
        if self.out_date:
            pcover_data['out_date'] = self.out_date

        if self.montacarguista_id:
            pcover_data['montacarguista_id'] = self.montacarguista_id.id
        
        if self.auditor_id:
            pcover_data['auditor_id'] = self.auditor_id.id

        if self.carrier_id:
            pcover_data['carrier_id'] = self.carrier_id.id
            pcover_data['carrier_name'] =  self.carrier_id.name
        elif self.carrier_name and self.carrier_manual:
            pcover_data['carrier_name'] = self.carrier_name
        
        if self.hr_driver_id:
            pcover_data['hr_driver_id'] = self.hr_driver_id.id
            pcover_data['hr_driver_name'] = self.hr_driver_id.name
        elif self.hr_driver_name and self.hr_driver_manual:
            pcover_data['hr_driver_name'] = self.hr_driver_name
        
        if self.vehicle_tag_id:
            pcover_data['vehicle_tag_id'] = self.vehicle_tag_id.id
            pcover_data['vehicle_tag_name'] = self.vehicle_tag_id.vehicle_licence
        elif self.vehicle_tag_name and self.vehicle_tag_manual:
            pcover_data['vehicle_tag_name'] = self.vehicle_tag_name

        if self.dest_location_id:
            pcover_data['dest_location_id'] = self.dest_location_id.id
        cover = cover_obj.create(pcover_data)
        return cover.generate_pdf()

    @api.onchange('line_ids')
    def _compute_moves_qty(self):
        for reg in self:
            qty = len(reg.line_ids.mapped('remision_id').mapped('move_line_ids_without_package'))
            reg.remition_qty = qty


class PcoverReportWizardLine(models.TransientModel):
    _name = "pcover.report.wizard.line"
    _description = "Lineas de reporte"

    @api.model
    def _domain_pickin_id(self):
        dom = [('state', 'in', ['assigned', 'done'])]
        if 'default_cover_type' in self._context:
            dom.append(('picking_type_id.type_cover', '=', self._context.get('default_cover_type')))
        return dom


    pcover_id = fields.Many2one('pcover.report.wizard', string="Portada")
    remision_id = fields.Many2one('stock.picking', string="Remision", domain=lambda self: self._domain_pickin_id(), required=True)

