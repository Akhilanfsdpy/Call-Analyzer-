from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import io
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai import OpenAISpeechToText
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import csv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize GridFS for audio file storage
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
gridfs_bucket = AsyncIOMotorGridFSBucket(db)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize AI clients
EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY')


# Define Models
class SentimentScores(BaseModel):
    empathy: int = 0
    engagement: int = 0
    enthusiasm: int = 0
    politeness: int = 0
    general_sentiment: str = "Neutral"
    profanity_detected: bool = False


class CallAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_id: str  # GridFS file ID
    duration_seconds: Optional[float] = None
    upload_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Transcription
    transcription: Optional[str] = None
    transcription_status: str = "pending"  # pending, processing, completed, failed
    
    # Analysis results
    agent_sentiment: Optional[SentimentScores] = None
    prospect_sentiment: Optional[SentimentScores] = None
    call_summary: Optional[str] = None
    positive_highlights: Optional[List[str]] = None
    improvement_suggestions: Optional[List[str]] = None
    overall_score: Optional[int] = None
    analysis_status: str = "pending"  # pending, processing, completed, failed


class CallAnalysisCreate(BaseModel):
    filename: str
    file_id: str


class CallListItem(BaseModel):
    id: str
    filename: str
    upload_timestamp: str
    transcription_status: str
    analysis_status: str
    overall_score: Optional[int] = None


@api_router.get("/")
async def root():
    return {"message": "Sales Call Analyzer API"}


@api_router.post("/upload-call")
async def upload_call(file: UploadFile = File(...)):
    """Upload audio file to GridFS"""
    try:
        # Validate file type
        allowed_extensions = ['.mp3', '.wav', '.m4a', '.mp4', '.mpeg', '.mpga', '.webm']
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Invalid file format. Supported: mp3, wav, m4a, mp4, mpeg, mpga, webm")
        
        # Check file size (25MB limit)
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > 25:
            raise HTTPException(status_code=400, detail="File size exceeds 25MB limit")
        
        # Upload to GridFS
        file_id = await gridfs_bucket.upload_from_stream(
            file.filename,
            io.BytesIO(content),
            metadata={"content_type": file.content_type, "size": len(content)}
        )
        
        # Create call record
        call_data = CallAnalysisCreate(filename=file.filename, file_id=str(file_id))
        call_obj = CallAnalysis(**call_data.model_dump())
        
        doc = call_obj.model_dump()
        doc['upload_timestamp'] = doc['upload_timestamp'].isoformat()
        
        await db.call_analysis.insert_one(doc)
        
        return {"call_id": call_obj.id, "message": "File uploaded successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@api_router.post("/transcribe/{call_id}")
async def transcribe_call(call_id: str):
    """Transcribe audio using Whisper API"""
    try:
        # Get call record
        call_doc = await db.call_analysis.find_one({"id": call_id})
        if not call_doc:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Update status to processing
        await db.call_analysis.update_one(
            {"id": call_id},
            {"$set": {"transcription_status": "processing"}}
        )
        
        # Download file from GridFS
        from bson import ObjectId
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(call_doc['file_id']))
        audio_data = await grid_out.read()
        
        # Transcribe using Whisper
        stt = OpenAISpeechToText(api_key=EMERGENT_KEY)
        audio_file = io.BytesIO(audio_data)
        audio_file.name = call_doc['filename']
        
        response = await stt.transcribe(
            file=audio_file,
            model="whisper-1",
            response_format="text",
            language="en"
        )
        
        transcription_text = response.text if hasattr(response, 'text') else str(response)
        
        # Update call record
        await db.call_analysis.update_one(
            {"id": call_id},
            {"$set": {
                "transcription": transcription_text,
                "transcription_status": "completed"
            }}
        )
        
        return {"message": "Transcription completed", "transcription": transcription_text}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Transcription error: {str(e)}")
        await db.call_analysis.update_one(
            {"id": call_id},
            {"$set": {"transcription_status": "failed"}}
        )
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@api_router.post("/analyze/{call_id}")
async def analyze_call(call_id: str):
    """Analyze sentiment and performance using GPT-5"""
    try:
        # Get call record
        call_doc = await db.call_analysis.find_one({"id": call_id})
        if not call_doc:
            raise HTTPException(status_code=404, detail="Call not found")
        
        if not call_doc.get('transcription'):
            raise HTTPException(status_code=400, detail="Call must be transcribed first")
        
        # Update status to processing
        await db.call_analysis.update_one(
            {"id": call_id},
            {"$set": {"analysis_status": "processing"}}
        )
        
        transcript = call_doc['transcription']
        
        # Initialize GPT-5 chat
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"analyze-{call_id}",
            system_message="You are an expert sales call analyst. Provide detailed, actionable feedback."
        ).with_model("openai", "gpt-5")
        
        # Analyze sentiment
        sentiment_prompt = f"""Analyze the tone and sentiment of this sales conversation.
Rate each metric (Empathy, Engagement, Enthusiasm, Politeness) between 0 and 100 for both the Agent and the Prospect separately.

Provide your response in this exact JSON format:
{{
  "agent": {{
    "empathy": <score>,
    "engagement": <score>,
    "enthusiasm": <score>,
    "politeness": <score>,
    "general_sentiment": "Positive/Neutral/Negative",
    "profanity_detected": false
  }},
  "prospect": {{
    "empathy": <score>,
    "engagement": <score>,
    "enthusiasm": <score>,
    "politeness": <score>,
    "general_sentiment": "Positive/Neutral/Negative",
    "profanity_detected": false
  }}
}}

Transcript:
{transcript}"""
        
        sentiment_response = await chat.send_message(UserMessage(text=sentiment_prompt))
        
        # Parse sentiment (extract JSON from response)
        import json
        sentiment_text = sentiment_response.strip()
        if "```json" in sentiment_text:
            sentiment_text = sentiment_text.split("```json")[1].split("```")[0].strip()
        elif "```" in sentiment_text:
            sentiment_text = sentiment_text.split("```")[1].split("```")[0].strip()
        
        sentiment_data = json.loads(sentiment_text)
        
        # Analyze performance
        performance_prompt = f"""You are an AI performance coach.
Based on this sales call transcript, generate:
1. A short call summary (2-3 sentences)
2. 3 positive highlights (as a JSON array)
3. 3 improvement recommendations (as a JSON array)
4. An overall performance score (0-100)

Provide your response in this exact JSON format:
{{
  "summary": "<summary text>",
  "positives": ["<positive 1>", "<positive 2>", "<positive 3>"],
  "improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
  "score": <0-100>
}}

Transcript:
{transcript}"""
        
        performance_response = await chat.send_message(UserMessage(text=performance_prompt))
        
        # Parse performance
        performance_text = performance_response.strip()
        if "```json" in performance_text:
            performance_text = performance_text.split("```json")[1].split("```")[0].strip()
        elif "```" in performance_text:
            performance_text = performance_text.split("```")[1].split("```")[0].strip()
        
        performance_data = json.loads(performance_text)
        
        # Update call record
        await db.call_analysis.update_one(
            {"id": call_id},
            {"$set": {
                "agent_sentiment": sentiment_data['agent'],
                "prospect_sentiment": sentiment_data['prospect'],
                "call_summary": performance_data['summary'],
                "positive_highlights": performance_data['positives'],
                "improvement_suggestions": performance_data['improvements'],
                "overall_score": performance_data['score'],
                "analysis_status": "completed"
            }}
        )
        
        return {
            "message": "Analysis completed",
            "agent_sentiment": sentiment_data['agent'],
            "prospect_sentiment": sentiment_data['prospect'],
            "summary": performance_data['summary'],
            "score": performance_data['score']
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Analysis error: {str(e)}")
        await db.call_analysis.update_one(
            {"id": call_id},
            {"$set": {"analysis_status": "failed"}}
        )
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@api_router.get("/calls")
async def get_calls():
    """Get all analyzed calls"""
    try:
        calls = await db.call_analysis.find({}, {"_id": 0}).to_list(1000)
        
        call_list = []
        for call in calls:
            call_list.append({
                "id": call['id'],
                "filename": call['filename'],
                "upload_timestamp": call['upload_timestamp'],
                "transcription_status": call['transcription_status'],
                "analysis_status": call['analysis_status'],
                "overall_score": call.get('overall_score')
            })
        
        return call_list
    except Exception as e:
        logging.error(f"Get calls error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve calls: {str(e)}")


@api_router.get("/calls/{call_id}")
async def get_call_details(call_id: str):
    """Get detailed analysis for a specific call"""
    try:
        call_doc = await db.call_analysis.find_one({"id": call_id}, {"_id": 0})
        if not call_doc:
            raise HTTPException(status_code=404, detail="Call not found")
        
        return call_doc
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Get call details error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve call details: {str(e)}")


@api_router.get("/export/{call_id}/{format}")
async def export_report(call_id: str, format: str):
    """Export call analysis as PDF or CSV"""
    try:
        call_doc = await db.call_analysis.find_one({"id": call_id}, {"_id": 0})
        if not call_doc:
            raise HTTPException(status_code=404, detail="Call not found")
        
        if call_doc.get('analysis_status') != 'completed':
            raise HTTPException(status_code=400, detail="Analysis not completed yet")
        
        if format.lower() == 'pdf':
            return await generate_pdf_report(call_doc)
        elif format.lower() == 'csv':
            return await generate_csv_report(call_doc)
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'pdf' or 'csv'")
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


async def generate_pdf_report(call_doc: dict) -> StreamingResponse:
    """Generate PDF report"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=30
    )
    story.append(Paragraph("Sales Call Analysis Report", title_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Call Info
    story.append(Paragraph(f"<b>File:</b> {call_doc['filename']}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {call_doc['upload_timestamp']}", styles['Normal']))
    story.append(Paragraph(f"<b>Overall Score:</b> {call_doc.get('overall_score', 'N/A')}/100", styles['Normal']))
    story.append(Spacer(1, 0.3 * inch))
    
    # Summary
    story.append(Paragraph("<b>Call Summary</b>", styles['Heading2']))
    story.append(Paragraph(call_doc.get('call_summary', 'N/A'), styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Sentiment Scores
    story.append(Paragraph("<b>Sentiment Analysis</b>", styles['Heading2']))
    
    agent_sent = call_doc.get('agent_sentiment', {})
    prospect_sent = call_doc.get('prospect_sentiment', {})
    
    sentiment_data = [
        ['Metric', 'Agent', 'Prospect'],
        ['Empathy', str(agent_sent.get('empathy', 0)), str(prospect_sent.get('empathy', 0))],
        ['Engagement', str(agent_sent.get('engagement', 0)), str(prospect_sent.get('engagement', 0))],
        ['Enthusiasm', str(agent_sent.get('enthusiasm', 0)), str(prospect_sent.get('enthusiasm', 0))],
        ['Politeness', str(agent_sent.get('politeness', 0)), str(prospect_sent.get('politeness', 0))],
    ]
    
    table = Table(sentiment_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#38bdf8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3 * inch))
    
    # Positive Highlights
    story.append(Paragraph("<b>Positive Highlights</b>", styles['Heading2']))
    for highlight in call_doc.get('positive_highlights', []):
        story.append(Paragraph(f"• {highlight}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Improvements
    story.append(Paragraph("<b>Improvement Suggestions</b>", styles['Heading2']))
    for improvement in call_doc.get('improvement_suggestions', []):
        story.append(Paragraph(f"• {improvement}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={call_doc['id']}_report.pdf"}
    )


async def generate_csv_report(call_doc: dict) -> StreamingResponse:
    """Generate CSV report"""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    
    # Header
    writer.writerow(['Sales Call Analysis Report'])
    writer.writerow([])
    writer.writerow(['File', call_doc['filename']])
    writer.writerow(['Date', call_doc['upload_timestamp']])
    writer.writerow(['Overall Score', call_doc.get('overall_score', 'N/A')])
    writer.writerow([])
    
    # Summary
    writer.writerow(['Call Summary'])
    writer.writerow([call_doc.get('call_summary', 'N/A')])
    writer.writerow([])
    
    # Sentiment
    writer.writerow(['Sentiment Analysis'])
    writer.writerow(['Metric', 'Agent', 'Prospect'])
    
    agent_sent = call_doc.get('agent_sentiment', {})
    prospect_sent = call_doc.get('prospect_sentiment', {})
    
    writer.writerow(['Empathy', agent_sent.get('empathy', 0), prospect_sent.get('empathy', 0)])
    writer.writerow(['Engagement', agent_sent.get('engagement', 0), prospect_sent.get('engagement', 0)])
    writer.writerow(['Enthusiasm', agent_sent.get('enthusiasm', 0), prospect_sent.get('enthusiasm', 0)])
    writer.writerow(['Politeness', agent_sent.get('politeness', 0), prospect_sent.get('politeness', 0)])
    writer.writerow([])
    
    # Positives
    writer.writerow(['Positive Highlights'])
    for highlight in call_doc.get('positive_highlights', []):
        writer.writerow([highlight])
    writer.writerow([])
    
    # Improvements
    writer.writerow(['Improvement Suggestions'])
    for improvement in call_doc.get('improvement_suggestions', []):
        writer.writerow([improvement])
    
    buffer.seek(0)
    
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={call_doc['id']}_report.csv"}
    )


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()