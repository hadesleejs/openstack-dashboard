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
    url(r'^create/$', views.CreateView.as_view(), name='create'),
    url(r'^create_qos/$', qos_views.CreateQosView.as_view(), name='create_qos'),
    url(QOS % 'update', qos_views.EditQosView.as_view(), name='edit_qos'),
    url(QOS % 'detail', qos_views.DetailQosView.as_view(), name='detail_qos'),
    url(QOS % 'create_rule', qos_views.CreateQosRuleView.as_view(), name='create_qos_rule'),
    url(QOS % 'rule', qos_views.QosRuleView.as_view(), name='qos_rule'),
    url(r'^import/$', views.ImportView.as_view(), name='import'),
    url(r'^(?P<keypair_name>[^/]+)/download/$', views.DownloadView.as_view(),
        name='download'),
    url(r'^(?P<keypair_name>[^/]+)/generate/$', views.GenerateView.as_view(),
        name='generate'),
    url(r'^(?P<keypair_name>[^/]+)/(?P<optional>[^/]+)/generate/$',
        views.GenerateView.as_view(), name='generate'),
    url(r'^(?P<keypair_name>[^/]+)/$', views.DetailView.as_view(),
        name='detail'),
)
