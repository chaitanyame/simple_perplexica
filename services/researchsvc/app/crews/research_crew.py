"""
CrewAI research crew with two agents:
1. Senior Research Analyst - Researches and analyzes information
2. Content Writer - Transforms research into engaging blog posts

Uses OpenRouter instead of Cohere for LLM interactions.
"""

import logging
from crewai import Agent, Task, Crew, LLM
from crewai_tools import SerperDevTool
from app.config import settings

logger = logging.getLogger(__name__)


def create_research_crew(topic: str, temperature: float = 0.7) -> Crew:
    """
    Create a CrewAI research crew with researcher and writer agents.

    Args:
        topic: The topic to research and write about
        temperature: LLM temperature for creativity control

    Returns:
        Configured Crew instance ready to execute
    """

    # Configure LLM to use OpenRouter
    # OpenRouter is compatible with OpenAI SDK, just needs different base_url
    llm = LLM(
        model=f"openai/{settings.openrouter_model}",
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
    )

    # Initialize web search tool
    search_tool = SerperDevTool(n_results=10)

    # Agent 1: Senior Research Analyst
    senior_research_analyst = Agent(
        role="Senior Research Analyst",
        goal=f"Research, analyze, and synthesize comprehensive information on {topic} from reliable web sources",
        backstory="You're an expert research analyst with advanced web research skills. "
        "You excel at finding, analyzing, and synthesizing information from "
        "across the internet using search tools. You're skilled at "
        "distinguishing reliable sources from unreliable ones, "
        "fact-checking, cross-referencing information, and "
        "identifying key patterns and insights. You provide "
        "well-organized research briefs with proper citations "
        "and source verification. Your analysis includes both "
        "raw data and interpreted insights, making complex "
        "information accessible and actionable.",
        allow_delegation=False,
        verbose=True,
        tools=[search_tool],
        llm=llm,
    )

    # Agent 2: Content Writer
    content_writer = Agent(
        role="Content Writer",
        goal="Transform research findings into engaging blog posts while maintaining accuracy",
        backstory="You're a skilled content writer specialized in creating "
        "engaging, accessible content from technical research. "
        "You work closely with the Senior Research Analyst and excel at maintaining the perfect "
        "balance between informative and entertaining writing, "
        "while ensuring all facts and citations from the research "
        "are properly incorporated. You have a talent for making "
        "complex topics approachable without oversimplifying them.",
        allow_delegation=False,
        verbose=True,
        llm=llm,
    )

    # Task 1: Research
    research_task = Task(
        description=(
            """
            1. Conduct comprehensive research on {topic} including:
                - Recent developments and news
                - Key industry trends and innovations
                - Expert opinions and analyses
                - Statistical data and market insights
            2. Evaluate source credibility and fact-check all information
            3. Organize findings into a structured research brief
            4. Include all relevant citations and sources
        """
        ),
        expected_output="""A detailed research report containing:
            - Executive summary of key findings
            - Comprehensive analysis of current trends and developments
            - List of verified facts and statistics
            - All citations and links to original sources
            - Clear categorization of main themes and patterns
            Please format with clear sections and bullet points for easy reference.""",
        agent=senior_research_analyst,
    )

    # Task 2: Writing
    writing_task = Task(
        description=(
            """
            Using the research brief provided, create an engaging blog post that:
            1. Transforms technical information into accessible content
            2. Maintains all factual accuracy and citations from the research
            3. Includes:
                - Attention-grabbing introduction
                - Well-structured body sections with clear headings
                - Compelling conclusion
            4. Preserves all source citations in [Source: URL] format
            5. Includes a References section at the end
        """
        ),
        expected_output="""A polished blog post in markdown format that:
            - Engages readers while maintaining accuracy
            - Contains properly structured sections
            - Includes Inline citations hyperlinked to the original source url
            - Presents information in an accessible yet informative way
            - Follows proper markdown formatting, use H1 for the title and H3 for the sub-sections""",
        agent=content_writer,
    )

    # Create and return the crew
    crew = Crew(
        agents=[senior_research_analyst, content_writer],
        tasks=[research_task, writing_task],
        verbose=True,
    )

    logger.info(f"Research crew created for topic: {topic}")
    return crew
