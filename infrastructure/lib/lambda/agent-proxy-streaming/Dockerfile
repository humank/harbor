FROM public.ecr.aws/lambda/provided:al2023

RUN dnf install -y python3.12 python3.12-pip && dnf clean all
RUN python3.12 -m pip install boto3 requests

COPY bootstrap /var/runtime/bootstrap
COPY app.py ${LAMBDA_TASK_ROOT}/app.py

RUN chmod +x /var/runtime/bootstrap

CMD ["app.handler"]
