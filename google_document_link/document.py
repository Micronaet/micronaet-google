# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)


_logger = logging.getLogger(__name__)


class GdocProtocol(orm.Model):
    """ Object gdoc.protocol
    """
    _name = 'gdoc.protocol'
    _description = 'Google document protocol'
    _order = 'name'

    _columns = {
        'name': fields.char('Protocol', size=64, required=True,
            translate=True),
        'note': fields.text('Note', translate=True),
        }

class GdocDocument(orm.Model):
    """ Object gdoc.document
    """
    _name = 'gdoc.document'
    _description = 'Google Document'
    _order = 'sequence, date desc'

    # -------------------------------------------------------------------------
    # Button:
    # -------------------------------------------------------------------------
    def open_gdoc_link(self, cr, uid, ids, context=None):
        """
        """
        gdoc = self.browse(cr, uid, ids, context=context)[0]
        return {
            'type': 'ir.actions.act_url',
            'url': gdoc.link,
            'target': 'blank',
            }

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def dummy(self, cr, uid, ids, context=None):
        return True

    # -------------------------------------------------------------------------
    # Workflow state event:
    # -------------------------------------------------------------------------
    def document_draft(self, cr, uid, ids, context=None):
        """ WF draft state
        """
        assert len(ids) == 1, 'Works only with one record a time'
        self.write(cr, uid, ids, {
            'state': 'draft',
            }, context=context)
        return True

    def document_confirmed(self, cr, uid, ids, context=None):
        """ WF confirmed state
        """
        assert len(ids) == 1, 'Works only with one record a time'
        data = {'state': 'confirmed'}

        protocol_pool = self.pool.get('gdoc.protocol')
        return self.write(cr, uid, ids, data, context=context)

    def document_timed(self, cr, uid, ids, context=None):
        """ WF timed state
        """
        assert len(ids) == 1, 'Works only with one record a time'
        data = {'state': 'timed'}

        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        if not current_proxy.deadline:
            raise osv.except_osv(
                _('Timed document'),
                _('For timed document need a deadline!'),
                )
        return self.write(cr, uid, ids, data, context=context)

    def document_cancel(self, cr, uid, ids, context=None):
        """ WF cancel state
        """
        assert len(ids) == 1, 'Works only with one record a time'
        data = {'state': 'cancel'}
        return self.write(cr, uid, ids, data, context=context)

    _columns = {
        'sequence': fields.integer('Sequence'),
        'name': fields.char('Subject', size=180, required=True),
        'description': fields.text('Description'),
        'note': fields.text('Note'),
        'link': fields.text('Google doc. Link', required=True),

        'date': fields.date('Date', required=True),
        'deadline_info': fields.char('Deadline info', size=80),
        'deadline': fields.date('Deadline'),

        # OpenERP many2one
        'protocol_id': fields.many2one('gdoc.protocol', 'Protocol'),
        'user_id': fields.many2one('res.users', 'User', required=True),

        # Foreign keys:
        'ticket_id': fields.many2one('account.analytic.ticket', 'Ticket'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'product_id': fields.many2one('product.product', 'Product'),
        'account_id': fields.many2one('account.analytic.account', 'Account'),
        'order_id': fields.many2one('sale.order', 'Sale Order'),
        'timesheet_id': fields.many2one('hr.analytic.timesheet', 'Timesheet'),
        'picking_id': fields.many2one('stock.picking', 'Picking'),
        # Invoice DDT

        'priority': fields.selection([
            ('lowest', 'Lowest'),
            ('low', 'Low'),
            ('normal', 'Normal'),
            ('high', 'high'),
            ('highest', 'Highest'),
            ], 'Priority'),

        'state': fields.selection([
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('timed', 'Timed'),
            ('cancel', 'Cancel'),
            ], 'State', readonly=True),
        }

    _defaults = {
        'sequence': 10,
        'date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT),
        'priority': lambda *x: 'normal',
        'state': lambda *x: 'draft',
        'user_id': lambda s, cr, uid, ctx: uid,
        }


class ResPartner(orm.Model):
    """ Model name: ResPartner
    """

    _inherit = 'res.partner'

    _columns = {
        'gdoc_ids': fields.one2many(
            'gdoc.document', 'partner_id', 'Google Document'),
        }

class SaleOrder(orm.Model):
    """ Model name: Sale order
    """

    _inherit = 'sale.order'

    _columns = {
        'gdoc_ids': fields.one2many(
            'gdoc.document', 'order_id', 'Google Document'),
        }

class ProductProduct(orm.Model):
    """ Model name: Product Product
    """

    _inherit = 'product.product'

    _columns = {
        'gdoc_ids': fields.one2many(
            'gdoc.document', 'product_id', 'Google Document'),
        }

class AccountAnalyticAccount(orm.Model):
    """ Model name: Account analytic account
    """

    _inherit = 'account.analytic.account'

    _columns = {
        'gdoc_ids': fields.one2many(
            'gdoc.document', 'account_id', 'Google Document'),
        }

class HrAnalyticTYimesheet(orm.Model):
    """ Model name: HR Analytic Timesheet
    """

    _inherit = 'hr.analytic.timesheet'

    _columns = {
        'gdoc_ids': fields.one2many(
            'gdoc.document', 'timesheet_id', 'Google Document'),
        }

class AccountAnalyticTicket(orm.Model):
    """ Model name: Ticket
    """

    _inherit = 'account.analytic.ticket'

    _columns = {
        'gdoc_ids': fields.one2many(
            'gdoc.document', 'ticket_id', 'Google Document'),
        }

class StockPicking(orm.Model):
    """ Model name: Stock Picking
    """

    _inherit = 'stock.picking'

    _columns = {
        'gdoc_ids': fields.one2many(
            'gdoc.document', 'picking_id', 'Google Document'),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
