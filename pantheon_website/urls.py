"""pantheon_website URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

import os
from pantheon import views

urlpatterns = [
    path('^$', views.index, name='index'),
    path('^overview/$', views.overview, name='overview'),
    path('^faq/$', views.faq, name='faq'),
    path('^measurements/(?P<expt_type>node|cloud|emu)/$',
         views.measurements, name='measurements'),
    path('^summary/$', views.rankings, name='summary'),
    path('^result/(?P<result_id>[0-9]+)/$', views.result, name='result'),
    path('^%s/(?P<expt_type>node|cloud|emu)/$'
         % os.environ['PANTHEON_UPDATE_URL'], views.update, name='update'),
]
