from odoo import fields, models, api, _
from odoo.addons.test_convert.tests.test_env import record
from odoo.exceptions import ValidationError
from ..tools.sequence_number import generate_sequence_number


class InsurancePolicy(models.Model):
    _name = 'insurance.policy'
    _description = 'Insurance Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(default='New', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Insured', help='Search account to relate the policy',
                                 tracking=True)
    policy_number = fields.Text(string='Policy', tracking=True)
    status = fields.Selection([('draft', 'Draft'),
                               ('active', 'Active'),
                               ('laps', 'Lapsed'),
                               ('cancel', 'Cancelled')],
                              default='draft', string='Policy Status', tracking=True)
    effective_date = fields.Date(string='Effective Date', help='Start date for the current active period',
                                 tracking=True)
    expiry_date = fields.Date(string='Expiry Date', help='Expiry date of the current active period', tracking=True)
    cancellation_date = fields.Date(string='Cancellation Date',
                                    help='if the policy is cancelled before the expiry date, enter here', tracking=True)
    notes = fields.Text(string='Underwriting Notes', help='Add into notes section on broker slip', tracking=True)
    # Todo: Needs to change the field type (M2o)
    insurer = fields.Selection([('A', 'A'), ('B', 'B'), ('C', 'C')], tracking=True)
    insurer_id = fields.Many2one('res.partner', domain=[('is_insurer', '=', True)], tracking=True,
                                 string='Insurer Name')
    # Todo: Need to be change in the reference and field types
    ppn_1 = fields.Integer(string='PPN1')
    commission_1 = fields.Integer(string='Commission 1',
                                  help='Auto populated from reference table.')

    ppn_2 = fields.Integer(string='PPN2')
    commission_2 = fields.Integer(string='Commission 2',
                                  help='Auto populated from reference table.')
    ppn_3 = fields.Integer(string='PPN3')
    commission_3 = fields.Integer(string='Commission 3',
                                  help='Auto populated from reference table.')
    policy_number_alias = fields.Char(string='Policy Number Alias',
                                      help='Change the Alias when guardian policy number change', tracking=True)
    # Todo: needs to be add the domain
    policy_id = fields.Many2one('insurance.policy', string='Master Policy',
                                help='Links and establishes hierarchy.', tracking=True)
    commission_ids = fields.One2many('policy.commission.line', 'commission_line_id')
    count = fields.Integer(string="Count", help="Number of commission lines.")
    final_count = fields.Integer(string="Final Count")
    risk_ids = fields.One2many('risk.history', 'insurance_policy_id', string='Risk History',
                               compute='_compute_history_ids')
    transaction_ids = fields.One2many('insurance.transaction', 'insurance_policy_id',
                                      string='Insurance Transactions',
                                      compute='_compute_insurance_transaction_ids')
    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', domain="[('active', '=', True)]",
                                  related='company_id.currency_id')
    risk_type = fields.Many2one('risk.type', string='Policy Type')
    policy_deduction_id = fields.Many2one('policy.deduction', string='Deductibles')
    deductive_note = fields.Html('Deductive Notes')
    policy_extension_id = fields.Many2one('policy.extension', string='Extension')
    extension_note = fields.Html('Extension Notes')
    reason_note = fields.Text('Reason', tracking=True)

    @api.onchange('risk_type')
    def get_policy_extension_type(self):
        """
        =====================================================
        *Get Policy Deduction ID of Related Records. And Policy Extension ID of related Records*
        =====================================================
        """
        for rec in self:
            rec.policy_extension_id = self.env['policy.extension'].search([('risk_type_id', '=', self.risk_type.id)])
            rec.extension_note = rec.policy_extension_id.risk_description
            rec.policy_deduction_id = self.env['policy.deduction'].search([('risk_type_id', '=', self.risk_type.id)])
            rec.deductive_note = rec.policy_deduction_id.risk_description

    """
        **=================================================**
        ** Generate new sequence number on create function **
        **      According To Their Specific Companies      **
        **=================================================**
    """

    @api.model_create_multi
    def create(self, vals):
        # if self.env.company.name == 'Nautica Insurance Brokers Ltd.':
        #         vals[0]['name'] = generate_sequence_number(self=self, code=
        #         'insurance.policy.nautica.insurance.brokers.limited.company')
        # elif self.env.company.name == 'Farah Insurance Brokers Ltd.':
        #         vals[0]['name'] = generate_sequence_number(self=self, code=
        #         'insurance.policy.farah.insurance.brokers.company')
        # elif self.env.company.name == 'Comprehensive Insurance Brokers Ltd.':
        #         vals[0]['name'] = generate_sequence_number(self=self, code=
        #         'insurance.policy.comprehensive.insurance.brokers.company')
        # else:
        #         vals[0]['name'] = generate_sequence_number(self=self,
        #                                                    code='insurance.policy.insurance.broker.group.company')
        if 'commission_ids' in vals[0]:
            self.create_policy_commission_line(values=vals)
        result = super(InsurancePolicy, self).create(vals)
        return result

    """
       **========================================================================================================**
       ** Create the count and SR No fields of policy commission lines based on the lead insurer and co-insurers **
       **========================================================================================================**
    """

    def create_policy_commission_line(self, values):
        for rec in range(1, 12):
            sequence_name = 'Insurer Details'
            code = "policy.commission.line"
            sequence_obj = self.env['ir.sequence'].search([('code', '=', code)]).ids
            referral_sequence = self.env['ir.sequence'].browse(sequence_obj)
            values[0]['commission_ids'].append((0, 0, {
                'sr_no': f'Lead Insurer{rec}'
            }))

    """
       **=================================================**
       ** Generate new sequence number on create function **
       **=================================================**
    """

    def write(self, vals):
        if self._context.get('skip_name_update'):
            return super(InsurancePolicy, self).write(vals)
        result = super(InsurancePolicy, self).write(vals)
        if not self.commission_ids:
            return result
        first_commission_line = self.commission_ids[0]
        policy_number = first_commission_line.police_number
        if policy_number and self.name != policy_number:
            self.with_context(skip_name_update=True).write({'name': policy_number})

        return result


    def policy_activate(self):
        self.status = 'active'

    def set_to_draft(self):
        self.status = 'draft'

    def policy_cancel(self):
        """
        =====================================================
        *Cancel the policy and give them reason*
        =====================================================
        """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'insurance.policy.wizard',
            'name': 'Cancellation Reason',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': {
                'default_policy_id': self.id,
            },
        }

    def policy_lapsed(self):
        self.status = 'laps'

    def get_new_risk(self):
        """
        =====================================================
        *Open a new risk policy form with default values set from the current insurance policy.*
        =====================================================
        """

        if not self.commission_ids[0].insurer_id:
            raise ValidationError(_("Please Select An Insurer"))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'risk.policy',
            'views': [(False, 'form')],
            'view_id': False,
            'name': 'Risk Policy',
            'target': 'new',
            'context': {
                'default_origin': self.name,
                'default_partner_id': self.partner_id.id,
                'default_policy_number': self.id,
                'default_risk_type_id': self.risk_type.id,
                'default_insurer_id': self.commission_ids[0].insurer_id.id,
                'create_history': True,
                'default_insurance_policy_id': self.id,
            },
        }

    @api.depends('partner_id', 'policy_number')
    def _compute_history_ids(self):
        """
        =====================================================
        *Compute and update the risk history IDs based on the partner ID and policy number*
        =====================================================
        """
        for record in self:
            record.risk_ids = self.env['risk.history'].search([('origin', '=', record.name)])

    def create_insurer_transaction_(self):
        """
        =====================================================
        *Open a new insurance transaction form with default values set from the current insurance policy.*
        =====================================================
        """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'insurance.transaction',
            'views': [(False, 'form')],
            'name': 'Insurance Transaction',
            'view_id': False,
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_currency_id': self.currency_id.id,
                'default_policy_number': self.policy_number,
                'default_insurance_policy_id': self.id,
            },
        }

    @api.depends('partner_id', 'policy_number')
    def _compute_insurance_transaction_ids(self):
        """
        =====================================================
        *Compute and update the Insurance Transaction IDs based on the partner ID and policy number*
        =====================================================
        """
        for record in self:
            record.transaction_ids = self.env['insurance.transaction'].search(
                [('insurance_policy_id', '=', record.id)])

    def copy(self, default=None):
        """
        =====================================================
        * Duplicate Record and
        --> Change the Status to Draft
        --> Move the risk history to new duplicated record and remove from original/previous policy*
        =====================================================
        """
        new_policy = super(InsurancePolicy, self).copy()
        new_policy.status = 'draft'
        for risk_history in self.history_ids:
            risk_history.write({
                'insurance_policy_id': new_policy.id,
                'origin': new_policy.name})
        return new_policy

    """
       *=====================================*
       * View Partner Insurance Policy Form *
       *=====================================*
    """

    def view_insurance_policy(self):
        """
            return:Current Insurance Policy Form View
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Insurance Partner',
            'res_model': 'insurance.policy',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
