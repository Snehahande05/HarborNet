pipeline {
    agent any

    environment {
        APP_NAME = "harbornet"
        DOCKER_REGISTRY = "registry.hub.docker.com"
        IMAGE_NAME = "harbornet-platform"
        IMAGE_TAG = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out source repository...'
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Setting up Python environment and dependencies...'
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                echo 'Running python code compilation and syntax checks...'
                sh '''
                    . venv/bin/activate
                    python -m py_compile app.py
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Building Docker container image...'
                sh '''
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest
                '''
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploying to Kubernetes staging environment...'
                // These commands are commented out to prevent execution errors in basic Jenkins agents,
                // but serve as a functional example of Kubernetes delivery.
                script {
                    echo "kubectl apply -f k8s/deployment.yaml"
                    echo "kubectl apply -f k8s/service.yaml"
                }
            }
        }
    }

    post {
        always {
            echo 'Cleaning workspace...'
            cleanWs()
        }
        success {
            echo 'Build successful. Notification sent.'
        }
        failure {
            echo 'Build failed. Investigation required.'
        }
    }
}
