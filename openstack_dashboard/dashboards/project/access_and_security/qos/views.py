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


"""detail qos"""


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


"""add rule"""


class AddRuleView(forms.ModalFormView):
    form_class = qos_forms.AddRule
    form_id = "create_security_group_rule_form"
    modal_header = _("Add Rule")
    modal_id = "create_security_group_rule_modal"
    template_name = 'project/access_and_security/qos/add_rule.html'
    submit_label = _("Add")
    submit_url = "horizon:project:access_and_security:qos:add_rule"
    url = "horizon:project:access_and_security:qos:detail_qos"
    page_title = _("Add Rule")

    def get_success_url(self):
        sg_id = self.kwargs['qos_id']
        return reverse(self.url, args=[sg_id])

    def get_context_data(self, **kwargs):
        context = super(AddRuleView, self).get_context_data(**kwargs)
        context["qos_id"] = self.kwargs['qos_id']
        args = (self.kwargs['qos_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        context['cancel_url'] = reverse(self.url, args=args)
        return context

    def get_initial(self):
        qos = api.neutron.policy_get(self.request,self.kwargs['qos_id'])
        if qos.rules:
            rule_id = qos.rules[0]['id']
            return {'id': self.kwargs['qos_id'],'rule':rule_id}
        else:
            return {'id': self.kwargs['qos_id'],'rule':'no'}

    def get_form_kwargs(self):
        kwargs = super(AddRuleView, self).get_form_kwargs()

        try:
            groups = api.network.security_group_list(self.request)
        except Exception:
            groups = []
            exceptions.handle(self.request,
                              _("Unable to retrieve security groups."))

        security_groups = []
        for group in groups:
            if group.id == self.kwargs['qos_id']:
                security_groups.append((group.id,
                                        _("%s (current)") % group.name))
            else:
                security_groups.append((group.id, group.name))
        kwargs['sg_list'] = security_groups
        return kwargs


"""updated rule """
"""the feature is completed. 2018/8/21"""


class UpdateView(forms.ModalFormView):
    pass