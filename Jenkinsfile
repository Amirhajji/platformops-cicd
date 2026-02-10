pipeline {
  agent any

  options {
    skipDefaultCheckout(true)
    disableConcurrentBuilds()
  }

  environment {
    CI = "true"
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
        script {
            def sha = env.GIT_SHA

            def backendFile = "backend/backend-${sha}.zip"
            def frontendFile = "platformops-frontend/frontend-${sha}.zip"

            sh """
                test -f ${backendFile}
                test -f ${frontendFile}
            """

            withCredentials([usernamePassword(
                credentialsId: 'nexus-credentials',
                usernameVariable: 'NEXUS_USER',
                passwordVariable: 'NEXUS_PASS'
            )]) {

                sh """
                set -e

                BACKEND_URL="http://192.168.21.132:8081/repository/backend-releases/backend/${sha}/backend-${sha}.zip"
                FRONTEND_URL="http://192.168.21.132:8081/repository/frontend-releases/frontend/${sha}/frontend-${sha}.zip"

                echo "Uploading backend artifact..."
                curl -u "$NEXUS_USER:$NEXUS_PASS" --fail --upload-file ${backendFile} "$BACKEND_URL"

                echo "Uploading frontend artifact..."
                curl -u "$NEXUS_USER:$NEXUS_PASS" --fail --upload-file ${frontendFile} "$FRONTEND_URL"

                echo "Downloading back for integrity check..."

                curl -u "$NEXUS_USER:$NEXUS_PASS" -o tmp_backend.zip "$BACKEND_URL"
                curl -u "$NEXUS_USER:$NEXUS_PASS" -o tmp_frontend.zip "$FRONTEND_URL"

                echo "Computing checksums..."

                sha256sum ${backendFile} > orig_backend.sha
                sha256sum tmp_backend.zip > dl_backend.sha

                sha256sum ${frontendFile} > orig_frontend.sha
                sha256sum tmp_frontend.zip > dl_frontend.sha

                echo "Verifying integrity..."

                diff orig_backend.sha dl_backend.sha
                diff orig_frontend.sha dl_frontend.sha

                echo "Nexus upload verified successfully."
                """
            }
        }
    }
}

  }
}
