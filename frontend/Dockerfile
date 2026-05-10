FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf.template
COPY . /usr/share/nginx/html
CMD ["/bin/sh", "-c", "envsubst '${SCRAPEBOOK_API_URL}' < /usr/share/nginx/html/index.html > /tmp/index.html && mv /tmp/index.html /usr/share/nginx/html/index.html && envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
