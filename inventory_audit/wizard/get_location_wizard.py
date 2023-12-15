# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
import logging

_log = logging.getLogger(__name__)


class GetLocationWizard(models.TransientModel):
    _name = "ia.get.location.wizard"
    _description = "Lee codigo de barras de la ubicación a auditar"

    location_name = fields.Char(string="Ubicación")

    
    api.onchange('location_name')
    def call_audit_wizard(self):
        _log.info(" lectura hecha .. %s" % self.location_name)