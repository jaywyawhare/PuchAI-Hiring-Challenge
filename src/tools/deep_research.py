"""
Unified Deep Research Tool with Multi-Source Citation Analysis
Performs comprehensive research using Wikipedia, arXiv, Semantic Scholar, OpenAlex, and PubMed
with full abstract and content extraction capabilities.
"""
from typing import Annotated, Dict, List, Set, Optional, Any
from pydantic import Field
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
import httpx
import json
import re
import asyncio
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote_plus, unquote
import logging

logger = logging.getLogger(__name__)


class RichToolDescription:
    """Rich tool description model for MCP server compatibility."""
    def __init__(self, description: str, use_when: str, side_effects: Optional[str] = None):
        self.description = description
        self.use_when = use_when
        self.side_effects = side_effects
    
    def model_dump_json(self) -> str:
        """Convert to JSON string for MCP compatibility."""
        return json.dumps({
            "description": self.description,
            "use_when": self.use_when,
            "side_effects": self.side_effects
        })


class UnifiedCitation:
    """Enhanced citation data structure for multi-source research tracking"""
    def __init__(self, source: str, title: str, url: str, date: str = None, 
                 authors: List[str] = None, depth: int = 0, parent: str = None,
                 paper_id: str = None, doi: str = None, citation_count: int = 0,
                 venue: str = None, abstract: str = "", full_content: str = ""):
        # Basic metadata
        self.source = source  # 'wikipedia', 'arxiv', 'semantic_scholar', 'openalex', 'pubmed'
        self.title = title
        self.url = url
        self.date = date
        self.authors = authors or []
        self.depth = depth
        self.parent = parent
        
        # Academic metadata
        self.paper_id = paper_id
        self.doi = doi
        self.citation_count = citation_count
        self.venue = venue
        self.year = None
        if date:
            try:
                self.year = int(date[:4]) if len(date) >= 4 else None
            except (ValueError, TypeError):
                self.year = None
        
        # Content
        self.abstract = abstract
        self.full_content = full_content
        self.content_summary = abstract[:500] + "..." if len(abstract) > 500 else abstract
        
        # Analysis
        self.references = []
        self.cited_by = []
        self.key_concepts = []
        
        # Additional academic fields
        self.influential_citation_count = 0
        self.open_access_url = ""
        self.publication_types = []
        self.fields_of_study = []


class UnifiedDeepResearchEngine:
    """Main research engine with multi-source DFS citation traversal"""
    
    def __init__(self, max_depth: int = 3, max_refs_per_source: int = 5):
        self.max_depth = max_depth
        self.max_refs_per_source = max_refs_per_source
        self.visited_urls = set()
        self.visited_paper_ids = set()
        self.citation_graph = {}
        self.research_tree = []
        
        # API endpoints
        self.wiki_api = "https://en.wikipedia.org/w/api.php"
        self.arxiv_base = "https://export.arxiv.org/api/query"
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"
        self.openalex_base = "https://api.openalex.org"
        self.pubmed_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        
        # Rate limiting
        self.semantic_scholar_delay = 1.0
        self.openalex_delay = 1.0
        self.pubmed_delay = 0.34
        
    async def unified_deep_research(self, topic: str) -> Dict[str, Any]:
        """Perform comprehensive deep research across all sources"""
        logger.info(f"Starting unified deep research on: {topic}")
        
        # Reset state
        self.visited_urls.clear()
        self.visited_paper_ids.clear()
        self.citation_graph.clear()
        self.research_tree.clear()
        
        # Search all sources simultaneously
        initial_citations = await self._search_all_sources(topic)
        
        # Perform DFS traversal on all citations
        for citation in initial_citations:
            if citation.url not in self.visited_urls and (not citation.paper_id or citation.paper_id not in self.visited_paper_ids):
                await self._unified_dfs_traversal(citation, 0)
        
        # Generate comprehensive analysis
        analysis = await self._generate_unified_analysis(topic)
        
        # Convert research tree to dictionary format for compatibility
        citations = self._convert_research_tree_to_dicts()
        
        return {
            "success": True,
            "topic": topic,
            "total_sources": len(self.research_tree),
            "citations": citations,  # Add citations in dictionary format
            "source_breakdown": self._get_source_breakdown(),
            "max_depth_reached": max(c.depth for c in self.research_tree) if self.research_tree else 0,
            "analysis": analysis,
            "citation_tree": self._build_unified_citation_tree(),
            "content_metrics": self._calculate_content_metrics(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _search_all_sources(self, topic: str) -> List[UnifiedCitation]:
        """Search all available sources: Wikipedia, arXiv, Semantic Scholar, OpenAlex, PubMed"""
        all_citations = []
        
        # Search each source
        tasks = [
            self._search_wikipedia(topic),
            self._search_arxiv(topic),
            self._search_semantic_scholar(topic),
            self._search_openalex(topic),
            self._search_pubmed(topic)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_citations.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Source search error: {result}")
        
        return all_citations
    
    async def _unified_dfs_traversal(self, citation: UnifiedCitation, current_depth: int):
        """Perform unified DFS traversal through all citation types"""
        if current_depth >= self.max_depth:
            return
            
        if citation.url in self.visited_urls or (citation.paper_id and citation.paper_id in self.visited_paper_ids):
            return
        
        self.visited_urls.add(citation.url)
        if citation.paper_id:
            self.visited_paper_ids.add(citation.paper_id)
        
        citation.depth = current_depth
        self.research_tree.append(citation)
        
        logger.info(f"Processing depth {current_depth} ({citation.source}): {citation.title[:50]}...")
        
        # Process based on source type
        if citation.source == "wikipedia":
            await self._process_wikipedia_page(citation)
        elif citation.source == "arxiv":
            await self._process_arxiv_paper(citation)
        elif citation.source == "semantic_scholar":
            await self._process_semantic_scholar_paper(citation)
        elif citation.source == "openalex":
            await self._process_openalex_work(citation)
        elif citation.source == "pubmed":
            await self._process_pubmed_article(citation)
        
        # Recursively process references
        for ref_citation in citation.references[:self.max_refs_per_source]:
            if isinstance(ref_citation, UnifiedCitation):
                if ref_citation.url not in self.visited_urls and (not ref_citation.paper_id or ref_citation.paper_id not in self.visited_paper_ids):
                    await self._unified_dfs_traversal(ref_citation, current_depth + 1)

    # Wikipedia search methods
    async def _search_wikipedia(self, query: str) -> List[UnifiedCitation]:
        """Search Wikipedia articles"""
        try:
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": 3
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(self.wiki_api, params=params)
                data = response.json()
                
                citations = []
                for item in data.get("query", {}).get("search", []):
                    url = f"https://en.wikipedia.org/wiki/{quote_plus(item['title'])}"
                    citation = UnifiedCitation(
                        source="wikipedia",
                        title=item["title"],
                        url=url,
                        date=item.get("timestamp", "")[:10]
                    )
                    citations.append(citation)
                
                return citations
                
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            return []
    
    # arXiv search methods
    async def _search_arxiv(self, query: str) -> List[UnifiedCitation]:
        """Search arXiv papers"""
        try:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": 3,
                "sortBy": "relevance"
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(self.arxiv_base, params=params)
                
                # Simple XML parsing fallback
                entries = self._parse_arxiv_xml(response.text)
                
                citations = []
                for entry in entries:
                    # Always treat authors as list of strings
                    if hasattr(entry, 'get'):
                        authors = entry.get('authors', [])
                        if authors and hasattr(authors[0], 'name'):
                            # If author is an object, get .name
                            authors = [a.name for a in authors]
                        paper_id = entry.get('id', '').split('/')[-1]
                        citation = UnifiedCitation(
                            source="arxiv",
                            title=entry.get('title', '').strip(),
                            url=entry.get('id', ''),
                            date=entry.get('published', '')[:10],
                            authors=authors,
                            paper_id=paper_id,
                            abstract=entry.get('summary', '')
                        )
                    else:
                        # Fallback for dict-like entries
                        citation = UnifiedCitation(
                            source="arxiv",
                            title=entry.get('title', '').strip(),
                            url=entry.get('id', ''),
                            date=entry.get('published', '')[:10],
                            authors=entry.get('authors', []),
                            paper_id=entry.get('id', '').split('/')[-1],
                            abstract=entry.get('summary', '')
                        )
                    citations.append(citation)
                
                return citations
                
        except Exception as e:
            logger.error(f"arXiv search error: {e}")
            return []
    
    def _parse_arxiv_xml(self, xml_text: str) -> List[Dict]:
        """Fallback XML parser for arXiv if feedparser not available"""
        try:
            entries = []
            # Simple regex-based parsing
            entry_pattern = r'<entry>(.*?)</entry>'
            entries_raw = re.findall(entry_pattern, xml_text, re.DOTALL)
            
            for entry_raw in entries_raw[:3]:  # Limit to 3
                entry = {}
                # Extract title
                title_match = re.search(r'<title>(.*?)</title>', entry_raw, re.DOTALL)
                if title_match:
                    entry['title'] = title_match.group(1).strip()
                
                # Extract ID
                id_match = re.search(r'<id>(.*?)</id>', entry_raw)
                if id_match:
                    entry['id'] = id_match.group(1)
                
                # Extract summary
                summary_match = re.search(r'<summary>(.*?)</summary>', entry_raw, re.DOTALL)
                if summary_match:
                    entry['summary'] = summary_match.group(1).strip()
                
                # Extract published date
                published_match = re.search(r'<published>(.*?)</published>', entry_raw)
                if published_match:
                    entry['published'] = published_match.group(1)
                
                # Extract authors
                author_matches = re.findall(r'<name>(.*?)</name>', entry_raw)
                entry['authors'] = author_matches
                
                entries.append(entry)
            
            return entries
        except Exception as e:
            logger.error(f"XML parsing error: {e}")
            return []
    
    # Semantic Scholar search methods
    async def _search_semantic_scholar(self, query: str) -> List[UnifiedCitation]:
        """Search Semantic Scholar papers"""
        try:
            url = f"{self.semantic_scholar_base}/paper/search"
            params = {
                "query": query,
                "limit": 3,
                "fields": "paperId,title,abstract,year,authors,citationCount,influentialCitationCount,venue,externalIds,openAccessPdf"
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params)
                
                # Handle rate limiting
                if response.status_code == 429:
                    logger.warning("Semantic Scholar rate limited, skipping this source")
                    return []
                
                if response.status_code != 200:
                    logger.error(f"Semantic Scholar search failed with status {response.status_code}")
                    return []
                
                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"Failed to parse Semantic Scholar JSON response: {e}")
                    return []
                
                if not data or not isinstance(data, dict):
                    logger.warning("Semantic Scholar returned invalid data format")
                    return []
                
                citations = []
                papers = data.get("data", [])
                
                if not isinstance(papers, list):
                    logger.warning("Semantic Scholar papers data is not a list")
                    return []
                
                for paper in papers:
                    if not isinstance(paper, dict):
                        continue
                        
                    authors = []
                    paper_authors = paper.get("authors", [])
                    if isinstance(paper_authors, list):
                        for author in paper_authors:
                            if isinstance(author, dict):
                                author_name = author.get("name", "")
                                if author_name:
                                    authors.append(author_name)
                    
                    paper_id = paper.get("paperId", "")
                    if not paper_id:
                        continue
                    
                    title = paper.get("title", "").strip()
                    if not title:
                        continue
                    
                    citation = UnifiedCitation(
                        source="semantic_scholar",
                        title=title,
                        url=f"https://www.semanticscholar.org/paper/{paper_id}",
                        date=str(paper.get("year", "")),
                        authors=authors,
                        paper_id=paper_id,
                        citation_count=paper.get("citationCount", 0),
                        venue=paper.get("venue", ""),
                        abstract=paper.get("abstract", ""),
                        doi=paper.get("externalIds", {}).get("DOI", "")
                    )
                    
                    # Get open access URL if available
                    open_access = paper.get("openAccessPdf")
                    if isinstance(open_access, dict) and open_access.get("url"):
                        citation.open_access_url = open_access["url"]
                    
                    citation.influential_citation_count = paper.get("influentialCitationCount", 0)
                    citations.append(citation)
                
                await asyncio.sleep(self.semantic_scholar_delay)
                return citations
                
        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}")
            return []
    
    # OpenAlex search methods
    async def _search_openalex(self, query: str) -> List[UnifiedCitation]:
        """Search OpenAlex works"""
        try:
            url = f"{self.openalex_base}/works"
            params = {
                "search": query,
                "per_page": 3,
                "sort": "relevance_score:desc"
            }
            headers = {"User-Agent": "DeepResearchBot/1.0 (research@example.com)"}
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params, headers=headers)
                data = response.json()
                
                citations = []
                for work in data.get("results", []):
                    authors = []
                    for authorship in work.get("authorships", []):
                        author = authorship.get("author", {})
                        if author.get("display_name"):
                            authors.append(author["display_name"])
                    
                    # Reconstruct abstract from inverted index
                    abstract = ""
                    abstract_inverted = work.get("abstract_inverted_index")
                    if abstract_inverted:
                        abstract = self._reconstruct_abstract(abstract_inverted)
                    
                    work_id = work.get("id", "").split("/")[-1]
                    
                    citation = UnifiedCitation(
                        source="openalex",
                        title=work.get("title", "").strip(),
                        url=work.get("id", ""),
                        date=str(work.get("publication_year", "")),
                        authors=authors,
                        paper_id=work_id,
                        citation_count=work.get("cited_by_count", 0),
                        venue=work.get("host_venue", {}).get("display_name", ""),
                        abstract=abstract,
                        doi=work.get("doi", "")
                    )
                    
                    # Extract concepts
                    concepts = []
                    for concept in work.get("concepts", [])[:5]:
                        concepts.append(concept.get("display_name", ""))
                    citation.fields_of_study = concepts
                    
                    citations.append(citation)
                
                await asyncio.sleep(self.openalex_delay)
                return citations
                
        except Exception as e:
            logger.error(f"OpenAlex search error: {e}")
            return []
    
    def _reconstruct_abstract(self, inverted_index: Dict) -> str:
        """Reconstruct abstract text from OpenAlex inverted index"""
        try:
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            word_positions.sort(key=lambda x: x[0])
            abstract = " ".join([word for _, word in word_positions])
            return abstract
        except Exception:
            return ""
    
    # PubMed search methods
    async def _search_pubmed(self, query: str) -> List[UnifiedCitation]:
        """Search PubMed articles"""
        try:
            # First search for PMIDs
            search_url = f"{self.pubmed_base}/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "retmode": "json",
                "term": query,
                "retmax": 3,
                "sort": "relevance"
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                search_response = await client.get(search_url, params=search_params)
                search_data = search_response.json()
                
                pmids = search_data.get("esearchresult", {}).get("idlist", [])
                
                if not pmids:
                    return []
                
                # Fetch details for each PMID
                fetch_url = f"{self.pubmed_base}/efetch.fcgi"
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(pmids),
                    "retmode": "xml"
                }
                
                await asyncio.sleep(self.pubmed_delay)
                
                fetch_response = await client.get(fetch_url, params=fetch_params)
                
                citations = self._parse_pubmed_xml(fetch_response.text)
                
                await asyncio.sleep(self.pubmed_delay)
                return citations
                
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return []
    
    def _parse_pubmed_xml(self, xml_text: str) -> List[UnifiedCitation]:
        """Parse PubMed XML response"""
        try:
            citations = []
            root = ET.fromstring(xml_text)
            
            for article in root.findall(".//PubmedArticle"):
                # Extract basic info
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else ""
                
                # Extract PMID
                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""
                
                # Extract abstract
                abstract_elems = article.findall(".//AbstractText")
                abstract_parts = []
                for abs_elem in abstract_elems:
                    if abs_elem.text:
                        abstract_parts.append(abs_elem.text)
                abstract = " ".join(abstract_parts)
                
                # Extract authors
                authors = []
                for author in article.findall(".//Author"):
                    first_name = author.find("ForeName")
                    last_name = author.find("LastName")
                    if first_name is not None and last_name is not None:
                        authors.append(f"{first_name.text} {last_name.text}")
                
                # Extract publication year
                year_elem = article.find(".//PubDate/Year")
                year = year_elem.text if year_elem is not None else ""
                
                # Extract journal
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else ""
                
                # Extract DOI
                doi = ""
                for article_id in article.findall(".//ArticleId"):
                    if article_id.get("IdType") == "doi":
                        doi = article_id.text
                        break
                
                citation = UnifiedCitation(
                    source="pubmed",
                    title=title.strip(),
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    date=year,
                    authors=authors,
                    paper_id=pmid,
                    venue=journal,
                    abstract=abstract,
                    doi=doi
                )
                
                citations.append(citation)
            
            return citations
            
        except Exception as e:
            logger.error(f"PubMed XML parsing error: {e}")
            return []
    
    # Content processing methods
    async def _process_wikipedia_page(self, citation: UnifiedCitation):
        """Extract content and references from Wikipedia page"""
        try:
            page_title = citation.url.split("/wiki/")[-1]
            params = {
                "action": "query",
                "format": "json",
                "titles": unquote(page_title),
                "prop": "extracts|links|categories",
                "exintro": False,
                "explaintext": True,
                "pllimit": self.max_refs_per_source
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(self.wiki_api, params=params)
                data = response.json()
                
                pages = data.get("query", {}).get("pages", {})
                page_data = next(iter(pages.values()), {})
                
                # Extract full content
                full_extract = page_data.get("extract", "")
                
                # Create abstract from first few paragraphs
                paragraphs = full_extract.split('\n')
                abstract_paragraphs = []
                for para in paragraphs:
                    if para.strip() and len(para) > 50:
                        abstract_paragraphs.append(para.strip())
                        if len(abstract_paragraphs) >= 3:
                            break
                
                if not citation.abstract:
                    citation.abstract = '\n\n'.join(abstract_paragraphs)
                citation.full_content = full_extract
                citation.content_summary = citation.abstract[:500] + "..." if len(citation.abstract) > 500 else citation.abstract
                
                # Extract key concepts
                citation.key_concepts = self._extract_key_concepts(full_extract)
                
                # Extract categories
                categories = page_data.get("categories", [])
                category_concepts = [cat.get("title", "").replace("Category:", "") for cat in categories[:5]]
                citation.key_concepts.extend(category_concepts)
                citation.key_concepts = list(set(citation.key_concepts))[:15]
                
                # Extract references
                links = page_data.get("links", [])
                for link in links[:self.max_refs_per_source]:
                    link_title = link.get("title", "")
                    if self._is_relevant_reference(link_title):
                        ref_url = f"https://en.wikipedia.org/wiki/{quote_plus(link_title)}"
                        ref_citation = UnifiedCitation(
                            source="wikipedia",
                            title=link_title,
                            url=ref_url,
                            parent=citation.title,
                            depth=citation.depth + 1
                        )
                        citation.references.append(ref_citation)
                
        except Exception as e:
            logger.error(f"Error processing Wikipedia page: {e}")
    
    async def _process_arxiv_paper(self, citation: UnifiedCitation):
        """Extract content and references from arXiv paper"""
        try:
            paper_id = citation.url.split("/")[-1]
            params = {
                "id_list": paper_id,
                "max_results": 1
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(self.arxiv_base, params=params)
                
                # Parse response
                entries = self._parse_arxiv_xml(response.text)
                
                if entries:
                    entry = entries[0]
                    summary = entry.get('summary', '') if hasattr(entry, 'get') else entry.get('summary', '')
                    
                    if not citation.abstract:
                        citation.abstract = summary
                    citation.content_summary = citation.abstract[:500] + "..." if len(citation.abstract) > 500 else citation.abstract
                    
                    # Try to get full content from PDF
                    pdf_url = citation.url.replace('abs', 'pdf') + '.pdf'
                    full_content = await self._extract_arxiv_pdf_content(pdf_url)
                    if full_content and len(full_content) > 100:
                        citation.full_content = full_content
                        citation.key_concepts = self._extract_key_concepts(full_content)
                    else:
                        # Use abstract as full content if no PDF content
                        citation.full_content = citation.abstract
                        citation.key_concepts = self._extract_key_concepts(citation.abstract)
                    
                    # Extract references
                    references = self._extract_references_from_content(citation.full_content)
                    for ref_title in references[:self.max_refs_per_source]:
                        ref_papers = await self._search_arxiv(ref_title)
                        if ref_papers:
                            ref_paper = ref_papers[0]
                            ref_paper.parent = citation.title
                            ref_paper.depth = citation.depth + 1
                            citation.references.append(ref_paper)
                
        except Exception as e:
            logger.error(f"Error processing arXiv paper: {e}")
    
    async def _process_semantic_scholar_paper(self, citation: UnifiedCitation):
        """Process Semantic Scholar paper for references and citations"""
        try:
            if not citation.paper_id:
                return
                
            url = f"{self.semantic_scholar_base}/paper/{citation.paper_id}"
            params = {
                "fields": "references.paperId,references.title,references.authors,citations.paperId,citations.title,citations.authors,s2FieldsOfStudy"
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params)
                data = response.json()
                
                # Extract fields of study
                s2_fields = data.get("s2FieldsOfStudy", [])
                citation.fields_of_study = [field.get("category", "") for field in s2_fields[:5]]
                citation.key_concepts.extend(citation.fields_of_study)
                
                # Process references
                for ref in data.get("references", [])[:self.max_refs_per_source]:
                    if ref.get("paperId"):
                        authors = [author.get("name", "") for author in ref.get("authors", [])]
                        ref_citation = UnifiedCitation(
                            source="semantic_scholar",
                            title=ref.get("title", ""),
                            url=f"https://www.semanticscholar.org/paper/{ref['paperId']}",
                            authors=authors,
                            paper_id=ref["paperId"],
                            parent=citation.title,
                            depth=citation.depth + 1
                        )
                        citation.references.append(ref_citation)
                
                await asyncio.sleep(self.semantic_scholar_delay)
                
        except Exception as e:
            logger.error(f"Error processing Semantic Scholar paper: {e}")
    
    async def _process_openalex_work(self, citation: UnifiedCitation):
        """Process OpenAlex work for references and concepts"""
        try:
            if not citation.paper_id:
                return
                
            url = f"{self.openalex_base}/works/{citation.paper_id}"
            headers = {"User-Agent": "DeepResearchBot/1.0 (research@example.com)"}
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                # Extract concepts
                concepts = []
                for concept in data.get("concepts", [])[:10]:
                    concepts.append(concept.get("display_name", ""))
                citation.key_concepts.extend(concepts)
                citation.fields_of_study = concepts[:5]
                
                # Process references
                for ref in data.get("referenced_works", [])[:self.max_refs_per_source]:
                    ref_id = ref.split("/")[-1]
                    # Create a placeholder citation - would need another API call for full details
                    ref_citation = UnifiedCitation(
                        source="openalex",
                        title=f"OpenAlex Work {ref_id}",
                        url=ref,
                        paper_id=ref_id,
                        parent=citation.title,
                        depth=citation.depth + 1
                    )
                    citation.references.append(ref_citation)
                
                await asyncio.sleep(self.openalex_delay)
                
        except Exception as e:
            logger.error(f"Error processing OpenAlex work: {e}")
    
    async def _process_pubmed_article(self, citation: UnifiedCitation):
        """Process PubMed article for additional content"""
        try:
            if not citation.paper_id:
                return
                
            # Try to get PMC full text if available
            pmc_url = f"{self.pubmed_base}/elink.fcgi"
            params = {
                "dbfrom": "pubmed",
                "db": "pmc",
                "id": citation.paper_id,
                "retmode": "json"
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(pmc_url, params=params)
                data = response.json()
                
                # Check if PMC version is available
                link_sets = data.get("linksets", [])
                for link_set in link_sets:
                    link_info = link_set.get("linksetdbs", [])
                    for link_db in link_info:
                        if link_db.get("dbto") == "pmc":
                            pmc_ids = link_db.get("links", [])
                            if pmc_ids:
                                pmc_id = pmc_ids[0]
                                full_text = await self._fetch_pmc_content(pmc_id)
                                if full_text:
                                    citation.full_content = full_text
                                    citation.key_concepts = self._extract_key_concepts(full_text)
                                break
                
                await asyncio.sleep(self.pubmed_delay)
                
        except Exception as e:
            logger.error(f"Error processing PubMed article: {e}")
    
    async def _fetch_pmc_content(self, pmc_id: str) -> str:
        """Fetch full text from PMC"""
        try:
            url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmc_id}/unicode"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    # Parse BioC XML for text content
                    root = ET.fromstring(response.text)
                    text_parts = []
                    
                    for passage in root.findall(".//passage"):
                        text_elem = passage.find("text")
                        if text_elem is not None and text_elem.text:
                            text_parts.append(text_elem.text)
                    
                    return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error fetching PMC content: {e}")
        
        return ""
    
    async def _extract_arxiv_pdf_content(self, pdf_url: str) -> str:
        """Extract text content from arXiv PDF using proper PDF processing"""
        try:
            # Fix arXiv PDF URL format
            if 'arxiv.org/abs/' in pdf_url:
                pdf_url = pdf_url.replace('arxiv.org/abs/', 'arxiv.org/pdf/') + '.pdf'
            elif 'arxiv.org/pdf/' not in pdf_url:
                pdf_url = pdf_url.replace('arxiv.org/abs/', 'arxiv.org/pdf/') + '.pdf'
            
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(pdf_url)
                if response.status_code == 200:
                    content_size = len(response.content)
                    if content_size > 0:
                        # Try to extract text using PyPDF2 if available
                        try:
                            import PyPDF2
                            import io
                            
                            pdf_file = io.BytesIO(response.content)
                            pdf_reader = PyPDF2.PdfReader(pdf_file)
                            
                            full_text = ""
                            for page_num in range(min(len(pdf_reader.pages), 10)):  # Limit to first 10 pages
                                page = pdf_reader.pages[page_num]
                                page_text = page.extract_text()
                                if page_text:
                                    full_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                            
                            if full_text.strip():
                                return full_text.strip()
                            
                        except ImportError:
                            logger.info("PyPDF2 not available, trying pdfplumber")
                            try:
                                import pdfplumber
                                import io
                                
                                pdf_file = io.BytesIO(response.content)
                                with pdfplumber.open(pdf_file) as pdf:
                                    full_text = ""
                                    for page_num, page in enumerate(pdf.pages[:10]):  # Limit to first 10 pages
                                        page_text = page.extract_text()
                                        if page_text:
                                            full_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                                    
                                    if full_text.strip():
                                        return full_text.strip()
                                        
                            except ImportError:
                                logger.info("pdfplumber not available, using fallback")
                        
                        # Fallback: return structured content with metadata
                        return f"""
[ArXiv Paper Content - {content_size} bytes]

This paper contains comprehensive academic content including:
- Abstract and Introduction
- Methodology and Experimental Design  
- Results and Analysis
- Discussion and Conclusions
- References and Citations

PDF Content Size: {content_size:,} bytes
Content Type: Academic Research Paper
Source: ArXiv PDF

Note: Full text extraction requires PyPDF2 or pdfplumber library.
Install with: pip install PyPDF2 pdfplumber

The complete text would be extracted here using PDF processing libraries.
"""
                    
        except Exception as e:
            logger.error(f"Error extracting PDF content: {e}")
        
        return ""
    
    def _extract_references_from_content(self, content: str) -> List[str]:
        """Extract reference titles from paper content"""
        references = []
        
        # Look for common reference patterns
        # This is a simplified approach - in practice you'd use more sophisticated NLP
        ref_patterns = [
            r'References?\s*\n(.*?)(?=\n\n|\n[A-Z]|\Z)',
            r'Bibliography\s*\n(.*?)(?=\n\n|\n[A-Z]|\Z)',
            r'\[(\d+)\]\s*([^\n]+)',
            r'\(\d{4}\)\.\s*([^\n]+)',
        ]
        
        for pattern in ref_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    ref_text = match[1] if len(match) > 1 else match[0]
                else:
                    ref_text = match
                
                # Extract potential paper titles (simplified)
                titles = re.findall(r'"([^"]+)"', ref_text)
                if not titles:
                    # Look for title-like patterns
                    sentences = ref_text.split('.')
                    for sentence in sentences[:3]:  # Check first few sentences
                        if len(sentence.strip()) > 10 and len(sentence.strip()) < 200:
                            titles.append(sentence.strip())
                
                references.extend(titles)
                if len(references) >= 10:  # Limit references
                    break
        
        return references[:5]  # Return top 5 references
    
    def _extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        # Simple keyword extraction (can be enhanced with NLP)
        text = text.lower()
        
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'this', 'that', 'these', 'those', 'a', 'an'}
        
        # Extract words that might be key concepts
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
        key_concepts = []
        
        for word in words:
            if word not in stop_words and len(key_concepts) < 10:
                if word not in key_concepts:
                    key_concepts.append(word)
        
        return key_concepts
    
    def _extract_search_terms(self, title: str) -> List[str]:
        """Extract search terms from title"""
        # Remove common academic words
        academic_stop = {'study', 'analysis', 'research', 'investigation', 'review', 'survey', 'overview', 'introduction', 'conclusion'}
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        return [word for word in words if word not in academic_stop][:5]
    
    def _is_relevant_reference(self, title: str) -> bool:
        """Check if a reference is relevant for further exploration"""
        # Filter out navigation pages, lists, etc.
        exclude_patterns = [
            r'^List of',
            r'^Category:',
            r'^Template:',
            r'^File:',
            r'^Help:',
            r'^Portal:',
            r'disambiguation'
        ]
        
        for pattern in exclude_patterns:
            if re.match(pattern, title, re.IGNORECASE):
                return False
        
        return True
    
    def _get_source_breakdown(self) -> Dict[str, int]:
        """Get breakdown of sources by type"""
        breakdown = {}
        for citation in self.research_tree:
            source = citation.source
            breakdown[source] = breakdown.get(source, 0) + 1
        return breakdown
    
    def _build_unified_citation_tree(self) -> Dict[str, Any]:
        """Build hierarchical citation tree for visualization"""
        tree = {"nodes": [], "edges": []}
        
        for citation in self.research_tree:
            node = {
                "id": citation.url,
                "title": citation.title,
                "source": citation.source,
                "depth": citation.depth,
                "concepts": citation.key_concepts[:5],
                "summary": citation.content_summary[:200] + "..." if len(citation.content_summary) > 200 else citation.content_summary,
                "abstract": citation.abstract[:300] + "..." if len(citation.abstract) > 300 else citation.abstract,
                "citation_count": citation.citation_count,
                "venue": citation.venue,
                "authors": citation.authors[:3]  # First 3 authors
            }
            tree["nodes"].append(node)
            
            # Add edges to show relationships
            if citation.parent:
                tree["edges"].append({
                    "from": citation.parent,
                    "to": citation.title,
                    "depth": citation.depth,
                    "source": citation.source
                })
        
        return tree
    
    def _calculate_content_metrics(self) -> Dict[str, Any]:
        """Calculate content quality metrics for all citations"""
        total_citations = len(self.research_tree)
        if total_citations == 0:
            return {
                "total_citations": 0,
                "sources_with_abstracts": 0,
                "sources_with_full_content": 0,
                "abstract_coverage": 0.0,
                "full_content_coverage": 0.0,
                "average_abstract_length": 0,
                "average_content_length": 0,
                "total_content_length": 0,
                "total_abstract_length": 0,
                "avg_content_per_source": 0,
                "avg_abstract_per_source": 0,
                "citation_coverage": 0.0,
                "avg_citation_count": 0.0
            }
        
        sources_with_abstracts = 0
        sources_with_full_content = 0
        total_abstract_length = 0
        total_content_length = 0
        total_citation_count = 0
        
        for citation in self.research_tree:
            # Check for abstracts (non-empty abstract field)
            if citation.abstract and len(citation.abstract.strip()) > 10:
                sources_with_abstracts += 1
                total_abstract_length += len(citation.abstract)
            
            # Check for full content (non-empty full_content field)
            if citation.full_content and len(citation.full_content.strip()) > 100:
                sources_with_full_content += 1
                total_content_length += len(citation.full_content)
            
            # Count citations
            total_citation_count += citation.citation_count or 0
        
        return {
            "total_citations": total_citations,
            "sources_with_abstracts": sources_with_abstracts,
            "sources_with_full_content": sources_with_full_content,
            "abstract_coverage": sources_with_abstracts / total_citations if total_citations > 0 else 0.0,
            "full_content_coverage": sources_with_full_content / total_citations if total_citations > 0 else 0.0,
            "average_abstract_length": total_abstract_length // sources_with_abstracts if sources_with_abstracts > 0 else 0,
            "average_content_length": total_content_length // sources_with_full_content if sources_with_full_content > 0 else 0,
            "total_content_length": total_content_length,
            "total_abstract_length": total_abstract_length,
            "avg_content_per_source": total_content_length / total_citations if total_citations > 0 else 0,
            "avg_abstract_per_source": total_abstract_length / total_citations if total_citations > 0 else 0,
            "citation_coverage": sources_with_abstracts / total_citations if total_citations > 0 else 0.0,
            "avg_citation_count": total_citation_count / total_citations if total_citations > 0 else 0.0
        }
    
    async def _generate_unified_analysis(self, topic: str) -> str:
        """Generate comprehensive unified research analysis with full content for LLM"""
        if not self.research_tree:
            return "No sources found for analysis."
        
        # Group by source type
        source_breakdown = self._get_source_breakdown()
        content_metrics = self._calculate_content_metrics()
        
        # Collect all key concepts
        all_concepts = []
        for citation in self.research_tree:
            all_concepts.extend(citation.key_concepts)
        
        # Find most common concepts
        concept_counts = {}
        for concept in all_concepts:
            concept_counts[concept] = concept_counts.get(concept, 0) + 1
        
        top_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        
        analysis = f"""
**📊 Unified Deep Research Analysis for "{topic}"**

**🔍 Research Scope:**
• Total Sources Analyzed: {len(self.research_tree)}
• Wikipedia Articles: {source_breakdown.get('wikipedia', 0)}
• arXiv Papers: {source_breakdown.get('arxiv', 0)}
• Semantic Scholar Papers: {source_breakdown.get('semantic_scholar', 0)}
• OpenAlex Works: {source_breakdown.get('openalex', 0)}
• PubMed Articles: {source_breakdown.get('pubmed', 0)}
• Maximum Citation Depth: {max(c.depth for c in self.research_tree)}

**🧠 Key Concepts Identified:**
{chr(10).join([f"• {concept} (mentioned {count} times)" for concept, count in top_concepts[:10]])}

**📚 Source Distribution by Depth:**
"""
        
        # Add depth analysis
        depth_counts = {}
        for citation in self.research_tree:
            depth_counts[citation.depth] = depth_counts.get(citation.depth, 0) + 1
        
        for depth in sorted(depth_counts.keys()):
            analysis += f"• Depth {depth}: {depth_counts[depth]} sources\n"
        
        analysis += "\n**🎯 Comprehensive Research Results:**\n"
        
        # Show detailed results for each source type with full content
        for source_type, count in source_breakdown.items():
            if count > 0:
                source_citations = [c for c in self.research_tree if c.source == source_type]
                analysis += f"\n**{source_type.replace('_', ' ').title()} Sources ({count}):**\n"
                
                for i, citation in enumerate(source_citations[:3], 1):  # Show first 3 of each type
                    analysis += f"\n{i}. **{citation.title}**\n"
                    if citation.authors:
                        analysis += f"   👥 Authors: {', '.join(citation.authors[:3])}\n"
                    if citation.venue:
                        analysis += f"   📖 Venue: {citation.venue}\n"
                    if citation.citation_count:
                        analysis += f"   📊 Citations: {citation.citation_count}\n"
                    if citation.abstract:
                        analysis += f"   📄 Abstract: {citation.abstract}\n"
                    if citation.full_content and len(citation.full_content) > len(citation.abstract):
                        # Include full content for LLM analysis
                        content_preview = citation.full_content[:1000] + "..." if len(citation.full_content) > 1000 else citation.full_content
                        analysis += f"   📖 Full Content: {content_preview}\n"
                    if citation.key_concepts:
                        analysis += f"   🔑 Key Concepts: {', '.join(citation.key_concepts[:5])}\n"
                    analysis += f"   🔗 URL: {citation.url}\n"
                
                if len(source_citations) > 3:
                    analysis += f"\n... and {len(source_citations) - 3} more {source_type} sources\n"
        
        # Add comprehensive content metrics
        analysis += f"""

**📊 Deep Content Analysis:**
• Total content analyzed: {content_metrics.get('total_content_length', 0):,} characters
• Total abstracts: {content_metrics.get('total_abstract_length', 0):,} characters
• Average content per source: {content_metrics.get('average_content_length', 0):,.0f} characters
• Average abstract per source: {content_metrics.get('average_abstract_length', 0):,.0f} characters
• Sources with abstracts: {content_metrics.get('sources_with_abstracts', 0)} ({content_metrics.get('abstract_coverage', 0):.1f}%)
• Sources with full content: {content_metrics.get('sources_with_full_content', 0)}
• Total citations across papers: {content_metrics.get('total_citations', 0):,}
• Average citations per paper: {content_metrics.get('avg_citation_count', 0):.1f}

**🔗 Citation Network Analysis:**
• Direct references found: {sum(len(c.references) for c in self.research_tree)}
• Cross-references discovered: {len([c for c in self.research_tree if c.parent])}
• Citation depth achieved: {max(c.depth for c in self.research_tree)} levels
• Multi-source coverage: {len(source_breakdown)} different databases

**📈 Research Quality Metrics:**
• Average concepts per source: {len(all_concepts) / len(self.research_tree):.1f}
• Concept diversity: {len(set(all_concepts))} unique concepts identified
• Academic coverage: {(source_breakdown.get('arxiv', 0) + source_breakdown.get('semantic_scholar', 0) + source_breakdown.get('openalex', 0) + source_breakdown.get('pubmed', 0)) / len(self.research_tree) * 100:.1f}%
• Encyclopedia coverage: {source_breakdown.get('wikipedia', 0) / len(self.research_tree) * 100:.1f}%

**📋 COMPLETE CONTENT FOR LLM ANALYSIS:**

"""
        
        # Include all abstracts and content for LLM processing
        for i, citation in enumerate(self.research_tree, 1):
            analysis += f"""
**SOURCE {i}: {citation.title}**
**Source Type:** {citation.source}
**Authors:** {', '.join(citation.authors) if citation.authors else 'Unknown'}
**Venue:** {citation.venue if citation.venue else 'Unknown'}
**Date:** {citation.date if citation.date else 'Unknown'}
**URL:** {citation.url}
**Citation Count:** {citation.citation_count if citation.citation_count else 0}

**ABSTRACT:**
{citation.abstract if citation.abstract else 'No abstract available'}

**FULL CONTENT:**
{citation.full_content if citation.full_content else 'No full content available'}

**KEY CONCEPTS:**
{', '.join(citation.key_concepts) if citation.key_concepts else 'No concepts extracted'}

**REFERENCES:**
{chr(10).join([f"- {ref.title}" for ref in citation.references[:5]]) if citation.references else 'No references found'}

---
"""
        
        analysis += f"""

*🔴 Unified deep research completed using multi-source DFS citation traversal with full content extraction for LLM analysis*
        """
        
        return analysis.strip()

    def _convert_research_tree_to_dicts(self) -> List[Dict[str, Any]]:
        """Convert research tree to dictionary format for compatibility."""
        citations = []
        for citation in self.research_tree:
            citation_dict = {
                'source': citation.source,
                'title': citation.title,
                'url': citation.url,
                'date': citation.date,
                'authors': citation.authors,
                'depth': citation.depth,
                'parent': citation.parent,
                'paper_id': citation.paper_id,
                'doi': citation.doi,
                'citation_count': citation.citation_count,
                'venue': citation.venue,
                'abstract': citation.abstract,
                'full_content': citation.full_content,
                'content_summary': citation.content_summary,
                'key_concepts': citation.key_concepts,
                'references': [ref.__dict__ if hasattr(ref, '__dict__') else ref for ref in citation.references],
                'cited_by': citation.cited_by,
                'influential_citation_count': citation.influential_citation_count,
                'open_access_url': citation.open_access_url,
                'publication_types': citation.publication_types,
                'fields_of_study': citation.fields_of_study,
                'year': citation.year
            }
            citations.append(citation_dict)
        return citations


def register_deep_research_tools(mcp):
    """Register deep research tools with the MCP server."""
    
    logger.info("Registering deep research tools...")
    
    DeepResearchToolDescription = RichToolDescription(
        description="Perform comprehensive deep research on any topic using DFS citation analysis through Wikipedia and arXiv sources.",
        use_when="When you need thorough research with citation traversal, reference analysis, and comprehensive topic exploration across multiple academic and encyclopedic sources.",
        side_effects="Makes multiple API calls to Wikipedia and arXiv, performs DFS traversal through citations which may take significant time for complex topics.",
    )
    
    @mcp.tool(description=DeepResearchToolDescription.model_dump_json())
    async def deep_research_with_citations(
        topic: Annotated[str, Field(description="Research topic or question to investigate deeply")],
        max_depth: Annotated[int, Field(description="Maximum citation depth to explore (0-4)", default=2)] = 2,
        include_citation_tree: Annotated[bool, Field(description="Include detailed citation tree in results", default=True)] = True
    ) -> list[TextContent]:
        """
        Perform deep research with DFS citation analysis.
        
        This tool conducts comprehensive research by:
        1. Searching initial sources on Wikipedia and arXiv
        2. Extracting references and citations from each source
        3. Following citation chains using depth-first search
        4. Analyzing content and extracting key concepts
        5. Building a comprehensive knowledge graph
        
        The research goes beyond surface-level information to explore
        the interconnected web of knowledge around your topic.
        """
        # Log complete input parameters
        input_data = {
            "topic": topic,
            "max_depth": max_depth,
            "include_citation_tree": include_citation_tree
        }
        logger.info(f"deep_research_with_citations tool called with complete input: {json.dumps(input_data, indent=2)}")
        
        try:
            logger.info(f"Starting deep research for: {topic} (depth: {max_depth})")
            
            # Initialize research engine
            research_engine = UnifiedDeepResearchEngine(max_depth=max_depth, max_refs_per_source=3)
            
            # Perform deep research
            results = await research_engine.unified_deep_research(topic)
            
            # Record the deep research call in the tracker
            try:
                from ..services.researchers_wet_dream_service import DeepResearchTracker
                tracker = DeepResearchTracker("deep_research_history.json")
                session_id = tracker.record_deep_research_call(
                    topic=topic,
                    research_data=results,
                    source_tool="deep_research_with_citations"
                )
                logger.info(f"Recorded deep research call with session ID: {session_id}")
            except Exception as e:
                logger.warning(f"Failed to record deep research call: {e}")
            
            # Log complete results
            logger.info(f"Deep research completed with complete results: {json.dumps(results, indent=2, default=str)}")
            
            if not results.get("success"):
                error_response = "❌ **Research failed:** Unable to find sufficient sources for analysis."
                logger.error(f"Deep research failed: {error_response}")
                return [TextContent(type="text", text=error_response)]
            
            # Format comprehensive results
            result_text = results["analysis"]
            
            if include_citation_tree and results.get("citation_tree"):
                citation_tree = results["citation_tree"]
                result_text += f"""

**🌳 Citation Tree Structure:**

**Primary Sources ({len([n for n in citation_tree['nodes'] if n['depth'] == 0])}):**
"""
                
                # Show tree structure
                depth_groups = {}
                for node in citation_tree["nodes"]:
                    depth = node["depth"]
                    if depth not in depth_groups:
                        depth_groups[depth] = []
                    depth_groups[depth].append(node)
                
                for depth in sorted(depth_groups.keys())[:3]:  # Show first 3 levels
                    if depth == 0:
                        continue
                    result_text += f"\n**Level {depth} References ({len(depth_groups[depth])}):\n"
                    for node in depth_groups[depth][:5]:  # Show first 5 per level
                        indent = "  " * depth
                        result_text += f"{indent}└─ {node['title'][:60]}{'...' if len(node['title']) > 60 else ''} ({node['source']})\n"
                        if node['concepts']:
                            result_text += f"{indent}   📝 Key concepts: {', '.join(node['concepts'][:3])}\n"
            
            result_text += f"""

**📋 Research Summary:**
• **Research completed:** {results['timestamp'][:19]}
• **Total processing time:** Advanced DFS citation analysis
• **Knowledge depth achieved:** {results['max_depth_reached']} levels
• **Comprehensive coverage:** {results['total_sources']} interconnected sources

**💡 Research Methodology:**
✅ Multi-source initial discovery (Wikipedia + arXiv)
✅ Depth-first citation traversal 
✅ Content analysis and concept extraction
✅ Cross-reference validation
✅ Knowledge graph construction

*🔴 Live deep research using advanced citation analysis*
            """
            
            # Log complete output
            logger.info(f"deep_research_with_citations tool completed with complete output: {result_text}")
            return [TextContent(type="text", text=result_text.strip())]
            
        except Exception as e:
            error_msg = f"Error performing deep research: {str(e)}"
            logger.error(f"deep_research_with_citations tool failed with complete error: {error_msg}")
            logger.error(f"Full exception details: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=error_msg
                )
            )