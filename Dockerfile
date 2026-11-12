# The image Cloudflare Containers runs (cloudflare.md). Everything a cold start needs is baked in: the disk
# resets to this image every time the container sleeps, so nothing should be downloaded at startup.
FROM --platform=linux/amd64 python:3.12-slim

ADD --checksum=sha256:cfb371176d164437ae869f8351cfde49bd1804ae71c61923f75c9cba9c9c006d \
    https://github.com/benbjohnson/litestream/releases/download/v0.5.17/litestream-0.5.17-linux-x86_64.tar.gz \
    /tmp/litestream.tar.gz
RUN tar -xzf /tmp/litestream.tar.gz -C /usr/local/bin litestream && rm /tmp/litestream.tar.gz

RUN useradd --create-home app && install -d -o app -g app /app /data

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY --chown=app:app . .
USER app

ENV DEBUG=False PYTHONUNBUFFERED=1 GITHUB_USERNAME=saravanagithub14

# build_rag_index downloads the ONNX models unless .model_cache/ came from the build context
RUN python manage.py collectstatic --noinput \
    && python manage.py migrate --noinput \
    && python manage.py build_rag_index

EXPOSE 8080
CMD ["sh", "container/start.sh"]
