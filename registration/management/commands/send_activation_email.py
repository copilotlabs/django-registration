try: from prism import registration
except: pass

from django.contrib.sites.models import RequestSite, Site
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from optparse import make_option

from prism.utils.debug import attempt
from registration.models import RegistrationProfile


class Command(BaseCommand):

    option_list = BaseCommand.option_list \
            + (make_option('--userid', dest='userid'),)


    def handle(self, *args, **options):
        """
        Make the user with the given userid inactive and send them an
        activation email.

        """

        traceback = options.get('traceback') or False # True or False
        attempt.traceback = bool(traceback)
        attempt.error_actions = { '*' : CommandError }

        userid = options.get('userid')
        if not userid:
            raise CommandError("Must provide --userid")

        with attempt('Looking up User by userid',
                { '*': CommandError("There is no User with that userid.") }):
            user = User.objects.get(id=userid)
            if user.is_active:
                print "There is nothing to be done, the user is already active."
                return

        with attempt("Looking up activation profile for given User"):
            try:
                profile = RegistrationProfile.objects.get(user=user)
            except:
                with attempt("Didn't find activation profile, creating a new one"):
                    profile = RegistrationProfile.objects.create_profile(user)
        
        if profile.activation_key_expired():
            with attempt("Activation key has expired, recreating activation profile"):
                profile = RegistrationProfile.objects.recreate_profile(profile)

        with attempt("Sending email"):
            profile.send_activation_email(Site.objects.get_current())

