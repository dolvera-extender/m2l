# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
_log = logging.getLogger("\n VEHICLE =====[%s]===" % __name__)


class L10Vehicle(models.Model):
    _inherit = "l10n_mx_edi.vehicle"

    vehicle_name = fields.Char(string="Nombre de vehículo")