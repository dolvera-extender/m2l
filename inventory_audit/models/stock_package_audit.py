# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import UserError
import pytz
from datetime import timedelta
import logging

_log = logging.getLogger(__name__)


class StockPackageAudit(models.Model):
    _name = "stock.package.audit"
    _description = "Rectificación  de existencias."

    name = fields.Char(string="Nombre")
    location_id = fields.Many2one('stock.location', string="Ubicación")
    audit_date = fields.Datetime(string="Fecha revisión")
    picking_id = fields.Many2one('stock.picking')
    audit_line_ids = fields.One2many('stock.package.audit.line', 'package_audit_id', string="Paquetes")

    def generate_move(self):
        """
        Generate picking to correct package location objects. 
        """
        picking_type_id = self.env['stock.picking.type'].search([('barcode','=', "WH-INTERNAL")])
    
        _log.info(" TIPO DE OPERACION ::: %s " % picking_type_id)
        picking = self.env['stock.picking'].create({
            'location_id': self.location_id.location_id.id,
            'location_dest_id': self.location_id.location_id.id,
            'picking_type_id': picking_type_id.id,
        })

        for line in self.audit_line_ids.filtered(lambda l: l.location_id != False and l.moved == True):
            _log.info(" MOVIENDO LINEA %s " % line)
            # Movimiento por cada paquete
            package_lines = []
            for pline in line.package_id.quant_ids:
                # Una linea de movimiento por cada quant del paquete
                move_line_data = [(0,0,{
                    'product_id': pline.product_id.id,
                    'location_id': line.location_id.id,
                    'location_dest_id': line.location_id.id,
                    'package_id': line.package_id.id,
                    'result_package_id': line.package_id.id,
                    'lot_id': pline.lot_id.id,
                    'product_uom_qty': pline.quantity,
                    'product_uom_id': pline.product_uom_id.id
                })]
                move = self.env['stock.move'].create({
                    'name': 'product1_move',
                    'location_id': line.package_id.location_id.id,
                    'location_dest_id': self.location_id.id,
                    'picking_id': picking.id,
                    'product_id': pline.product_id.id,
                    'product_uom': pline.product_uom_id.id,
                    'product_uom_qty': sum(line.package_id.quant_ids.mapped('quantity')),
                    # 'move_line_ids': move_line_data
                })
        self.picking_id = picking.id
        picking.action_confirm()
        # picking.action_assign()
        # picking.button_validate()

        # Revisar la asignación de paquetes en las lineas de movimiento. 

    def generate_pdf_report(self):
        user_tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
        createdate = pytz.utc.localize(self.audit_date).astimezone(user_tz)
        lines = []
        for line in self.audit_line_ids:
            lines.append({
                'package_name': line.package_id.name,
                'location': line.location_id.name if line.moved else self.location_id.name,
                'moved': "Transferido" if line.moved else ""
            })
        data = {
            'name': self.name,
            'location_id': self.location_id.name,
            'audit_date': createdate.strftime('%d/%m/%Y %I:%M %p'),
            'lines':lines
        }
        _log.info(" DATOS PARA EL REPORTE :: %s" % data )
        report_action = self.env.ref('inventory_audit.report_inventory_audit_pdf').report_action(self, data=data)
        report_action.update({
            'close_on_report_download': True,
        })
        return report_action


class StockPackageAuditLine(models.Model):
    _name = "stock.package.audit.line"
    _description = "Rectificación  de existencias."

    package_audit_id = fields.Many2one('stock.package.audit', string="Auditoria")
    package_id = fields.Many2one('stock.quant.package', string="Paquete")
    location_id = fields.Many2one('stock.location', string="Ubicación en odoo")
    moved = fields.Boolean(string="Transferido", default=False)
