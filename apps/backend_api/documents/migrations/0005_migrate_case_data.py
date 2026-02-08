# Custom migration to migrate existing Case data to Document + CaseAnalysis

from django.db import migrations
import uuid


def migrate_cases_to_documents(apps, schema_editor):
    """
    Migrate existing Case records to Document + CaseAnalysis
    """
    Case = apps.get_model('cases', 'Case')
    Document = apps.get_model('documents', 'Document')
    CaseAnalysis = apps.get_model('documents', 'CaseAnalysis')
    ChatHistory = apps.get_model('cases', 'ChatHistory')

    # Migrate each Case to Document + CaseAnalysis
    for case in Case.objects.all():
        # Create Document from Case
        document = Document.objects.create(
            user=case.user,
            title=case.title,
            doc_type='CASE',
            status='UPLOADED',
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

        # Extract analysis data
        analysis = case.analysis or {}

        # Create CaseAnalysis from Case.analysis
        CaseAnalysis.objects.create(
            document=document,
            suggested_case_name=analysis.get('suggested_case_name', case.title),
            document_types=analysis.get('document_types', []),
            parties=analysis.get('parties', {}),
            key_dates=analysis.get('key_dates', {}),
            issues=analysis.get('issues', []),
            related_precedents=analysis.get('related_cases', []),  # Note: renamed field
            suggested_next_steps=analysis.get('suggested_next_steps', []),
            scenario=analysis.get('scenario'),
            llm_model=analysis.get('llm_model', 'legacy-migration'),
        )

        # Update ChatHistory to point to the new Document
        ChatHistory.objects.filter(case=case).update(document=document)

    print(f"Migrated {Case.objects.count()} cases to documents")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - just clear the document field in ChatHistory
    """
    ChatHistory = apps.get_model('cases', 'ChatHistory')
    ChatHistory.objects.filter(document__isnull=False).update(document=None)

    # Delete Documents that were created from Cases
    Document = apps.get_model('documents', 'Document')
    Document.objects.filter(doc_type='CASE').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_add_case_analysis'),
        ('cases', '0002_add_document_field'),
    ]

    operations = [
        migrations.RunPython(
            migrate_cases_to_documents,
            reverse_migration
        ),
    ]