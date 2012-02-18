
from registration.backends.default import DefaultBackend
from registration.forms import RegistrationFormUsernameEmailMatch


class NamelessBackend(DefaultBackend):

    def get_form_class(self, request):
        return RegistrationFormUsernameEmailMatch

    def post_activation_redirect(self, request, user):
        """
        Return the name of the URL to redirect to after successful
        account activation and login.
        """

        new_user = authenticate(username=username, password=password)
        login(request, new_user)
        return ('/', (), {})
