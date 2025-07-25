# Plumber API for RStudio integration
# This provides local endpoints for the HTML interface to interact with RStudio

library(plumber)
library(rstudioapi)

#' @plumber
function(pr) {
  # Serve static index.html at /
  pr$handle("GET", "/", function(req, res) {
    static_dir <- system.file("public", package = "rstudioai")
    res$setHeader("Cache-Control", "no-cache")
    res$sendFile(file.path(static_dir, "index.html"))
  })
  pr$mount("/static", plumber::pr_static(system.file("public", package = "rstudioai")))

  # POST /insert_code
  pr$handle("POST", "/insert_code", function(req, res) {
    code <- req$body$code
    tryCatch({
      rstudioapi::insertText(code)
      list(success = TRUE, message = "Code inserted successfully")
    }, error = function(e) {
      list(success = FALSE, message = paste("Error inserting code:", e$message))
    })
  })

  # GET /health
  pr$handle("GET", "/health", function(req, res) {
    list(status = "healthy", service = "rstudio-plumber-api")
  })

  pr
