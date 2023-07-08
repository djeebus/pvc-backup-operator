import kopf
import logging

from pvcbackupoperator import annotations
from pvcbackupoperator.processor import Processor

processor = Processor()


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    pass


@kopf.on.create('persistentvolumeclaims', annotations={
    annotations.enable: 'true',
})
def on_pvc_created(body, **kwargs):
    logging.debug(f'a pvc was modified: {body}')
    processor.on_pvc_created(body)


@kopf.on.update('persistentvolumeclaims', annotations={
    annotations.enable: 'true',
})
def on_pvc_modified(body, **kwargs):
    logging.debug(f'a pvc was modified: {body}')
    processor.on_pvc_modified(body)


@kopf.on.delete('persistentvolumeclaims', annotations={
    annotations.enable: 'true',
})
def on_pvc_deleted(body, **kwargs):
    logging.debug(f'a pvc was deleted: {body}')
    processor.on_pvc_deleted(body)
