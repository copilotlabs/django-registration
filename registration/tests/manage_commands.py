try: from prism import registration
except: pass

from django.test import TransactionTestCase
from registration.tests.backends import _mock_request
from registration.backends.default import DefaultBackend

from django.core import mail
from registration.management.commands.send_activation_email \
        import Command as SendActivationEmailCommand
from django.core.management.base import CommandError
from django.contrib.auth.models import User
from registration.models import RegistrationProfile
from prism.units.models import Unit

class SendActivationEmailCommand (TransactionTestCase):

    command = SendActivationEmailCommand()
    backend = DefaultBackend()

    def test_no_args(self):
        with self.assertRaises(CommandError):
            self.command.handle()

    def _create_test_user(self, username='bob',
            password='secret', email=None):
        """
        Create a test user

        Email will be username@example.com if not provided

        """
        test_user = self.backend.register(
                        _mock_request(),
                        username=username,
                        email=(email or username+'@example.com'),
                        password1=password
                    )
        self.assertTrue(test_user)
        return (test_user, username, password, email)

    def test_activation_not_active(self):
        new_user, username, password, email = self._create_test_user()
        email_count = len(mail.outbox)
        self.command.handle(userid=new_user.id)
        self.assertEqual(len(mail.outbox), email_count + 1)

    def test_activation_already_active(self):

        new_user, username, password, email = self._create_test_user()
        profile = RegistrationProfile.objects.get(user=new_user)
        self.backend.activate(_mock_request(), profile.activation_key)

        email_count = len(mail.outbox)
        
        self.command.handle(userid=new_user.id)
        self.assertEqual(len(mail.outbox), email_count)

    def test_missing_or_wrong_userid_or_unitid(self):

        user, username, password, email = self._create_test_user()
        unit = Unit(user=user)
        unit.save()
        userid = user.id
        unitid = unit.id
        wrong = -1
        passing_cases = [
            { 'userid': userid, 'unitid': unitid },
            { 'userid': userid },
            { 'unitid': unitid },
        ]
        failing_cases = [
            { 'userid': wrong },
            { 'userid': wrong , 'unitid': wrong },
            { 'userid': userid, 'unitid': wrong },
            { 'userid': wrong , 'unitid': unitid },
            { 'unitid': wrong },
        ]

        for kwargs in passing_cases:
            email_count = len(mail.outbox)
            self.command.handle(**kwargs)
            self.assertEqual(len(mail.outbox), email_count + 1)
            user.is_valid = False

        for kwargs in failing_cases:
            with self.assertRaises(CommandError):
                self.command.handle(**kwargs)
