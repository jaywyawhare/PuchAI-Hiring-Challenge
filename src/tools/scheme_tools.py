from typing import Optional
from mcp.types import TextContent
from src.services.scheme_search import SchemeSearchService
from ..models.base import RichToolDescription
import json
import logging

logger = logging.getLogger(__name__)

def register_scheme_tools(mcp):
    """Register scheme search tools with the MCP server."""
    
    scheme_service = SchemeSearchService()
    
    # Create rich descriptions for tools
    search_schemes_desc = RichToolDescription(
        description="AI-powered semantic search for government schemes with comprehensive filtering options",
        use_when="User needs to find relevant government schemes based on criteria like demographics, location, or specific needs",
        side_effects="Makes database queries to search scheme information"
    )
    
    categories_desc = RichToolDescription(
        description="Get all available government scheme categories",
        use_when="User needs to know what categories of schemes are available (e.g., Education, Agriculture, Health)",
        side_effects=None
    )
    
    states_desc = RichToolDescription(
        description="Get all available states/regions for government schemes",
        use_when="User needs to know which states or regions have specific schemes available",
        side_effects=None
    )

    # Convert rich descriptions to JSON strings for the tool decorators
    search_desc_json = search_schemes_desc.model_dump_json()
    categories_desc_json = categories_desc.model_dump_json()
    states_desc_json = states_desc.model_dump_json()

    @mcp.tool(description=search_desc_json)
    async def search_government_schemes(
        query: str,
        state: Optional[str] = None,
        category: Optional[str] = None,
        gender: Optional[str] = None,
        caste: Optional[str] = None,
        is_bpl: Optional[bool] = None,
        is_student: Optional[bool] = None,
        is_minority: Optional[bool] = None,
        is_differently_abled: Optional[bool] = None,
        age_min: Optional[int] = None,
        age_max: Optional[int] = None,
        limit: int = 10,
        language: Optional[str] = None
    ) -> list[TextContent]:
        """
        Search government schemes using AI-powered semantic search with optional filters.
        
        This tool uses vector embeddings to find relevant government schemes based on:
        - Natural language queries (e.g., "scholarship for students", "agriculture support")
        - Optional filters for state, category, demographics, etc.
        
        Args:
            query: Natural language search query describing what you're looking for in any language
            state: Optional state/region filter (e.g., "Gujarat", "All")
            category: Optional category filter (e.g., "Education", "Agriculture")
            gender: Optional gender filter ("male", "female", "transgender")
            caste: Optional caste category (e.g., "sc", "st", "obc", "general")
            is_bpl: Optional Below Poverty Line filter (True/False)
            is_student: Optional student filter (True/False)
            is_minority: Optional minority community filter (True/False)
            is_differently_abled: Optional disability filter (True/False)
            age_min: Optional minimum age requirement
            age_max: Optional maximum age requirement
            limit: Maximum number of results to return (default: 10)
            language: Optional language code of the input query (e.g., "hi" for Hindi, "mr" for Marathi). Auto-detects if not provided.
            
        Returns:
            List of matching government schemes with details and similarity scores
        """
        try:
            logger.info(f"Searching schemes with query: '{query}' and filters")
            
            results = await scheme_service.search_schemes(
                query=query,
                state=state,
                category=category,
                gender=gender,
                caste=caste,
                is_bpl=is_bpl,
                is_student=is_student,
                is_minority=is_minority,
                is_differently_abled=is_differently_abled,
                age_min=age_min,
                age_max=age_max,
                limit=limit,
                source_lang=language
            )
            
            if "error" in results:
                return [TextContent(
                    type="text",
                    text=f"❌ Search Error: {results['error']}"
                )]
            
            if not results["results"]:
                return [TextContent(
                    type="text",
                    text=f"🔍 No schemes found for query: '{query}'\n\n" +
                          f"Filters applied: {json.dumps(results['filters_applied'], indent=2)}\n\n" +
                          "Try:\n" +
                          "- Broader search terms\n" +
                          "- Different filter combinations\n" +
                          "- Removing some filters"
                )]                # Format results for display
            # Handle title translation based on language
            title = "Government Schemes Search Results"
            query_label = "Query"
            found_label = "Found"
            schemes_label = "matching schemes"
            
            if language == "mr":
                title = "सरकारी योजनांचे शोध परिणाम"
                query_label = "शोध"
                found_label = "सापडले"
                schemes_label = "जुळणाऱ्या योजना"
            elif language == "hi":
                title = "सरकारी योजनाओं के खोज परिणाम"
                query_label = "खोज"
                found_label = "मिले"
                schemes_label = "मिलती-जुलती योजनाएं"
            
            response_parts = [
                f"🎯 **{title}**",
                f"📝 **{query_label}:** '{query}'",
                f"📊 **{found_label}** {results['total_count']} {schemes_label}",
                ""
            ]
            
            # Add applied filters with translations
            filters_title = "Applied Filters"
            if language == "mr":
                filters_title = "लागू केलेले फिल्टर"
            elif language == "hi":
                filters_title = "लागू किए गए फ़िल्टर"
                
            applied_filters = {k: v for k, v in results['filters_applied'].items() if v is not None}
            if applied_filters:
                response_parts.append(f"🔧 **{filters_title}:**")
                filter_translations = {
                    'state': 'राज्य' if language in ["mr", "hi"] else 'State',
                    'category': 'श्रेणी' if language in ["mr", "hi"] else 'Category',
                    'gender': 'लिंग' if language in ["mr", "hi"] else 'Gender',
                    'caste': 'जात' if language in ["mr", "hi"] else 'Caste',
                    'is_bpl': 'बीपीएल' if language in ["mr", "hi"] else 'BPL',
                    'is_student': 'विद्यार्थी' if language in ["mr", "hi"] else 'Student',
                    'is_minority': 'अल्पसंख्यांक' if language in ["mr", "hi"] else 'Minority',
                    'is_differently_abled': 'दिव्यांग' if language in ["mr", "hi"] else 'Differently Abled'
                }
                for key, value in applied_filters.items():
                    translated_key = filter_translations.get(key, key)
                    response_parts.append(f"  • {translated_key}: {value}")
                response_parts.append("")
            
            # Add scheme results with translations
            schemes_title = "Matching Schemes"
            if language == "mr":
                schemes_title = "जुळणाऱ्या योजना"
            elif language == "hi":
                schemes_title = "मिलती-जुलती योजनाएं"
                
            response_parts.append(f"📋 **{schemes_title}:**")
            response_parts.append("")
            
            for i, scheme in enumerate(results["results"], 1):
                similarity_percentage = (1 - scheme["similarity_score"]) * 100
                
                scheme_info = [
                    f"**{i}. {scheme['name']}** (Match: {similarity_percentage:.1f}%)",
                    f"🏛️ **State:** {scheme['state']}",
                    f"📂 **Category:** {scheme['category']}",
                    f"📝 **Description:** {scheme['description'][:200]}{'...' if len(scheme['description']) > 200 else ''}",
                ]
                
                # Add demographic info with translations
                demographic_info = []
                
                # Define translations
                translations = {
                    'mr': {
                        'Gender': 'लिंग',
                        'Caste': 'जात',
                        'BPL eligible': 'बीपीएल पात्र',
                        'For students': 'विद्यार्थ्यांसाठी',
                        'For minorities': 'अल्पसंख्यांकांसाठी',
                        'For differently abled': 'दिव्यांगांसाठी'
                    },
                    'hi': {
                        'Gender': 'लिंग',
                        'Caste': 'जाति',
                        'BPL eligible': 'बीपीएल पात्र',
                        'For students': 'छात्रों के लिए',
                        'For minorities': 'अल्पसंख्यकों के लिए',
                        'For differently abled': 'दिव्यांगों के लिए'
                    }
                }
                
                lang_dict = translations.get(language, {})
                
                if scheme['gender']:
                    label = lang_dict.get('Gender', 'Gender')
                    demographic_info.append(f"{label}: {scheme['gender']}")
                if scheme['caste']:
                    label = lang_dict.get('Caste', 'Caste')
                    demographic_info.append(f"{label}: {scheme['caste']}")
                if scheme['is_bpl']:
                    demographic_info.append(lang_dict.get('BPL eligible', 'BPL eligible'))
                if scheme['is_student']:
                    demographic_info.append(lang_dict.get('For students', 'For students'))
                if scheme['is_minority']:
                    demographic_info.append(lang_dict.get('For minorities', 'For minorities'))
                if scheme['is_differently_abled']:
                    demographic_info.append(lang_dict.get('For differently abled', 'For differently abled'))
                
                if demographic_info:
                    scheme_info.append(f"👥 **Eligibility:** {', '.join(demographic_info)}")
                
                if scheme['url']:
                    scheme_info.append(f"🔗 **More Info:** {scheme['url']}")
                
                if scheme['tags']:
                    scheme_info.append(f"🏷️ **Tags:** {scheme['tags']}")
                
                response_parts.extend(scheme_info)
                response_parts.append("")
            
            # Add usage tips with translations
            if language == "mr":
                response_parts.extend([
                    "💡 **चांगल्या परिणामांसाठी टिप्स:**",
                    "• विशिष्ट कीवर्ड वापरा (उदा., 'शिष्यवृत्ती', 'शेती', 'आरोग्य')",
                    "• लक्षित परिणामांसाठी फिल्टर एकत्र करा",
                    "• परिणाम न मिळाल्यास वेगवेगळे शोध शब्द वापरून पहा",
                    "• पात्रतेच्या तपशीलांसाठी योजनेचे URLs तपासा"
                ])
            elif language == "hi":
                response_parts.extend([
                    "💡 **बेहतर परिणामों के लिए सुझाव:**",
                    "• विशिष्ट कीवर्ड का प्रयोग करें (जैसे, 'छात्रवृत्ति', 'कृषि', 'स्वास्थ्य')",
                    "• लक्षित परिणामों के लिए फ़िल्टर को संयोजित करें",
                    "• परिणाम नहीं मिलने पर अलग खोज शब्द आज़माएं",
                    "• पात्रता विवरण के लिए योजना URLs की जांच करें"
                ])
            else:
                response_parts.extend([
                    "💡 **Tips for better results:**",
                    "• Use specific keywords (e.g., 'scholarship', 'agriculture', 'health')",
                    "• Combine filters for targeted results",
                    "• Try different search terms if no results found",
                    "• Check scheme URLs for detailed eligibility criteria"
                ])
            
            return [TextContent(
                type="text",
                text="\n".join(response_parts)
            )]
            
        except Exception as e:
            logger.error(f"Error in search_government_schemes: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Unexpected error occurred: {str(e)}"
            )]
    
    @mcp.tool(description=categories_desc_json)
    async def get_scheme_categories() -> list[TextContent]:
        """
        Get all available government scheme categories.
        
        This tool returns a list of all available categories for filtering schemes,
        such as Education, Agriculture, Health, etc.
        
        Returns:
            List of all available scheme categories
        """
        try:
            categories = await scheme_service.get_scheme_categories()
            
            if not categories:
                return [TextContent(
                    type="text",
                    text="❌ No categories found or database error"
                )]
            
            response_parts = [
                "📂 **Available Government Scheme Categories:**",
                "",
                f"📊 Total categories: {len(categories)}",
                ""
            ]
            
            # Group categories for better display
            for i, category in enumerate(categories, 1):
                response_parts.append(f"{i:2d}. {category}")
            
            response_parts.extend([
                "",
                "💡 **Usage:**",
                "Use these categories as the 'category' parameter in search_government_schemes",
                "Example: search_government_schemes('student support', category='Education & Learning')"
            ])
            
            return [TextContent(
                type="text",
                text="\n".join(response_parts)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_scheme_categories: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error fetching categories: {str(e)}"
            )]
    
    @mcp.tool(description=states_desc_json)
    async def get_scheme_states() -> list[TextContent]:
        """
        Get all available states/regions for government schemes.
        
        This tool returns a list of all available states and regions for filtering schemes.
        
        Returns:
            List of all available states/regions
        """
        try:
            states = await scheme_service.get_scheme_states()
            
            if not states:
                return [TextContent(
                    type="text",
                    text="❌ No states found or database error"
                )]
            
            response_parts = [
                "🗺️ **Available States/Regions for Government Schemes:**",
                "",
                f"📊 Total states/regions: {len(states)}",
                ""
            ]
            
            # Group states for better display
            for i, state in enumerate(states, 1):
                response_parts.append(f"{i:2d}. {state}")
            
            response_parts.extend([
                "",
                "💡 **Usage:**",
                "Use these states as the 'state' parameter in search_government_schemes",
                "• 'All' means schemes available across India",
                "• Specific state names for state-specific schemes",
                "Example: search_government_schemes('farmer support', state='Gujarat')"
            ])
            
            return [TextContent(
                type="text",
                text="\n".join(response_parts)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_scheme_states: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error fetching states: {str(e)}"
            )]
