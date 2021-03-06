from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _
from django.dispatch import receiver
from django.db.models.signals import post_save
from oioioi.base.fields import EnumRegistry, EnumField
from oioioi.problems.models import Problem, make_problem_filename
from oioioi.filetracker.fields import FileField
from oioioi.contests.models import Submission, SubmissionReport, \
        submission_statuses, submission_report_kinds, ProblemInstance
from oioioi.contests.fields import ScoreField

import os.path

test_kinds = EnumRegistry()
test_kinds.register('NORMAL', _("Normal test"))
test_kinds.register('EXAMPLE', _("Example test"))

class Test(models.Model):
    problem = models.ForeignKey(Problem)
    name = models.CharField(max_length=30, verbose_name=_("name"))
    input_file = FileField(upload_to=make_problem_filename,
            verbose_name=_("input"), null=True, blank=True)
    output_file = FileField(upload_to=make_problem_filename,
            verbose_name=_("output/hint"), null=True, blank=True)
    kind = EnumField(test_kinds, verbose_name=_("kind"))
    group = models.CharField(max_length=30, verbose_name=_("group"))
    time_limit = models.IntegerField(verbose_name=_("time limit (ms)"),
            null=True, blank=True)
    memory_limit = models.IntegerField(verbose_name=_("memory limit (kB)"),
            null=True, blank=True)
    max_score = models.IntegerField(verbose_name=_("score"),
            default=10)

class OutputChecker(models.Model):
    problem = models.OneToOneField(Problem)
    exe_file = FileField(upload_to=make_problem_filename,
            null=True, blank=True)

@receiver(post_save, sender=Problem)
def _add_output_checker_to_problem(sender, instance, created, **kwargs):
    if created:
        OutputChecker(problem=instance).save()

model_solution_kinds = EnumRegistry()
model_solution_kinds.register('NORMAL', _("Model solution"))
model_solution_kinds.register('SLOW', _("Slow solution"))
model_solution_kinds.register('INCORRECT', _("Incorrect solution"))

class ModelSolutionsManager(models.Manager):
    def recreate_model_submissions(self, problem_instance):
        with transaction.commit_on_success():
            for model_submission in ModelProgramSubmission.objects.filter(
                    problem_instance=problem_instance):
                model_submission.delete()
        controller = problem_instance.contest.controller
        for model_solution in self.filter(problem=problem_instance.problem):
            with transaction.commit_on_success():
                submission = ModelProgramSubmission(
                        model_solution=model_solution,
                        problem_instance=problem_instance,
                        source_file=model_solution.source_file)
                submission.save()
            controller.judge(submission)

class ModelSolution(models.Model):
    objects = ModelSolutionsManager()

    problem = models.ForeignKey(Problem)
    name = models.CharField(max_length=30, verbose_name=_("name"))
    source_file = FileField(upload_to=make_problem_filename,
            verbose_name=_("source"))
    kind = EnumField(model_solution_kinds, verbose_name=_("kind"))

    @property
    def short_name(self):
        return self.name.rsplit('.', 1)[0]

@receiver(post_save, sender=ProblemInstance)
def _autocreate_model_submissions_for_problem_instance(sender, instance,
        created, raw, **kwargs):
    if created and not raw:
        ModelSolution.objects.recreate_model_submissions(instance)

@receiver(post_save, sender=ModelSolution)
def _autocreate_model_submissions_for_model_solutions(sender, instance,
        created, raw, **kwargs):
    if created and not raw:
        pis = ProblemInstance.objects.filter(problem=instance.problem)
        for pi in pis:
            ModelSolution.objects.recreate_model_submissions(pi)

def make_submission_filename(instance, filename):
    if not instance.id:
        instance.save()
    return 'submissions/%s/%d%s' % (instance.problem_instance.contest.id,
            instance.id, os.path.splitext(filename)[1])

class ProgramSubmission(Submission):
    source_file = FileField(upload_to=make_submission_filename)

class ModelProgramSubmission(ProgramSubmission):
    model_solution = models.ForeignKey(ModelSolution)

submission_statuses.register('CE', _("Compilation failed"))
submission_statuses.register('RE', _("Runtime error"))
submission_statuses.register('WA', _("Wrong answer"))
submission_statuses.register('TLE', _("Time limit exceeded"))
submission_statuses.register('MLE', _("Memory limit exceeded"))
submission_statuses.register('SE', _("System error"))
submission_statuses.register('SV', _("Security violation"))

submission_report_kinds.register('INITIAL', _("Initial report"))
submission_report_kinds.register('HIDDEN', _("Hidden report (for admins only)"))

class CompilationReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport)
    status = EnumField(submission_statuses)
    compiler_output = models.TextField()

class TestReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport)
    status = EnumField(submission_statuses)
    comment = models.CharField(max_length=255, blank=True)
    score = ScoreField(blank=True)
    time_used = models.IntegerField(blank=True)

    test = models.ForeignKey(Test, blank=True, null=True,
            on_delete=models.SET_NULL)
    test_name = models.CharField(max_length=30)
    test_group = models.CharField(max_length=30)
    test_time_limit = models.IntegerField(null=True, blank=True)
    test_max_score = models.IntegerField(null=True, blank=True)

class GroupReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport)
    group = models.CharField(max_length=30)
    score = ScoreField()
    status = EnumField(submission_statuses)
