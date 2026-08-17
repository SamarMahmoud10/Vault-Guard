FROM node:latest
USER root
WORKDIR /usr/src/app
COPY . .
CMD ["node", "index.js"]
