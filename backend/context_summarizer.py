import json
import re
from typing import Dict, List, Any
from datetime import datetime

class ContextSummarizer:
    """Summarize R environment context data to reduce memory usage"""
    
    def __init__(self):
        self.max_summary_length = 1000
        self.max_items_per_category = 10
    
    def summarize_context(self, context_data: Dict) -> Dict:
        """Create a compact summary of the R environment context"""
        if not context_data:
            return {"summary": "No context data available"}
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "workspace_summary": self._summarize_workspace(context_data.get("workspace_objects", {})),
            "console_summary": self._summarize_console_history(context_data.get("console_history", [])),
            "document_summary": self._summarize_document_content(context_data.get("document_content", "")),
            "environment_summary": self._summarize_environment(context_data.get("environment_info", {})),
            "functions_summary": self._summarize_functions(context_data.get("custom_functions", [])),
            "plots_summary": self._summarize_plots(context_data.get("plot_history", [])),
            "errors_summary": self._summarize_errors(context_data.get("error_history", []))
        }
        
        return summary
    
    def _summarize_workspace(self, workspace_objects) -> str:
        """Summarize workspace objects with important details preserved"""
        if not workspace_objects:
            return "No workspace objects"
        
        # Handle array-wrapped values from R frontend
        if isinstance(workspace_objects, list):
            if len(workspace_objects) == 0:
                return "No workspace objects"
            elif len(workspace_objects) == 1:
                workspace_objects = workspace_objects[0]
            else:
                return f"Multiple workspace objects: {len(workspace_objects)} objects"
        
        summary_parts = []
        object_counts = {}
        
        for obj_name, obj_info in workspace_objects.items():
            if isinstance(obj_info, dict):
                # Handle R format (class, rows, columns, preview)
                obj_class = obj_info.get("class", "unknown")
                obj_rows = obj_info.get("rows", "unknown")
                obj_columns = obj_info.get("columns", "unknown")
                obj_preview = obj_info.get("preview", "")
                
                # Determine object type from class
                if "data.frame" in obj_class:
                    obj_type = "dataframe"
                elif "function" in obj_class:
                    obj_type = "function"
                elif "numeric" in obj_class or "integer" in obj_class or "character" in obj_class:
                    obj_type = "vector"
                elif "list" in obj_class:
                    obj_type = "list"
                else:
                    obj_type = "object"
                
                # Create size description
                if obj_type == "dataframe":
                    size_desc = f"{obj_rows} rows, {obj_columns} cols" if obj_columns else f"{obj_rows} rows"
                elif obj_type == "vector":
                    size_desc = f"{obj_rows} elements"
                elif obj_type == "function":
                    size_desc = "function"
                else:
                    size_desc = f"{obj_rows} items" if obj_rows != "unknown" else "object"
                
                # Add preview if available
                details = []
                if obj_preview and obj_preview != "Error reading object:":
                    # Ensure obj_preview is a string
                    if isinstance(obj_preview, list):
                        if len(obj_preview) == 1:
                            obj_preview = str(obj_preview[0])
                        elif len(obj_preview) == 0:
                            obj_preview = ""
                        else:
                            obj_preview = str(obj_preview)
                    else:
                        obj_preview = str(obj_preview)
                    
                    # Clean up preview (remove newlines, truncate)
                    clean_preview = obj_preview.replace('\n', ' ').strip()
                    if len(clean_preview) > 100:
                        clean_preview = clean_preview[:100] + "..."
                    details.append(f"preview: {clean_preview}")
                
                # Create detailed summary
                if details:
                    summary_parts.append(f"{obj_name} ({obj_type}, {size_desc}): {'; '.join(details)}")
                else:
                    summary_parts.append(f"{obj_name} ({obj_type}, {size_desc})")
                
                # Group by type for counting
                if obj_type not in object_counts:
                    object_counts[obj_type] = []
                object_counts[obj_type].append(obj_name)
        
        # If we have too many objects, provide a summary by type
        if len(summary_parts) > self.max_items_per_category:
            type_summary = []
            for obj_type, objects in object_counts.items():
                if len(objects) <= 3:
                    type_summary.append(f"{obj_type}: {', '.join(objects)}")
                else:
                    type_summary.append(f"{obj_type}: {len(objects)} objects including {', '.join(objects[:2])}...")
            
            # Add detailed info for first few objects
            detailed_objects = summary_parts[:3]
            return f"{'; '.join(type_summary)}. Details: {'; '.join(detailed_objects)}"
        
        return "; ".join(summary_parts)
    
    def _summarize_console_history(self, console_history: List) -> str:
        """Summarize console command history"""
        if not console_history:
            return "No console history"
        
        if len(console_history) <= self.max_items_per_category:
            return f"Recent commands: {'; '.join(console_history[-self.max_items_per_category:])}"
        else:
            recent_commands = console_history[-self.max_items_per_category:]
            return f"Recent commands: {'; '.join(recent_commands)} (and {len(console_history) - self.max_items_per_category} more)"
    
    def _summarize_document_content(self, document_content) -> str:
        """Summarize document content with key elements preserved"""
        # Handle array-wrapped values from R frontend
        if isinstance(document_content, list):
            if len(document_content) == 1:
                document_content = document_content[0]
            elif len(document_content) == 0:
                document_content = ""
            else:
                document_content = "\n".join(str(item) for item in document_content)
        
        if not document_content:
            return "No document content"
        
        # Ensure it's a string
        document_content = str(document_content)
        
        # Count lines and functions
        lines = document_content.split('\n')
        function_count = len(re.findall(r'function\s*\(', document_content))
        variable_count = len(re.findall(r'<-|=', document_content))
        
        # Extract function names
        function_names = re.findall(r'(\w+)\s*<-?\s*function\s*\(', document_content)
        function_summary = ""
        if function_names:
            if len(function_names) <= 5:
                function_summary = f"functions: {', '.join(function_names)}"
            else:
                function_summary = f"functions: {', '.join(function_names[:3])}... ({len(function_names)} total)"
        
        # Extract variable assignments
        variable_assignments = re.findall(r'(\w+)\s*<-?\s*[^#\n]+', document_content)
        variable_summary = ""
        if variable_assignments:
            # Remove duplicates and limit
            unique_vars = list(dict.fromkeys(variable_assignments))  # Preserve order
            if len(unique_vars) <= 8:
                variable_summary = f"variables: {', '.join(unique_vars)}"
            else:
                variable_summary = f"variables: {', '.join(unique_vars[:5])}... ({len(unique_vars)} total)"
        
        # Extract library calls
        library_calls = re.findall(r'library\(([^)]+)\)', document_content)
        library_summary = ""
        if library_calls:
            if len(library_calls) <= 5:
                library_summary = f"libraries: {', '.join(library_calls)}"
            else:
                library_summary = f"libraries: {', '.join(library_calls[:3])}... ({len(library_calls)} total)"
        
        # Get first few lines as preview (but skip empty lines and comments)
        non_empty_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
        preview_lines = non_empty_lines[:3]
        preview = '\n'.join(preview_lines)
        
        if len(non_empty_lines) > 3:
            preview += f"\n... ({len(non_empty_lines) - 3} more lines)"
        
        # Build comprehensive summary
        summary_parts = [f"Document: {len(lines)} lines"]
        
        if function_count > 0:
            summary_parts.append(f"{function_count} functions")
        if variable_count > 0:
            summary_parts.append(f"{variable_count} assignments")
        
        if function_summary:
            summary_parts.append(function_summary)
        if variable_summary:
            summary_parts.append(variable_summary)
        if library_summary:
            summary_parts.append(library_summary)
        
        summary_parts.append(f"Preview: {preview}")
        
        return "; ".join(summary_parts)
    
    def _summarize_environment(self, environment_info) -> str:
        """Summarize environment information"""
        if not environment_info:
            return "No environment info"
        
        # Handle array-wrapped values from R frontend
        if isinstance(environment_info, list):
            if len(environment_info) == 1:
                environment_info = environment_info[0]
            elif len(environment_info) == 0:
                return "No environment info"
            else:
                # If it's a list of strings, join them
                if all(isinstance(item, str) for item in environment_info):
                    return f"Environment: {'; '.join(environment_info)}"
                else:
                    return "Environment info available"
        
        summary_parts = []
        
        if "r_version" in environment_info:
            r_version = environment_info["r_version"]
            # Handle array-wrapped r_version
            if isinstance(r_version, list):
                r_version = r_version[0] if r_version else "Unknown"
            summary_parts.append(f"R {r_version}")
        
        if "packages" in environment_info:
            packages = environment_info["packages"]
            # Handle array-wrapped packages
            if isinstance(packages, list):
                if len(packages) <= self.max_items_per_category:
                    summary_parts.append(f"Packages: {', '.join(packages)}")
                else:
                    summary_parts.append(f"Packages: {len(packages)} loaded including {', '.join(packages[:5])}...")
            elif isinstance(packages, str):
                summary_parts.append(f"Packages: {packages}")
        
        if "working_directory" in environment_info:
            wd = environment_info["working_directory"]
            # Handle array-wrapped working_directory
            if isinstance(wd, list):
                wd = wd[0] if wd else "Unknown"
            summary_parts.append(f"WD: {wd}")
        
        return "; ".join(summary_parts) if summary_parts else "Basic environment info available"
    
    def _summarize_functions(self, custom_functions: List) -> str:
        """Summarize custom functions"""
        if not custom_functions:
            return "No custom functions"
        
        if len(custom_functions) <= self.max_items_per_category:
            return f"Custom functions: {', '.join(custom_functions)}"
        else:
            return f"Custom functions: {len(custom_functions)} functions including {', '.join(custom_functions[:3])}..."
    
    def _summarize_plots(self, plot_history: List) -> str:
        """Summarize plot history"""
        if not plot_history:
            return "No plot history"
        
        if len(plot_history) <= self.max_items_per_category:
            return f"Recent plots: {', '.join(plot_history[-self.max_items_per_category:])}"
        else:
            recent_plots = plot_history[-self.max_items_per_category:]
            return f"Recent plots: {', '.join(recent_plots)} (and {len(plot_history) - self.max_items_per_category} more)"
    
    def _summarize_errors(self, error_history: List) -> str:
        """Summarize error history"""
        if not error_history:
            return "No recent errors"
        
        if len(error_history) <= self.max_items_per_category:
            return f"Recent errors: {', '.join(error_history[-self.max_items_per_category:])}"
        else:
            recent_errors = error_history[-self.max_items_per_category:]
            return f"Recent errors: {', '.join(recent_errors)} (and {len(error_history) - self.max_items_per_category} more)"
    
    def get_context_fingerprint(self, context_data: Dict) -> str:
        """Create a fingerprint for context similarity checking"""
        if not context_data:
            return "empty"
        
        # Create a hash of key context elements
        fingerprint_data = {
            "workspace_keys": sorted(context_data.get("workspace_objects", {}).keys()),
            "recent_commands": context_data.get("console_history", [])[-5:],  # Last 5 commands
            "active_packages": context_data.get("environment_info", {}).get("packages", [])[:10],  # First 10 packages
            "document_length": len(context_data.get("document_content", ""))
        }
        
        return json.dumps(fingerprint_data, sort_keys=True) 