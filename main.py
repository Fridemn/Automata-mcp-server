"""
Automata MCP Server - A Model Context Protocol server with plugin architecture
"""
from pathlib import Path
from sys import stdout

from dotenv import load_dotenv
from loguru import logger

from app import main


if __name__ == "__main__":
    # Configure logging
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logger.remove()
    logger.add(
        logs_dir / "automata.log",
        rotation="10 MB",
        retention="1 week",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )
    logger.add(
        stdout,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    # Load environment variables
    load_dotenv()
    # Start the main application
    main()
