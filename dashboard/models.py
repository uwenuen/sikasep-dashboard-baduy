# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AppSettings(models.Model):
    id = models.BigAutoField(primary_key=True)
    setting_key = models.CharField(unique=True, max_length=100)
    setting_value = models.JSONField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'app_settings'


class AuditLogs(models.Model):
    id = models.BigAutoField(primary_key=True)
    actor_user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100, blank=True, null=True)
    entity_id = models.PositiveBigIntegerField(blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'audit_logs'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class Cadres(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField('Users', models.DO_NOTHING)
    cadre_code = models.CharField(unique=True, max_length=50)
    region = models.ForeignKey('Regions', models.DO_NOTHING, blank=True, null=True)
    assigned_area = models.CharField(max_length=150, blank=True, null=True)
    active = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cadres'


class Citizens(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField('Users', models.DO_NOTHING, blank=True, null=True)
    cadre = models.ForeignKey(Cadres, models.DO_NOTHING, blank=True, null=True)
    region = models.ForeignKey('Regions', models.DO_NOTHING, blank=True, null=True)
    nik = models.CharField(unique=True, max_length=30, blank=True, null=True)
    name = models.CharField(max_length=150)
    initials = models.CharField(max_length=10, blank=True, null=True)
    gender = models.CharField(max_length=9, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    age = models.PositiveSmallIntegerField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    household_size = models.PositiveSmallIntegerField(blank=True, null=True)
    consent_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'citizens'


class DashboardMetricSnapshots(models.Model):
    id = models.BigAutoField(primary_key=True)
    snapshot_date = models.DateField()
    metric_key = models.CharField(max_length=100)
    metric_value = models.DecimalField(max_digits=14, decimal_places=2)
    dimension_key = models.CharField(max_length=100, blank=True, null=True)
    dimension_value = models.CharField(max_length=150, blank=True, null=True)
    payload = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'dashboard_metric_snapshots'
        unique_together = (('snapshot_date', 'metric_key', 'dimension_key', 'dimension_value'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class EducationMaterials(models.Model):
    id = models.BigAutoField(primary_key=True)
    slug = models.CharField(unique=True, max_length=120)
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=80)
    summary = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    education_type = models.CharField(max_length=7)
    youtube_url = models.CharField(max_length=255, blank=True, null=True)
    image_path = models.CharField(max_length=255, blank=True, null=True)
    video_url = models.CharField(max_length=255, blank=True, null=True)
    audio_url = models.CharField(max_length=255, blank=True, null=True)
    thumbnail_url = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=9)
    created_by_user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    reviewed_by_user = models.ForeignKey('Users', models.DO_NOTHING, related_name='educationmaterials_reviewed_by_user_set', blank=True, null=True)
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'education_materials'

    def __str__(self):
        return self.title

    @property
    def display_status(self):
        mapping = {
            'published': 'Aktif',
            'review': 'Review',
            'draft': 'Draft'
        }
        return mapping.get(self.status, self.status.capitalize() if self.status else 'Draft')

    @property
    def display_type(self):
        mapping = {
            'youtube': 'Link YouTube',
            'image': 'Gambar'
        }
        return mapping.get(self.education_type, self.education_type)

    @property
    def file_url(self):
        if self.image_path:
            return self.image_path if self.image_path.startswith(('http://', 'https://', '/')) else f"/media/{self.image_path}"
        return None




class Kader(models.Model):
    cadre_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    region = models.CharField(max_length=150, default="Kawasan Baduy")
    phone = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, default="Aktif")
    screening_count = models.IntegerField(default=0)
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kader_data"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.cadre_code} - {self.name}"


class MedicationLogs(models.Model):
    id = models.BigAutoField(primary_key=True)
    citizen = models.ForeignKey(Citizens, models.DO_NOTHING)
    treatment_course = models.ForeignKey('TbTreatmentCourses', models.DO_NOTHING, blank=True, null=True)
    input_by_user = models.ForeignKey('Users', models.DO_NOTHING)
    dose_date = models.DateField()
    status_minum_obat = models.CharField(max_length=5)
    taken_time = models.TimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    reported_late = models.IntegerField()
    reported_at = models.DateTimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'medication_logs'
        unique_together = (('citizen', 'dose_date'),)


class PasswordResetTokens(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING)
    token_hash = models.CharField(unique=True, max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'password_reset_tokens'


class Permissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=100)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'permissions'


class Referrals(models.Model):
    id = models.BigAutoField(primary_key=True)
    referral_code = models.CharField(unique=True, max_length=40)
    screening = models.ForeignKey('ScreeningSessions', models.DO_NOTHING, blank=True, null=True)
    citizen = models.ForeignKey(Citizens, models.DO_NOTHING)
    created_by_user = models.ForeignKey('Users', models.DO_NOTHING)
    destination = models.CharField(max_length=150)
    status = models.CharField(max_length=15)
    follow_up_status = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    referral_date = models.DateField()
    scheduled_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'referrals'


class Regions(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=150)
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'regions'


class Reports(models.Model):
    id = models.BigAutoField(primary_key=True)
    report_code = models.CharField(unique=True, max_length=50)
    report_type = models.CharField(max_length=14)
    title = models.CharField(max_length=180)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    region = models.ForeignKey(Regions, models.DO_NOTHING, blank=True, null=True)
    cadre = models.ForeignKey(Cadres, models.DO_NOTHING, blank=True, null=True)
    generated_by_user = models.ForeignKey('Users', models.DO_NOTHING)
    summary = models.TextField(blank=True, null=True)
    payload = models.JSONField(blank=True, null=True)
    file_url = models.CharField(max_length=255, blank=True, null=True)
    generated_at = models.DateTimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'reports'


class RolePermissions(models.Model):
    pk = models.CompositePrimaryKey('role_id', 'permission_id')
    role = models.ForeignKey('Roles', models.DO_NOTHING)
    permission = models.ForeignKey(Permissions, models.DO_NOTHING)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'role_permissions'


class Roles(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'roles'


class ScreeningAnswers(models.Model):
    id = models.BigAutoField(primary_key=True)
    screening = models.ForeignKey('ScreeningSessions', models.DO_NOTHING)
    question = models.ForeignKey('ScreeningQuestions', models.DO_NOTHING)
    answer_value = models.CharField(max_length=50)
    answer_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'screening_answers'
        unique_together = (('screening', 'question'),)


class ScreeningPhysicalMeasurements(models.Model):
    id = models.BigAutoField(primary_key=True)
    screening = models.OneToOneField('ScreeningSessions', models.DO_NOTHING)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    bmi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    nutrition_status = models.CharField(max_length=100, blank=True, null=True)
    has_diabetes = models.IntegerField()
    has_kidney_disease = models.IntegerField()
    has_hiv = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'screening_physical_measurements'


class ScreeningQuestions(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=80)
    group_code = models.CharField(max_length=13)
    label = models.CharField(max_length=255)
    factor_label = models.CharField(max_length=255, blank=True, null=True)
    answer_type = models.CharField(max_length=6)
    respondent_scope = models.CharField(max_length=5)
    sort_order = models.PositiveSmallIntegerField()
    is_active = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'screening_questions'


class ScreeningResults(models.Model):
    id = models.BigAutoField(primary_key=True)
    screening = models.OneToOneField('ScreeningSessions', models.DO_NOTHING)
    result = models.CharField(max_length=8)
    status_label = models.CharField(max_length=100)
    score = models.DecimalField(max_digits=6, decimal_places=2)
    reason_summary = models.TextField(blank=True, null=True)
    recommendation = models.TextField(blank=True, null=True)
    factors = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'screening_results'


class ScreeningSessions(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=40)
    citizen = models.ForeignKey(Citizens, models.DO_NOTHING)
    created_by_user = models.ForeignKey('Users', models.DO_NOTHING)
    cadre = models.ForeignKey(Cadres, models.DO_NOTHING, blank=True, null=True)
    screening_date = models.DateField()
    respondent_category = models.CharField(max_length=6)
    self_screening = models.IntegerField()
    sync_status = models.CharField(max_length=7)
    status = models.CharField(max_length=9)
    consent_accepted_at = models.DateTimeField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    gps_accuracy = models.FloatField(blank=True, null=True)
    gps_recorded_at = models.DateTimeField(blank=True, null=True)
    location_address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'screening_sessions'


class ScreeningTreatmentHistories(models.Model):
    id = models.BigAutoField(primary_key=True)
    screening = models.OneToOneField(ScreeningSessions, models.DO_NOTHING)
    previous_tb_treatment = models.IntegerField()
    treatment_completed = models.IntegerField(blank=True, null=True)
    status_label = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'screening_treatment_histories'


class TbTreatmentCourses(models.Model):
    id = models.BigAutoField(primary_key=True)
    citizen = models.ForeignKey(Citizens, models.DO_NOTHING)
    created_by_user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    regimen_name = models.CharField(max_length=150, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=15)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tb_treatment_courses'


class UserProfiles(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField('Users', models.DO_NOTHING)
    nik = models.CharField(unique=True, max_length=30, blank=True, null=True)
    gender = models.CharField(max_length=9, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    age = models.PositiveSmallIntegerField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    region = models.ForeignKey(Regions, models.DO_NOTHING, blank=True, null=True)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_profiles'


class UserSessions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING)
    token_jti = models.CharField(unique=True, max_length=36)
    refresh_token_hash = models.CharField(max_length=64, blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_sessions'


class Users(models.Model):
    id = models.BigAutoField(primary_key=True)
    role = models.ForeignKey(Roles, models.DO_NOTHING)
    username = models.CharField(unique=True, max_length=80)
    email = models.CharField(unique=True, max_length=150, blank=True, null=True)
    password_hash = models.CharField(max_length=255)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True, null=True)
    status = models.CharField(max_length=9)
    email_verified_at = models.DateTimeField(blank=True, null=True)
    last_login_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'
