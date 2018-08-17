#!/usr/bin/env python
# coding=utf-8
# author=hades
# @Time    : 2018/8/17 9:24
import logging

from django.utils.translation import string_concat  # noqa
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django import template
from neutronclient.common import exceptions as neutron_exceptions
from django.core.urlresolvers import reverse  # noqa
from django.conf import settings

from horizon import tables
from horizon import exceptions
import six


from openstack_dashboard.utils import filters
from openstack_dashboard import api
from openstack_dashboard.usage import quotas
from openstack_dashboard import policy
POLICY_CHECK = getattr(settings, "POLICY_CHECK_FUNCTION",
                       lambda policy, request, target: True)

LOG = logging.getLogger(__name__)


def get_policies(qos):
    template_name = 'project/networks/qos/_policies.html'
    context = {"qos": qos}
    return template.loader.render_to_string(template_name, context)


class DeleteQoSPolicy(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete QoS Policy",
            u"Delete QoS Policies",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Delete QoS Policy",
            u"Delete QoS Policies",
            count
        )

    def delete(self, request, obj_id):
        try:
            api.neutron.qos_delete(request, obj_id)
        except neutron_exceptions.NeutronClientException as e:
            LOG.info(e.message)
            redirect = reverse('horizon:admin:networks:index')
            exceptions.handle(request, e.message, redirect=redirect)
        except Exception:
            msg = _('Failed to delete QoS policy %s') % obj_id
            LOG.info(msg)
            redirect = reverse('horizon:admin:networks:index')
            exceptions.handle(request, msg, redirect=redirect)


class CreateQoSPolicy(tables.LinkAction):
    name = "create"
    verbose_name = _("Create QoS Policy")
    url = "horizon:admin:networks:qos:create"
    classes = ("ajax-modal", "btn-create")


class EditQoSPolicy(tables.LinkAction):
    name = "update"
    verbose_name = _("Edit QoS Policy")
    url = "horizon:admin:networks:qos:update"
    classes = ("ajax-modal", "btn-edit")


class QosFilterAction(tables.FilterAction):
    def filter(self, table, qoses, filter_string):
        """Naive case-insensitive search."""
        q = filter_string.lower()
        return [qos for qos in qoses
                if q in qos.name.lower()]


class QoSPolicyTable(tables.DataTable):
    tenant = tables.Column("tenant_name", verbose_name=_("Project"))
    name = tables.Column("name", verbose_name=_("Name"),
                         link='horizon:admin:networks:qos:detail')
    policy = tables.Column(get_policies,
                           verbose_name=_("Policy"))

    class Meta(object):
        name = "qos"
        verbose_name = _("QoS Policies")
        table_actions = (CreateQoSPolicy, DeleteQoSPolicy, QosFilterAction)
        row_actions = (EditQoSPolicy, DeleteQoSPolicy)


class CreateQos(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Quality of Service")
    url = "horizon:project:access_and_security:qos:create_qos"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("compute", "compute_extension:keypairs:create"),)

    def allowed(self, request, keypair=None):
        return True
    #
    # def allowed(self, request, keypair=None):
    #     usages = quotas.tenant_quota_usages(request)
    #     count = len(self.table.data)
    #     if (usages.get('key_pairs')
    #             and usages['key_pairs']['quota'] <= count):
    #         if "disabled" not in self.classes:
    #             self.classes = [c for c in self.classes] + ['disabled']
    #             self.verbose_name = string_concat(self.verbose_name, ' ',
    #                                               _("(Quota exceeded)"))
    #     else:
    #         self.verbose_name = _("Create Key Pair")
    #         classes = [c for c in self.classes if c != "disabled"]
    #         self.classes = classes
    #     return True


class ImportKeyPair():
    pass

def filter_direction(direction):
    if direction is None or direction.lower() == 'ingress':
        return _('Ingress')
    else:
        return _('Egress')

def filter_protocol(protocol):
    if protocol is None:
        return _('Any')
    return six.text_type.upper(protocol)

def get_port_range(rule):
    # There is no case where from_port is None and to_port has a value,
    # so it is enough to check only from_port.
    if rule.from_port is None:
        return _('Any')
    ip_proto = rule.ip_protocol
    if rule.from_port == rule.to_port:
        return check_rule_template(rule.from_port, ip_proto)
    else:
        return (u"%(from)s - %(to)s" %
                {'from': check_rule_template(rule.from_port, ip_proto),
                 'to': check_rule_template(rule.to_port, ip_proto)})

def get_remote_ip_prefix(rule):
    if 'cidr' in rule.ip_range:
        if rule.ip_range['cidr'] is None:
            range = '::/0' if rule.ethertype == 'IPv6' else '0.0.0.0/0'
        else:
            range = rule.ip_range['cidr']
        return range
    else:
        return None


def get_remote_security_group(rule):
    return rule.group.get('name')

class CreateRule(tables.LinkAction):
    name = "add_rule"
    verbose_name = _("Add Rule")
    url = "horizon:project:access_and_security:qos:create_qos_rule"
    classes = ("ajax-modal",)
    icon = "plus"

    def allowed(self, request, security_group_rule=None):
        return True

    def get_link_url(self):
        return reverse(self.url, args=[self.table.kwargs['qos_id']])


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

    def allowed(self, request, security_group_rule=None):
        return True
    def delete(self, request, obj_id ):
        qos_id = self.table.kwargs['qos_id']
        print(qos_id)
        try:
            api.neutron.delete_qos_bandwidth(request, obj_id, qos_id)
        except Exception:
            return False

    def get_success_url(self, request):
        sg_id = self.table.kwargs['qos_id']
        return reverse("horizon:project:access_and_security:"
                       "qos:detail_qos", args=[sg_id])


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
        api.neutron.policy_delete(request, obj_id)


class KeypairsFilterAction():
    pass


class EditQos(policy.PolicyTargetMixin, tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit Quality of Service")
    url = "horizon:project:access_and_security:qos:edit_qos"
    classes = ("ajax-modal",)
    icon = "pencil"

    def allowed(self, request, qos=None):
        return True


class ManageRules(policy.PolicyTargetMixin, tables.LinkAction):
    name = "manage_rules"
    verbose_name = _("Manage Rules")
    url = "horizon:project:access_and_security:qos:detail_qos"
    icon = "pencil"

    def allowed(self, request, security_group=None):
        return True



class QosTable(tables.DataTable):
    name = tables.Column('name', verbose_name=_('Name'))
    id = tables.Column('id',verbose_name=_('ID'),link='horizon:project:access_and_security:qos:detail_qos')
    description = tables.Column('description',verbose_name=_('Description'))
    tenant_id = tables.Column('tenant_id',verbose_name=_('Project'))
    shared = tables.Column('shared',verbose_name=_('Shared'))

    def get_object_id(self, qos):
        return "%s" % (qos.id)

    class Meta(object):
        name = "quality_of_service"
        verbose_name = _("Quality of Service")
        table_actions = (CreateQos, DeleteQos,QosFilterAction,)
        row_actions = (EditQos,ManageRules)
