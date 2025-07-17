#!/usr/bin/env python3
"""
Kobo Notes Exporter

This script exports highlights and annotations from a Kobo eReader's SQLite database.
It supports multiple output formats including plain text, markdown, and JSON.

The script extracts:
- Highlighted text and annotations
- Book metadata (title, author)
- Chapter information and reading progress
- Highlight colors and types
- Creation dates and context

Usage:
    python export_kobo_notes.py -d /path/to/KoboReader.sqlite [-f format] [-o output_file]
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

def parse_date(date_str: Optional[str]) -> Optional[str]:
    """
    Parse date string from Kobo database into a consistent format.
    
    Args:
        date_str: Date string from Kobo database
        
    Returns:
        Formatted date string in 'YYYY-MM-DD HH:MM:SS' format,
        original string if parsing fails, or None if input is None
    """
    date_formats = [
        "%Y-%m-%dT%H:%M:%S.%f",  # Standard Kobo format
        "%Y-%m-%dT%H:%M:%S",     # Without microseconds
        "%Y-%m-%d %H:%M:%S",     # Alternative format
        "%Y-%m-%d"               # Just date
    ]
    
    if not date_str:
        return None
        
    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    
    return date_str  # Return original if no format matches

def get_highlights(db_path: str) -> List[Dict[str, Any]]:
    """
    Extract highlights from the Kobo SQLite database.
    
    Args:
        db_path: Path to the KoboReader.sqlite database file
        
    Returns:
        List of dictionaries containing highlight data with keys:
        - text: The highlighted text
        - annotation: User's annotation (if any)
        - date: Creation date
        - book_title: Title of the book
        - author: Book's author
        - progress: Reading progress as percentage
        - type: Type of highlight
        - context: Surrounding text context
    """
    highlights = []
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        query = """
        SELECT 
            b.Text,
            b.Annotation,
            b.DateCreated,
            b.VolumeID,
            c.Title,
            c.Attribution,
            b.ChapterProgress,
            b.Type,
            b.ContextString
        FROM Bookmark b
        LEFT JOIN content c ON b.VolumeID = c.ContentID
        WHERE b.Text IS NOT NULL OR b.Annotation IS NOT NULL
        ORDER BY b.DateCreated
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        for row in results:
            (text, annotation, date_created, volume_id, title, attribution, 
             chapter_progress, highlight_type, context_string) = row
            
            # Clean up the volume ID to extract book title if content table didn't have it
            if not title:
                try:
                    title = Path(volume_id).stem.split(' - ')[0].replace('_', ' ')
                    attribution = Path(volume_id).stem.split(' - ')[1].replace('.kepub', '').replace('_', ' ')
                except (IndexError, AttributeError):
                    title = volume_id
                    attribution = "Unknown Author"
            
            # Parse the date
            formatted_date = parse_date(date_created)
            
            # Format chapter progress as percentage
            progress_pct = f"{chapter_progress * 100:.1f}%" if chapter_progress is not None else None
            
            highlights.append({
                "text": text,
                "annotation": annotation,
                "date": formatted_date,
                "book_title": title,
                "author": attribution,
                "progress": progress_pct,
                "type": highlight_type or "highlight",
                "context": context_string
            })
    
    return highlights

def export_markdown(highlights: List[Dict[str, Any]]) -> str:
    """
    Export highlights in Markdown format.
    
    Args:
        highlights: List of highlight dictionaries from get_highlights()
        
    Returns:
        String containing formatted markdown text
    """
    output = "# Kobo Reader Highlights\n\n"
    current_book = None
    
    for h in highlights:
        if h["book_title"] != current_book:
            current_book = h["book_title"]
            output += f"\n## {h['book_title']}\n"
            output += f"*by {h['author']}*\n\n"
        
        # Add progress info if available
        if h["progress"]:
            output += f"*Progress: {h['progress']}*\n\n"
        
        # Add the highlight - ensure each line starts with >
        quote_lines = (h['text'] or "").splitlines()
        formatted_quote = '\n'.join(f"> {line.strip()}" if line.strip() else ">" for line in quote_lines)
        output += f"{formatted_quote}\n\n"
        
        # Add context if available
        if h["context"]:
            output += f"Context: _{h['context']}_\n\n"
        
        # Add annotation if available
        if h['annotation']:
            output += f"Note: *{h['annotation']}*\n\n"
        
        output += f"*Highlighted on {h['date']}*\n\n"
    
    return output

def export_plain(highlights: List[Dict[str, Any]]) -> str:
    """
    Export highlights in plain text format.
    
    Args:
        highlights: List of highlight dictionaries from get_highlights()
        
    Returns:
        String containing formatted plain text
    """
    output = "KOBO READER HIGHLIGHTS\n\n"
    current_book = None
    
    for h in highlights:
        if h["book_title"] != current_book:
            current_book = h["book_title"]
            output += f"\n{h['book_title']}\n"
            output += f"by {h['author']}\n"
            output += "=" * 40 + "\n\n"
        
        # Add progress info if available
        if h["progress"]:
            output += f"Progress: {h['progress']}\n\n"
        
        # Add the highlight
        output += f'"{h["text"]}"\n\n'
        
        # Add context if available
        if h["context"]:
            output += f"Context: {h['context']}\n\n"
        
        # Add annotation if available
        if h['annotation']:
            output += f"Note: {h['annotation']}\n\n"
        
        output += f"Highlighted on {h['date']}\n"
        output += "-" * 40 + "\n\n"
    
    return output

def main() -> int:
    """
    Main entry point for the script.
    
    Returns:
        0 on success, 1 on error
    """
    parser = argparse.ArgumentParser(description="Export highlights from Kobo Reader database")
    parser.add_argument(
        "-d", "--database",
        required=True,
        help="Path to KoboReader.sqlite database file"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["markdown", "json", "text"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (if not specified, prints to stdout)"
    )
    
    args = parser.parse_args()
    
    # Verify database file exists
    if not Path(args.database).is_file():
        print(f"Error: Database file not found: {args.database}")
        return 1
    
    # Get highlights
    try:
        highlights = get_highlights(args.database)
    except sqlite3.Error as e:
        print(f"Error reading database: {e}")
        return 1
    
    # Generate output in requested format
    if args.format == "json":
        output = json.dumps(highlights, indent=2)
    elif args.format == "markdown":
        output = export_markdown(highlights)
    else:  # text
        output = export_plain(highlights)
    
    # Write output
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Highlights exported to {args.output}")
        except IOError as e:
            print(f"Error writing output file: {e}")
            return 1
    else:
        print(output)
    
    return 0

if __name__ == "__main__":
    exit(main()) 