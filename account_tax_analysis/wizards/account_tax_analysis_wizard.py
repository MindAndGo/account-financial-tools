# -*- coding: utf-8 -*-
# Author: Damien Crier
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api

import logging
import datetime

_logger = logging.getLogger(__name__)

class AccountTaxDeclarationAnalysis(models.TransientModel):
    _name = 'account.vat.declaration.wizard'
    _description = 'Account Vat Declaration wizard'

    date_range_type_id = fields.Many2one(
        comodel_name='date.range.type',
        string='Plage de date',
        help='Fiscalyear to look on',
        required=True,
    )

    date_range_list = fields.Many2many(
        comodel_name='date.range',
#        relation='account_tax_period_rel',
        column1='tax_analysis_id',
        column2='date_range_id',
        string='Periods',
        help="If no period is selected, all the periods of the "
             "fiscal year will be used",
    )
    
    tax_list = fields.Many2many(
        comodel_name='account.tax',
        string='Taxes',

    )

    @api.multi
    def show_vat_analysis(self):
        periods = self.date_range_list
        
        domain = []
        if not periods:
            periods = self.env['date.range'].search([('type_id', '=', self.date_range_type_id.id)])
            
        i = 0
        while i <= len(periods) -1:
            _logger.debug("ITERATE i : %s AND len %s" % (i, len(periods)))
            if i != len(periods) -1:
                domain.append(str('|'))
            domain.append(periods[i].get_domain('date'))
            i += 1
        
        declaration_id = self.env['account.vat.declaration.analysis'].create({
            'date_range_list':[(6,0, [periods.ids])],
            'name': 'Declaration - ' + datetime.datetime.now().strftime('%d-%m-%Y'),
            'date': datetime.datetime.now().strftime('%d-%m-%Y'),
            'company_id': self.env.user.company_id.id
        })
        for tax in self.tax_list:
            declaration_id.add_tax_line(tax)
        

        domain = [('id', '=', declaration_id.id)]
        _logger.debug("Domain %s" % domain)        
        action = self.env.ref('account_tax_analysis.action_view_tax_analysis')
        action_fields = action.read()[0]
        action_fields['domain'] = domain
        return action_fields
