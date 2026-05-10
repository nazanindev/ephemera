FROM nginx:alpine
COPY . /usr/share/nginx/html
CMD ["/bin/sh", "-c", "envsubst '${SCRAPEBOOK_API_URL}' < /usr/share/nginx/html/index.html > /tmp/index.html && mv /tmp/index.html /usr/share/nginx/html/index.html && printf 'server{listen %s;root /usr/share/nginx/html;index index.html;location/{try_files $uri $uri/ /index.html;}}' \"${PORT:-80}\" > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
