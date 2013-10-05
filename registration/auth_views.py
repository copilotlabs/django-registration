
import json

from django.views.decorators.cache import never_cache

from django.http import HttpResponse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import login as auth_views_login

@never_cache
def login(request, authentication_form=AuthenticationForm,
          *args, **kwargs):
    """
    Handles the login action.
    """
    json_response = lambda data: HttpResponse(json.dumps(data), mimetype='application/json')
    response_data = {'success':True}

    accept = request.META.get('HTTP_ACCEPT')
    if bool(accept) and 'application/json' in accept:

        if request.method == 'POST':

            form = authentication_form(data=request.POST)

            if form.is_valid():

                auth_login(request, form.get_user())

                if request.session.test_cookie_worked():
                    request.session.delete_test_cookie()

            else:

                response_data['success'] = False

                if bool(form.errors):
                    response_data['errors'] = form.errors

            return json_response(response_data)
        else:

            response_data['success'] = False
            response_data['errors'] = [u'Only the POST method is supported for this endpoint.']
            return json_response(response_data)

    return auth_views_login(request, *args, **kwargs)

