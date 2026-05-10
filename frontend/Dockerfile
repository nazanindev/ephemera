FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY . /usr/share/nginx/html
CMD ["/bin/sh", "-c", "envsubst '${SCRAPEBOOK_API_URL}' < /usr/share/nginx/html/index.html > /tmp/index.html && mv /tmp/index.html /usr/share/nginx/html/index.html && nginx -g 'daemon off;'"]
