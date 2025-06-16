# PuchAI Hiring Challenge - MCP Server Implementation

This repository contains my submission for the PuchAI hiring challenge. 

## Requirements

- Python 3.11
- Dependencies listed in `requirements.txt`

## Setup

1. Create and activate a Python virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with the following variables:
```
TOKEN=your_bearer_token_here
MY_NUMBER=your_number_here
```

## Running the Server

To start the MCP server:

```bash
python main.py
```

The server will run on `http://0.0.0.0:8085` with the following endpoints:

## References

- [Puch AI Challenge Announcement](https://x.com/puch_ai/status/1934600752007364906)
- [Challenge Gist](https://gist.github.com/ArjitJ/cc7356bff1f782c03bf59a4f65a9d2d6)