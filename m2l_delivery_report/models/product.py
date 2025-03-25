# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
_log = logging.getLogger("___name: %s" % __name__)
import re


class ProductDr(models.Model):
    _inherit = "product.product"

    def get_product_head_text(self):
        text = re.compile('<.*?>')
        pretext = "[%s] %s" % (self.categ_id.name, re.sub(text, '', self.description or " "))
        finaltext = pretext.replace("&nbsp;", "")
        return finaltext