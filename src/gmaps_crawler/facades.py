import logging
from dataclasses import asdict
from typing import TypedDict

import boto3
from mypy_boto3_sqs.type_defs import SendMessageResultTypeDef

from entities import Place
from exceptions import CantEmitPlace

logger = logging.getLogger(__name__)


class SQSMessageFormat(TypedDict):
    body: str
    attributes: dict


class SQSEmitter:
    def __init__(self, queue_url: str):
        self.client = boto3.client("sqs")
        self.queue_url = queue_url

    def emit(self, place: Place):
        try:
            message = self._create_message(place)
            self._send_message(message)
        except Exception as ex:
            logger.exception("[red]Failed to emit place[/] %s to SQS", place, extra={"markup": True})
            raise CantEmitPlace(place, self.queue_url) from ex
        else:
            logger.info("Emitted place %s to SQS", place)

    def _create_message(self, place: Place) -> SQSMessageFormat:
        body = str(asdict(place))
        return dict(
            body=body,
            attributes=dict(
                place_id={
                    "DataType": "String",
                    "StringValue": place.identifier,
                }
            ),
        )

    def _send_message(self, message: SQSMessageFormat) -> SendMessageResultTypeDef:
        response = self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=message["body"],
            MessageAttributes=message["attributes"],
        )
        return response
