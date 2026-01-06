from odoo import models, api, _
from odoo.exceptions import UserError, AccessError


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    # -------------------------------
    # WRITE
    # -------------------------------
    def write(self, vals):
        """Override write to prevent updates based on configuration"""

        # Skip for system admins
        if self.env.user.has_group('base.group_system'):
            return super().write(vals)

        # Get related access configurations
        configs = self.env['field.access.config'].sudo().search([
            ('active', '=', True),
            ('model_name', '=', self._name)
        ])

        for config in configs:
            if not config._check_user_affected(self.env.user):
                continue

            # Fully prevent write
            if config.prevent_write:
                raise UserError(_(
                    'You are not allowed to update records of type "%s" due to access restrictions.'
                ) % self._description)

            # Check restricted fields
            for line in config.field_line_ids:
                if line.field_name in vals and line.access_type in ['readonly', 'hidden']:
                    raise UserError(_(
                        'You are not allowed to modify the field "%s" in "%s".'
                    ) % (line.field_description or line.field_name, self._description))

            # Check usage restriction
            if config.check_usage and config.usage_model_ids:
                for usage in config.usage_model_ids:
                    if usage.prevent_update_if_used:
                        self._check_record_usage(usage, 'update')

        return super().write(vals)

    # -------------------------------
    # UNLINK
    # -------------------------------
    def unlink(self):
        """Override unlink to prevent deletion based on configuration"""

        # Skip for system admins
        if self.env.user.has_group('base.group_system'):
            return super().unlink()

        configs = self.env['field.access.config'].sudo().search([
            ('active', '=', True),
            ('model_name', '=', self._name)
        ])

        for config in configs:
            if not config._check_user_affected(self.env.user):
                continue

            # Prevent delete entirely
            if config.prevent_delete:
                raise UserError(_(
                    'You are not allowed to delete records of type "%s" due to access restrictions.'
                ) % self._description)

            # Check if record is used elsewhere
            if config.check_usage and config.usage_model_ids:
                for usage in config.usage_model_ids:
                    if usage.prevent_delete_if_used:
                        self._check_record_usage(usage, 'delete')

        return super().unlink()

    # -------------------------------
    # COPY (Duplication Prevention)
    # -------------------------------
    def copy(self, default=None):
        """Override copy to prevent duplication based on usage"""

        # Skip for system admins
        if self.env.user.has_group('base.group_system'):
            return super().copy(default=default)

        configs = self.env['field.access.config'].sudo().search([
            ('active', '=', True),
            ('model_name', '=', self._name)
        ])

        for config in configs:
            if not config._check_user_affected(self.env.user):
                continue

            # Check if record is used elsewhere - prevent duplication if used
            if config.check_usage and config.usage_model_ids:
                for usage in config.usage_model_ids:
                    if usage.prevent_duplicate_if_used:
                        self._check_record_usage(usage, 'duplicate')

        return super().copy(default=default)

    # -------------------------------
    # RECORD USAGE CHECKER (Access-Safe)
    # -------------------------------
    def _check_record_usage(self, usage_config, operation='update', restricted_fields=None):
        """
        Check if records are being used in other models and prevent operation

        :param usage_config: field.access.config.usage record
        :param operation: 'update', 'delete', or 'duplicate'
        :param restricted_fields: set of field names being updated (only for 'update' operation)
        """
        self.ensure_one()

        usage_model = self.env[usage_config.usage_model_name]
        field_name = usage_config.relation_field_name
        field_obj = usage_model._fields.get(field_name)
        if not field_obj:
            return

        target_ids = self.ids
        # Special case for product templates → product variants
        if self._name == 'product.template' and field_obj.comodel_name == 'product.product':
            variants = self.env['product.product'].sudo().search([('product_tmpl_id', 'in', self.ids)])
            field_name = usage_config.relation_field_name
            target_ids = variants.ids
            if not target_ids:
                return

        # Count usage
        domain = [(field_name, 'in', target_ids)]
        usage_count = usage_model.sudo().search_count(domain)
        if usage_count > 0:
            # Safe access to usage model name
            try:
                usage_model_name = usage_config.usage_model_id.name
            except AccessError:
                usage_model_name = usage_config.usage_model_id.model or _("restricted model")

            # Map operation to user-friendly text
            operation_map = {
                'update': _('update'),
                'delete': _('delete'),
                'duplicate': _('duplicate')
            }
            operation_text = operation_map.get(operation, operation)

            # Build error message
            error_msg = _(
                'Cannot %(operation)s "%(record)s" because it is being used in:\n'
                '%(usage_model)s\n\n'
                'Total usage count: %(count)s'
            ) % {
                            'operation': operation_text,
                            'record': self.display_name,
                            'usage_model': usage_model_name,
                            'count': usage_count
                        }

            # Add information about which restricted fields are being updated
            if operation == 'update' and restricted_fields:
                field_labels = []
                for field_name in restricted_fields:
                    field_obj = self._fields.get(field_name)
                    if field_obj:
                        field_labels.append(field_obj.string or field_name)
                    else:
                        field_labels.append(field_name)

                error_msg += _('\n\nRestricted fields being updated: %s') % ', '.join(field_labels)

            # Raise UserError with appropriate message
            raise UserError(error_msg)