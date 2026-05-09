#!/bin/bash
# deploy_blog_post.sh — Deploy blog post + regenerate index
# Usage: ./deploy_blog_post.sh <file.html>
set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 <file.html>"
  exit 1
fi

FILE="$1"
BLOG_DIR="/var/www/html/blog"
FILENAME=$(basename "$FILE")
SLUG="${FILENAME%.html}"

# 1. Copy file to blog dir
cp "$FILE" "$BLOG_DIR/$FILENAME"
chmod 644 "$BLOG_DIR/$FILENAME"
echo "Deployed $FILENAME to $BLOG_DIR/"

# 2. Regenerate index from all posts
python3 /home/moltstack/moltstack/scripts/generate_blog_index.py

# 3. Verify
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://moltrust.ch/blog/$FILENAME")
echo "Blog post: https://moltrust.ch/blog/$FILENAME — HTTP $HTTP_CODE"

if curl -s "https://moltrust.ch/blog/" | grep -q "$SLUG"; then
  echo "✅ Post visible in blog listing"
else
  echo "⚠️ Post not found in listing — check generate_blog_index.py"
fi
