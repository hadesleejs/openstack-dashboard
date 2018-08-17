#!/usr/bin/env python
# coding=utf-8
# author=hades
# @Time    : 2018/8/17 9:24
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django import http
from django.template.defaultfilters import slugify  # noqa
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.generic import View  # noqa

from horizon import exceptions
from horizon import forms
from horizon.utils import memoized
from horizon import views
from horizon import tables

from openstack_dashboard import api
from openstack_dashboard.utils import filters
from openstack_dashboard.dashboards.project.access_and_security.keypairs \
    import forms as project_forms

from openstack_dashboard.dashboards.project.access_and_security.qos import  forms as qos_forms
from openstack_dashboard.dashboards.project.access_and_security.\
    security_groups import tables as project_tables
from openstack_dashboard.dashboards.project.access_and_security.qos import tables as qos_tables


class CreateQosView(forms.ModalFormView):
    form_class = qos_forms.CreateQoSPolicy
    form_id = "create_qos_form"
    modal_header = _("Create Quality of Service")
    template_name = 'project/access_and_security/qos/create.html'
    submit_label = _("Create Quality of Service")
    submit_url = reverse_lazy(
        "horizon:project:access_and_security:qos:create_qos")
    success_url = 'horizon:project:access_and_security:index'
    page_title = _("Create Quality of Service")
    cancel_url = reverse_lazy(
        "horizon:project:access_and_security:index")


class DetailQosView(tables.DataTableView):
    table_class = qos_tables.RulesTable
    template_name = 'project/access_and_security/qos/detail.html'
    page_title = _("Manage Qos Rules: ")

    @memoized.memoized_method
    def _get_data(self):
        qos_id = filters.get_int_or_uuid(self.kwargs['qos_id'])
        try:
            return api.neutron.policy_get(self.request, qos_id)
        except Exception:
            redirect = reverse('horizon:project:access_and_security:index')
            exceptions.handle(self.request,
                              _('Unable to retrieve qos.'),
                              redirect=redirect)

    def get_data(self):
        data = self._get_data()
        if data is None:
            return []
        return data.rules

    def get_context_data(self, **kwargs):
        context = super(DetailQosView, self).get_context_data(**kwargs)
        context["qos"] = self._get_data()
        return context

class EditQosView(forms.ModalFormView):
    form_class = qos_forms.UpdateQos
    form_id = "update_qos_form"
    modal_header = _("Edit Quality of Service")
    modal_id = "update_qos_modal"
    template_name = 'project/access_and_security/security_groups/update.html'
    submit_label = _("Edit Quality of Service")
    submit_url = "horizon:project:access_and_security:security_groups:update"
    success_url = reverse_lazy('horizon:project:access_and_security:index')
    page_title = _("Edit Quality of Service")

    @memoized.memoized_method
    def get_object(self):
        sg_id = filters.get_int_or_uuid(self.kwargs['security_group_id'])
        try:
            return api.network.security_group_get(self.request, sg_id)
        except Exception:
            msg = _('Unable to retrieve security group.')
            url = reverse('horizon:project:access_and_security:index')
            exceptions.handle(self.request, msg, redirect=url)

    def get_context_data(self, **kwargs):
        context = super(EditQosView, self).get_context_data(**kwargs)
        context["security_group"] = self.get_object()
        args = (self.kwargs['security_group_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        security_group = self.get_object()
        return {'id': self.kwargs['security_group_id'],
                'name': security_group.name,
                'description': security_group.description}


class QosRuleView(forms.ModalFormView):
    pass
class CreateQosRuleView(forms.ModalFormView):
    form_class = qos_forms.AddRule
    form_id = "create_qos_rule_form"
    modal_header = _("Add Rule")
    modal_id = "create_qos_rule_modal"
    template_name = 'project/access_and_security/qos/add_rule.html'
    submit_label = _("Add")
    success_url = 'horizon:project:access_and_security:index'
    submit_url = "horizon:project:access_and_security:qos:create_qos_rule"
    url = "horizon:project:access_and_security:qos:detail_qos"
    page_title = _("Add Rule")
    cancel_url = reverse_lazy(
        "horizon:project:access_and_security:index")
    def get_success_url(self):
        sg_id = self.kwargs['qos_id']
        return reverse(self.url, args=[sg_id])

    def get_context_data(self, **kwargs):
        context = super(CreateQosRuleView, self).get_context_data(**kwargs)
        context["qos_id"] = self.kwargs['qos_id']
        args = (self.kwargs['qos_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        context['cancel_url'] = reverse(self.url, args=args)
        return context

    def get_initial(self):
        qos = api.neutron.policy_get(self.request,self.kwargs['qos_id'])
        if qos.rules == []:
            return {'id': self.kwargs['qos_id'],}
        else:
            return {'id': self.kwargs['qos_id'],'max_burst_kbps':qos.rules[0]['max_burst_kbps'],
                    'rule_id':qos.rules[0]['id'],'max_kbps':qos.rules[0]['max_kbps']}

