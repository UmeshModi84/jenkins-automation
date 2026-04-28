pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
    }

    environment {
        CONTAINER_NAME = 'test-ai-backend-container'
        APP_PORT = '3000'
        LOCAL_IMAGE = 'test-ai-backend'
        // Used only when the agent has no Node/npm (see Setup Node stage)
        NODE_VERSION = '20.18.0'
        // Standalone CPython from astral-sh (used when no system python3 / no root apt)
        PYTHON_STANDALONE_VER = '3.12.8'
        PYTHON_STANDALONE_RELEASE = '20241219'
        PIP_DEFAULT_TIMEOUT = '180'
        // Static Docker CLI from download.docker.com (when `docker` is not on the agent)
        DOCKER_CLI_VERSION = '27.3.1'
        DOCKER_BUILDKIT = '0'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Node') {
            steps {
                script {
                    def hasNpm = sh(returnStatus: true, script: 'command -v npm >/dev/null 2>&1') == 0
                    if (!hasNpm) {
                        sh '''
                            set -e
                            NODE_HOME="${WORKSPACE}/.nodejs"
                            if [ -x "${NODE_HOME}/bin/npm" ]; then
                                exit 0
                            fi
                            ARCH="$(uname -m)"
                            case "$ARCH" in
                                x86_64) NODE_ARCH=linux-x64 ;;
                                aarch64) NODE_ARCH=linux-arm64 ;;
                                *) echo "Unsupported machine (need Node binary): $ARCH"; exit 1 ;;
                            esac
                            TARBALL="node-v${NODE_VERSION}-${NODE_ARCH}.tar.gz"
                            URL="https://nodejs.org/dist/v${NODE_VERSION}/${TARBALL}"
                            mkdir -p "${NODE_HOME}"
                            curl -fsSL "$URL" | tar -xz --strip-components=1 -C "${NODE_HOME}"
                        '''
                        env.PATH = "${WORKSPACE}/.nodejs/bin:${env.PATH}"
                    }
                }
            }
        }

        stage('Setup Python') {
            steps {
                script {
                    sh '''
                        set -e
                        have_py3() {
                            command -v python3 >/dev/null 2>&1 && python3 -c "import sys; raise SystemExit(0 if sys.version_info>=(3,8) else 1)"
                        }
                        if [ -x "${WORKSPACE}/.cpython/python/bin/python3" ]; then
                            export PATH="${WORKSPACE}/.cpython/python/bin:${PATH}"
                        fi
                        if have_py3; then exit 0; fi

                        if command -v apt-get >/dev/null 2>&1 && [ "$(id -u)" -eq 0 ]; then
                            export DEBIAN_FRONTEND=noninteractive
                            apt-get update -qq
                            apt-get install -y -qq python3 python3-pip python3-venv || true
                        fi
                        if have_py3; then exit 0; fi

                        if command -v apk >/dev/null 2>&1 && [ "$(id -u)" -eq 0 ]; then
                            apk add --no-cache python3 py3-pip || true
                        fi
                        if have_py3; then exit 0; fi

                        PYTHON_HOME="${WORKSPACE}/.cpython"
                        if [ -x "${PYTHON_HOME}/python/bin/python3" ]; then
                            exit 0
                        fi

                        ARCH="$(uname -m)"
                        case "$ARCH" in
                            x86_64) PY_ARCH=x86_64-unknown-linux-gnu ;;
                            aarch64) PY_ARCH=aarch64-unknown-linux-gnu ;;
                            *) echo "Unsupported arch for bundled Python: $ARCH"; exit 1 ;;
                        esac
                        TARBALL="cpython-${PYTHON_STANDALONE_VER}+${PYTHON_STANDALONE_RELEASE}-${PY_ARCH}-install_only_stripped.tar.gz"
                        URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PYTHON_STANDALONE_RELEASE}/${TARBALL}"
                        mkdir -p "${PYTHON_HOME}"
                        curl -fsSL "$URL" | tar -xz -C "${PYTHON_HOME}"
                        test -x "${PYTHON_HOME}/python/bin/python3"
                    '''
                    if (fileExists("${env.WORKSPACE}/.cpython/python/bin/python3")) {
                        env.PATH = "${env.WORKSPACE}/.cpython/python/bin:${env.PATH}"
                    }
                }
            }
        }

        stage('Setup Docker') {
            steps {
                script {
                    sh '''
                        set -e
                        if command -v docker >/dev/null 2>&1; then
                            exit 0
                        fi
                        CLI_HOME="${WORKSPACE}/.docker-cli"
                        BIN="${CLI_HOME}/bin/docker"
                        if [ -x "$BIN" ]; then
                            exit 0
                        fi

                        mkdir -p "${CLI_HOME}/bin"
                        ARCH="$(uname -m)"
                        case "$ARCH" in
                            x86_64) DARCH=x86_64 ;;
                            aarch64) DARCH=aarch64 ;;
                            *) echo "Unsupported arch for Docker static CLI: $ARCH"; exit 1 ;;
                        esac
                        URL="https://download.docker.com/linux/static/stable/${DARCH}/docker-${DOCKER_CLI_VERSION}.tgz"
                        TMP="$(mktemp -d)"
                        curl -fsSL "$URL" | tar -xz -C "$TMP"
                        install -m 0755 "$TMP/docker/docker" "$BIN"
                        rm -rf "$TMP"
                    '''
                    if (fileExists("${env.WORKSPACE}/.docker-cli/bin/docker")) {
                        env.PATH = "${env.WORKSPACE}/.docker-cli/bin:${env.PATH}"
                    }
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    set -e
                    ( cd backend && npm install )
                    n=0
                    while [ "$n" -lt 3 ]; do
                        n=$((n + 1))
                        python3 -m pip install --retries 15 --default-timeout 180 --progress-bar off \
                            -r "${WORKSPACE}/ai/requirements.txt" && break
                        [ "$n" -ge 3 ] && exit 1
                        sleep 20
                    done
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    set +e
                    cd backend && npx eslint . || true
                    cd "${WORKSPACE}" && flake8 ai backend --exclude=node_modules || true
                    set -e
                '''
            }
        }

        stage('Unit Test') {
            steps {
                sh '''
                    set +e
                    cd backend && npm test || true
                    set -e
                '''
            }
        }

        stage('AI Code Review') {
            steps {
                sh '''
                    set -e
                    cd "${WORKSPACE}"
                    python3 ai/code_review.py | tee ai_report.txt
                    python3 ai/security_scanner.py > security_report.txt || true
                    python3 ai/bug_predictor.py > bug_predictor_report.txt || true
                    python3 ai/deploy_decision_ai.py | tee deploy_decision.json || true
                    python3 ai/suggest_fix.py --code-review ai_report.txt --security security_report.txt || true
                    printf "metric 100\\nmetric 102\\nmetric 500\\n" | python3 ai/anomaly_detector.py - || true
                    python3 ai/auto_fix.py --dry-run || true
                '''
            }
        }

        stage('Security Scan') {
            steps {
                sh '''
                    set +e
                    cd backend
                    npm audit --audit-level=high
                    AUDIT_RC=$?
                    cd "${WORKSPACE}"
                    echo "--- grep for potential secrets (informational) ---"
                    grep -RInE "password|secret|api_key" --include="*.js" --include="*.py" . \
                        --exclude-dir=node_modules \
                        --exclude-dir=.git \
                        --exclude-dir=venv \
                        --exclude-dir=.venv \
                        || true
                    set -e
                    exit "${AUDIT_RC}"
                '''
            }
        }

        stage('Check Docker daemon') {
            steps {
                script {
                    def rc = sh(returnStatus: true, script: 'docker info >/dev/null 2>&1')
                    env.DOCKER_DAEMON_OK = (rc == 0) ? 'true' : 'false'
                    if (env.DOCKER_DAEMON_OK != 'true') {
                        echo '''
WARNING: Docker daemon not reachable (e.g. unix:///var/run/docker.sock). Skipping Docker Build, Push, Deploy, Health Check, and container log analysis.

Fix on the server: mount the host socket into the Jenkins container (-v /var/run/docker.sock:/var/run/docker.sock) and grant the jenkins user access (host docker group GID via group_add), install Docker on a shell agent, or set DOCKER_HOST to a remote engine.
'''
                    }
                }
            }
        }

        stage('Docker Build') {
            when {
                expression {
                    return env.DOCKER_DAEMON_OK == 'true'
                }
            }
            steps {
                sh '''
                    set -e
                    cd "${WORKSPACE}"
                    docker build -t ${LOCAL_IMAGE}:${BUILD_NUMBER} .
                '''
            }
        }

        stage('Deploy') {
            when {
                expression {
                    return env.DOCKER_DAEMON_OK == 'true'
                }
            }
            steps {
                sh '''
                    set -e
                    docker stop ${CONTAINER_NAME} || true
                    docker rm ${CONTAINER_NAME} || true
                    docker run -d --name ${CONTAINER_NAME} \
                        -p ${APP_PORT}:3000 \
                        -e AI_REPORTS_DIR=/reports \
                        -v "${WORKSPACE}:/reports:ro" \
                        ${LOCAL_IMAGE}:${BUILD_NUMBER}
                '''
            }
        }

        stage('Health Check') {
            when {
                expression {
                    return env.DOCKER_DAEMON_OK == 'true'
                }
            }
            steps {
                sh '''
                    set -e
                    sleep 2
                    curl -fsS "http://127.0.0.1:${APP_PORT}/health"
                    curl -fsS "http://127.0.0.1:${APP_PORT}/ai-dashboard/" | grep -q "AI pipeline"
                '''
            }
        }

        stage('AI Log Analysis') {
            when {
                expression {
                    return env.DOCKER_DAEMON_OK == 'true'
                }
            }
            steps {
                sh '''
                    set -e
                    cd "${WORKSPACE}"
                    docker logs ${CONTAINER_NAME} > docker_app.log 2>&1 || true
                    python3 ai/log_analysis.py docker_app.log
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'ai_report.txt,security_report.txt,bug_predictor_report.txt,deploy_decision.json', allowEmptyArchive: true
        }
    }
}
