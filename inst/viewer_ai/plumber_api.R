#* @plumber
function(pr) {
  # Mount static files from the public directory
  static_dir <- system.file("public", package = "rstudioai")
  pr$mount("/static", static_dir)
  
  # Root endpoint to serve index.html
  pr$handle("GET", "/", function(req, res) {
    tryCatch({
      html_file <- file.path(static_dir, "index.html")
      if (file.exists(html_file)) {
        res$setHeader("Content-Type", "text/html")
        res$setHeader("Cache-Control", "no-cache")
        html_content <- paste(readLines(html_file), collapse = "\n")
        return(html_content)
      } else {
        res$status <- 404
        return(list(error = "HTML file not found"))
      }
    }, error = function(e) {
      res$status <- 500
      return(list(error = paste("Server error:", e$message)))
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
