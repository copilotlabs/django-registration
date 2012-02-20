
from registration.backends.default import DefaultBackend
from registration.forms import RegistrationFormUsernameEmailMatch
from django.contrib.auth import login


class NamelessBackend(DefaultBackend):

    def get_form_class(self, request):
        return RegistrationFormUsernameEmailMatch

    def post_activation_redirect(self, request, user):
        """
        Return the name of the URL to redirect to after successful
        account activation and login.
        """

        user.backend = self.__class__
        login(request, user)
        return ('/', (), {})
