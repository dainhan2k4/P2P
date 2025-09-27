# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TrainModelsWizard(models.TransientModel):
    _name = 'train.models.wizard'
    _description = 'Wizard to Train Credit Risk Models'

    model_types = fields.Selection([
        ('all', 'All Models (PD, EAD, LGD)'),
        ('pd', 'PD Model Only'),
        ('ead', 'EAD Model Only'),
        ('lgd', 'LGD Model Only')
    ], string='Models to Train', required=True, default='all')

    def action_train_models(self):
        """Train the selected credit risk models"""
        self.ensure_one()

        try:
            if self.model_types == 'all':
                result = self.env['credit.risk.model'].train_all_models()
                message = _("All credit risk models (PD, EAD, LGD) have been trained successfully!")

            elif self.model_types == 'pd':
                model = self.env['credit.risk.model'].create_pd_model()
                message = _("PD model trained successfully with accuracy: %.4f") % model.accuracy_score

            elif self.model_types == 'ead':
                model = self.env['credit.risk.model'].create_ead_model()
                message = _("EAD model trained successfully with MSE: %.4f") % model.mse_score

            elif self.model_types == 'lgd':
                model = self.env['credit.risk.model'].create_lgd_model()
                message = _("LGD model trained successfully with MSE: %.4f") % model.mse_score

            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Training Completed'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(_("Training failed: %s") % str(e))