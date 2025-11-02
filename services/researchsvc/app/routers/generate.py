"""
API router for content generation endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException
from app.models import GenerateContentRequest, GenerateContentResponse
from app.crews.research_crew import create_research_crew

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=GenerateContentResponse)
async def generate_content(request: GenerateContentRequest):
    """
    Generate research-based content on a given topic.

    This endpoint uses a multi-agent CrewAI system with:
    - Research Analyst: Searches and analyzes information
    - Content Writer: Transforms research into engaging blog posts

    Args:
        request: GenerateContentRequest with topic and optional temperature

    Returns:
        GenerateContentResponse with generated content
    """
    try:
        logger.info(f"Received content generation request for topic: {request.topic}")

        # Create and execute the research crew
        crew = create_research_crew(
            topic=request.topic, temperature=request.temperature
        )

        logger.info("Executing crew...")
        result = crew.kickoff(inputs={"topic": request.topic})

        logger.info(f"Content generation completed for topic: {request.topic}")

        return GenerateContentResponse(
            topic=request.topic,
            content=str(result),  # The final output from the crew
            raw_output=result.raw,  # Raw output for debugging
            status="success",
        )

    except Exception as e:
        logger.error(
            f"Error generating content for topic '{request.topic}': {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Content generation failed: {str(e)}"
        )
