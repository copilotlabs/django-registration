try: from prism import registration
except: pass

import datetime

import simplejson as json

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from registration import forms
from django.contrib.auth.forms import SetPasswordForm
from registration.models import RegistrationProfile


class BackendRegistrationViewTests(TestCase):
    """
    Test the registration views.

    """
    urls = 'registration.tests.urls'

    def _create_test_user(self, username='bob',
            password='secret', email=None):
        """
        Create a test user

        Email will be username@example.com if not provided

        """

        email = (email or username+'@example.com')
        self.client.post(reverse('registration_register'),
                         data={'username': username,
                               'email': email,
                               'password1': password,
                               'password2': password})
        profile = RegistrationProfile.objects.get(user__username=username)
        user = User.objects.get(username=username)
        return (profile, user, username, password, email)

    def setUp(self):
        """
        These tests use the default backend, since we know it's
        available; that needs to have ``ACCOUNT_ACTIVATION_DAYS`` set.

        """
        self.old_activation = getattr(settings, 'ACCOUNT_ACTIVATION_DAYS', None)
        if self.old_activation is None:
            settings.ACCOUNT_ACTIVATION_DAYS = 7

    def tearDown(self):
        """
        Yank ``ACCOUNT_ACTIVATION_DAYS`` back out if it wasn't
        originally set.

        """
        if self.old_activation is None:
            settings.ACCOUNT_ACTIVATION_DAYS = self.old_activation

    def test_registration_view_initial(self):
        """
        A ``GET`` to the ``register`` view uses the appropriate
        template and populates the registration form into the context.

        """
        response = self.client.get(reverse('registration_register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'registration/registration_form.html')
        self.failUnless(isinstance(response.context['form'],
                                   forms.RegistrationForm))

    def test_registration_view_success(self):
        """
        A ``POST`` to the ``register`` view with valid data properly
        creates a new user and issues a redirect.

        """
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'})
        self.assertRedirects(response,
                             'http://testserver%s' % reverse('registration_complete'))
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_view_success_json(self):
        """
        A ``POST`` to the ``register`` view with valid data properly
        creates a new user and returns a json object.

        """
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'},
                                    **{'HTTP_ACCEPT':'application/json'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['success'])
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_view_failure(self):
        """
        A ``POST`` to the ``register`` view with invalid data does not
        create a user, and displays appropriate error messages.

        """
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'bob',
                                          'email': 'bobe@example.com',
                                          'password1': 'foo',
                                          'password2': 'bar'})
        self.assertEqual(response.status_code, 200)
        self.failIf(response.context['form'].is_valid())
        self.assertFormError(response, 'form', field=None,
                             errors=u"The two password fields didn't match.")
        self.assertEqual(len(mail.outbox), 0)

    def test_registration_view_failure_json(self):
        """
        A ``POST`` to the ``register`` view with invalid data does not
        create a user, and return json object with appropriate
        error messages.

        """
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'bob',
                                          'email': 'bobe@example.com',
                                          'password1': 'foo',
                                          'password2': 'bar'},
                                    **{'HTTP_ACCEPT':'application/json'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(json.loads(response.content)['success'])
        self.assertTrue(u"The two password fields didn't match." in json.loads(response.content)['errors'].get('__all__', None))
        self.assertEqual(len(mail.outbox), 0)

    def test_registration_view_closed(self):
        """
        Any attempt to access the ``register`` view when registration
        is closed fails and redirects.

        """
        old_allowed = getattr(settings, 'REGISTRATION_OPEN', True)
        settings.REGISTRATION_OPEN = False

        closed_redirect = 'http://testserver%s' % reverse('registration_disallowed')

        response = self.client.get(reverse('registration_register'))
        self.assertRedirects(response, closed_redirect)

        # Even if valid data is posted, it still shouldn't work.
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'})
        self.assertRedirects(response, closed_redirect)
        self.assertEqual(RegistrationProfile.objects.count(), 0)

        settings.REGISTRATION_OPEN = old_allowed

    def test_registration_view_closed_json(self):
        """
        Any attempt to access the ``register`` view when registration
        is closed fails and redirects.

        """
        def assert_closed(response):
            self.assertEqual(response.status_code, 200)
            self.assertFalse(json.loads(response.content)['success'])
            self.assertTrue(u"Registration is closed." in json.loads(response.content)['errors'])

        old_allowed = getattr(settings, 'REGISTRATION_OPEN', True)
        settings.REGISTRATION_OPEN = False

        closed_redirect = 'http://testserver%s' % reverse('registration_disallowed')

        response = self.client.get(reverse('registration_register'),
                                    **{'HTTP_ACCEPT':'application/json'})
        assert_closed(response)

        # Even if valid data is posted, it still shouldn't work.
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'},
                                    **{'HTTP_ACCEPT':'application/json'})
        assert_closed(response)
        self.assertEqual(RegistrationProfile.objects.count(), 0)

        settings.REGISTRATION_OPEN = old_allowed

    def test_registration_template_name(self):
        """
        Passing ``template_name`` to the ``register`` view will result
        in that template being used.

        """
        response = self.client.get(reverse('registration_test_register_template_name'))
        self.assertTemplateUsed(response,
                                'registration/test_template_name.html')

    def test_registration_extra_context(self):
        """
        Passing ``extra_context`` to the ``register`` view will
        correctly populate the context.

        """
        response = self.client.get(reverse('registration_test_register_extra_context'))
        self.assertEqual(response.context['foo'], 'bar')
        # Callables in extra_context are called to obtain the value.
        self.assertEqual(response.context['callable'], 'called')

    def test_registration_disallowed_url(self):
        """
        Passing ``disallowed_url`` to the ``register`` view will
        result in a redirect to that URL when registration is closed.

        """
        old_allowed = getattr(settings, 'REGISTRATION_OPEN', True)
        settings.REGISTRATION_OPEN = False

        closed_redirect = 'http://testserver%s' % reverse('registration_test_custom_disallowed')

        response = self.client.get(reverse('registration_test_register_disallowed_url'))
        self.assertRedirects(response, closed_redirect)

        settings.REGISTRATION_OPEN = old_allowed

    def test_registration_success_url(self):
        """
        Passing ``success_url`` to the ``register`` view will result
        in a redirect to that URL when registration is successful.
        
        """
        success_redirect = 'http://testserver%s' % reverse('registration_test_custom_success_url')
        response = self.client.post(reverse('registration_test_register_success_url'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'})
        self.assertRedirects(response, success_redirect)

    def test_valid_activation(self):
        """
        Test that the ``activate`` view properly handles a valid
        activation (in this case, based on the default backend's
        activation window).

        """
        success_redirect = 'http://testserver%s' % reverse('registration_activation_complete')
        
        # First, register an account.
        self.client.post(reverse('registration_register'),
                         data={'username': 'alice',
                               'email': 'alice@example.com',
                               'password1': 'swordfish',
                               'password2': 'swordfish'})
        profile = RegistrationProfile.objects.get(user__username='alice')
        response = self.client.get(reverse('registration_activate',
                                           kwargs={'activation_key': profile.activation_key}))
        self.assertRedirects(response, success_redirect)
        self.failUnless(User.objects.get(username='alice').is_active)

    def test_invalid_activation(self):
        """
        Test that the ``activate`` view properly handles an invalid
        activation (in this case, based on the default backend's
        activation window).

        """
        # Register an account and reset its date_joined to be outside
        # the activation window.
        self.client.post(reverse('registration_register'),
                         data={'username': 'bob',
                               'email': 'bob@example.com',
                               'password1': 'secret',
                               'password2': 'secret'})
        expired_user = User.objects.get(username='bob')
        expired_user.date_joined = expired_user.date_joined - datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        expired_user.save()

        expired_profile = RegistrationProfile.objects.get(user=expired_user)
        response = self.client.get(reverse('registration_activate',
                                           kwargs={'activation_key': expired_profile.activation_key}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['activation_key'],
                         expired_profile.activation_key)
        self.failIf(User.objects.get(username='bob').is_active)

    def test_activation_success_url(self):
        """
        Passing ``success_url`` to the ``activate`` view and
        successfully activating will result in that URL being used for
        the redirect.
        
        """
        success_redirect = 'http://testserver%s' % reverse('registration_test_custom_success_url')
        self.client.post(reverse('registration_register'),
                         data={'username': 'alice',
                               'email': 'alice@example.com',
                               'password1': 'swordfish',
                               'password2': 'swordfish'})
        profile = RegistrationProfile.objects.get(user__username='alice')
        response = self.client.get(reverse('registration_test_activate_success_url',
                                           kwargs={'activation_key': profile.activation_key}))
        self.assertRedirects(response, success_redirect)
        
    def test_activation_template_name(self):
        """
        Passing ``template_name`` to the ``activate`` view will result
        in that template being used.

        """
        response = self.client.get(reverse('registration_test_activate_template_name',
                                   kwargs={'activation_key': 'foo'}))
        self.assertTemplateUsed(response, 'registration/test_template_name.html')

    def test_activation_extra_context(self):
        """
        Passing ``extra_context`` to the ``activate`` view will
        correctly populate the context.

        """
        response = self.client.get(reverse('registration_test_activate_extra_context',
                                           kwargs={'activation_key': 'foo'}))
        self.assertEqual(response.context['foo'], 'bar')
        # Callables in extra_context are called to obtain the value.
        self.assertEqual(response.context['callable'], 'called')


class NamelessBackendRegistrationViewTests(object):
    """
    Test views specific to NamelessBackend
    """

    def _create_test_user(self, username='user@example.com',
            password='secret', email='user@example.com'):
        """
        Create a test user

        'username' and 'email' must match if provided

        """
        self.assertTrue(username == email)
        return super(NamelessBackendRegistrationViewTests, self)._create_test_user(
                        username=username,
                        email=email,
                        password=password
                    )

    def test_activate_np_first_click_valid_code(self):
        """
        Test the activate_new_password view's initial response given a valid activation code

        """

        # User registers an account.
        profile, user, username, password, email = self._create_test_user()

        # User clicks link
        response = self.client.get(reverse('registration_activate_new_password',
                            kwargs={'activation_key': profile.activation_key}))

        # Check that we respond with a set-password page
        self.assertTemplateUsed(response,
                                'registration/password_set_form.html')
        self.assertTrue(isinstance(response.context['form'], SetPasswordForm))

        # User shouldn't be active at this point
        self.assertFalse(user.is_active)

    def test_activate_np_first_click_no_code(self):
        """
        Test the activate_new_password view's initial response given an invalid link

        """

        # User registers an account.
        profile, user, username, password, email = self._create_test_user()

        # User clicks incorrect link (maybe cut off in email)
        response = self.client.get(reverse('registration_activate_new_password',
                            kwargs={'activation_key': ''}))

        # Check that we respond with a 'something went wrong' page
        self.assertTrue('registration/activate.html' in response.templates)
        self.assertFalse('account' in response.context)

        # User shouldn't be active at this point
        self.assertFalse(user.is_active)

    def test_activate_np_first_click_expired_code(self):
        """
        Test the activate_new_password view's initial response given an invalid link

        """

        # User registers an account.
        profile, user, username, password, email = self._create_test_user()
        activation_key = profile.activation_key
        user.date_joined = user.date_joined - datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        user.save()

        # User clicks old link
        response = self.client.get(reverse('registration_activate_new_password',
                            kwargs={'activation_key': activation_key}))

        # Check that we respond with a 'something went wrong' page
        self.assertTrue('registration/activate.html' in response.templates)
        self.assertFalse('account' in response.context)

        # User shouldn't be active at this point
        self.assertFalse(user.is_active)

    def test_activate_np_complete_success(self):
        """
        Test the activate_new_password view's initial response given a valid activation code

        """

        # User registers an account.
        profile, user, username, password, email = self._create_test_user()

        # User clicks link
        response = self.client.get(reverse('registration_activate_new_password',
                            kwargs={'activation_key': profile.activation_key}))

        # Check that we respond with a set-password page
        self.assertTemplateUsed(response,
                                'registration/password_set_form.html')
        self.assertTrue(isinstance(response.context['form'], SetPasswordForm))

        # User submits SetPasswordForm
        response = self.client.get(reverse('registration_activate_new_password',
                                    kwargs={'new_password1': 'newpass',
                                            'new_password2': 'newpass'}))

        # should perform post_activation_redirect
        self.assertRedirects(response, (user.get_absolute_url(), (), {}))

        # User should be active at this point
        self.assertFalse(user.is_active)

    def test_activate_np_post_activate_link(self):
        """
        steps: valid link clicked
            -> password entered
            -> user activated
            -> link loaded again (new session?)
            -> invalid message
        """

        # User registers an account.
        profile, user, username, password, email = self._create_test_user()

        # User clicks link
        response = self.client.get(reverse('registration_activate_new_password',
                            kwargs={'activation_key': profile.activation_key}))

        # Check that we respond with a set-password page
        self.assertTemplateUsed(response,
                                'registration/password_set_form.html')
        self.assertTrue(isinstance(response.context['form'], SetPasswordForm))

        # User submits SetPasswordForm
        response = self.client.get(reverse('registration_activate_new_password',
                                    kwargs={'new_password1': 'newpass',
                                            'new_password2': 'newpass'}))

        # should perform post_activation_redirect
        self.assertRedirects(response, (user.get_absolute_url(), (), {}))

        # User should be active at this point
        self.assertFalse(user.is_active)

        # User clicks link again
        response = self.client.get(reverse('registration_activate_new_password',
                            kwargs={'activation_key': profile.activation_key}))

        # Check that we respond with a 'something went wrong' page
        self.assertTrue('registration/activate.html' in response.templates)
        self.assertFalse('account' in response.context)

        # User should still be active
        self.assertFalse(user.is_active)

    def test_activate_np_multi_click(self):
        """
        steps: valid link clicked
            -> link reloaded (new session?)
            -> password entered
            -> user activated
        """


        # User registers an account.
        profile, user, username, password, email = self._create_test_user()

        # User clicks link
        self.client.get(reverse('registration_activate_new_password',
                            kwargs={'activation_key': profile.activation_key}))
        # User clicks link again
        response = self.client.get(reverse('registration_activate_new_password',
                            kwargs={'activation_key': profile.activation_key}))

        # Check that we respond with a set-password page
        self.assertTemplateUsed(response,
                                'registration/password_set_form.html')
        self.assertTrue(isinstance(response.context['form'], SetPasswordForm))

        # User submits SetPasswordForm
        response = self.client.get(reverse('registration_activate_new_password',
                                    kwargs={'new_password1': 'newpass',
                                            'new_password2': 'newpass'}))

        # should perform post_activation_redirect
        self.assertRedirects(response, (user.get_absolute_url(), (), {}))

        # User should be active at this point
        self.assertFalse(user.is_active)
