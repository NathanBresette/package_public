
# Find an available port for the plumber server
find_available_port <- function(start_port = 8888, max_attempts = 100) {
  for (port in start_port:(start_port + max_attempts)) {
    tryCatch({
      # Try to create a connection to test if port is available
      con <- socketConnection(host = "127.0.0.1", port = port, server = TRUE, blocking = FALSE)
      close(con)
      return(port)
    }, error = function(e) {
      # Port is in use, try next one
    })
  }
  stop("No available ports found in range ", start_port, ":", start_port + max_attempts)
}
