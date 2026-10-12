ARG SQUAD_AGENT_IMAGE
FROM ${SQUAD_AGENT_IMAGE}

ARG RUNNER_VERSION=2.338.0
ARG RUNNER_SHA256=af4b794c1bc41d73d40535e3fe092a39f9679cd8d965954c2aca25a05ca41d32
USER root
RUN test -n "${RUNNER_SHA256}" \
    && mkdir -p /runner \
    && curl -fsSL "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" -o /runner/runner.tar.gz \
    && echo "${RUNNER_SHA256}  /runner/runner.tar.gz" | sha256sum -c - \
    && tar -xzf /runner/runner.tar.gz -C /runner \
    && rm /runner/runner.tar.gz \
    && /runner/bin/installdependencies.sh \
    && useradd --create-home --uid 10001 runner \
    && chown -R runner:runner /runner /workspace
COPY entrypoint.sh /runner-entrypoint.sh
RUN chmod +x /runner-entrypoint.sh
USER runner
WORKDIR /runner
ENTRYPOINT ["/runner-entrypoint.sh"]
