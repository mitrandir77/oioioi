from django.test import TestCase
from django.core.urlresolvers import reverse
from oioioi.base.tests import check_not_accessible
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.messages.models import Message

class TestMessages(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_messages']

    def test_visibility(self):
        contest = Contest.objects.get()
        all_messages = ['problem-question', 'contest-question',
                'public-answer', 'private-answer']
        url = reverse('contest_messages', kwargs={'contest_id': contest.id})
        def check_visibility(*should_be_visible):
            response = self.client.get(url)
            for m in all_messages:
                if m in should_be_visible:
                    self.assertIn(m, response.content)
                else:
                    self.assertNotIn(m, response.content)
        self.client.login(username='test_user')
        check_visibility('public-answer', 'private-answer')
        self.client.login(username='test_user2')
        check_visibility('public-answer')
        self.client.login(username='test_admin')
        check_visibility('public-answer', 'private-answer')

    def test_new_labels(self):
        self.client.login(username='test_user')
        contest = Contest.objects.get()
        list_url = reverse('contest_messages',
                kwargs={'contest_id': contest.id})
        response = self.client.get(list_url)
        self.assertEqual(response.content.count('>NEW<'), 2)
        public_answer = Message.objects.get(topic='public-answer')
        response = self.client.get(reverse('message', kwargs={
            'contest_id': contest.id, 'message_id': public_answer.id}))
        self.assertIn('public-answer-body', response.content)
        self.assertNotIn('contest-question', response.content)
        self.assertNotIn('problem-question', response.content)
        response = self.client.get(list_url)
        self.assertEqual(response.content.count('>NEW<'), 1)

    def test_ask_and_reply(self):
        self.client.login(username='test_user2')
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        url = reverse('add_contest_message', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertEqual(len(form.fields['category'].choices), 2)

        post_data = {
                'category': str(pi.id),
                'topic': 'the-new-question',
                'content': 'the-new-body',
            }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        new_question = Message.objects.get(topic='the-new-question')
        self.assertEqual(new_question.content, 'the-new-body')
        self.assertEqual(new_question.kind, 'QUESTION')
        self.assertIsNone(new_question.top_reference)
        self.assertEqual(new_question.contest, contest)
        self.assertIsNone(new_question.problem)
        self.assertEqual(new_question.problem_instance, pi)
        self.assertEqual(new_question.author.username, 'test_user2')

        self.client.login(username='test_admin')
        list_url = reverse('contest_messages',
                kwargs={'contest_id': contest.id})
        response = self.client.get(list_url)
        self.assertIn('the-new-question', response.content)

        url = reverse('message_reply', kwargs={'contest_id': contest.id,
            'message_id': new_question.id})
        response = self.client.get(url)
        self.assertIn('form', response.context)

        post_data = {
                'kind': 'PUBLIC',
                'topic': 're-new-question',
                'content': 're-new-body',
            }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        new_reply = Message.objects.get(topic='re-new-question')
        self.assertEqual(new_reply.content, 're-new-body')
        self.assertEqual(new_reply.kind, 'PUBLIC')
        self.assertEqual(new_reply.top_reference, new_question)
        self.assertEqual(new_reply.contest, contest)
        self.assertIsNone(new_reply.problem)
        self.assertEqual(new_reply.problem_instance, pi)
        self.assertEqual(new_reply.author.username, 'test_admin')

        self.client.login(username='test_user')
        q_url = reverse('message', kwargs={'contest_id': contest.id,
            'message_id': new_question.id})
        check_not_accessible(self, q_url)
        repl_url = reverse('message', kwargs={'contest_id': contest.id,
            'message_id': new_reply.id})
        response = self.client.get(repl_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('re-new-question', response.content)
        self.assertIn('re-new-body', response.content)
        self.assertNotIn('the-new-question', response.content)
        self.assertNotIn('the-new-body', response.content)
        response = self.client.get(list_url)
        self.assertIn(repl_url, response.content)
        self.assertIn('re-new-question', response.content)
        self.assertNotIn('the-new-question', response.content)

        self.client.login(username='test_user2')
        response = self.client.get(q_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('the-new-question', response.content)
        self.assertIn('the-new-body', response.content)
        self.assertIn('re-new-body', response.content)
        response = self.client.get(list_url)
        self.assertIn(q_url, response.content)
        self.assertIn('re-new-question', response.content)
        self.assertNotIn('the-new-question', response.content)
