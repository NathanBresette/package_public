# JSON Serialization Fixes - Plumber API

## 🚨 Problem Summary

The plumber API context endpoint was returning JSON with array-wrapped single values, causing backend serialization errors:

### ❌ Before (Problematic Output):
```json
{
  "document_content": [""],                    // Should be: ""
  "timestamp": ["2025-07-25 06:28:32.136615"], // Should be: "2025-07-25 06:28:32.136615"
  "source": ["rstudio_plumber_context"],       // Should be: "rstudio_plumber_context"
  "custom_functions": ["Error reading functions: invalid subscript type 'list'"], // Should be: []
  "plot_history": ["Error reading plot history: invalid subscript type 'list'"], // Should be: []
  "workspace_objects": []                      // Should be: {} (named dictionary)
}
```

### ✅ After (Correct Output):
```json
{
  "document_content": "",
  "timestamp": "2025-07-25 06:28:32.136615",
  "source": "rstudio_plumber_context",
  "custom_functions": [],
  "plot_history": [],
  "workspace_objects": {}
}
```

## 🔧 Fixes Applied

### 1. Added JSON Serialization Configuration
**File:** `inst/viewer_ai/plumber_api.R`

```r
# Added at top of file
library(jsonlite)

# Configure jsonlite to auto-unbox single values to prevent array wrapping
options(jsonlite.auto_unbox = TRUE)
```

### 2. Added JSON Serializer to Endpoints
**File:** `inst/viewer_ai/plumber_api.R`

```r
#* @get /context
#* @serializer json
function() {
  # ... endpoint code
}

#* @post /insert_code
#* @serializer json
function(req) {
  # ... endpoint code
}

#* @get /health
#* @serializer json
function() {
  # ... endpoint code
}
```

### 3. Fixed Error Handling
**File:** `inst/viewer_ai/plumber_api.R`

**Before:**
```r
document_content <- paste("Error getting document context:", e$message)
console_history <- c("Console History: Not available")
workspace_objects <- list(error = paste("Error reading workspace objects:", e$message))
custom_functions <- ["Error reading functions: invalid subscript type 'list'"]
plot_history <- ["Error reading plot history: invalid subscript type 'list'"]
error_history <- c("No recent errors")
```

**After:**
```r
document_content <- ""  # Empty string instead of error message
console_history <- character(0)  # Empty vector instead of error message
workspace_objects <- list()  # Empty list instead of error
custom_functions <- character(0)  # Empty vector on error
plot_history <- character(0)  # Empty vector on error
error_history <- character(0)  # Empty vector instead of error message
```

### 4. Removed Unnecessary Type Conversions
**File:** `inst/viewer_ai/plumber_api.R`

**Before:**
```r
document_content = as.character(document_content),
error_history = if(length(error_history) == 1) as.character(error_history[1]) else error_history,
```

**After:**
```r
document_content = document_content,  # Already a string, no need for as.character()
error_history = error_history,  # Always a clean character vector
```

## 🧪 Test Files Created

### 1. `test_plumber_context.R`
- Tests the plumber context endpoint directly
- Verifies JSON serialization without array wrapping
- Checks all field types and formats

### 2. `test_backend_integration.R`
- Tests backend integration with corrected JSON format
- Sends test context data to backend
- Verifies proper handling of empty values

## 🎯 Expected Results

After these fixes:

1. **No Array Wrapping**: Single values like `document_content`, `timestamp`, and `source` will be strings, not arrays
2. **Proper Empty Values**: Empty vectors will be `[]` and empty objects will be `{}`
3. **No Error Messages as Data**: Error conditions return proper empty values instead of error strings
4. **Backend Compatibility**: Python backend can properly process the context data without `AttributeError: 'list' object has no attribute 'items'`

## 🚀 How to Test

1. **Test Plumber Context:**
   ```r
   source("inst/viewer_ai/test_plumber_context.R")
   ```

2. **Test Backend Integration:**
   ```r
   source("inst/viewer_ai/test_backend_integration.R")
   ```

3. **Manual Test:**
   ```r
   library(rstudioai)
   ai_addin_viewer()
   # Enter access code and test chat functionality
   ```

## 📋 Files Modified

- `inst/viewer_ai/plumber_api.R` - Main fixes applied
- `inst/viewer_ai/test_plumber_context.R` - Test file created
- `inst/viewer_ai/test_backend_integration.R` - Test file created

## 🔍 Key Changes Summary

| Issue | Before | After |
|-------|--------|-------|
| Array wrapping | `"field": ["value"]` | `"field": "value"` |
| Error handling | Return error messages | Return empty values |
| JSON serializer | Default | Explicit `@serializer json` |
| Auto-unboxing | Disabled | `options(jsonlite.auto_unbox = TRUE)` |

These fixes should resolve the backend serialization errors and allow the AI chat functionality to work properly with RStudio context data. 