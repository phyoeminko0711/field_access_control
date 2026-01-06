from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FieldAccessConfig(models.Model):
    _name = 'field.access.config'
    _description = 'Field Access Configuration'
    _order = 'sequence, id'

    name = fields.Char(string='Configuration Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    model_id = fields.Many2one('ir.model', string='Target Model', required=True,
                               domain=[('transient', '=', False)], ondelete='cascade',
                               help='The model to protect (e.g., product.template)')
    model_name = fields.Char(related='model_id.model', string='Model Technical Name', store=True)

    # Access Control
    apply_to = fields.Selection([
        ('users', 'Specific Users'),
        ('groups', 'User Groups'),
        ('all', 'All Users (except admins)')
    ], string='Apply To', required=True, default='groups')

    user_ids = fields.Many2many('res.users', 'field_access_config_user_rel',
                                'config_id', 'user_id', string='Users',
                                help='Users affected by this configuration')
    group_ids = fields.Many2many('res.groups', 'field_access_config_group_rel',
                                 'config_id', 'group_id', string='Groups',
                                 help='Groups affected by this configuration')

    # Field Configurations
    field_line_ids = fields.One2many('field.access.config.line', 'config_id',
                                     string='Field Configurations', ondelete='cascade')

    # Usage Tracking - Models that use this target model
    usage_model_ids = fields.One2many('field.access.config.usage', 'config_id',
                                      string='Usage Models',
                                      help='Prevent updates/deletes when target model is used in these models')

    # Prevent Write/Delete on entire record
    prevent_write = fields.Boolean(string='Prevent All Updates',
                                   help='Prevent any updates to records of this model')
    prevent_delete = fields.Boolean(string='Prevent Delete',
                                    help='Prevent deletion of records of this model')

    # Check usage before allowing updates/deletes
    check_usage = fields.Boolean(string='Check Usage Before Update/Delete',
                                 default=False,
                                 help='Prevent updates/deletes if record is used in specified models')

    @api.constrains('apply_to', 'user_ids', 'group_ids')
    def _check_access_configuration(self):
        for record in self:
            if record.apply_to == 'users' and not record.user_ids:
                raise ValidationError(_('Please select at least one user.'))
            if record.apply_to == 'groups' and not record.group_ids:
                raise ValidationError(_('Please select at least one group.'))

    def _check_user_affected(self, user):
        """Check if the current user is affected by this configuration"""
        self.ensure_one()

        # System admins are never affected
        if user.has_group('base.group_system'):
            return False

        if self.apply_to == 'all':
            return True
        elif self.apply_to == 'users':
            return user.id in self.user_ids.ids
        elif self.apply_to == 'groups':
            user_groups = user.groups_id.ids
            return bool(set(self.group_ids.ids) & set(user_groups))

        return False


class FieldAccessConfigLine(models.Model):
    _name = 'field.access.config.line'
    _description = 'Field Access Configuration Line'
    _order = 'sequence, id'

    config_id = fields.Many2one('field.access.config', string='Configuration',
                                required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    field_id = fields.Many2one('ir.model.fields', string='Field', required=True,
                               domain="[('model_id', '=', parent.model_id)]", ondelete='cascade')
    field_name = fields.Char(related='field_id.name', string='Field Technical Name', store=True)
    field_description = fields.Char(related='field_id.field_description', string='Field Label')

    access_type = fields.Selection([
        ('readonly', 'Read Only'),
        ('hidden', 'Hidden'),
    ], string='Access Type', required=True, default='readonly')


class FieldAccessConfigUsage(models.Model):
    _name = 'field.access.config.usage'
    _description = 'Field Access Configuration Usage Model'
    _order = 'sequence, id'

    config_id = fields.Many2one('field.access.config', string='Configuration',
                                required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    usage_model_id = fields.Many2one('ir.model', string='Usage Model', required=True,
                                     ondelete='cascade',
                                     help='Model that uses the target model (e.g., sale.order.line)')
    usage_model_name = fields.Char(related='usage_model_id.model', string='Model Technical Name', store=True)

    relation_field_id = fields.Many2one('ir.model.fields', string='Relation Field', required=True,
                                        domain="[('model_id', '=', usage_model_id)]",
                                        ondelete='cascade',
                                        help='Field in usage model that links to target model (e.g., product_id in sale.order.line)')
    relation_field_name = fields.Char(related='relation_field_id.name', string='Field Name', store=True)

    prevent_update_if_used = fields.Boolean(string='Prevent Update if Used', default=True,
                                            help='Prevent updates to target record if it exists in this model')
    prevent_delete_if_used = fields.Boolean(string='Prevent Delete if Used', default=True,
                                            help='Prevent deletion of target record if it exists in this model')
    prevent_duplicate_if_used = fields.Boolean(string='Prevent Duplicate if Used', default=True,
                                            help='Prevent duplicate of target record if it exists in this model')
