# -*- coding: utf-8 -*-

from datetime import datetime, time, timedelta
from collections import defaultdict

from odoo import api, models
from odoo.fields import Datetime


import logging
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class HrAttendanceInherit(models.Model):
    _inherit = 'hr.attendance'

    def _create_work_entries(self):
        # Upon creating or closing an attendance, create the work entry directly if the attendance
        # was created within an already generated period
        # This code assumes that attendances are not created/written in big batches
        work_entries_vals_list = []
        for attendance in self:
            # Filter closed attendances
            if not attendance.check_out:
                continue
            contracts = attendance.employee_id.sudo()._get_contracts(
                attendance.check_in, attendance.check_out, states=['open', 'close'])
            for contract in contracts:
                if attendance.check_out and attendance.check_in and attendance.check_out >= contract.date_generated_from and attendance.check_in <= contract.date_generated_to:
                    start_stamp, start_date = attendance.check_in, attendance.check_in.date()
                    end_stamp, end_date = attendance.check_out, attendance.check_out.date()

                    if start_date == end_date:
                        day_bounds = datetime.combine(start_date, time.min), datetime.combine(start_date, time.max)
                        work_entries_vals_list += contract._get_work_entries_values(*day_bounds)
                    else:
                        work_entries_vals_list += contract._get_work_entries_values(start_stamp, datetime.combine(start_date, time.max))
                        date_cursor = start_date + timedelta(days=1)
                        while date_cursor < end_date:
                            bounds = datetime.combine(date_cursor, time.min), datetime.combine(date_cursor, time.max)
                            work_entries_vals_list += contract._get_work_entries_values(*bounds)
                            date_cursor += timedelta(days=1)
                        work_entries_vals_list += contract._get_work_entries_values(datetime.combine(end_date, time.min), end_stamp)

        if work_entries_vals_list:
            new_work_entries = self.env['hr.work.entry'].sudo().create(work_entries_vals_list)
            if new_work_entries:
                # Fetch overlapping work entries, grouped by employees
                start = min((datetime.combine(a.check_in, time.min) for a in self if a.check_in), default=False)
                stop = max((datetime.combine(a.check_out, time.max) for a in self if a.check_out), default=False)
                work_entry_groups = self.env['hr.work.entry'].sudo()._read_group([
                    ('date_start', '<', stop),
                    ('date_stop', '>', start),
                    ('employee_id', 'in', self.employee_id.ids),
                ], ['employee_id'], ['id:recordset'])
                work_entries_by_employee = {
                    employee.id: records
                    for employee, records in work_entry_groups
                }

                # Archive work entries included in new work entries
                included = self.env['hr.work.entry']
                overlappping = self.env['hr.work.entry']
                for work_entries in work_entries_by_employee.values():
                    # Work entries for this employee
                    new_employee_work_entries = work_entries & new_work_entries
                    previous_employee_work_entries = work_entries - new_work_entries

                    # Build intervals from work entries
                    attendance_intervals = new_employee_work_entries._to_intervals()
                    conflicts_intervals = previous_employee_work_entries._to_intervals()

                    # Compute intervals completely outside any attendance
                    # Intervals are outside, but associated records are overlapping.
                    outside_intervals = conflicts_intervals - attendance_intervals

                    overlappping |= self.env['hr.work.entry']._from_intervals(outside_intervals)
                    included |= previous_employee_work_entries - overlappping
                overlappping.sudo().write({'attendance_id': False})
                included.sudo().write({'active': False})