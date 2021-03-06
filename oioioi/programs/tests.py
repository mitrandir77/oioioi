from django.test import TestCase
from django.core.urlresolvers import reverse
from oioioi.base.tests import check_not_accessible
from oioioi.contests.models import Submission, ProblemInstance
from oioioi.programs.models import Test, ModelSolution

class TestProgramsViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission']

    def test_submission_views(self):
        self.client.login(username='test_user')
        submission = Submission.objects.get()
        kwargs = {'contest_id': submission.problem_instance.contest.id,
                'submission_id': submission.id}
        show_response = self.client.get(reverse('show_submission_source',
            kwargs=kwargs))
        self.assertEqual(show_response.status_code, 200)
        download_response = self.client.get(reverse(
            'download_submission_source', kwargs=kwargs))
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(show_response.content, download_response.content)
        self.assertIn('main()', show_response.content)
        self.assertTrue(show_response.content.strip().endswith('}'))
        self.assertTrue(download_response['Content-Disposition'].startswith(
            'attachment'))

    def test_test_views(self):
        self.client.login(username='test_admin')
        test = Test.objects.get(name='0')
        kwargs = {'test_id': test.id}
        response = self.client.get(reverse('download_input_file',
            kwargs=kwargs))
        self.assertEqual(response.content.strip(), '1 2')
        response = self.client.get(reverse('download_output_file',
            kwargs=kwargs))
        self.assertEqual(response.content.strip(), '3')

    def test_submissions_permissions(self):
        submission = Submission.objects.get()
        test = Test.objects.get(name='0')
        for view in ['show_submission_source', 'download_submission_source']:
            check_not_accessible(self, view, kwargs={
                'contest_id': submission.problem_instance.contest.id,
                'submission_id': submission.id})
        for view in ['download_input_file', 'download_output_file']:
            check_not_accessible(self, view, kwargs={'test_id': test.id})
        self.client.login(user='test_user')
        for view in ['download_input_file', 'download_output_file']:
            check_not_accessible(self, view, kwargs={'test_id': test.id})

    def test_model_solutions_view(self):
        pi = ProblemInstance.objects.get()
        ModelSolution.objects.recreate_model_submissions(pi)
        url = reverse('oioioiadmin:contests_probleminstance_models',
                args=(pi.id,))
        self.client.login(username='test_admin')
        response = self.client.get(url)
        for element in ['>sum<', '>sum1<', '>sumb0<', '>sums1<', '>100<',
                '>0<']:
            self.assertIn(element, response.content)
        self.assertEqual(response.content.count('subm_status subm_OK'), 9)
        self.assertEqual(response.content.count('subm_status subm_CE'), 2)
        self.assertEqual(response.content.count('>10.00s<'), 5)

class TestSubmissionAdmin(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission']

    def test_submissions_changelist(self):
        self.client.login(username='test_admin')
        pi = ProblemInstance.objects.get()
        ModelSolution.objects.recreate_model_submissions(pi)
        url = reverse('oioioiadmin:contests_submission_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('(sum.c)', response.content)
        self.assertIn('test_user', response.content)
        self.assertIn('subm_status subm_OK', response.content)
