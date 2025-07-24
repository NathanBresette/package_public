# RStudio AI Add-in Configuration
# Set your backend URL here
BACKEND_URL <- "https://rgent.onrender.com"

# Function to switch between local and cloud backends
switch_backend <- function(type = "cloud") {
  if (type == "cloud") {
    BACKEND_URL <<- "https://rgent.onrender.com"
    cat("✅ Switched to cloud backend:", BACKEND_URL, "\n")
  } else if (type == "local") {
    BACKEND_URL <<- "http://127.0.0.1:8001"
    cat("✅ Switched to local backend:", BACKEND_URL, "\n")
  } else {
    cat("❌ Invalid backend type. Use 'cloud' or 'local'\n")
  }
}

# Helper function for R Markdown integration
ai_help_rmd <- function(prompt) {
  # This function can be used in R Markdown chunks
  # to get AI assistance while writing
  message("AI Help requested: ", prompt)
  # Implementation would connect to your backend
}

# Code review function
ai_code_review <- function(code) {
  # Send code to AI for review
  message("Code review requested for: ", substr(code, 1, 50), "...")
  # Implementation would connect to your backend
}

# Code explanation function
ai_explain_code <- function(code) {
  # Get AI explanation of code
  message("Code explanation requested for: ", substr(code, 1, 50), "...")
  # Implementation would connect to your backend
} 