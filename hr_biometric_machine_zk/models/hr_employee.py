# -*- coding: utf-8 -*-

import pytz
import datetime
from .base import ZK

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import models, fields, api, exceptions, SUPERUSER_ID, _
from odoo.exceptions import UserError

import logging
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class hrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    def _compute_hours_last_month(self):
        """
        Compute hours in the current month, if we are the 15th of october, will compute hours from 1 oct to 15 oct
        """
        now = fields.Datetime.now()
        now_utc = pytz.utc.localize(now)
        for employee in self:
            tz = pytz.timezone(employee.tz or 'UTC')
            now_tz = now_utc.astimezone(tz)
            start_tz = now_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_naive = start_tz.astimezone(pytz.utc).replace(tzinfo=None)
            end_tz = now_tz
            end_naive = end_tz.astimezone(pytz.utc).replace(tzinfo=None)

            hours = sum(
                att.worked_hours or 0
                for att in employee.attendance_ids.filtered(
                    lambda att: att.check_in and att.check_in >= start_naive and att.check_out and att.check_out <= end_naive
                )
            )

            employee.hours_last_month = round(hours, 2)
            employee.hours_last_month_display = "%g" % employee.hours_last_month

class hrAttemdamceInherit(models.Model):
    _inherit = 'hr.attendance'

    def _compute_color(self):
        for attendance in self:
            if attendance.check_out:
                attendance.color = 1 if attendance.worked_hours > 16 else 0
            else:
                attendance.color = 1 if attendance.check_in and attendance.check_in < (datetime.today() - timedelta(days=1)) else 10

