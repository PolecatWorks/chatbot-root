from inspect import signature, cleandoc
from typing import Callable, Dict, Any, get_origin, get_args
import typing

def generate_tool_definition(func: Callable) -> Dict[str, Any]:
    """Generate a tool definition from a function's signature and docstring.
    
    Args:
        func: The function to generate a tool definition for.
        
    Returns:
        A dictionary containing the tool definition in the format required by Gemini.
    """
    sig = signature(func)
    doc = cleandoc(func.__doc__ or "")
    
    # Split docstring into description and args
    doc_parts = doc.split("Args:")
    description = doc_parts[0].strip()
    
    properties = {}
    required = []
    
    for name, param in sig.parameters.items():
        param_type = param.annotation
        required.append(name)
        
        if param_type == param.empty:
            # No type hint, default to string
            param_props = {"type": "string"}
        else:
            param_props = _type_to_json_schema(param_type)
            
        # Try to find parameter description in docstring
        if len(doc_parts) > 1:
            param_doc = doc_parts[1]
            param_lines = param_doc.split("\n")
            for line in param_lines:
                if line.strip().startswith(f"{name}:"):
                    param_props["description"] = line.split(":", 1)[1].strip()
                    break
        
        properties[name] = param_props
    
    return {
        "name": func.__name__,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }

def _type_to_json_schema(type_hint: Any) -> Dict[str, Any]:
    """Convert a Python type hint to a JSON Schema type definition."""
    origin = get_origin(type_hint)
    args = get_args(type_hint)
    
    if origin is None:
        if type_hint == str:
            return {"type": "string"}
        elif type_hint == int:
            return {"type": "integer"}
        elif type_hint == float:
            return {"type": "number"}
        elif type_hint == bool:
            return {"type": "boolean"}
    elif origin == list:
        item_type = args[0] if args else Any
        return {
            "type": "array",
            "items": _type_to_json_schema(item_type)
        }
    elif origin == dict:
        return {
            "type": "object",
            "additionalProperties": True
        }
    
    # Default to string for unknown types
    return {"type": "string"}
