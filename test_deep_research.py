#!/usr/bin/env python3
"""
Simple test script for the unified deep research tool
"""
import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_deep_research():
    """Test the unified deep research functionality"""
    try:
        from src.tools.deep_research import UnifiedDeepResearchEngine
        
        print("🔍 Starting Unified Deep Research Test...")
        print("=" * 60)
        
        # Initialize the research engine
        engine = UnifiedDeepResearchEngine(max_depth=1, max_refs_per_source=2)
        
        # Perform research on AI
        print("📊 Researching 'artificial intelligence' at depth 1...")
        results = await engine.unified_deep_research('artificial intelligence')
        
        if results['success']:
            print(f"✅ Research completed successfully!")
            print(f"📈 Total sources analyzed: {results['total_sources']}")
            print(f"🎯 Max depth reached: {results['max_depth_reached']}")
            
            print("\n📋 SOURCE BREAKDOWN:")
            breakdown = results['source_breakdown']
            for source, count in breakdown.items():
                print(f"  • {source.replace('_', ' ').title()}: {count} sources")
            
            print("\n📊 CONTENT METRICS:")
            metrics = results['content_metrics']
            print(f"  • Total content: {metrics['total_content_length']:,} characters")
            print(f"  • Sources with abstracts: {metrics['sources_with_abstracts']}")
            print(f"  • Sources with full content: {metrics['sources_with_full_content']}")
            print(f"  • Average citations per paper: {metrics['avg_citation_count']:.1f}")
            
            print("\n📄 DETAILED ANALYSIS:")
            print(results['analysis'])
            
        else:
            print("❌ Research failed")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed")
    except Exception as e:
        print(f"❌ Error during research: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_deep_research())
