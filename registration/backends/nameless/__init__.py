try: from prism import registration
except: pass

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import login

from registration.backends.default import DefaultBackend
from registration.models import RegistrationProfile
from registration.forms import RegistrationFormUsernameEmailMatch
from registration import signals


class NamelessBackend(DefaultBackend):

    send_email = False

    def get_form_class(self, request):
        return RegistrationFormUsernameEmailMatch

    def post_activation_redirect(self, request, user):
        """
        After the user successfully changes their password and is subsequently
        activated, redirect to the user's account page.
        
        """

        # automatically login user
        # TODO: determine if this authentication hack is safe; if not, find the
        # right way to authenticate users, most likely using an auth backend
        # user.backend = self.__class__
        # login(request, user)

        redirect_to = user.get_absolute_url()

        if REDIRECT_FIELD_NAME in request.REQUEST:
            redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME)
            # Don't allow redirection to a different host.
            netloc = urlparse.urlparse(redirect_to)[1]
            if netloc and netloc != request.get_host():
                redirect_to = settings.LOGIN_REDIRECT_URL

        return (redirect_to, (), {})
