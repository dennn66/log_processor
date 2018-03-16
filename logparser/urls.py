from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from . import views
import settings

urlpatterns = [
    url(r'^$', views.request_list, name='request_list'),
    url(r'^list/$', views.request_list, name='request_list'),
    url(r'^rqst_many_upd/$', views.rqst_many_upd, name='rqst_many_upd'),
    url(r'^request/(?P<pk>\d+)/$', views.request_detail, name='request_detail'),
    url(r'^request/add/$', views.request_new, name='request_new'),
    url(r'^request/(?P<pk>\d+)/edit/$', views.request_edit, name='request_edit'),
    url(r'^request/(?P<pk>\d+)/test/$', views.test, name='test'),
    url(r'^request/(?P<pk>\d+)/delete/$', views.request_delete, name='request_delete'),
    url(r'^request/(?P<pk>\d+)/do_delete/$', views.request_do_delete, name='request_do_delete'),
]



urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += staticfiles_urlpatterns()