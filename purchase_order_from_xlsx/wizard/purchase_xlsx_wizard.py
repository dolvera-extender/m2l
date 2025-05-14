# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import pandas as pd
from io import BytesIO


class PurchaseXlsxWizardModel(models.TransientModel):
    _name = 'purchase.xlsx.wizard'
    _description = 'Creación de compra desde Excel'

    excel_file = fields.Binary(string='Archivo Excel', required=True)
    excel_file_name = fields.Char(string='Nombre del archivo')
    partner_id = fields.Many2one('res.partner', string="Proveedor", required=True)
    asn = fields.Char('ASN')
    no_factura = fields.Char('No. Factura')
    preview_html = fields.Html(string="Vista previa de líneas", readonly=True)
    xlsx_validated = fields.Boolean(string="Excel Válido", default=False)

    @api.onchange('excel_file')
    def action_validate_file(self):
        """Validar archivo con pandas y mostrar preview."""
        self.ensure_one()

        if not self.excel_file:
            return

        if not self.excel_file_name.lower().endswith('.xlsx'):
            raise ValidationError("El archivo debe tener extensión .xlsx")

        try:
            file_data = base64.b64decode(self.excel_file)
            df = pd.read_excel(BytesIO(file_data), engine='openpyxl')
        except Exception as e:
            raise ValidationError(f"Error al leer el archivo Excel: {str(e)}")

        expected_columns = ['pallet','numero de articulo ','Nombre del producto', 'Cantidad', 'UM']
        for col in expected_columns:
            if col not in df.columns:
                raise ValidationError(f"Falta la columna obligatoria: '{col}'")

        df.fillna('', inplace=True)
        df['pallet'] = df['pallet'].replace('', pd.NA).fillna(method='ffill')
        product_model = self.env['product.product']
        uom_model = self.env['uom.uom']

        table_html = ["""
            <table border="1" style="border-collapse: collapse; width: 100%;">
              <tr>
                <th style="padding:4px;">Línea</th>
                <th style="padding:4px;">Pallet</th>
                <th style="padding:4px;">Lote</th>
                <th style="padding:4px;">Producto</th>
                <th style="padding:4px;">Cantidad</th>
                <th style="padding:4px;">Unidad de Medida</th>
                <th style="padding:4px;">Unidad de Medida Odoo</th>
                <th style="padding:4px;">Estado</th>
              </tr>
        """]

        all_valid = True
        for index, row in df.iterrows():
            pallet = str(row['pallet']).strip()
            line_num = index + 2  # porque la fila 1 es encabezado
            product_name = str(row['numero de articulo ']).strip()
            qty = row['Cantidad']
            uom_name = str(row['UM']).strip()
            lote = str(row['Lote Serie']).strip()

            estado = "OK"
            uom_name_odoo = ''
            if not product_name or pd.isna(qty):
                estado = "Datos incompletos"
                all_valid = False
            else:
                product = product_model.search([('name', '=ilike', product_name)], limit=1)
                if not product:
                    estado = "Producto no encontrado"
                    all_valid = False
                else:
                    uom_name_odoo = product.uom_po_id.name


            table_html.append(f"""
              <tr>
                <td style="padding:4px;">{line_num}</td>
                <td style="padding:4px;">{pallet}</td>
                <td style="padding:4px;">{lote}</td>
                <td style="padding:4px;">{product_name}</td>
                <td style="padding:4px;">{qty}</td>
                <td style="padding:4px;">{uom_name}</td>
                <td style="padding:4px;">{uom_name_odoo}</td>
                <td style="padding:4px;">{estado}</td>
              </tr>
            """)

        table_html.append("</table>")
        self.preview_html = "".join(table_html)
        self.xlsx_validated = all_valid

        if not all_valid:
            message = ("Existen errores en el archivo Excel, "
                       "por favor revise la vista previa antes de confirmar.")
        else:
            message = "Archivo validado correctamente."

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validación de Excel',
                'message': message,
                'sticky': False,
            }
        }

    def int_to_letter(self,n):
        """Convierte 1 -> A, 2 -> B, ..., 27 -> AA, etc."""
        result = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            result = chr(65 + remainder) + result
        return result

    def action_create_purchase(self):
        """Crear la orden de compra desde el Excel ya validado."""
        self.ensure_one()

        if not self.xlsx_validated:
            raise ValidationError("Debe validar el archivo antes de confirmar.")

        try:
            file_data = base64.b64decode(self.excel_file)
            df = pd.read_excel(BytesIO(file_data), engine='openpyxl')
        except Exception as e:
            raise ValidationError(f"Error al leer el archivo: {str(e)}")

        df.fillna('', inplace=True)
        df['pallet'] = df['pallet'].replace('', pd.NA).fillna(method='ffill')
        expected_columns = ['pallet','numero de articulo ','Nombre del producto', 'Cantidad', 'UM','Lote Serie']
        for col in expected_columns:
            if col not in df.columns:
                raise ValidationError(f"Falta la columna obligatoria: '{col}'")

        order_lines_by_package = {}
        errores = []

        product_model = self.env['product.product']
        uom_model = self.env['uom.uom']

        purchase = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
        })
        product_seller_ids = self.env['product.supplierinfo'].search([('partner_id', '=', self.partner_id.id)])
        for index, row in df.iterrows():
            line_num = index + 2
            pallet_name = str(row['pallet']).strip()
            lote = str(row['Lote Serie']).strip()
            product_name = str(row['numero de articulo ']).strip()
            qty = row['Cantidad']
            uom_name = str(row['UM']).strip()
            peso_por_pallet = str(0)

            if not product_name or pd.isna(qty):
                errores.append(f"Línea {line_num}: Datos incompletos.")
                continue

            product = product_model.search([('name', '=ilike', product_name)], limit=1)
            if not product:
                errores.append(f"Línea {line_num}: Producto '{product_name}' no encontrado.")
                continue

            supplier_price = product_seller_ids.filtered_domain([('product_id', '=', product.id)])
            price_unit = product.standard_price
            if supplier_price:
                price_unit = supplier_price.price

            data ={
                'product_id': product.id,
                'name': product.name,
                'product_qty': qty,
                'product_uom': product.uom_po_id.id,
                'price_unit': price_unit,
                'order_id': purchase.id,
                'x_studio_asn':self.asn,
                "x_studio_no_factura":self.no_factura,
            }
            if line_num not in order_lines_by_package:
                order_lines_by_package[line_num] = {}
            order_lines_by_package[line_num]['data'] = data
            order_lines_by_package[line_num]['pallet'] = pallet_name
            order_lines_by_package[line_num]['lote'] = lote
            order_lines_by_package[line_num]['peso_por_pallet'] = peso_por_pallet

        if errores:
            raise ValidationError("Errores detectados:\n" + "\n".join(errores))

        if not order_lines_by_package:
            raise ValidationError("No hay líneas válidas para crear la orden.")

        purchase_line_by_pallet = {}
        for line_num, datas in order_lines_by_package.items():
            data_create = order_lines_by_package[line_num]['data']
            pallet_name = order_lines_by_package[line_num]['pallet']
            peso_por_pallet = order_lines_by_package[line_num]['peso_por_pallet']
            lote = order_lines_by_package[line_num]['lote']

            line_id = self.env['purchase.order.line'].create(data_create)
            if pallet_name not in purchase_line_by_pallet:
                purchase_line_by_pallet[pallet_name] = []
            purchase_line_by_pallet[pallet_name].append({
                'line_id':line_id,
                'peso_por_pallet':peso_por_pallet,
                'lote':lote,
            })

        purchase.button_confirm()

        for pallet_name, array_lines in purchase_line_by_pallet.items():
            for i, line in enumerate(array_lines):
                line_id = line['line_id']
                peso_por_pallet = line['peso_por_pallet']
                lote = line['lote']
                letra = self.int_to_letter(i + 1)  # empieza desde A
                pallet_name_new = f"{pallet_name}"


                for stock_move in line_id.move_ids:
                    package_id = self.env['stock.quant.package'].search(
                        [('name', '=', pallet_name_new), ('location_id', '=',stock_move.location_id.id)], limit=1)
                    if not package_id:
                        package_id = self.env['stock.quant.package'].create({
                            'location_id': stock_move.location_dest_id.id,
                            'name': pallet_name_new,
                            'shipping_weight': 0
                        })
                    package_id.shipping_weight +=float(peso_por_pallet)

                    stock_move.write({
                        'move_line_ids':[
                            (6,0,[]),
                            (0,0,{
                                'location_dest_id':stock_move.location_dest_id.id,
                                'product_id':stock_move.product_id.id,
                                'location_id':stock_move.location_id.id,
                                'result_package_id':package_id.id,
                                'quantity':stock_move.product_uom_qty,
                                'product_uom_id':stock_move.product_id.uom_po_id.id,
                                'picking_id':stock_move.picking_id.id,
                                'lot_name':lote,
                            })
                        ]
                    })




        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': purchase.id,
            'view_mode': 'form',
            'target': 'current',
        }
