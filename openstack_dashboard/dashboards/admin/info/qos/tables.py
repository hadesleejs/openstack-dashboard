#!/usr/bin/env python
# coding=utf-8
# author=hades
# @Time    : 2018/8/17 9:24
import logging

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django.core.urlresolvers import reverse  # noqa

from horizon import tables
import six
from horizon import exceptions


from openstack_dashboard import api
from openstack_dashboard import policy


LOG = logging.getLogger(__name__)


"""create rule"""


class CreateRule(tables.LinkAction):
    name = "add_rule"
    verbose_name = _("Add Rule")
    url = "horizon:admin:info:qos:add_rule"
    classes = ("ajax-modal",)
    icon = "plus"

    def allowed(self, request, qos_rule=None):
        return True

    def get_link_url(self):
        return reverse(self.url, args=[self.table.kwargs['qos_id']])


"""delete rule"""


class DeleteRule(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Rule",
            u"Delete Rules",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Rule",
            u"Deleted Rules",
            count
        )

    def allowed(self, request, rule=None):
        return True

    def delete(self, request, obj_id ):
        qos_id = self.table.kwargs['qos_id']
        print(qos_id)
        try:
            api.neutron.delete_qos_bandwidth(request, qos_id, obj_id)
        except Exception:
            return False

    def get_success_url(self, request):
        sg_id = self.table.kwargs['qos_id']
        return reverse("horizon:admin:info:"
                       "qos:detail", args=[sg_id])


"""rule table"""


class RulesTable(tables.DataTable):
    max_kbps = tables.Column('max_kbps',verbose_name="max-kbps")
    max_burst_kbps = tables.Column('max_burst_kbps',verbose_name="max-burst-kbps")

    def get_object_id(self, obj):
        return "%s" % (obj['id'])

    def get_object_display(self, rule):
        return six.text_type(rule)

    class Meta(object):
        name = "rules"
        verbose_name = _("Quality of Service Rules")
        table_actions = (CreateRule, DeleteRule)
        row_actions = (DeleteRule,)


"""create qos"""


class CreateQos(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Quality of Service")
    url = "horizon:admin:info:qos:create"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("compute", "compute_extension:keypairs:create"),)

    def allowed(self, request, keypair=None):
        return True


"""filter qos"""


class QosFilterAction(tables.FilterAction):
    def filter(self, table, qoses, filter_string):
        """Naive case-insensitive search."""
        q = filter_string.lower()
        return [qos for qos in qoses
                if q in qos.name.lower()]


"""delete qos"""


class DeleteQos(tables.DeleteAction):
    policy_rules = (("compute", "compute_extension:keypairs:delete"),)
    help_text = _("Removing a qos can leave OpenStack resources orphaned."
                  " You should not remove a qos unless you are certain it"
                  " is not being used anywhere.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Quality of Service",
            u"Delete Quality of Services",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Quality of Service",
            u"Deleted Quality of Services",
            count
        )

    def delete(self, request, obj_id):
        try:
            api.neutron.policy_delete(request, obj_id)
        except Exception,e:
            redirect = reverse("horizon:admin:info:"
                               "qos:detail", args={obj_id:obj_id})
            msg = e
            exceptions.handle(request, msg, redirect=redirect)


"""manager qos"""


class ManageRules(policy.PolicyTargetMixin, tables.LinkAction):
    name = "manage_rules"
    verbose_name = _("Manage Rules")
    url = "horizon:admin:info:qos:detail"
    icon = "pencil"

    def allowed(self, request, security_group=None):
        return True


"""qos table"""


class QosTable(tables.DataTable):
    name = tables.Column('name', verbose_name=_('Name'))
    id = tables.Column('id',verbose_name=_('ID'),link='horizon:admin:info:qos:detail')
    description = tables.Column('description',verbose_name=_('Description'))
    tenant_id = tables.Column('tenant_id',verbose_name=_('Project'))
    shared = tables.Column('shared',verbose_name=_('Shared'))

    def get_object_id(self, qos):
        return "%s" % (qos.id)

    class Meta(object):
        name = "quality_of_service"
        verbose_name = _("Quality of Service")
        table_actions = (CreateQos, DeleteQos, QosFilterAction,)
        row_actions = (ManageRules,)
