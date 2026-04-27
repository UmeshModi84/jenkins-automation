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

        stage('Install Dependencies') {
            steps {
                sh '''
                    set -e
                    cd backend && npm install
                    python3 -m pip install -r ai/requirements.txt
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

        stage('Docker Build') {
            steps {
                sh '''
                    set -e
                    cd "${WORKSPACE}"
                    docker build -t ${LOCAL_IMAGE}:${BUILD_NUMBER} .
                '''
            }
        }

        stage('Docker Push') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'docker-hub-credentials',
                        usernameVariable: 'DOCKERHUB_USER',
                        passwordVariable: 'DOCKERHUB_PASS'
                    )
                ]) {
                    sh '''
                        set -e
                        echo "${DOCKERHUB_PASS}" | docker login -u "${DOCKERHUB_USER}" --password-stdin
                        docker tag ${LOCAL_IMAGE}:${BUILD_NUMBER} ${DOCKERHUB_USER}/${LOCAL_IMAGE}:${BUILD_NUMBER}
                        docker tag ${LOCAL_IMAGE}:${BUILD_NUMBER} ${DOCKERHUB_USER}/${LOCAL_IMAGE}:latest
                        docker push ${DOCKERHUB_USER}/${LOCAL_IMAGE}:${BUILD_NUMBER}
                        docker push ${DOCKERHUB_USER}/${LOCAL_IMAGE}:latest
                    '''
                }
            }
        }

        stage('Deploy') {
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
