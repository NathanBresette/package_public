# Test backend integration with corrected JSON format
library(httr)
library(jsonlite)

# Backend URL
backend_url <- "https://rgent.onrender.com"

# Test access code
access_code <- "DEMO123"

# Create test context data with proper format (no array wrapping)
test_context <- list(
  document_content = "test document content",
  console_history = c("command1", "command2"),
  workspace_objects = list(
    test_data = list(
      class = "data.frame",
      rows = 5,
      columns = 2,
      preview = "test preview"
    )
  ),
  environment_info = list(
    r_version = "R version 4.2.0",
    platform = "x86_64-apple-darwin17.0",
    working_directory = "/test/dir",
    packages = "test packages"
  ),
  custom_functions = c("test_function"),
  plot_history = character(0),
  error_history = character(0),
  timestamp = "2025-01-27 12:00:00",
  source = "test_context"
)

# Test 1: Send context with chat request
cat("🧪 Test 1: Sending context with chat request...\n")

chat_request <- list(
  message = "What objects are in my workspace?",
  context_data = test_context,
  context_type = "general",
  access_code = access_code
)

response1 <- POST(
  url = paste0(backend_url, "/chat"),
  body = toJSON(chat_request, auto_unbox = TRUE),
  content_type("application/json")
)

if (response1$status_code == 200) {
  content1 <- fromJSON(rawToChar(response1$content))
  cat("✅ Test 1 successful\n")
  cat("Response:", content1$response, "\n\n")
} else {
  cat("❌ Test 1 failed with status:", response1$status_code, "\n")
  cat("Response:", rawToChar(response1$content), "\n\n")
}

# Test 2: Send context with empty values
cat("🧪 Test 2: Sending context with empty values...\n")

test_context_empty <- list(
  document_content = "",
  console_history = character(0),
  workspace_objects = list(),
  environment_info = list(
    r_version = "R version 4.2.0",
    platform = "x86_64-apple-darwin17.0",
    working_directory = "/test/dir",
    packages = "No packages loaded"
  ),
  custom_functions = character(0),
  plot_history = character(0),
  error_history = character(0),
  timestamp = "2025-01-27 12:00:00",
  source = "test_context_empty"
)

chat_request2 <- list(
  message = "What's in my workspace?",
  context_data = test_context_empty,
  context_type = "general",
  access_code = access_code
)

response2 <- POST(
  url = paste0(backend_url, "/chat"),
  body = toJSON(chat_request2, auto_unbox = TRUE),
  content_type("application/json")
)

if (response2$status_code == 200) {
  content2 <- fromJSON(rawToChar(response2$content))
  cat("✅ Test 2 successful\n")
  cat("Response:", content2$response, "\n\n")
} else {
  cat("❌ Test 2 failed with status:", response2$status_code, "\n")
  cat("Response:", rawToChar(response2$content), "\n\n")
}

# Test 3: Verify JSON format
cat("🧪 Test 3: Verifying JSON format...\n")

json_string <- toJSON(test_context, auto_unbox = TRUE, pretty = TRUE)
cat("Generated JSON:\n")
cat(json_string, "\n\n")

# Check for array wrapping
if (grepl('"document_content":\\s*\\[', json_string)) {
  cat("❌ document_content is still wrapped in array\n")
} else {
  cat("✅ document_content is not wrapped in array\n")
}

if (grepl('"timestamp":\\s*\\[', json_string)) {
  cat("❌ timestamp is still wrapped in array\n")
} else {
  cat("✅ timestamp is not wrapped in array\n")
}

if (grepl('"source":\\s*\\[', json_string)) {
  cat("❌ source is still wrapped in array\n")
} else {
  cat("✅ source is not wrapped in array\n")
}

if (grepl('"custom_functions":\\s*\\[\\]', json_string)) {
  cat("✅ custom_functions is properly formatted as empty array\n")
} else {
  cat("❌ custom_functions is not properly formatted\n")
}

if (grepl('"workspace_objects":\\s*\\{\\}', json_string)) {
  cat("✅ workspace_objects is properly formatted as empty object\n")
} else {
  cat("❌ workspace_objects is not properly formatted\n")
}

cat("\n🏁 Backend integration test completed\n") 