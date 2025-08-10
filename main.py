# reporting-engine/main.py - Compliance reporting and analytics service
# Generates reports for DCAA audits, compliance monitoring, and business intelligence

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
from google.cloud import bigquery
from google.cloud import storage
from google.cloud import secretmanager
import psycopg2
from psycopg2.extras import RealDictCursor
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
from jinja2 import Template

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="ProposalOS Reporting Engine",
    description="Compliance reporting and analytics service for ProposalOS",
    version="2.0.0"
)

# Configuration
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "proposalos-prod")
BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET", "proposalos_analytics")
REPLICA_DB_URL = os.environ.get("REPLICA_DB_URL")
STORAGE_BUCKET = os.environ.get("REPORT_STORAGE_BUCKET", "proposalos-reports")

# Initialize clients
bq_client = bigquery.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)
secret_client = secretmanager.SecretManagerServiceClient()

# Report types
class ReportType(str, Enum):
    COMPLIANCE_AUDIT = "compliance_audit"
    DCAA_SYSTEM_ADEQUACY = "dcaa_system_adequacy"
    FAR_COMPLIANCE = "far_compliance"
    COST_ANALYSIS = "cost_analysis"
    AUDIT_TRAIL = "audit_trail"
    EXECUTIVE_DASHBOARD = "executive_dashboard"
    ANOMALY_DETECTION = "anomaly_detection"
    USER_ACTIVITY = "user_activity"

# Report formats
class ReportFormat(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"
    HTML = "html"
    CSV = "csv"

# Models
class ReportRequest(BaseModel):
    report_type: ReportType
    format: ReportFormat = ReportFormat.PDF
    start_date: datetime
    end_date: datetime
    filters: Optional[Dict[str, Any]] = {}
    include_charts: bool = True
    email_recipients: Optional[List[str]] = []

class ReportStatus(BaseModel):
    report_id: str
    status: str
    progress: int
    message: str
    download_url: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class ComplianceMetrics(BaseModel):
    compliance_score: float
    audit_findings: int
    critical_violations: int
    remediation_rate: float
    days_since_last_audit: int
    upcoming_audits: List[Dict]

# Database connection
def get_db_connection():
    """Get database connection from replica for reporting"""
    if REPLICA_DB_URL:
        return psycopg2.connect(REPLICA_DB_URL)
    else:
        # Get from secret manager
        secret_name = f"projects/{PROJECT_ID}/secrets/db-connection-string/versions/latest"
        response = secret_client.access_secret_version(request={"name": secret_name})
        connections = json.loads(response.payload.data.decode("UTF-8"))
        return psycopg2.connect(connections["replica"])

# Report generators
class ReportGenerator:
    """Base class for report generation"""
    
    def __init__(self, request: ReportRequest):
        self.request = request
        self.report_id = f"{request.report_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.temp_files = []
    
    async def generate(self) -> str:
        """Generate report and return storage URL"""
        raise NotImplementedError
    
    def cleanup(self):
        """Clean up temporary files"""
        for file in self.temp_files:
            try:
                os.remove(file)
            except:
                pass

class ComplianceAuditReport(ReportGenerator):
    """Generate comprehensive compliance audit reports"""
    
    async def generate(self) -> str:
        logger.info(f"Generating compliance audit report: {self.report_id}")
        
        # Fetch data
        audit_data = await self._fetch_audit_data()
        compliance_metrics = await self._calculate_compliance_metrics()
        violations = await self._fetch_violations()
        
        # Generate report based on format
        if self.request.format == ReportFormat.PDF:
            return await self._generate_pdf_report(audit_data, compliance_metrics, violations)
        elif self.request.format == ReportFormat.EXCEL:
            return await self._generate_excel_report(audit_data, compliance_metrics, violations)
        elif self.request.format == ReportFormat.JSON:
            return await self._generate_json_report(audit_data, compliance_metrics, violations)
        else:
            raise ValueError(f"Unsupported format: {self.request.format}")
    
    async def _fetch_audit_data(self) -> pd.DataFrame:
        """Fetch audit trail data from BigQuery"""
        query = f"""
        SELECT 
            timestamp,
            event_type,
            user_id,
            service,
            action,
            resource,
            result,
            compliance_rules,
            risk_score,
            details
        FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.audit_events`
        WHERE timestamp BETWEEN @start_date AND @end_date
        ORDER BY timestamp DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", self.request.start_date),
                bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", self.request.end_date),
            ]
        )
        
        df = bq_client.query(query, job_config=job_config).to_dataframe()
        return df
    
    async def _calculate_compliance_metrics(self) -> ComplianceMetrics:
        """Calculate compliance metrics"""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get compliance score
                cur.execute("""
                    SELECT 
                        AVG(score) as avg_score,
                        COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failures,
                        COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END) as critical
                    FROM compliance_checks
                    WHERE checked_at BETWEEN %s AND %s
                """, (self.request.start_date, self.request.end_date))
                
                metrics = cur.fetchone()
                
                # Get audit info
                cur.execute("""
                    SELECT 
                        MAX(completed_at) as last_audit,
                        COUNT(*) as total_audits
                    FROM audit_sessions
                    WHERE status = 'COMPLETED'
                """)
                
                audit_info = cur.fetchone()
                
                return ComplianceMetrics(
                    compliance_score=float(metrics['avg_score'] or 0),
                    audit_findings=metrics['failures'] or 0,
                    critical_violations=metrics['critical'] or 0,
                    remediation_rate=0.85,  # Calculate from actual data
                    days_since_last_audit=(
                        (datetime.now() - audit_info['last_audit']).days 
                        if audit_info['last_audit'] else 999
                    ),
                    upcoming_audits=[]
                )
        finally:
            conn.close()
    
    async def _fetch_violations(self) -> pd.DataFrame:
        """Fetch compliance violations"""
        query = f"""
        SELECT 
            v.violation_id,
            v.detected_at,
            v.rule_type,
            v.severity,
            v.description,
            v.remediation_status,
            v.remediated_at,
            v.assigned_to
        FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.compliance_violations` v
        WHERE v.detected_at BETWEEN @start_date AND @end_date
        ORDER BY v.severity DESC, v.detected_at DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", self.request.start_date),
                bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", self.request.end_date),
            ]
        )
        
        df = bq_client.query(query, job_config=job_config).to_dataframe()
        return df
    
    async def _generate_pdf_report(self, audit_data: pd.DataFrame, 
                                  metrics: ComplianceMetrics, 
                                  violations: pd.DataFrame) -> str:
        """Generate PDF compliance report"""
        filename = f"/tmp/{self.report_id}.pdf"
        self.temp_files.append(filename)
        
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        story.append(Paragraph("ProposalOS Compliance Audit Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Report metadata
        meta_data = [
            ['Report Period:', f"{self.request.start_date.strftime('%Y-%m-%d')} to {self.request.end_date.strftime('%Y-%m-%d')}"],
            ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Report ID:', self.report_id],
            ['Compliance Score:', f"{metrics.compliance_score:.1f}%"]
        ]
        
        meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(meta_table)
        story.append(Spacer(1, 0.5*inch))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        summary_text = f"""
        The compliance audit for the period {self.request.start_date.strftime('%B %d, %Y')} to 
        {self.request.end_date.strftime('%B %d, %Y')} shows an overall compliance score of 
        {metrics.compliance_score:.1f}%. There were {metrics.audit_findings} audit findings 
        identified, including {metrics.critical_violations} critical violations that require 
        immediate attention.
        """
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Compliance Metrics Table
        story.append(Paragraph("Compliance Metrics", styles['Heading2']))
        metrics_data = [
            ['Metric', 'Value', 'Status'],
            ['Overall Compliance Score', f"{metrics.compliance_score:.1f}%", self._get_status_indicator(metrics.compliance_score)],
            ['Total Audit Findings', str(metrics.audit_findings), 'Review Required' if metrics.audit_findings > 0 else 'Good'],
            ['Critical Violations', str(metrics.critical_violations), 'Action Required' if metrics.critical_violations > 0 else 'Good'],
            ['Remediation Rate', f"{metrics.remediation_rate*100:.1f}%", self._get_status_indicator(metrics.remediation_rate*100)],
            ['Days Since Last Audit', str(metrics.days_since_last_audit), 'Schedule Audit' if metrics.days_since_last_audit > 90 else 'Good']
        ]
        
        metrics_table = Table(metrics_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        metrics_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(metrics_table)
        story.append(PageBreak())
        
        # Violations Summary
        if not violations.empty:
            story.append(Paragraph("Compliance Violations", styles['Heading2']))
            
            # Group by severity
            severity_counts = violations['severity'].value_counts()
            
            severity_data = [['Severity', 'Count', 'Percentage']]
            total_violations = len(violations)
            
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                count = severity_counts.get(severity, 0)
                percentage = (count / total_violations * 100) if total_violations > 0 else 0
                severity_data.append([severity, str(count), f"{percentage:.1f}%"])
            
            severity_table = Table(severity_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            severity_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            
            story.append(severity_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Top violations
            story.append(Paragraph("Top Violations by Type", styles['Heading3']))
            top_violations = violations['rule_type'].value_counts().head(10)
            
            violation_data = [['Rule Type', 'Count']]
            for rule_type, count in top_violations.items():
                violation_data.append([rule_type, str(count)])
            
            violation_table = Table(violation_data, colWidths=[4*inch, 1.5*inch])
            violation_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(violation_table)
        
        # Generate charts if requested
        if self.request.include_charts:
            story.append(PageBreak())
            story.append(Paragraph("Compliance Trends", styles['Heading2']))
            
            # Create compliance trend chart
            chart_filename = await self._create_compliance_chart(audit_data)
            if chart_filename:
                from reportlab.platypus import Image
                img = Image(chart_filename, width=6*inch, height=4*inch)
                story.append(img)
                self.temp_files.append(chart_filename)
        
        # Build PDF
        doc.build(story)
        
        # Upload to storage
        bucket = storage_client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(f"reports/{self.report_id}.pdf")
        blob.upload_from_filename(filename)
        
        return blob.public_url
    
    async def _generate_excel_report(self, audit_data: pd.DataFrame,
                                   metrics: ComplianceMetrics,
                                   violations: pd.DataFrame) -> str:
        """Generate Excel compliance report"""
        filename = f"/tmp/{self.report_id}.xlsx"
        self.temp_files.append(filename)
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # Summary sheet
            summary_df = pd.DataFrame({
                'Metric': ['Compliance Score', 'Audit Findings', 'Critical Violations', 
                          'Remediation Rate', 'Days Since Last Audit'],
                'Value': [f"{metrics.compliance_score:.1f}%", metrics.audit_findings,
                         metrics.critical_violations, f"{metrics.remediation_rate*100:.1f}%",
                         metrics.days_since_last_audit]
            })
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Audit events
            if not audit_data.empty:
                audit_data.to_excel(writer, sheet_name='Audit Events', index=False)
            
            # Violations
            if not violations.empty:
                violations.to_excel(writer, sheet_name='Violations', index=False)
            
            # Format workbook
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1e40af',
                'font_color': 'white'
            })
            
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                worksheet.set_row(0, None, header_format)
        
        # Upload to storage
        bucket = storage_client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(f"reports/{self.report_id}.xlsx")
        blob.upload_from_filename(filename)
        
        return blob.public_url
    
    async def _generate_json_report(self, audit_data: pd.DataFrame,
                                  metrics: ComplianceMetrics,
                                  violations: pd.DataFrame) -> str:
        """Generate JSON compliance report"""
        report_data = {
            "report_id": self.report_id,
            "report_type": "compliance_audit",
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start": self.request.start_date.isoformat(),
                "end": self.request.end_date.isoformat()
            },
            "metrics": metrics.dict(),
            "audit_events": audit_data.to_dict(orient='records') if not audit_data.empty else [],
            "violations": violations.to_dict(orient='records') if not violations.empty else []
        }
        
        filename = f"/tmp/{self.report_id}.json"
        self.temp_files.append(filename)
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Upload to storage
        bucket = storage_client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(f"reports/{self.report_id}.json")
        blob.upload_from_filename(filename)
        
        return blob.public_url
    
    async def _create_compliance_chart(self, audit_data: pd.DataFrame) -> Optional[str]:
        """Create compliance trend chart"""
        if audit_data.empty:
            return None
        
        filename = f"/tmp/{self.report_id}_chart.png"
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # Chart 1: Events over time
        audit_data['date'] = pd.to_datetime(audit_data['timestamp']).dt.date
        daily_events = audit_data.groupby(['date', 'event_type']).size().unstack(fill_value=0)
        
        daily_events.plot(kind='area', ax=ax1, alpha=0.7)
        ax1.set_title('Audit Events Over Time', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Number of Events')
        ax1.legend(title='Event Type', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Chart 2: Risk score distribution
        if 'risk_score' in audit_data.columns:
            audit_data['risk_score'].hist(bins=20, ax=ax2, color='#1e40af', alpha=0.7)
            ax2.set_title('Risk Score Distribution', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Risk Score')
            ax2.set_ylabel('Frequency')
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def _get_status_indicator(self, score: float) -> str:
        """Get status indicator based on score"""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 70:
            return "Fair"
        else:
            return "Needs Improvement"

# Report factory
def get_report_generator(request: ReportRequest) -> ReportGenerator:
    """Factory method to get appropriate report generator"""
    generators = {
        ReportType.COMPLIANCE_AUDIT: ComplianceAuditReport,
        # Add other report types here
    }
    
    generator_class = generators.get(request.report_type)
    if not generator_class:
        raise ValueError(f"Unsupported report type: {request.report_type}")
    
    return generator_class(request)

# API endpoints
@app.post("/reports/generate", response_model=ReportStatus)
async def generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    """Generate a new report"""
    generator = get_report_generator(request)
    
    # Create initial status
    status = ReportStatus(
        report_id=generator.report_id,
        status="processing",
        progress=0,
        message="Report generation started",
        created_at=datetime.now()
    )
    
    # Start generation in background
    background_tasks.add_task(process_report, generator, status)
    
    return status

async def process_report(generator: ReportGenerator, status: ReportStatus):
    """Process report generation in background"""
    try:
        # Generate report
        url = await generator.generate()
        
        # Update status
        status.status = "completed"
        status.progress = 100
        status.message = "Report generated successfully"
        status.download_url = url
        status.completed_at = datetime.now()
        
        # Store status in cache/db
        # TODO: Implement status storage
        
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}")
        status.status = "failed"
        status.message = f"Report generation failed: {str(e)}"
    finally:
        generator.cleanup()

@app.get("/reports/{report_id}/status", response_model=ReportStatus)
async def get_report_status(report_id: str):
    """Get report generation status"""
    # TODO: Implement status retrieval from cache/db
    raise HTTPException(status_code=404, detail="Report not found")

@app.get("/reports/types")
async def get_report_types():
    """Get available report types"""
    return {
        "report_types": [
            {
                "type": report_type.value,
                "name": report_type.value.replace("_", " ").title(),
                "description": f"Generate {report_type.value.replace('_', ' ')} report",
                "formats": [fmt.value for fmt in ReportFormat]
            }
            for report_type in ReportType
        ]
    }

@app.get("/metrics/compliance", response_model=ComplianceMetrics)
async def get_compliance_metrics():
    """Get current compliance metrics"""
    # Create a temporary report request for current month
    request = ReportRequest(
        report_type=ReportType.COMPLIANCE_AUDIT,
        format=ReportFormat.JSON,
        start_date=datetime.now().replace(day=1),
        end_date=datetime.now()
    )
    
    generator = ComplianceAuditReport(request)
    metrics = await generator._calculate_compliance_metrics()
    
    return metrics

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "reporting-engine",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)