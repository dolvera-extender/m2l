# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
import logging

_log = logging.getLogger(__name__)


class PackagesAuditWizard(models.TransientModel):
    _name = "ia.packages.audit.wizard"
    _description = "Leer paquetes a auditar"

    package_name_read = fields.Char(string="Paquete")
    