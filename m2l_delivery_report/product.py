# -*- coding: utf-8 -*-

from cgitb import reset
from odoo import models, fields, api
import logging
_log = logging.getLogger("___name: %s" % __name__)
import re


class ProductDr(models.Model):
    _inherit = "product.product"

    def get_product_head_text(self):
        # _log.info(" DIR DESCR:: %s " % dir(self.description))
        text = re.compile('<.*?>')
        return "[%s] %s" % (self.categ_id.name, re.sub(text, '', self.description))