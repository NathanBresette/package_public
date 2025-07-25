# Plumber API for RStudio integration
# This provides local endpoints for the HTML interface to interact with RStudio

library(plumber)
library(rstudioapi)

# Serve static files (index.html and assets) from the package's public directory
#' @plumber
function(pr) {
  pr$handle("GET", "/", function(req, res) {
    static_dir <- system.file("public", package = "rstudioai")
    res$setHeader("Cache-Control", "no-cache")
    res$sendFile(file.path(static_dir, "index.html"))
  })
  pr$mount("/static", plumber::pr_static(system.file("public", package = "rstudioai")))
  pr
}

#* @post /insert_code
#* @param code:string The code to insert into RStudio
function(code) {
  tryCatch({
    # Insert code into the active RStudio document
    rstudioapi::insertText(code)
    list(success = TRUE, message = "Code inserted successfully")
  }, error = function(e) {
    list(success = FALSE, message = paste("Error inserting code:", e$message))
  })
}

#* @get /health
function() {
  list(status = "healthy", service = "rstudio-plumber-api")
} 