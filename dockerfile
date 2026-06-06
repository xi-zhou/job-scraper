FROM public.ecr.aws/lambda/python:3.12

# Install Python dependencies into the Lambda task root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t ${LAMBDA_TASK_ROOT}

# Copy application code and configs
COPY src ${LAMBDA_TASK_ROOT}/src
COPY lambda_handler.py linkedin.py indeed.py ${LAMBDA_TASK_ROOT}/
COPY config-xi.yaml config-hao.yaml ${LAMBDA_TASK_ROOT}/

# Ensure the non-root Lambda runtime user can read all files (host files may be 0600)
RUN chmod -R a+rX ${LAMBDA_TASK_ROOT}

# Lambda entrypoint
CMD ["lambda_handler.lambda_handler"]