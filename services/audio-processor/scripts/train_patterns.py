#!/usr/bin/env python3
"""
CLI script to train rhythm patterns from MusicXML files.

Usage:
    python scripts/train_patterns.py --sample 500
    python scripts/train_patterns.py --directory ./training_data
    python scripts/train_patterns.py --url https://example.com/file.musicxml
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.data_collector import DataCollector
from app.models.rhythm_patterns import PatternDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def train_from_sample(count: int, output_path: Path):
    """Generate training data from built-in sample patterns."""
    logger.info(f"Generating {count} sample patterns...")
    
    collector = DataCollector()
    patterns_added = await collector.collect_sample_data(count)
    
    collector.save_database(output_path)
    
    logger.info(f"Training complete!")
    logger.info(f"  - Patterns generated: {patterns_added}")
    logger.info(f"  - Database saved to: {output_path}")
    
    return collector.get_database()


async def train_from_directory(directory: Path, output_path: Path):
    """Train from MusicXML files in a directory."""
    logger.info(f"Training from directory: {directory}")
    
    collector = DataCollector()
    files_processed = await collector.collect_from_directory(directory)
    
    if files_processed == 0:
        logger.warning("No MusicXML files found in directory")
        return None
    
    collector.save_database(output_path)
    
    database = collector.get_database()
    total_patterns = sum(
        len(m.patterns) for m in database.time_signatures.values()
    )
    
    logger.info(f"Training complete!")
    logger.info(f"  - Files processed: {files_processed}")
    logger.info(f"  - Patterns learned: {total_patterns}")
    logger.info(f"  - Database saved to: {output_path}")
    
    return database


async def train_from_url(url: str, output_path: Path):
    """Download and train from a single MusicXML file."""
    logger.info(f"Downloading from: {url}")
    
    collector = DataCollector()
    filepath = await collector.download_from_url(url)
    
    if filepath is None:
        logger.error("Failed to download file")
        return None
    
    await collector._process_file(filepath)
    collector.save_database(output_path)
    
    logger.info(f"Training complete!")
    logger.info(f"  - Database saved to: {output_path}")
    
    return collector.get_database()


def print_database_stats(database: PatternDatabase):
    """Print statistics about the pattern database."""
    print("\n" + "=" * 50)
    print("Pattern Database Statistics")
    print("=" * 50)
    print(f"Total songs analyzed: {database.total_songs_analyzed}")
    print(f"Total unique patterns: {database.total_patterns_learned}")
    print(f"Time signatures covered: {list(database.time_signatures.keys())}")
    
    for ts, model in database.time_signatures.items():
        print(f"\n{ts} Time Signature:")
        print(f"  - Patterns: {len(model.patterns)}")
        print(f"  - Beat positions tracked: {len(model.beat_position_stats)}")
        
        top_patterns = model.get_top_patterns(5)
        if top_patterns:
            print(f"  - Top patterns:")
            for p in top_patterns:
                durs = [f"{d:.2f}" for d in p.durations]
                print(f"      [{', '.join(durs)}] (freq: {p.frequency})")


def main():
    parser = argparse.ArgumentParser(
        description="Train rhythm patterns from MusicXML files"
    )
    
    parser.add_argument(
        "--sample", "-s",
        type=int,
        help="Generate N sample patterns (no external data needed)"
    )
    
    parser.add_argument(
        "--directory", "-d",
        type=str,
        help="Directory containing MusicXML files"
    )
    
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="URL to download MusicXML file from"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output path for pattern database (default: data/patterns.json)"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print database statistics after training"
    )
    
    parser.add_argument(
        "--load",
        type=str,
        help="Load and display stats for existing database"
    )
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(__file__).parent.parent / "data" / "patterns.json"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Handle --load option
    if args.load:
        logger.info(f"Loading database from: {args.load}")
        database = PatternDatabase.load(args.load)
        print_database_stats(database)
        return 0
    
    # Run training
    database = None
    
    if args.sample:
        database = asyncio.run(train_from_sample(args.sample, output_path))
    
    elif args.directory:
        directory = Path(args.directory)
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return 1
        database = asyncio.run(train_from_directory(directory, output_path))
    
    elif args.url:
        database = asyncio.run(train_from_url(args.url, output_path))
    
    else:
        # Default: generate sample data
        logger.info("No input specified, generating sample patterns...")
        database = asyncio.run(train_from_sample(500, output_path))
    
    # Print stats if requested
    if args.stats and database:
        print_database_stats(database)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
