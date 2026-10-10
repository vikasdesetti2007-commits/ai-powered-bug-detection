"""Syntax and indentation error detector using standard library AST parser.

Never executes untrusted code. Only performs passive syntax validation.
"""

import ast
from typing import Optional, Tuple
from bug_detector.models import SyntaxErrorInfo


def format_pointer_diagram(line_text: str, offset: int, end_offset: Optional[int] = None) -> str:
    """Format a visual ASCII diagram pointing to the error column using a caret (`^`).
    
    Args:
        line_text: The source code line where error occurred.
        offset: 1-indexed or 0-indexed column offset reported by SyntaxError.
        end_offset: Optional ending column offset.
    """
    if not line_text:
        return ""
    
    # Strip newline characters for clean display
    clean_line = line_text.rstrip("\r\n")
    
    # Python offset in SyntaxError is usually 1-indexed.
    # Protect against 0 or negative offsets.
    caret_pos = max(0, offset - 1 if offset > 0 else 0)
    
    # Limit caret position to length of line
    if caret_pos > len(clean_line):
        caret_pos = len(clean_line)
    
    # Determine length of caret underline
    if end_offset and end_offset > offset:
        span_len = max(1, end_offset - offset)
        carets = "^" * span_len
    else:
        carets = "^"
        
    spaces = " " * caret_pos
    return f"{clean_line}\n{spaces}{carets}"


def check_syntax(
    source_code: str,
    filename: str = "<input>",
) -> Tuple[bool, Optional[SyntaxErrorInfo], Optional[ast.AST]]:
    """Parse Python source code to verify syntax without executing it.
    
    Args:
        source_code: Python source code string.
        filename: Optional filename identifier for error reporting.
        
    Returns:
        A tuple of (is_valid, syntax_error_info, ast_tree):
        - is_valid: True if source parses without SyntaxError/IndentationError.
        - syntax_error_info: Detailed SyntaxErrorInfo if invalid, else None.
        - ast_tree: The parsed ast.AST node if valid, else None.
    """
    try:
        tree = ast.parse(source_code, filename=filename)
        return True, None, tree
    except (SyntaxError, IndentationError) as err:
        line_no = err.lineno or 1
        col_offset = max(0, (err.offset - 1) if err.offset is not None else 0)
        end_col_offset = max(0, (err.end_offset - 1) if err.end_offset is not None else col_offset)
        raw_text = err.text or ""
        
        pointer = format_pointer_diagram(
            line_text=raw_text,
            offset=err.offset or 1,
            end_offset=err.end_offset,
        )
        
        error_info = SyntaxErrorInfo(
            message=str(err.msg) if err.msg else "Syntax error",
            line_number=line_no,
            column_offset=col_offset,
            end_line_number=err.end_lineno or line_no,
            end_column_offset=end_col_offset,
            line_text=raw_text.rstrip("\r\n") if raw_text else None,
            pointer_diagram=pointer if pointer else None,
        )
        return False, error_info, None
