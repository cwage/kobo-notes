#!/usr/bin/env python3

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

def get_highlights(db_path: str) -> List[Dict[str, Any]]:
    """Extract highlights from the Kobo SQLite database."""
    conn = sqlite3.connect(db_path)
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
        b.StartContainerPath,
        b.Type,
        b.Color,
        b.ContextString,
        c.BookTitle,
        c.CurrentChapterProgress
    FROM Bookmark b
    LEFT JOIN content c ON b.VolumeID = c.ContentID
    WHERE b.Text IS NOT NULL OR b.Annotation IS NOT NULL
    ORDER BY b.DateCreated
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    # Get color mapping from database if it exists
    try:
        cursor.execute("SELECT ColorValue, DisplayName FROM Color")
        color_map = dict(cursor.fetchall())
    except sqlite3.Error:
        color_map = {
            0: "none",
            1: "green",
            2: "blue",
            3: "red",
            4: "yellow"
        }
    
    highlights = []
    for row in results:
        (text, annotation, date_created, volume_id, title, attribution, 
         chapter_progress, container_path, highlight_type, color, context_string,
         book_title, chapter_title) = row
        
        # Clean up the volume ID to extract book title if content table didn't have it
        if not title:
            # Extract from volume_id path (e.g., ".../Book Title - Author.kepub.epub")
            try:
                title = Path(volume_id).stem.split(' - ')[0].replace('_', ' ')
                attribution = Path(volume_id).stem.split(' - ')[1].replace('.kepub', '').replace('_', ' ')
            except:
                title = volume_id
                attribution = "Unknown Author"
        
        # Parse the date
        try:
            date_obj = datetime.strptime(date_created, "%Y-%m-%dT%H:%M:%S.%f")
            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_date = date_created
        
        # Extract chapter information from container path if not in content table
        if not chapter_title and container_path:
            try:
                # Look for #pgepubid... in the path which often contains chapter info
                chapter_id = container_path.split('#')[-1]
                if chapter_id.startswith('pgepubid'):
                    chapter_title = f"Chapter {chapter_id.replace('pgepubid', '')}"
            except:
                chapter_title = None
        
        # Format chapter progress as percentage
        progress_pct = f"{chapter_progress * 100:.1f}%" if chapter_progress is not None else None
        
        highlights.append({
            "text": text,
            "annotation": annotation,
            "date": formatted_date,
            "book_title": title,
            "author": attribution,
            "chapter": chapter_title,
            "progress": progress_pct,
            "type": highlight_type or "highlight",
            "color": color_map.get(color, "unknown") if color is not None else None,
            "context": context_string
        })
    
    conn.close()
    return highlights

def export_markdown(highlights: List[Dict[str, Any]]) -> str:
    """Export highlights in Markdown format."""
    output = "# Kobo Reader Highlights\n\n"
    current_book = None
    
    for h in highlights:
        if h["book_title"] != current_book:
            current_book = h["book_title"]
            output += f"\n## {h['book_title']}\n"
            output += f"*by {h['author']}*\n\n"
        
        # Add chapter and progress info if available
        location_info = []
        if h["chapter"]:
            location_info.append(h["chapter"])
        if h["progress"]:
            location_info.append(f"Progress: {h['progress']}")
        if location_info:
            output += f"*Location: {' - '.join(location_info)}*\n\n"
        
        # Add the highlight with its color
        if h["color"] and h["color"] != "none":
            output += f"> {h['text']} _{h['color']} highlight_\n\n"
        else:
            output += f"> {h['text']}\n\n"
        
        # Add context if available
        if h["context"]:
            output += f"Context: _{h['context']}_\n\n"
        
        # Add annotation if available
        if h['annotation']:
            output += f"Note: *{h['annotation']}*\n\n"
        
        output += f"*Highlighted on {h['date']}*\n\n"
    
    return output

def export_plain(highlights: List[Dict[str, Any]]) -> str:
    """Export highlights in plain text format."""
    output = "KOBO READER HIGHLIGHTS\n\n"
    current_book = None
    
    for h in highlights:
        if h["book_title"] != current_book:
            current_book = h["book_title"]
            output += f"\n{h['book_title']}\n"
            output += f"by {h['author']}\n"
            output += "=" * 40 + "\n\n"
        
        # Add chapter and progress info if available
        location_info = []
        if h["chapter"]:
            location_info.append(h["chapter"])
        if h["progress"]:
            location_info.append(f"Progress: {h['progress']}")
        if location_info:
            output += f"Location: {' - '.join(location_info)}\n\n"
        
        # Add the highlight with its color
        if h["color"] and h["color"] != "none":
            output += f'"{h["text"]}" ({h["color"]} highlight)\n\n'
        else:
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

def main():
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