FROM nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236

# Package with infra/scripts/package_web_release.py into this build's public/.
# Source maps and private inputs never belong in this context.
COPY nginx.conf /etc/nginx/nginx.conf
COPY start.sh /etc/nginx/start.sh
COPY public/ /usr/share/nginx/html/
USER nginx
EXPOSE 8080
ENTRYPOINT ["sh", "/etc/nginx/start.sh"]
