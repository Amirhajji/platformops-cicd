pipeline {
  agent any

  options {
    timestamps()
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
          sh '''
            set -euxo pipefail

            python3 -m venv .venv
            . .venv/bin/activate
            python -m pip install --upgrade pip
            pip install -r requirements.txt

            # Import-safety check (CI=true prevents DB init)
            python -c "import app.main; print('Backend import OK')"

            ART="backend-${GIT_SHA}.zip"
            rm -f "$ART"
            zip -r "$ART" app requirements.txt \
              -x "*.pyc" -x "__pycache__/*" -x ".venv/*"

            ls -lh "$ART"
          '''
        }
      }
    }

    stage('Frontend: build + package') {
      steps {
        dir('platformops-frontend') {
          sh '''
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
        sh '''
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
  }
}
