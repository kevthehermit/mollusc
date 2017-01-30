"""mollusc URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from web import views

urlpatterns = [
    # Admin / Auth
    url(r'^admin/', admin.site.urls),
    url(r'^login/', views.login_page),
    url(r'^logout/', views.logout_page),
    # Main Page
    url(r'^$', views.main_page),
    # Session Page
    url(r'^session/(?P<session_id>.+)/$', views.session_page),
    # TTY Player
    url(r'^ttylog/(?P<session_id>.+)/$', views.get_ttylog),
    # AjaxHandlers
    url(r'^ajaxhandler/(?P<command>.+)/$', views.ajax_handler),
    # Feeds
    url(r'^feeds/(?P<datatype>.+)/(?P<format>.+)/$', views.feeds),
    # Passwords
    url(r'^passwords/', views.passwords),
    # Usernames
    url(r'^usernames/', views.usernames),
    # Commands
    url(r'^commands/', views.commands_page),
    # Downloads
    url(r'^downloads/', views.downloads_page),
    # IP Lookup
    url(r'^ipaddress/(?P<ipadd>.+)/$', views.ipaddress_page),
]
