#* @plumber
function(pr) {
  # Root endpoint to serve index.html
  pr$handle("GET", "/", function(req, res) {
    tryCatch({
      static_dir <- system.file("public", package = "rstudioai")
      html_file <- file.path(static_dir, "index.html")
      if (file.exists(html_file)) {
        res$setHeader("Content-Type", "text/html")
        res$setHeader("Cache-Control", "no-cache")
        res$sendFile(html_file)
      } else {
        res$status <- 404
        res$body <- list(error = "HTML file not found")
      }
    }, error = function(e) {
      res$status <- 500
      res$body <- list(error = paste("Server error:", e$message))
    })
  })
  
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
}
