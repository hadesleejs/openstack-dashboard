# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse_lazy

from horizon import exceptions
from horizon import tabs
from horizon import version
from horizon import forms
from horizon import tables

from openstack_dashboard import api
from openstack_dashboard.dashboards.admin.networks \
    import forms as project_forms
from openstack_dashboard.dashboards.admin.info import constants
from openstack_dashboard.dashboards.admin.info import tabs as project_tabs
from openstack_dashboard.dashboards.admin.info import forms as info_forms
from openstack_dashboard.dashboards.admin.info import tables as qos_tables

class IndexView(tabs.TabbedTableView):
    tab_group_class = project_tabs.SystemInfoTabs
    template_name = constants.INFO_TEMPLATE_NAME
    page_title = _("System Information")

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        try:
            context["version"] = version.version_info.version_string()
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve version information.'))

        return context


class CreateView(forms.ModalFormView):
    form_class = project_forms.CreateNetwork
    template_name = 'admin/networks/create.html'
    success_url = reverse_lazy('horizon:admin:info:index')
    page_title = _("Create Network")


class Create_Qos_View(forms.ModalFormView):
    form_class = ''
    template_name = ''
    success_url = reverse_lazy('')
    page_title = _("")



class DetailView(tables.DataTableView):
    table_class = qos_tables.QoSPolicyTable
    template_name = 'admin/info/qos/detail.html'
    failure_url = reverse_lazy('horizon:project:networks:index')
    page_title = '{{ "QoS Policy Detail: "|add:qos.name }}'

    def get_data(self):
        try:
            qos_id = self.kwargs['qos_id']
            self.table.kwargs['qos'] = self._get_data()
            qos = api.neutron.qos_get(self.request, qos_id)
        except Exception:
            qos = []
            msg = _('QoS policy can not be retrieved.')
            exceptions.handle(self.request, msg)
        return qos

    def _get_data(self):
        if not hasattr(self, "_qos"):
            try:
                qos_id = self.kwargs['qos_id']
                qos = api.neutron.qos_get(self.request, qos_id)
            except Exception:
                redirect = self.failure_url
                exceptions.handle(self.request,
                                  _('Unable to retrieve details for '
                                    'QoS policy "%s".') % qos_id,
                                  redirect=redirect)
            self._qos = qos
        return self._qos

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context["qos"] = self._get_data()
        return context
