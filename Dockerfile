# Use minimal glibc-based image
FROM debian:bookworm-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl ca-certificates binutils && \
    rm -rf /var/lib/apt/lists/*

# Configuration
ENV LLAMAFILE_URL="https://huggingface.co/mozilla-ai/llamafile_0.10.0/resolve/main/Qwen3.5-9B-Q5_K_S.llamafile"
ENV LLAMAFILE_NAME="Qwen3.5-9B-Q5_K_S.llamafile"
ENV PORT=1111

# Working directory
WORKDIR /home

# Download and prepare the Llamafile
RUN curl -L "${LLAMAFILE_URL}" -o "${LLAMAFILE_NAME}" && \
    chmod +x "${LLAMAFILE_NAME}"

# Create an entrypoint script
RUN echo "#!/bin/sh\nexec /home/$LLAMAFILE_NAME --server --port $PORT --host 0.0.0.0 -ngl 9999" > /entrypoint.sh && \
    chmod +x /entrypoint.sh

EXPOSE ${PORT}
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]

# Running Commands
# docker build -t debian-llamafile .
# docker run -d -p 1111:1111 debian-llamafile
# docker run -d --gpus all -p 11434:1111 debian-llamafile