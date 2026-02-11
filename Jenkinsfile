pipeline {
  agent any

  options {
    skipDefaultCheckout(true)
    disableConcurrentBuilds()
  }

  environment {
    CI = "true"

    // Infra : 
    NEXUS_BASE = "http://192.168.21.132:8081"
    BACKEND_HOST = "192.168.21.133"
    FRONTEND_HOST = "192.168.21.134"
    SSH_USER = "devops"

    BACKEND_HEALTH = "http://192.168.21.133:8000/health"
    FRONTEND_URL = "http://192.168.21.134"
  }

  stages {

    stage('Checkout') {
      steps {
        deleteDir()
        checkout scm
        script {
          env.GIT_SHA = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
          echo "Commit short SHA = ${env.GIT_SHA}"
        }
        sh 'ls -la'
      }
    }

    stage('Backend: build + package') {
      steps {
        dir('backend') {
          sh '''#!/bin/bash
            set -euxo pipefail

            python3 -m venv .venv
            source .venv/bin/activate
            python -m pip install --upgrade pip
            pip install -r requirements.txt

            python -c "import app.main; print('Backend import OK')"

            ART="backend-${GIT_SHA}.zip"
            rm -f "$ART"

            zip -r "$ART" app requirements.txt \
              -x "*.pyc" \
              -x "__pycache__/*" \
              -x ".venv/*"

            ls -lh "$ART"
          '''
        }
      }
    }

    stage('Frontend: build + package') {
      steps {
        dir('platformops-frontend') {
          sh '''#!/bin/bash
            set -euxo pipefail

            npm ci
            npm run build

            test -f dist/index.html

            ART="frontend-${GIT_SHA}.zip"
            rm -f "$ART"

            (cd dist && zip -r "../$ART" .)

            ls -lh "$ART"
          '''
        }
      }
    }

    stage('Verify + archive artifacts') {
      steps {
        sh '''#!/bin/bash
          set -euxo pipefail

          test -f "backend/backend-${GIT_SHA}.zip"
          test -f "platformops-frontend/frontend-${GIT_SHA}.zip"

          unzip -l "backend/backend-${GIT_SHA}.zip" | grep -E "app/|requirements.txt"
          unzip -l "platformops-frontend/frontend-${GIT_SHA}.zip" | grep -E "index.html"

          mkdir -p artifacts
          cp "backend/backend-${GIT_SHA}.zip" artifacts/
          cp "platformops-frontend/frontend-${GIT_SHA}.zip" artifacts/

          ls -lh artifacts
        '''

        archiveArtifacts artifacts: 'artifacts/*.zip', fingerprint: true
      }
    }

    stage('Publish artifacts to Nexus') {
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'nexus-credentials',
          usernameVariable: 'NEXUS_USER',
          passwordVariable: 'NEXUS_PASS'
        )]) {

          sh '''#!/bin/bash
            set -euxo pipefail

            BACKEND_URL="${NEXUS_BASE}/repository/backend-releases/backend/${GIT_SHA}/backend-${GIT_SHA}.zip"
            FRONTEND_URL="${NEXUS_BASE}/repository/frontend-releases/frontend/${GIT_SHA}/frontend-${GIT_SHA}.zip"

            curl -u "$NEXUS_USER:$NEXUS_PASS" --fail --upload-file backend/backend-${GIT_SHA}.zip "$BACKEND_URL"
            curl -u "$NEXUS_USER:$NEXUS_PASS" --fail --upload-file platformops-frontend/frontend-${GIT_SHA}.zip "$FRONTEND_URL"

            curl -u "$NEXUS_USER:$NEXUS_PASS" -o tmp_backend.zip "$BACKEND_URL"
            curl -u "$NEXUS_USER:$NEXUS_PASS" -o tmp_frontend.zip "$FRONTEND_URL"

            sha256sum backend/backend-${GIT_SHA}.zip | awk '{print $1}' > orig_backend.sha
            sha256sum tmp_backend.zip | awk '{print $1}' > dl_backend.sha

            sha256sum platformops-frontend/frontend-${GIT_SHA}.zip | awk '{print $1}' > orig_frontend.sha
            sha256sum tmp_frontend.zip | awk '{print $1}' > dl_frontend.sha

            diff orig_backend.sha dl_backend.sha
            diff orig_frontend.sha dl_frontend.sha
          '''
        }
      }
    }

   stage('Deploy Backend') {
  steps {
    withCredentials([usernamePassword(
      credentialsId: 'nexus-credentials',
      usernameVariable: 'NEXUS_USER',
      passwordVariable: 'NEXUS_PASS'
    )]) {

      sh '''#!/bin/bash
        set -eux

        SHA="${GIT_SHA}"

        ssh ${SSH_USER}@${BACKEND_HOST} "
          set -eux

          REL=/opt/backend/releases/${SHA}
          TMP=/tmp/backend-${SHA}.zip

          sudo mkdir -p \\$REL

          curl -u ${NEXUS_USER}:${NEXUS_PASS} -f -L \
            -o \\$TMP \
            ${NEXUS_BASE}/repository/backend-releases/backend/${SHA}/backend-${SHA}.zip

          sudo unzip -oq \\$TMP -d \\$REL

          sudo python3 -m venv \\$REL/venv
          sudo \\$REL/venv/bin/pip install -r \\$REL/requirements.txt

          sudo ln -sfn \\$REL /opt/backend/current
          sudo systemctl restart backend
        "

        echo "Waiting for backend to become healthy..."

        for i in {1..30}; do
          if curl -sf ${BACKEND_HEALTH}; then
            echo "Backend is healthy"
            exit 0
          fi
          sleep 2
        done

        echo "Backend failed health check"
        exit 1
      '''
    }
  }
}


    stage('Deploy Frontend') {
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'nexus-credentials',
          usernameVariable: 'NEXUS_USER',
          passwordVariable: 'NEXUS_PASS'
        )]) {

          sh '''#!/bin/bash
            set -eux

            SHA="${GIT_SHA}"

            ssh ${SSH_USER}@${FRONTEND_HOST} "
              set -eux

              REL=/var/www/frontend/releases/${SHA}
              TMP=/tmp/frontend-${SHA}.zip

              sudo mkdir -p \\$REL

              curl -u ${NEXUS_USER}:${NEXUS_PASS} -f -L \
                -o \\$TMP \
                ${NEXUS_BASE}/repository/frontend-releases/frontend/${SHA}/frontend-${SHA}.zip

              sudo unzip -oq \\$TMP -d \\$REL

              sudo ln -sfn \\$REL /var/www/frontend/current
              sudo systemctl reload nginx
            "

            curl -f ${FRONTEND_URL}
          '''
        }
      }
    }

  }
}
