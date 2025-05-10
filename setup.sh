#!/bin/bash

# Define directories for the front end (HTML/JavaScript) and back end (Python)
frontend_dirs=(
    "frontend"
    "frontend/assets"
    "frontend/css"
    "frontend/js"
)

backend_dirs=(
    "backend"
    "backend/api"
    "backend/models"
    "backend/routes"
)

# Define files
files=(
    "frontend/index.html"
    "frontend/css/style.css"
    "frontend/js/app.js"
    "backend/app.py"
    "README.md"
    ".gitignore"
)

# Create front end directories
for dir in "${frontend_dirs[@]}"; do
    mkdir -p "$dir"
    echo "Created front end directory: $dir"
done

# Create back end directories
for dir in "${backend_dirs[@]}"; do
    mkdir -p "$dir"
    echo "Created back end directory: $dir"
done

# Create files
for file in "${files[@]}"; do
    touch "$file"
    echo "Created file: $file"
done

echo "Setup complete!"
