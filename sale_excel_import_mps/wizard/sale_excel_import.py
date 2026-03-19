import base64
import io
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import pandas as pd


class SaleExcelImport(models.TransientModel):
    _name = "sale.excel.import"
    _description = "Importar ventas desde Excel"

    file = fields.Binary(string="Archivo Excel")
    filename = fields.Char(string="Nombre del archivo")

    preview_html = fields.Html(string="Vista previa", readonly=True)
    xlsx_validated = fields.Boolean(default=False)

    parsed_data = fields.Text(string="Datos parseados")

    partner_id = fields.Many2one("res.partner", string="Cliente")
    user_id = fields.Many2one("res.users", string="Vendedor")
    client_order_ref = fields.Char(string="Ref Cliente")

    tag_ids = fields.Many2many(
        comodel_name='crm.tag',
        string="Tags"
    )

    def _clean_cell(self, value):
        if value is None:
            return ""
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return str(value)
        return str(value).strip()

    # =========================
    # PARSE
    # =========================
    @api.onchange("file", "filename")
    def action_parse(self):
        if not self.file:
            return

        if not self.filename or not self.filename.lower().endswith(".xlsx"):
            raise UserError(_("Solo se permiten archivos .xlsx"))

        df = pd.read_excel(
            io.BytesIO(base64.b64decode(self.file)),
            engine="openpyxl"
        )

        df.columns = [str(c).strip() for c in df.columns]
        df.fillna("", inplace=True)

        for col in ["Cliente", "Vendedor", "Linea/Producto", "Paquetes/Producto","Paquetes/Paquete"]:
            df[col] = df[col].apply(self._clean_cell)

        partner_names = set(df["Cliente"])
        user_names = set(df["Vendedor"])
        product_names = set(df["Linea/Producto"])
        package_names = set(df["Paquetes/Paquete"])

        partner_map = {p.name: p for p in self.env["res.partner"].search([("name", "in", list(partner_names))])}
        user_map = {u.name: u for u in self.env["res.users"].search([("name", "in", list(user_names))])}
        product_map = {p.name: p for p in self.env["product.product"].search(["|",("name", "in", list(product_names)),("default_code", "in", list(product_names))])}
        package_map = {p.name: p for p in self.env["stock.quant.package"].search([("name", "in", list(package_names))])}

        # TAGS
        tag_names = set()
        for val in df["Etiqueta"]:
            if val:
                tag_names.update([t.strip() for t in str(val).split(",") if t.strip()])

        existing_tags = self.env["crm.tag"].search([("name", "in", list(tag_names))])
        tag_map = {t.name: t for t in existing_tags}

        # =========================
        # ESTADOS
        # =========================
        last_partner = False
        last_user = False
        last_ref = ""
        last_tags = []

        header_partner = False
        header_user = False
        header_ref = ""
        header_tags = []

        sale_lines = []
        package_lines = []

        html_sale = []
        html_package = []

        error_count = 0
        all_valid = True

        for i, row in df.iterrows():
            excel_row = i + 2

            cliente_txt = row["Cliente"]
            vendedor_txt = row["Vendedor"]
            ref_txt = self._clean_cell(row["Ref Cliente"])
            tag_txt = self._clean_cell(row["Etiqueta"])

            producto_txt = row["Linea/Producto"]
            paquete_txt = row["Paquetes/Paquete"]
            product_paquete_txt = row["Paquetes/Producto"]

            # HERENCIAS
            if cliente_txt:
                partner = partner_map.get(cliente_txt)
                if partner:
                    last_partner = partner
            else:
                partner = last_partner

            if vendedor_txt:
                user = user_map.get(vendedor_txt)
                if user:
                    last_user = user
            else:
                user = last_user

            if ref_txt:
                last_ref = ref_txt
            else:
                ref_txt = last_ref

            if tag_txt:
                tag_list = [tag_map[t.strip()].id for t in tag_txt.split(",") if t.strip() in tag_map]
                last_tags = tag_list
            else:
                tag_list = last_tags

            # HEADER
            if not header_partner and partner:
                header_partner = partner
            if not header_user and user:
                header_user = user
            if not header_ref and ref_txt:
                header_ref = ref_txt
            if not header_tags and tag_list:
                header_tags = tag_list

            # =========================
            # LINEAS DE VENTA
            # =========================
            if producto_txt:
                errores = []
                product = product_map.get(producto_txt)

                if not product:
                    errores.append("Producto")

                has_error = bool(errores)
                if has_error:
                    error_count += 1
                    all_valid = False

                badge = "OK" if not has_error else f"Error: {', '.join(errores)}"

                html_sale.append(f"""
                <tr>
                    <td>{excel_row}</td>
                    <td>{producto_txt}</td>
                    <td>{row["Linea/Cantidad"]}</td>
                    <td>{row["Linea/Precio unitario"]}</td>
                    <td>{badge}</td>
                </tr>
                """)

                sale_lines.append({
                    "product_id": product.id if product else False,
                    "qty": float(row["Linea/Cantidad"] or 0),
                    "price": float(row["Linea/Precio unitario"] or 0),
                    "error": has_error
                })

            # =========================
            # PAQUETES
            # =========================
            if paquete_txt:
                errores = []

                package = package_map.get(paquete_txt)
                product = product_map.get(str(product_paquete_txt))

                if not package:
                    errores.append("Paquete")

                if not product:
                    errores.append("Producto")

                available_qty = 0.0

                # VALIDACIONES DE STOCK
                if package and product:
                    quants = self.env["stock.quant"].search([
                        ("package_id", "=", package.id),
                        ("product_id", "=", product.id),
                        ("quantity", ">", 0),
                    ])

                    if not quants:
                        errores.append("No está en el paquete")
                    else:
                        # calcular disponible real
                        available_qty = sum(q.quantity - q.reserved_quantity for q in quants)

                        if available_qty <= 0:
                            errores.append("Sin disponibilidad")

                has_error = bool(errores)

                if has_error:
                    error_count += 1
                    all_valid = False

                badge = "OK" if not has_error else f"Error: {', '.join(errores)}"

                html_package.append(f"""
                <tr>
                    <td>{excel_row}</td>
                    <td>{paquete_txt}</td>
                    <td>{product_paquete_txt}</td>
                    <td>{round(available_qty, 2)}</td>
                    <td>{badge}</td>
                </tr>
                """)

                package_lines.append({
                    "product_id": product.id if product else False,
                    "package_id": package.id if package else False,
                    "available_qty": available_qty,
                    "error": has_error
                })

        # =========================
        # HTML
        # =========================
        self.preview_html = f"""
        <div><b>Total errores:</b> {error_count}</div>

        <h4>Líneas de Venta</h4>
        <table class="table table-bordered">
            <tr><th>#</th><th>Producto</th><th>Cantidad</th><th>Precio</th><th>Estado</th></tr>
            {''.join(html_sale)}
        </table>

        <h4>Paquetes</h4>
        <table class="table table-bordered">
            <tr><th>#</th><th>Paquete</th><th>Producto</th><th>Cantidad Disponible</th><th>Estado</th></tr>
            {''.join(html_package)}
        </table>
        """

        self.xlsx_validated = all_valid
        self.parsed_data = json.dumps({
            "sale_lines": sale_lines,
            "package_lines": package_lines
        })

        if not self.partner_id:
            self.partner_id = header_partner.id if header_partner else False
        if not self.user_id:
            self.user_id = header_user.id if header_user else False
        if not self.client_order_ref:
            self.client_order_ref = header_ref
        if not self.tag_ids:
            self.tag_ids = [(6, 0, header_tags)]

    # =========================
    # CONFIRM
    # =========================
    def action_confirm(self):
        self.action_parse()
        if not self.xlsx_validated:
            raise UserError(_("Corrige errores antes de confirmar"))

        if not self.partner_id or not self.user_id:
            raise UserError(_("Cliente y vendedor son obligatorios"))

        data = json.loads(self.parsed_data or "{}")

        order = self.env["sale.order"].create({
            "partner_id": self.partner_id.id,
            "user_id": self.user_id.id,
            "client_order_ref": self.client_order_ref,
            "tag_ids": [(6, 0, self.tag_ids.ids)],
        })

        for line in data.get("sale_lines", []):
            self.env["sale.order.line"].create({
                "order_id": order.id,
                "product_id": line["product_id"],
                "product_uom_qty": line["qty"],
                "price_unit": line["price"],
            })

        for line in data.get("package_lines", []):
            if line["package_id"]:
                line = self.env["sale.mps"].create({
                    "sale_id_se": order.id,
                    "package_id": line["package_id"],
                    "product_id": line["product_id"],
                })
                #COMENTADO POR QUE ACTUALIZA TODAS LAS LINEAS DEL MISMO PRODUCTO
                #line.update_qty_selected()

        order.action_confirm()
        return {
            "type": "ir.actions.act_window",
            "name": _("Orden de venta"),
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": order.id,
            "target": "current",
        }

    def action_download_template(self):
        headers = [
            "Cliente",
            "Vendedor",
            "Ref Cliente",
            "Etiqueta",
            "Linea/Producto",
            "Linea/Cantidad",
            "Linea/Precio unitario",
            "Paquetes/Producto",
            "Paquetes/Paquete",
        ]

        df = pd.DataFrame(columns=headers)

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        file_data = base64.b64encode(buffer.read())

        attachment = self.env["ir.attachment"].create({
            "name": "plantilla_importacion_ventas.xlsx",
            "type": "binary",
            "datas": file_data,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }