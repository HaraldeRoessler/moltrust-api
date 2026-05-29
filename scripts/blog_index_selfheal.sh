#!/bin/bash
# blog_index_selfheal.sh — regenerate /var/www/html/blog/index.html + fix ownership.
# Run by /etc/cron.d/moltrust-blog-index every 15 minutes, as root.
#
# Rationale: full site deploys ship a stale blog/index.html and clobber the
# index that deploy_blog_post.sh regenerates live (root cause established
# 2026-05-21). This regenerates the index from the actual post files in
# /var/www/html/blog/, so any clobber self-heals within <=15 min.
echo "=== $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
python3 /home/moltstack/moltstack/scripts/generate_blog_index.py
chown www-data:www-data /var/www/html/blog/index.html
echo "ownership: $(stat -c '%U:%G' /var/www/html/blog/index.html)"
