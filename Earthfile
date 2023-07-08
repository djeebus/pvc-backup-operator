VERSION 0.7

build-base:
    ARG python_version
    FROM python:${python_version}-slim


build:
    FROM +build-base
    RUN apt-get update \
        && apt-get install --no-install-recommends -y \
            # deps for installing poetry
            curl \
            # deps for building python deps
            build-essential

    # install poetry - respects $POETRY_VERSION & $POETRY_HOME
    RUN curl -sSL https://install.python-poetry.org | python3 -
    RUN /root/.local/bin/poetry config virtualenvs.in-project true

    WORKDIR /app
    COPY poetry.lock pyproject.toml /app/
    RUN mkdir -p /wheels/ && /root/.local/bin/poetry export > /wheels/requirements.txt
    RUN pip3 wheel \
        --requirement /wheels/requirements.txt \
        --wheel-dir /wheels/

    SAVE ARTIFACT /wheels/

    COPY pvcbackupoperator /app/pvcbackupoperator
    RUN ls -l /app/
    RUN /root/.local/bin/poetry build --format=wheel --no-ansi
    SAVE ARTIFACT /app/dist/

image:
    FROM +build-base

    COPY +build/wheels/ /wheels/
    RUN pip3 install \
        -r /wheels/requirements.txt \
        --no-index \
        --find-links file:///wheels/
    WORKDIR /app/

    COPY +build/dist/ /wheels/
    RUN ls -l /wheels/
    RUN pip3 install file:///wheels/pvc_backup_operator-0.1.0-py3-none-any.whl

    COPY bin/entrypoint.sh /bin/

    ENTRYPOINT /bin/entrypoint.sh
    RUN chmod +x /bin/entrypoint.sh

    ARG image
    ARG tag
    SAVE IMAGE ${image}:${tag}
