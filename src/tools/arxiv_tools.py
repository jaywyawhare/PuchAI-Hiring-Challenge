"""
arXiv API tools for searching and retrieving academic papers.
Uses arXiv.org's official API with proper rate limiting.
"""
from typing import Annotated, Dict, List, Any, Optional
from pydantic import Field
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
import asyncio
import logging
import feedparser
import httpx
from datetime import datetime, timedelta
import openai


class RichToolDescription(openai.BaseModel):
    """Rich tool description model for MCP server compatibility."""
    description: str
    use_when: str
    side_effects: Optional[str]

logger = logging.getLogger(__name__)

class ArxivAPI:
    """arXiv API client with rate limiting and proper error handling."""
    
    def __init__(self):
        self.base_url = "https://export.arxiv.org/api/query"
        self._last_request: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
    async def _wait_for_rate_limit(self) -> None:
        """Ensures we respect arXiv's rate limit of 1 request every 3 seconds."""
        async with self._lock:
            if self._last_request is not None:
                elapsed = datetime.now() - self._last_request
                if elapsed < timedelta(seconds=3):
                    await asyncio.sleep(3 - elapsed.total_seconds())
            self._last_request = datetime.now()

    def _clean_text(self, text: str) -> str:
        """Clean up text by removing extra whitespace and newlines."""
        return " ".join(text.split())

    def _get_html_url(self, arxiv_id: str) -> str:
        """Get HTML version URL for a paper."""
        base_id = arxiv_id.split('v')[0]
        return f"https://arxiv.org/html/{base_id}"

    def _parse_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a feed entry into a paper dictionary."""
        # Extract URLs
        pdf_url = None
        abstract_url = None
        for link in entry.get('links', []):
            if isinstance(link, dict):
                if link.get('type') == 'application/pdf':
                    pdf_url = link.get('href')
                elif link.get('type') == 'text/html':
                    abstract_url = link.get('href')

        # Get paper ID and create HTML URL
        paper_id = entry.get('id', '').split("/abs/")[-1].rstrip()
        html_url = self._get_html_url(paper_id) if paper_id else None

        # Extract authors
        authors = []
        for author in entry.get('authors', []):
            if isinstance(author, dict) and 'name' in author:
                authors.append(author['name'])
            elif hasattr(author, 'name'):
                authors.append(author.name)

        # Extract categories
        categories = []
        primary_category = None
        
        if 'arxiv_primary_category' in entry:
            if isinstance(entry['arxiv_primary_category'], dict):
                primary_category = entry['arxiv_primary_category'].get('term')
            elif hasattr(entry['arxiv_primary_category'], 'term'):
                primary_category = entry['arxiv_primary_category'].term
        
        for category in entry.get('tags', []):
            if isinstance(category, dict) and 'term' in category:
                categories.append(category['term'])
            elif hasattr(category, 'term'):
                categories.append(category.term)

        if primary_category and primary_category in categories:
            categories.remove(primary_category)

        return {
            "id": paper_id,
            "title": self._clean_text(entry.get('title', '')),
            "authors": authors,
            "primary_category": primary_category,
            "categories": categories,
            "published": entry.get('published', ''),
            "updated": entry.get('updated', ''),
            "summary": self._clean_text(entry.get('summary', '')),
            "comment": self._clean_text(entry.get('arxiv_comment', '')),
            "journal_ref": entry.get('arxiv_journal_ref', ''),
            "doi": entry.get('arxiv_doi', ''),
            "pdf_url": pdf_url,
            "abstract_url": abstract_url,
            "html_url": html_url
        }

    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search arXiv papers with advanced query syntax support."""
        await self._wait_for_rate_limit()
        
        # Convert advanced query to arXiv API format
        formatted_query = query
        if 'ti:' in query or 'au:' in query:
            # Handle advanced query with proper URL encoding
            import urllib.parse
            formatted_query = query.replace('"', '%22')  # Encode quotes
            formatted_query = formatted_query.replace(' AND ', '+AND+')
            formatted_query = urllib.parse.quote_plus(formatted_query, safe=':+"')
        
        params = {
            "search_query": formatted_query,
            "start": 0,
            "max_results": min(max_results, 2000),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        
        logger.debug(f"ArXiv API request: {self.base_url}?search_query={formatted_query}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.base_url, 
                    params=params,
                    headers={
                        'User-Agent': 'ChupAI/1.0 (github.com/jaywyawhare/puch-ai-hiring)'
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                
                feed = feedparser.parse(response.text)
                if not feed.entries:
                    logger.warning(f"No results found for query: {query}")
                    return []
                    
                return [self._parse_entry(entry) for entry in feed.entries]
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error while searching: {e}")
                raise ValueError(f"arXiv API HTTP error: {str(e)}")

    async def get_paper(self, paper_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific paper."""
        await self._wait_for_rate_limit()
        
        params = {
            "id_list": paper_id,
            "max_results": 1
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                
                feed = feedparser.parse(response.text)
                if not isinstance(feed, dict) or 'entries' not in feed:
                    logger.error("Invalid response from arXiv API")
                    raise ValueError("Invalid response from arXiv API")
                
                if not feed.get('entries'):
                    raise ValueError(f"Paper not found: {paper_id}")
                    
                return self._parse_entry(feed.entries[0])
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error while fetching paper: {e}")
                raise ValueError(f"arXiv API HTTP error: {str(e)}")


def register_arxiv_tools(mcp):
    """Register arXiv-related tools with the MCP server."""
    
    logger.info("Registering arXiv tools...")
    
    SearchArxivToolDescription = RichToolDescription(
        description="Search for academic papers on arXiv.org with advanced query support.",
        use_when="User asks for academic papers, research, or scientific literature on specific topics.",
        side_effects="Makes API calls to arXiv.org and may be subject to rate limiting (3 second delays between requests).",
    )
    
    @mcp.tool(description=SearchArxivToolDescription.model_dump_json())
    async def search_arxiv_papers(
        query: Annotated[str, Field(description="Search query (supports advanced syntax)")],
        max_results: Annotated[int, Field(description="Maximum number of results", default=5)] = 5,
        include_abstracts: Annotated[bool, Field(description="Include paper abstracts", default=False)] = False
    ) -> list[TextContent]:
        """
        Search for academic papers on arXiv.org with advanced query support.
        
        Example queries:
        - Simple: machine learning, quantum computing
        - Title only: ti:"neural networks"
        - Author: au:"Hinton" AND ti:"deep learning"
        - Category: cat:cs.AI
        """
        try:
            logger.info(f"Searching arXiv papers for query: {query}")
            arxiv = ArxivAPI()
            papers = await arxiv.search(query, max_results)
            
            if not papers:
                return [TextContent(
                    type="text",
                    text=f"❌ **No papers found for query:** {query}"
                )]
            
            result_text = f"""
**📚 arXiv Paper Search Results**
*Query: {query}*

Found {len(papers)} papers:

"""
            
            for i, paper in enumerate(papers, 1):
                pub_date = datetime.fromisoformat(paper['published'].replace('Z', '+00:00'))
                
                result_text += f"""
**{i}. {paper['title']}**
📝 **Authors:** {', '.join(paper['authors'][:3])}{"..." if len(paper['authors']) > 3 else ""}
📅 **Published:** {pub_date.strftime('%Y-%m-%d')}
📌 **Category:** {paper['primary_category']}
🔗 **Links:**
  • Abstract: {paper['abstract_url']}
  • PDF: {paper['pdf_url']}
  • HTML: {paper['html_url']}
"""

                if include_abstracts:
                    result_text += f"\n📖 **Abstract:**\n{paper['summary']}\n"
                    
                if paper['doi']:
                    result_text += f"📎 **DOI:** {paper['doi']}\n"
                    
                if paper['journal_ref']:
                    result_text += f"📰 **Journal:** {paper['journal_ref']}\n"
            
            result_text += f"""
💡 **Search Tips:**
• Use `ti:"keywords"` to search in titles only
• Use `au:"name"` to search by author
• Use `cat:cs.AI` to filter by category
• Combine with AND, OR (e.g., `ti:"neural" AND au:"hinton"`)

*🔴 Live data from arXiv.org API*
"""
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in search_arxiv_papers: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error searching arXiv: {str(e)}"
                )
            )

    GetArxivPaperToolDescription = RichToolDescription(
        description="Get detailed information about a specific arXiv paper by its ID.",
        use_when="User provides a specific arXiv paper ID or asks for details about a known paper.",
        side_effects="Makes API calls to arXiv.org and may be subject to rate limiting (3 second delays between requests).",
    )

    @mcp.tool(description=GetArxivPaperToolDescription.model_dump_json())
    async def get_arxiv_paper(
        paper_id: Annotated[str, Field(
            description="arXiv paper ID in the format YYMM.NNNNN or NNNN.NNNN (e.g., 2103.08220)")],
    ) -> list[TextContent]:
        """
        Get detailed information about a specific arXiv paper by its ID.
        
        Use search_arxiv_papers() for searching papers by keywords.
        This tool only accepts valid arXiv IDs like: 2103.08220, 1234.5678
        """
        try:
            logger.info(f"Getting arXiv paper details for ID: {paper_id}")
            # Validate arXiv ID format
            import re
            if not re.match(r'^\d{4}\.\d{4,5}(?:v\d+)?$', paper_id):
                raise ValueError(
                    f"Invalid arXiv ID format: {paper_id}\n"
                    "Please use search_arxiv_papers() for searching papers by keywords.\n"
                    "Example: search_arxiv_papers('neural networks')"
                )
            
            arxiv = ArxivAPI()
            paper = await arxiv.get_paper(paper_id)
            
            pub_date = datetime.fromisoformat(paper['published'].replace('Z', '+00:00'))
            update_date = datetime.fromisoformat(paper['updated'].replace('Z', '+00:00'))
            
            result_text = f"""
**📄 arXiv Paper: {paper_id}**

**{paper['title']}**

👥 **Authors:**
{', '.join(paper['authors'])}

📅 **Dates:**
• Published: {pub_date.strftime('%Y-%m-%d')}
• Last Updated: {update_date.strftime('%Y-%m-%d')}

📚 **Categories:**
• Primary: {paper['primary_category']}
{f"• Other: {', '.join(paper['categories'])}" if paper['categories'] else ""}

📖 **Abstract:**
{paper['summary']}

🔗 **Links:**
• Abstract Page: {paper['abstract_url']}
• PDF Version: {paper['pdf_url']}
• HTML Version: {paper['html_url']}

"""
            if paper['comment']:
                result_text += f"💬 **Comments:** {paper['comment']}\n"
                
            if paper['journal_ref']:
                result_text += f"📰 **Journal Reference:** {paper['journal_ref']}\n"
                
            if paper['doi']:
                result_text += f"📎 **DOI:** {paper['doi']}\n"
            
            result_text += "\n*🔴 Live data from arXiv.org API*"
            
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            logger.error(f"Error in get_arxiv_paper: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Error fetching arXiv paper: {str(e)}"
                )
            )
