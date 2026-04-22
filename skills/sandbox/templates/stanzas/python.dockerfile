# Python toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Symlink python -> python3 (Ubuntu 24.04 only ships python3)
RUN ln -s /usr/bin/python3 /usr/bin/python

# Project Python dependencies (install at build time for speed; editable
# installs of in-workspace packages happen at runtime in the entrypoint because
# /workspace is only bind-mounted when the container is running).
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt
