* Login to AWS from Browser
  * `https://d-9067f507f9.awsapps.com/start/#/?tab=accounts`
* Create / Utilize ECR Repository
  * `aws ecr create-repository --repository-name core-api-dev`
* Enable AWS CLI Tokens
  * ```
    export AWS_ACCESS_KEY_ID=""
    export AWS_SECRET_ACCESS_KEY=""
    export AWS_SESSION_TOKEN=""
    ```
* Login to AWS CLI
  * `aws configure`
  * `aws configure sso`
  * `aws sso login --profile ElevatedDeploymentProvisioner-851725533006`
* Save the Repository URI
  * `851725533006.dkr.ecr.us-east-1.amazonaws.com/core-api-dev`
* Login to Docker
  * `docker login --username AWS -p $(aws ecr get-login-password  --region us-east-1) 851725533006.dkr.ecr.us-east-1.amazonaws.com/core-api-dev`
  * Username is `AWS`
* Build Your Image
  * `docker buildx build --platform linux/arm64 -t core-api-dev:latest .`
* Tag your build
  * `docker tag core-api-dev:latest 851725533006.dkr.ecr.us-east-1.amazonaws.com/core-api-dev:latest`
* Push your image
  * `docker push 851725533006.dkr.ecr.us-east-1.amazonaws.com/core-api-dev:latest`
* Initialize Terraform
  * `terraform init`
* Apply Terraform
  * `terraform apply`
