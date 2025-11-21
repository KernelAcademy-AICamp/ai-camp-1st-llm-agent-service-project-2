# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class PrecedentFeedback(models.Model):
    id = models.UUIDField(primary_key=True)
    precedent_id = models.CharField(max_length=200)
    user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    query = models.CharField(max_length=1000)
    feedback_type = models.CharField(max_length=20)
    is_helpful = models.BooleanField()
    relevance_score = models.IntegerField(blank=True, null=True)
    comment = models.CharField(max_length=500, blank=True, null=True)
    session_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'precedent_feedback'


class PrecedentFeedbackStats(models.Model):
    precedent_id = models.CharField(primary_key=True, max_length=200)
    total_likes = models.IntegerField()
    total_dislikes = models.IntegerField()
    like_ratio = models.FloatField()
    total_feedback_count = models.IntegerField()
    avg_relevance_score = models.FloatField(blank=True, null=True)
    should_exclude = models.BooleanField()
    exclusion_threshold = models.FloatField()
    last_updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'precedent_feedback_stats'


class Precedents(models.Model):
    id = models.UUIDField(primary_key=True)
    case_number = models.CharField(unique=True, max_length=100)
    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True, null=True)
    full_text = models.TextField(blank=True, null=True)
    judgment_summary = models.TextField(blank=True, null=True)
    reference_statutes = models.CharField()
    reference_precedents = models.CharField()
    precedent_id = models.CharField(max_length=100, blank=True, null=True)
    court = models.CharField(max_length=100)
    decision_date = models.DateTimeField()
    case_type = models.CharField(max_length=50)
    specialization_tags = models.CharField()
    citation = models.CharField(max_length=200, blank=True, null=True)
    case_link = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'precedents'


class Users(models.Model):
    id = models.UUIDField(primary_key=True)
    email = models.CharField(unique=True)
    hashed_password = models.CharField()
    full_name = models.CharField()
    lawyer_registration_number = models.CharField(blank=True, null=True)
    specializations = models.TextField()  # This field type is a guess.
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'users'
