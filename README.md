# PuchAI Hiring Challenge - Enhanced MCP Server Implementation

This repository contains my submission for the PuchAI hiring challenge. While the core requirement was to implement a simple MCP server with resume functionality, I decided to extend it into a comprehensive backend implementation showcasing additional capabilities.

## 🎯 Base Requirements
- Implement MCP server with resume tool
- Return developer's resume in markdown format
- Include validation tool required by Puch AI system

## 🚀 Extended Implementation   
I went beyond the basic requirements to demonstrate expertise by implementing a comprehensive suite of tools and services:

### 🛠️ Service Architecture

#### Core Services
- **Content Fetcher**: Smart HTML-to-markdown conversion and content processing
- **URL Validator**: Robust URL validation and normalization
- **Core Service**: Base MCP functionality and tool registration
- **Web Service**: Content fetching and internet search capabilities
- **Railway Service**: Indian Railways integration
- **Music Service**: Multi-platform music streaming and search
- **Weather Service**: Real-time weather information
- **Academic Service**: Academic paper search and retrieval
- **News Service**: Hacker News integration
- **Scheme Search Service**: AI-powered government scheme search

### 🔧 Available Tools

#### Core Tools
- **Resume Tool**: Serves the developer's resume in markdown format
- **Validation Tool**: Required by Puch AI system
- **Help Menu**: Comprehensive documentation for all available tools

#### Web Tools
- **Content Fetcher**: 
  - Smart HTML-to-markdown conversion
  - Configurable content length and processing
  - Support for various content types
- **Internet Search**:
  - DuckDuckGo API integration
  - Customizable search results
  - Clean result formatting

#### Railway Tools (🔴 Live Data)
- Live train status tracking
- Station-to-station train search
- PNR status checking
- Complete train schedules
- Real-time station status
- Integration with erail.in API

#### Music Tools (🎵 Multi-Platform)
- Cross-platform music search
  - YouTube Music
  - Spotify
  - Apple Music
- Music recommendations by:
  - Genre
  - Mood
  - Artist
- YouTube integration:
  - High-quality audio streaming
  - Multiple format support
  - Custom quality selection
  - Direct download capabilities

#### Weather Tools (🌤️ Real-Time)
- Current weather conditions
- Location-based forecasts
- OpenMeteo API integration
- Timezone-aware results
- Comprehensive weather data

#### Academic Tools (📚 arXiv Integration)
- Paper search with advanced queries
- Detailed paper information
- Rate-limited API access
- Support for:
  - Multiple categories
  - Cross-references
  - Author search
  - Title search

#### News Tools (📰 Hacker News)
- Story retrieval by type:
  - Top stories
  - New submissions
  - Ask HN
  - Show HN
- Full-text search
- User profiles
- Comment threads
- Real-time updates

#### Government Scheme Search (🔍 AI-Powered)
- Semantic search using embeddings
- Smart filtering options:
  - State/Region
  - Category
  - Demographics
  - Eligibility criteria
- Natural language processing
- Similarity scoring