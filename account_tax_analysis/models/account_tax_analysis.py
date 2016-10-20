# -*- coding: utf-8 -*-
# Author: Damien Crier
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api

import logging

_logger = logging.getLogger(__name__)

class AccountTaxDeclarationAnalysis(models.Model):
    _name = 'account.vat.declaration.analysis'
    _description = 'Account Vat Declaration Analysis'



    @api.multi
    def recompute(self):
        return True
        
       
    @api.multi
    def button_done(self):
        return 
        
    date = fields.Date("Analysis Date", required=True)
    name = fields.Char("Name", required=True)
    
    date_range_list = fields.Many2many(
        comodel_name='date.range',
        column1='tax_analysis_id',
        column2='date_range_id',
        string='Periods',
        help="If no period is selected, all the periods of the "
             "fiscal year will be used",
        required=True
    )

    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], required=True, default='draft')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', 
                                required=True, store=True)
    
    sale_vat_lines = fields.One2many(comodel_name='account.vat.declaration.line',
                                    inverse_name='analysis_id',
                                    string='Sale Taxes',
                                    domain=[('type_tax_use', '=', 'sale'),
                                    ('line_type', '=', 'tax')
                                    ])

    purchase_vat_lines = fields.One2many(comodel_name='account.vat.declaration.line',
                                    inverse_name='analysis_id',
                                    string='Purchase Taxes',
                                    domain=[('type_tax_use', '=', 'purchase'),
                                    ('line_type', '=', 'tax')])
                                    
    other_vat_lines = fields.One2many(comodel_name='account.vat.declaration.line',
                                    inverse_name='analysis_id',
                                    string='Other Taxes',
                                    domain=[('type_tax_use', '=', 'none'),
                                    ('line_type', '=', 'tax')])


    base_sale_vat_lines = fields.One2many(comodel_name='account.vat.declaration.line',
                                    inverse_name='analysis_id',
                                    string='Sale Taxes',
                                    domain=[('type_tax_use', '=', 'sale'),
                                    ('line_type', '=', 'base')])

    base_purchase_vat_lines = fields.One2many(comodel_name='account.vat.declaration.line',
                                    inverse_name='analysis_id',
                                    string='Purchase Taxes',
                                    domain=[('type_tax_use', '=', 'purchase'),
                                    ('line_type', '=', 'base')])
                                    
    base_other_vat_lines = fields.One2many(comodel_name='account.vat.declaration.line',
                                    inverse_name='analysis_id',
                                    string='Other Taxes',
                                    domain=[('type_tax_use', '=', 'none'),
                                    ('line_type', '=', 'base')])
    @api.multi
    def get_domain(self):
        self.ensure_one()
        periods = self.date_range_list
        domain = []
            
        i = 0
        while i <= len(periods) -1:
            _logger.debug("ITERATE i : %s AND len %s" % (i, len(periods)))
            if (i == 0 and len(periods) > 1) or i != len(periods) -1 :
                domain.append('|')
            domain.append('&')
            domain.append(periods[i].get_domain('date')[0])
            domain.append(periods[i].get_domain('date')[1])
            i += 1
        _logger.debug("DOMAIN %s" % domain)
        return domain

    @api.multi
    def add_tax_line(self, tax_id):
        self.ensure_one()
        #ADD Values for taxes
        vals_for_tax = {
            'analysis_id': self.id,
            'tax_id' : tax_id.id,
            'line_type': 'tax'            
        }        
        self.env['account.vat.declaration.line'].create(vals_for_tax)
        
        vals_for_tax.update({'line_type': 'base'})
        self.env['account.vat.declaration.line'].create(vals_for_tax)

class AccountTaxDeclarationLine(models.Model):
    _name = 'account.vat.declaration.line'
    _description = 'Account Vat Declaration Line'
    
    
    
    @api.multi
    def _get_line_ids(self):
        self.ensure_one()
        ids = []
        
        if not self.id:
            return
        date_domain = self.analysis_id.get_domain()
        
        move_lines = self.env['account.move.line'].search(date_domain)
        ids = [x.id for x in move_lines]
        
        
        sql_query = """select distinct li.id
                        FROM account_move_line AS li
                        INNER JOIN account_move AS mv ON li.move_id = mv.id
                        WHERE mv.state = 'posted'
                        AND li.id IN %s 
                        """
        if self.line_type == 'tax' :
            sql_query = "%s %s" % (sql_query, """ AND li.tax_line_id = %s """)
            
        else:
            sql_query = "%s %s" % (sql_query, " AND li.tax_line_id IS NULL ")
            sql_query = "%s %s" % (sql_query, """ AND li.id IN (
                                    SELECT account_move_line_id
                                    FROM account_move_line_account_tax_rel
                                    WHERE account_tax_id = %s                                                                        
                                    ) """)
#            self.env.cr.execute(sql_query, [tuple(ids, ), ])
        self.env.cr.execute(sql_query, [tuple(ids, ), self.tax_id.id])
        ids = [line.get('id') for line in self.env.cr.dictfetchall()]
        
        _logger.debug("IDS %s" % ids)
        return ids
        
        
    
    @api.multi
    @api.depends('tax_id')
    def _compute_balance(self):
        
        for line in self:
            debit , credit , balance = (0.0, )* 3

            if not line.id :
                return
            if len(line._get_line_ids()) == 0 : continue
            sql_query = """select sum(credit)::decimal(16,2) AS credit, 
                            sum(debit)::decimal(16,2) AS debit
                            FROM account_move_line AS li
                            WHERE li.id IN %s 
                            """       

            self.env.cr.execute(sql_query, [tuple(line._get_line_ids(), ), ])

            result = self.env.cr.dictfetchall()

            debit = result[0]['debit']
            credit = result[0]['credit']
            balance = debit - credit

            line.debit = debit
            line.credit = credit
            line.balance = balance
        
#        return 0.0
    
    line_type = fields.Selection([('tax', 'Taxes'), ('base', 'Tax Basis')], required=True, default='tax')
    tax_id = fields.Many2one(comodel_name='account.tax', required=True)
    account_id = fields.Many2one(comodel_name='account.account', related="tax_id.account_id")
    type_tax_use = fields.Selection([('sale', 'Sales'), ('purchase', 'Purchases'), ('none', 'None')]
                        , string='Tax Scope', required=True, default="sale",
                        related="tax_id.type_tax_use")         
    analysis_id = fields.Many2one(comodel_name='account.vat.declaration.analysis', string='Analysis')
    
    company_id = fields.Many2one(comodel_name='res.company', related='tax_id.company_id', string='Company', store=True)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True,
        help='Utility field to express amount currency', store=True)
    debit = fields.Monetary(compute='_compute_balance', currency_field='company_currency_id')
    credit = fields.Monetary(compute='_compute_balance', currency_field='company_currency_id')
    balance = fields.Monetary(compute='_compute_balance', currency_field='company_currency_id', default=0.0, help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
    
    
    @api.multi
    def open_lines(self):
        self.ensure_one()
        
        action = self.env.ref('account_tax_analysis.action_view_tax_wizard')
        action_fields = action.read()[0]
        action_fields['domain'] = [('id', 'in', self._get_line_ids())]
        _logger.debug("ACTION FIELDS %s" % action_fields)
        return action_fields
