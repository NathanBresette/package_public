#!/usr/bin/env Rscript

# Script to check what context data is captured in the database
# Run this after testing with TEST123 in RStudio

library(httr)
library(jsonlite)

BACKEND_URL <- "https://rgent.onrender.com"
ACCESS_CODE <- "TEST123"

cat("🔍 Checking context capture for access code:", ACCESS_CODE, "\n\n")

# 1. Check if access code is valid
cat("1. Validating access code...\n")
validation_response <- POST(
  paste0(BACKEND_URL, "/validate"),
  body = toJSON(list(access_code = ACCESS_CODE), auto_unbox = TRUE),
  content_type("application/json")
)

if (validation_response$status_code == 200) {
  cat("✅ Access code is valid\n\n")
} else {
  cat("❌ Access code validation failed\n")
  quit(status = 1)
}

# 2. Get usage statistics
cat("2. Getting usage statistics...\n")
usage_response <- GET(
  paste0(BACKEND_URL, "/usage/", ACCESS_CODE)
)

if (usage_response$status_code == 200) {
  usage_data <- fromJSON(rawToChar(usage_response$content))
  cat("✅ Usage data retrieved\n")
  cat("Total requests:", usage_data$total_requests, "\n")
  cat("Total cost:", usage_data$total_cost, "\n")
  cat("Total tokens:", usage_data$total_tokens, "\n")
  cat("Daily requests:", usage_data$daily_requests, "\n")
  cat("Monthly cost:", usage_data$monthly_cost, "\n\n")
} else {
  cat("❌ Could not retrieve usage data\n\n")
}

# 3. Get context summary
cat("3. Getting context summary...\n")
context_summary_response <- GET(
  paste0(BACKEND_URL, "/context/summary/", ACCESS_CODE)
)

if (context_summary_response$status_code == 200) {
  context_summary <- fromJSON(rawToChar(context_summary_response$content))
  cat("✅ Context summary retrieved\n")
  cat("Context summary structure:\n")
  print(str(context_summary))
  cat("\n")
} else {
  cat("❌ Could not retrieve context summary\n\n")
}

# 4. Get user analytics
cat("4. Getting user analytics...\n")
analytics_response <- GET(
  paste0(BACKEND_URL, "/context/analytics/", ACCESS_CODE)
)

if (analytics_response$status_code == 200) {
  analytics_data <- fromJSON(rawToChar(analytics_response$content))
  cat("✅ Analytics data retrieved\n")
  cat("Analytics structure:\n")
  print(str(analytics_data))
  cat("\n")
} else {
  cat("❌ Could not retrieve analytics data\n\n")
}

# 5. Get conversations
cat("5. Getting conversations...\n")
conversations_response <- GET(
  paste0(BACKEND_URL, "/conversations/", ACCESS_CODE)
)

if (conversations_response$status_code == 200) {
  conversations <- fromJSON(rawToChar(conversations_response$content))
  cat("✅ Conversations retrieved\n")
  cat("Number of conversations:", length(conversations), "\n")
  if (length(conversations) > 0) {
    cat("Conversation details:\n")
    for (i in seq_along(conversations)) {
      conv <- conversations[[i]]
      cat("  Conversation", i, ":\n")
      cat("    ID:", conv$conversation_id, "\n")
      cat("    Title:", conv$title, "\n")
      cat("    Last updated:", conv$last_updated, "\n")
      cat("    Active:", conv$is_active, "\n")
    }
  }
  cat("\n")
} else {
  cat("❌ Could not retrieve conversations\n\n")
}

# 6. Test a chat request to see what context is sent
cat("6. Testing chat request with sample context...\n")
sample_context <- list(
  document_content = "test document content",
  console_history = c("library(ggplot2)", "data <- mtcars", "head(data)"),
  workspace_objects = list(
    mtcars = list(
      class = "data.frame",
      rows = 32,
      columns = 11,
      preview = "Mazda RX4: 21.0 6 160 110 3.90 2.620 16.46 0 1 4 4"
    )
  ),
  environment_info = list(
    r_version = "R version 4.5.1",
    platform = "x86_64-apple-darwin20",
    working_directory = "/test/dir",
    packages = "ggplot2, dplyr"
  ),
  custom_functions = c("my_function <- function(x) x * 2"),
  plot_history = c("hist(mtcars$mpg)"),
  error_history = c("Error in read.csv(): file not found"),
  timestamp = Sys.time(),
  source = "test_context"
)

chat_request <- list(
  prompt = "What context data is being captured?",
  context_data = sample_context,
  context_type = "test",
  access_code = ACCESS_CODE
)

chat_response <- POST(
  paste0(BACKEND_URL, "/chat"),
  body = toJSON(chat_request, auto_unbox = TRUE),
  content_type("application/json")
)

if (chat_response$status_code == 200) {
  chat_data <- fromJSON(rawToChar(chat_response$content))
  cat("✅ Chat request successful\n")
  cat("Response length:", nchar(chat_data$response), "characters\n")
  cat("First 200 chars:", substr(chat_data$response, 1, 200), "\n")
  cat("Context summary keys:", paste(names(chat_data$context_summary), collapse = ", "), "\n")
  cat("Retrieved contexts:", length(chat_data$retrieved_context), "\n")
} else {
  cat("❌ Chat request failed\n")
  cat("Response:", rawToChar(chat_response$content), "\n")
}

cat("\n🎉 Context capture analysis complete!\n")
cat("Access code for testing:", ACCESS_CODE, "\n")
cat("Backend URL:", BACKEND_URL, "\n") 