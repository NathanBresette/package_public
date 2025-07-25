# Test script to verify plumber context endpoint JSON serialization
library(plumber)
library(jsonlite)

# Set up test environment
test_data <- data.frame(x = 1:5, y = letters[1:5])
test_function <- function(x) x * 2

# Start plumber server
pr <- plumb("inst/viewer_ai/plumber_api.R")

# Test the context endpoint
cat("🧪 Testing plumber context endpoint...\n")

# Get context data
context_response <- pr$call(plumber::PlumberRequest$new("GET", "/context"))

# Parse the response
if (context_response$status == 200) {
  context_data <- fromJSON(context_response$body)
  
  cat("✅ Context endpoint returned successfully\n")
  cat("📊 Response structure:\n")
  
  # Check each field for proper formatting
  fields_to_check <- c("document_content", "timestamp", "source", "custom_functions", "plot_history", "workspace_objects")
  
  for (field in fields_to_check) {
    if (field %in% names(context_data)) {
      value <- context_data[[field]]
      cat(sprintf("  %s: %s (type: %s)\n", 
                  field, 
                  if (length(value) == 0) "empty" else paste(class(value), collapse=", "),
                  typeof(value)))
      
      # Check for array wrapping issues
      if (field %in% c("document_content", "timestamp", "source")) {
        if (is.list(value) && length(value) == 1) {
          cat(sprintf("    ⚠️  WARNING: %s is wrapped in array: %s\n", field, paste(value, collapse=", ")))
        } else {
          cat(sprintf("    ✅ %s is properly formatted\n", field))
        }
      }
    } else {
      cat(sprintf("  %s: missing\n", field))
    }
  }
  
  # Test JSON serialization
  cat("\n🔍 Testing JSON serialization...\n")
  json_string <- toJSON(context_data, auto_unbox = TRUE, pretty = TRUE)
  cat("✅ JSON serialization successful\n")
  
  # Check for array wrapping in JSON
  if (grepl('"document_content":\\s*\\[', json_string)) {
    cat("❌ document_content is still wrapped in array in JSON\n")
  } else {
    cat("✅ document_content is not wrapped in array in JSON\n")
  }
  
  if (grepl('"timestamp":\\s*\\[', json_string)) {
    cat("❌ timestamp is still wrapped in array in JSON\n")
  } else {
    cat("✅ timestamp is not wrapped in array in JSON\n")
  }
  
  if (grepl('"source":\\s*\\[', json_string)) {
    cat("❌ source is still wrapped in array in JSON\n")
  } else {
    cat("✅ source is not wrapped in array in JSON\n")
  }
  
} else {
  cat("❌ Context endpoint failed with status:", context_response$status, "\n")
  cat("Response:", context_response$body, "\n")
}

cat("\n�� Test completed\n") 