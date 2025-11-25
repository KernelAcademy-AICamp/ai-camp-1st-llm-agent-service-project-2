"""
Dashboard API - Overview Statistics
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

from documents.models import Document, RiskAnalysisResult, Summary, KeyClause
from organizations.models import Organization, Project


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_overview(request):
    """
    Get dashboard overview statistics for the current user.

    Returns:
        - total_documents: Total number of documents
        - documents_by_status: Document count grouped by status
        - documents_by_type: Document count grouped by doc_type
        - risk_stats: Risk analysis statistics
        - recent_activity: Recent documents (last 7 days)
        - organization_stats: Organization/Project counts
    """
    user = request.user

    # Document statistics
    user_documents = Document.objects.filter(user=user)
    total_documents = user_documents.count()

    # Documents by status
    documents_by_status = list(
        user_documents.values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )

    # Documents by type
    documents_by_type = list(
        user_documents.values('doc_type')
        .annotate(count=Count('id'))
        .order_by('doc_type')
    )

    # Risk analysis statistics
    risk_analyses = RiskAnalysisResult.objects.filter(document__user=user)
    documents_with_risk = risk_analyses.values('document').distinct().count()

    risk_by_severity = list(
        risk_analyses.values('severity')
        .annotate(count=Count('id'))
        .order_by('severity')
    )

    avg_risk_score = risk_analyses.aggregate(avg=Avg('overall_risk_score'))['avg'] or 0

    high_risk_count = risk_analyses.filter(
        Q(severity='CRITICAL') | Q(severity='HIGH')
    ).values('document').distinct().count()

    # Summary and Clause statistics
    summaries_count = Summary.objects.filter(document__user=user).count()
    clauses_count = KeyClause.objects.filter(document__user=user).count()

    # Recent activity (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_documents = user_documents.filter(created_at__gte=seven_days_ago).count()
    recent_analyses = risk_analyses.filter(created_at__gte=seven_days_ago).count()

    # Organization statistics
    from organizations.models import Membership
    user_memberships = Membership.objects.filter(user=user)
    organizations_count = user_memberships.count()
    projects_count = Project.objects.filter(
        organization__memberships__user=user
    ).distinct().count()

    return Response({
        'total_documents': total_documents,
        'documents_by_status': documents_by_status,
        'documents_by_type': documents_by_type,
        'risk_stats': {
            'documents_analyzed': documents_with_risk,
            'documents_with_risk_analysis': documents_with_risk,
            'avg_risk_score': round(avg_risk_score, 1),
            'high_risk_documents': high_risk_count,
            'risk_by_severity': risk_by_severity
        },
        'analysis_stats': {
            'summaries_generated': summaries_count,
            'clauses_extracted': clauses_count
        },
        'recent_activity': {
            'documents_last_7_days': recent_documents,
            'analyses_last_7_days': recent_analyses
        },
        'organization_stats': {
            'organizations': organizations_count,
            'projects': projects_count
        }
    }, status=status.HTTP_200_OK)
