"""
Logging configuration for orchestrator agents.

Provides structured logging with dual output:
- Plaintext log: Human-readable step-by-step execution trace
- JSON Lines log: Machine-parseable log (one JSON object per line)

Usage:
    from logger_config import setup_logging
    logger = setup_logging(log_dir="logs", task_id=None)
    logger.info("[TASK_INIT] Backend: Ollama | Model: mistral")
    logger.info("[LLM_CALL] Response: ...text... | Latency: 1250ms")
"""

import logging
import json
import os
from pathlib import Path
from datetime import datetime


class JSONLineHandler(logging.Handler):
    """
    Custom logging handler that outputs JSON Lines format.
    
    Each log record is written as a single JSON object on one line,
    making it easy to parse programmatically.
    
    JSON structure:
    {
        "timestamp": "2026-03-24T14:23:15.789Z",
        "level": "INFO",
        "logger": "orchestrator.OllamaAgent",
        "event_type": "TASK_INIT|LLM_CALL|TOOL_EXECUTION|...",
        "message": "Full message text",
        "data": { "key": "value", ... }  # Optional context-specific fields
    }
    """
    
    def __init__(self, filename):
        """Initialize handler with target JSON Lines file."""
        super().__init__()
        self.filename = filename
        # Truncate file on initialization (clear old data)
        with open(filename, 'w') as f:
            pass  # Create empty file
    
    def emit(self, record):
        """
        Emit a log record as a JSON Line.
        
        Args:
            record: LogRecord from the logging system
        """
        try:
            # Parse event_type from message (format: "[EVENT_TYPE] ...")
            message = record.getMessage()
            event_type = "UNKNOWN"
            data = {}
            
            # Extract event type from bracket notation: "[EVENT_TYPE]"
            if message.startswith("[") and "]" in message:
                event_type = message[1:message.index("]")]
                # Remove the event type prefix from message for cleaner output
                message_content = message[message.index("]")+1:].strip()
            else:
                message_content = message
            
            # Build JSON object
            log_obj = {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "level": record.levelname,
                "logger": record.name,
                "event_type": event_type,
                "message": message_content,
            }
            
            # Write as single line JSON
            with open(self.filename, 'a') as f:
                f.write(json.dumps(log_obj, separators=(',', ':')) + '\n')
        
        except Exception as e:
            # Silently fail to avoid breaking the application
            # (but errors in logging shouldn't crash the main program)
            self.handleError(record)


def setup_logging(log_dir="logs", task_id=None, log_level=logging.INFO):
    """
    Initialize structured logging for agent tasks.
    
    Creates log directory if needed and sets up dual handlers:
    - Plaintext log for human consumption
    - JSON Lines log for machine parsing
    
    Args:
        log_dir (str): Directory where logs will be stored (default: "logs" in current working directory)
        task_id (str): Unique task identifier for log file naming. If None, generates from current timestamp.
        log_level (int): Logging level (logging.DEBUG, logging.INFO, logging.WARNING, etc.)
    
    Returns:
        logging.Logger: Configured logger instance ready for use
    
    Example:
        >>> logger = setup_logging(log_dir="logs")
        >>> logger.info("[TASK_INIT] Starting task with model: mistral")
        >>> logger.info("[LLM_CALL] Response received | Latency: 1200ms")
        >>> logger.info("[TASK_COMPLETE] Success: True | Iterations: 3")
        
        Generates:
        - logs/agent_20260324_142315.log      (plaintext)
        - logs/agent_20260324_142315.jsonl    (JSON Lines)
    """
    
    # Generate task_id if not provided (format: YYYYMMDD_HHMMSS)
    if task_id is None:
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Define log file paths
    plaintext_log = log_path / f"agent_{task_id}.log"
    json_log = log_path / f"agent_{task_id}.jsonl"
    
    # Create logger
    logger = logging.getLogger(f"orchestrator.{task_id}")
    logger.setLevel(log_level)
    
    # Clear any existing handlers (in case logger is reused)
    logger.handlers.clear()
    
    # === Plaintext Handler ===
    plaintext_handler = logging.FileHandler(plaintext_log, mode='w')
    plaintext_handler.setLevel(log_level)
    plaintext_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s — %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    plaintext_handler.setFormatter(plaintext_formatter)
    logger.addHandler(plaintext_handler)
    
    # === JSON Lines Handler ===
    json_handler = JSONLineHandler(str(json_log))
    json_handler.setLevel(log_level)
    logger.addHandler(json_handler)
    
    # Log initialization
    logger.info("[LOG_INIT] Logging initialized | Plaintext: %(plaintext_log)s | JSON: %(json_log)s" % {
        "plaintext_log": plaintext_log.name,
        "json_log": json_log.name
    })
    
    return logger, str(plaintext_log), str(json_log)


if __name__ == "__main__":
    # Simple test
    logger, txt_path, json_path = setup_logging(log_dir="logs")
    
    logger.info("[TEST_INIT] Test event with basic data")
    logger.info("[TOOL_EXECUTION] Tool: read_file | Params: file_path=config.json | Result: success | Latency: 145ms")
    logger.info("[TASK_COMPLETE] Success: True | Iterations: 2 | Total Duration: 3.5s")
    
    print(f"✓ Plaintext log: {txt_path}")
    print(f"✓ JSON Lines log: {json_path}")
    print("\nPlaintext log content:")
    with open(txt_path) as f:
        print(f.read())
    print("\nJSON Lines log content:")
    with open(json_path) as f:
        for line in f:
            obj = json.loads(line)
            print(f"  Event: {obj['event_type']} | {obj['message']}")
