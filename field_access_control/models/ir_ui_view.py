from odoo import models, api, _
from lxml import etree
import json
from odoo.exceptions import UserError


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def _apply_field_access_attrs(self, arch, model_name):
        """Apply field access configurations to view architecture"""

        # Get active configurations for this model
        configs = self.env['field.access.config'].search([
            ('active', '=', True),
            ('model_name', '=', model_name)
        ])

        if not configs:
            return arch

        user = self.env.user

        # Skip for system admins
        if user.has_group('base.group_system'):
            return arch

        # Collect field modifications
        field_attrs = {}

        for config in configs:
            if not config._check_user_affected(user):
                continue

            for line in config.field_line_ids:
                field_name = line.field_name

                if field_name not in field_attrs:
                    field_attrs[field_name] = {
                        'readonly': False,
                        'invisible': False,
                        'required': False,
                    }

                if line.access_type == 'readonly':
                    field_attrs[field_name]['readonly'] = True
                elif line.access_type == 'hidden':
                    field_attrs[field_name]['invisible'] = True
                elif line.access_type == 'required':
                    field_attrs[field_name]['required'] = True

        # Apply modifications to arch
        if field_attrs:
            arch_tree = etree.fromstring(arch)

            for field_name, attrs in field_attrs.items():
                # Find all field nodes with this name
                for field_node in arch_tree.xpath(f"//field[@name='{field_name}']"):
                    # Build attrs dict
                    attrs_dict = {}
                    if attrs['readonly']:
                        attrs_dict['readonly'] = '1'
                    if attrs['invisible']:
                        attrs_dict['invisible'] = '1'
                    if attrs['required']:
                        attrs_dict['required'] = '1'

                    if attrs_dict:
                        # Merge with existing attrs
                        existing_attrs = field_node.get('attrs', '{}')
                        if existing_attrs and existing_attrs != '{}':
                            try:
                                existing_dict = eval(existing_attrs)
                                # Add readonly/invisible as additional conditions
                                for key, value in attrs_dict.items():
                                    if key in existing_dict:
                                        # Keep existing condition
                                        pass
                                    else:
                                        existing_dict[key] = value
                                field_node.set('attrs', str(existing_dict))
                            except:
                                field_node.set('attrs', str(attrs_dict))
                        else:
                            field_node.set('attrs', str(attrs_dict))

            arch = etree.tostring(arch_tree, encoding='unicode')

        return arch

    @api.model
    def _apply_view_inheritance(self, source, specs_tree, inherit_id):
        """Override to apply field access control"""
        arch = super()._apply_view_inheritance(source, specs_tree, inherit_id)

        # Get model from view
        if self.env.context.get('check_field_access'):
            view = self.browse(inherit_id) if inherit_id else self
            if view.model:
                arch = self._apply_field_access_attrs(arch, view.model)

        return arch

    def read_combined(self, fields=None):
        """Override to apply field access on view load"""
        result = super().read_combined(fields=fields)

        if result.get('arch') and result.get('model'):
            result['arch'] = self._apply_field_access_attrs(
                result['arch'],
                result['model']
            )

        return result


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def write(self, vals):
        """Override write to prevent updates based on configuration"""

        # Skip for system admins
        if self.env.user.has_group('base.group_system'):
            return super().write(vals)

        # Check for field access configurations
        configs = self.env['field.access.config'].search([
            ('active', '=', True),
            ('model_name', '=', self._name)
        ])

        for config in configs:
            if not config._check_user_affected(self.env.user):
                continue

            # Check if write is completely prevented
            if config.prevent_write:
                raise UserError(_(
                    'You are not allowed to update records of type "%s" due to access restrictions.'
                ) % self._description)

            # Check individual fields
            for line in config.field_line_ids:
                if line.field_name in vals and line.access_type in ['readonly', 'hidden']:
                    raise UserError(_(
                        'You are not allowed to modify the field "%s" in "%s".'
                    ) % (line.field_description or line.field_name, self._description))

        return super().write(vals)

    def unlink(self):
        """Override unlink to prevent deletion based on configuration"""

        # Skip for system admins
        if self.env.user.has_group('base.group_system'):
            return super().unlink()

        # Check for field access configurations
        configs = self.env['field.access.config'].search([
            ('active', '=', True),
            ('model_name', '=', self._name)
        ])

        for config in configs:
            if not config._check_user_affected(self.env.user):
                continue

            if config.prevent_delete:
                raise UserError(_(
                    'You are not allowed to delete records of type "%s" due to access restrictions.'
                ) % self._description)

        return super().unlink()