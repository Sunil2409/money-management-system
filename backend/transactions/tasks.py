import io
import logging
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Sum
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from .models import Transaction

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(name='transactions.tasks.dispatch_monthly_statements')
def dispatch_monthly_statements():
    """Trigger individual statement tasks for all active users for the previous month."""
    now = datetime.utcnow()
    # Calculate previous month
    if now.month == 1:
        prev_month = 12
        prev_year = now.year - 1
    else:
        prev_month = now.month - 1
        prev_year = now.year

    active_user_ids = User.objects.filter(is_active=True).values_list('id', flat=True)
    for user_id in active_user_ids:
        generate_monthly_pdf_statement.delay(user_id, prev_year, prev_month)
    return f"Dispatched {len(active_user_ids)} statement generation jobs."


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='transactions.tasks.generate_monthly_pdf_statement'
)
def generate_monthly_pdf_statement(self, user_id: int, year: int, month: int):
    """Generates an itemized monthly statement and uploads it to an encrypted private S3 bucket."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found.")
        return

    # 1. Aggregate monthly transactions
    qs = Transaction.objects.filter(
        user=user,
        date__year=year,
        date__month=month
    ).order_by('-date')

    income_total = qs.filter(status='income').aggregate(total=Sum('amount'))['total'] or 0
    spent_total = qs.filter(status='spent').aggregate(total=Sum('amount'))['total'] or 0
    net_savings = income_total - spent_total

    # 2. Build PDF in memory using ReportLab (Low RAM footprint)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    elements = []
    styles = getSampleStyleSheet()

    # Title & Metadata
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=12
    )
    elements.append(Paragraph(f"Monthly Financial Statement — {datetime(year, month, 1).strftime('%B %Y')}", title_style))
    elements.append(Paragraph(f"Account Holder: <b>{user.username}</b> ({user.email})", styles['Normal']))
    elements.append(Spacer(1, 14))

    # Summary Card Table
    summary_data = [
        ["Total Income", "Total Spent", "Net Savings"],
        [f"${income_total:,.2f}", f"${spent_total:,.2f}", f"${net_savings:,.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[180, 180, 180])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#334155')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 18))

    # Transaction Itemized Table
    table_data = [["Date", "Category", "Description", "Status", "Amount"]]
    for tx in qs[:50]:  # Limit rows per single-month statement for predictable memory
        table_data.append([
            tx.date.strftime("%Y-%m-%d"),
            tx.category.title(),
            tx.description[:30] if tx.description else "-",
            tx.status.capitalize(),
            f"${tx.amount:,.2f}"
        ])

    tx_table = Table(table_data, colWidths=[70, 90, 220, 70, 90])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(tx_table)

    # Compile PDF
    doc.build(elements)
    buffer.seek(0)

    # 3. Stream direct to private S3 bucket with AES256 server-side encryption
    s3_key = f"statements/user_{user_id}/{year}_{month:02d}_statement.pdf"
    s3_client = boto3.client('s3', region_name=settings.AWS_DEFAULT_REGION)

    try:
        s3_client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=s3_key,
            Body=buffer.getvalue(),
            ContentType='application/pdf',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Uploaded statement to S3: {s3_key}")
        buffer.close()
        return s3_key
    except ClientError as exc:
        logger.error(f"S3 Upload failed: {exc}")
        buffer.close()
        raise self.retry(exc=exc)