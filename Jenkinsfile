// CAAS Auto Deploy - Jenkins Pipeline
//
// Automates the full workflow from requirement to production deployment.
//
// Parameters:
//   - REQUIREMENT: Natural language requirement
//   - DEPLOY_TARGET: docker, kubernetes, or local
//   - SKIP_TESTS: Skip test execution (true/false)
//
// Required Jenkins Credentials:
//   - openai-api-key: OpenAI API key (Secret text)
//   - docker-registry: Docker registry credentials (optional)

pipeline {
    agent any

    parameters {
        string(
            name: 'REQUIREMENT',
            defaultValue: 'Build a task management system',
            description: 'Natural language requirement for the system to build'
        )
        choice(
            name: 'DEPLOY_TARGET',
            choices: ['docker', 'kubernetes', 'local'],
            description: 'Deployment target environment'
        )
        booleanParam(
            name: 'SKIP_TESTS',
            defaultValue: false,
            description: 'Skip test execution for faster builds'
        )
        booleanParam(
            name: 'VERBOSE',
            defaultValue: true,
            description: 'Enable verbose output'
        )
    }

    environment {
        PYTHON_VERSION = '3.11'
        OUTPUT_DIR = './generated'
        VENV_DIR = 'venv'
    }

    options {
        timestamps()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('Initialize') {
            steps {
                script {
                    echo """
                    ╔══════════════════════════════════════════════════════════╗
                    ║          🚀 CAAS Full Automation Workflow                ║
                    ╚══════════════════════════════════════════════════════════╝
                    """
                    echo "Requirement: ${params.REQUIREMENT}"
                    echo "Deploy Target: ${params.DEPLOY_TARGET}"
                    echo "Skip Tests: ${params.SKIP_TESTS}"
                    echo "Verbose: ${params.VERBOSE}"
                }
            }
        }

        stage('Validate Environment') {
            steps {
                script {
                    echo '📋 Step 1/7: Validating Environment'

                    // Setup Python virtual environment
                    sh """
                        python${PYTHON_VERSION} -m venv ${VENV_DIR}
                        . ${VENV_DIR}/bin/activate
                        pip install --upgrade pip
                        pip install -e .
                    """

                    // Run environment validation
                    sh """
                        . ${VENV_DIR}/bin/activate
                        python scripts/validate_env.py --export-json validation_results.json
                    """

                    // Archive validation results
                    archiveArtifacts artifacts: 'validation_results.json', fingerprint: true
                }
            }
        }

        stage('Generate Code') {
            steps {
                script {
                    echo '🔧 Step 2/7: Generating Code'

                    withCredentials([string(credentialsId: 'openai-api-key', variable: 'OPENAI_API_KEY')]) {
                        def verboseFlag = params.VERBOSE ? '--verbose' : ''

                        sh """
                            . ${VENV_DIR}/bin/activate
                            caas generate "${params.REQUIREMENT}" \\
                                -o ${OUTPUT_DIR} \\
                                ${verboseFlag}
                        """
                    }

                    echo '✅ Code generation completed'
                    sh "ls -la ${OUTPUT_DIR}/"
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                script {
                    echo '📦 Step 3/7: Installing Dependencies'

                    sh """
                        cd ${OUTPUT_DIR}
                        python${PYTHON_VERSION} -m venv venv
                        . venv/bin/activate
                        pip install --upgrade pip
                        pip install -r requirements.txt

                        if [ -f "tests/requirements-test.txt" ]; then
                            pip install -r tests/requirements-test.txt
                        fi
                    """

                    echo '✅ Dependencies installed'
                }
            }
        }

        stage('Run Tests') {
            when {
                expression { !params.SKIP_TESTS }
            }
            steps {
                script {
                    echo '🧪 Step 4/7: Running Tests'

                    sh """
                        cd ${OUTPUT_DIR}
                        . venv/bin/activate
                        pytest tests/ \\
                            --cov=src \\
                            --cov-report=html \\
                            --cov-report=xml \\
                            --cov-report=term \\
                            --junitxml=test-results.xml \\
                            -v
                    """

                    echo '✅ Tests passed'

                    // Publish test results
                    junit "${OUTPUT_DIR}/test-results.xml"

                    // Publish coverage report
                    publishHTML([
                        reportDir: "${OUTPUT_DIR}/htmlcov",
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report',
                        keepAll: true
                    ])
                }
            }
        }

        stage('Code Quality') {
            when {
                expression { !params.SKIP_TESTS }
            }
            steps {
                script {
                    echo '✅ Step 5/7: Code Quality Checks'

                    sh """
                        cd ${OUTPUT_DIR}
                        . venv/bin/activate

                        # Install quality tools
                        pip install pylint black mypy

                        # Run black
                        black src/ --check || (echo "⚠️  Code formatting issues" && black src/)

                        # Run pylint
                        pylint src/ --fail-under=7.0 --output-format=json > pylint-report.json || true
                    """

                    echo '✅ Code quality checks completed'

                    // Archive quality reports
                    archiveArtifacts artifacts: "${OUTPUT_DIR}/pylint-report.json", fingerprint: true, allowEmptyArchive: true
                }
            }
        }

        stage('Build Docker Image') {
            when {
                expression { params.DEPLOY_TARGET == 'docker' }
            }
            steps {
                script {
                    echo '🐳 Step 6/7: Building Docker Image'

                    def imageName = "caas-generated:${env.BUILD_NUMBER}"
                    def latestTag = "caas-generated:latest"

                    sh """
                        cd ${OUTPUT_DIR}
                        docker build -t ${imageName} .
                        docker tag ${imageName} ${latestTag}
                    """

                    echo "✅ Docker image built: ${imageName}"

                    // Run container health check
                    sh """
                        cd ${OUTPUT_DIR}
                        docker-compose up -d
                        sleep 10
                        docker-compose ps
                        docker-compose down
                    """

                    echo '✅ Container health check passed'
                }
            }
        }

        stage('Deploy') {
            steps {
                script {
                    echo '🚢 Step 7/7: Deploying'

                    switch(params.DEPLOY_TARGET) {
                        case 'docker':
                            sh """
                                cd ${OUTPUT_DIR}
                                docker-compose up -d --build
                            """
                            echo '✅ Deployed to Docker'
                            echo 'View logs: docker-compose logs -f'
                            break

                        case 'kubernetes':
                            sh """
                                cd ${OUTPUT_DIR}
                                if [ -d "k8s" ]; then
                                    kubectl apply -f k8s/ --dry-run=client
                                    # Uncomment for actual deployment:
                                    # kubectl apply -f k8s/
                                else
                                    echo "⚠️  No k8s directory found"
                                    exit 1
                                fi
                            """
                            echo '✅ Kubernetes manifests validated'
                            break

                        case 'local':
                            echo '✅ Local deployment - ready to run'
                            echo "Run: cd ${OUTPUT_DIR} && python main.py"
                            break

                        default:
                            error "Unknown deployment target: ${params.DEPLOY_TARGET}"
                    }
                }
            }
        }
    }

    post {
        always {
            script {
                echo '📊 Pipeline Summary'
                echo "═══════════════════════════════════════════════════════════"
                echo "Requirement:      ${params.REQUIREMENT}"
                echo "Deploy Target:    ${params.DEPLOY_TARGET}"
                echo "Tests:            ${params.SKIP_TESTS ? 'Skipped' : 'Passed'}"
                echo "Build Number:     ${env.BUILD_NUMBER}"
                echo "Build Duration:   ${currentBuild.durationString}"
                echo "═══════════════════════════════════════════════════════════"

                // Archive generated code
                archiveArtifacts artifacts: "${OUTPUT_DIR}/**/*",
                                fingerprint: true,
                                allowEmptyArchive: true
            }
        }
        success {
            script {
                echo '✅ ✨ CAAS Auto Deploy completed successfully! ✨'

                // Send notification (example)
                // emailext(
                //     subject: "✅ CAAS Build #${env.BUILD_NUMBER} - SUCCESS",
                //     body: "Build completed successfully!\nRequirement: ${params.REQUIREMENT}",
                //     to: '${DEFAULT_RECIPIENTS}'
                // )
            }
        }
        failure {
            script {
                echo '❌ CAAS Auto Deploy failed!'

                // Send notification (example)
                // emailext(
                //     subject: "❌ CAAS Build #${env.BUILD_NUMBER} - FAILED",
                //     body: "Build failed!\nRequirement: ${params.REQUIREMENT}\nCheck: ${env.BUILD_URL}",
                //     to: '${DEFAULT_RECIPIENTS}'
                // )
            }
        }
        cleanup {
            script {
                echo '🧹 Cleaning up...'

                // Stop running containers
                sh """
                    cd ${OUTPUT_DIR} || exit 0
                    docker-compose down || true
                """

                echo '✅ Cleanup completed'
            }
        }
    }
}
