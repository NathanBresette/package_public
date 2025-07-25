#* @plumber
function(pr) {
  pr$handle("GET", "/", function(req, res) {
    static_dir <- system.file("public", package = "rstudioai")
    res$setHeader("Cache-Control", "no-cache")
    res$sendFile(file.path(static_dir, "index.html"))
  })
  
  pr$handle("POST", "/insert_code", function(req, res) {
    code <- req$body$code
    tryCatch({
      rstudioapi::insertText(code)
      list(success = TRUE, message = "Code inserted successfully")
    }, error = function(e) {
      list(success = FALSE, message = paste("Error inserting code:", e$message))
    })
  })
  
  pr$handle("GET", "/health", function(req, res) {
    list(status = "healthy", service = "rstudio-plumber-api")
  })
  
  pr
}
