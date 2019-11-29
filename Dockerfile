FROM python:3.7-alpine
  
LABEL maintainer="Robert Kaussow <mail@geeklabor.de>" \
    org.label-schema.name="git-batch" \
    org.label-schema.vcs-url="https://github.com/xoxys/git-batch" \
    org.label-schema.vendor="Robert Kaussow" \
    org.label-schema.schema-version="1.0"

ENV PY_COLORS=1

ADD dist/git_batch-*.whl /

RUN apk --update add --virtual .build-deps build-base libffi-dev libressl-dev && \
    apk --update add git && \
    pip install --upgrade --no-cache-dir pip && \
    pip install --no-cache-dir --find-links=. git-batch && \
    apk del .build-deps && \
    rm -rf /var/cache/apk/* && \
    rm -rf /root/.cache/  && \
    rm -f git_batch-*.whl

USER root
CMD []
ENTRYPOINT ["/usr/local/bin/git-batch"]
