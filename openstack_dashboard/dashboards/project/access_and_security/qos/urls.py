#!/usr/bin/env python
# coding=utf-8
# author=hades
# @Time    : 2018/8/17 9:24
from django.conf.urls import patterns
from django.conf.urls import url

from openstack_dashboard.dashboards.project.access_and_security.keypairs \
    import views

from openstack_dashboard.dashboards.project.access_and_security.qos \
    import views as qos_views

QOS = r'^(?P<qos_id>[^/]+)/%s$'

urlpatterns = patterns(
    '',
    url(r'^create/$', qos_views.CreateQosView.as_view(), name='create_qos'),
    url(QOS % 'detail', qos_views.DetailQosView.as_view(), name='detail_qos'),
    url(r'^(?P<qos_id>[^/]+)/add_rule/$',
        qos_views.AddRuleView.as_view(),
        name='add_rule'),
    url(r'^(?P<qos_id>[^/]+)/update/$',
        qos_views.UpdateView.as_view(),
        name='update'),

)
