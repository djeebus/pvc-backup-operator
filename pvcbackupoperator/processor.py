import os

import jmespath
import kubernetes
import logging

from pvcbackupoperator import annotations


def _create_cron_job_resource(config, pvc):
    pvc_name = pvc['metadata']['name']
    pvc_namespace = pvc['metadata']['namespace']

    cronjob = {
        'apiVersion': 'v1',
        'kind': 'CronJob',
        'metadata': {
            'name': pvc_name,
            'namespace': pvc_namespace,
        },
        'spec': {
            'jobTemplate': {
                'spec': {
                    'template': {
                        'spec': config['spec']['template']['spec'],
                    },
                },
            },
        },
    }

    env_map = config['spec']['envMap']
    containers = cronjob['spec']['jobTemplate']['spec']['template']['spec']['containers']
    for c in containers:
        env = c.setdefault('env', list())
        for key, path in env_map.items():
            value = jmespath.search(path, pvc)
            env.append({
                'name': key,
                'value': value,
            })

    return cronjob


def _parse_config_name(text: str, default_ns: str):
    parts = text.split('/')
    if len(parts) == 1:
        return default_ns, parts[0]

    if len(parts) == 2:
        return parts[0], parts[1]

    raise Exception(f'failed to parse "{text}"')


def _deep_equal(one, two):
    if type(one) != type(two):
        return False

    if isinstance(one, list):
        if len(one) != len(two):
            return False

        for idx in range(len(one)):
            if _deep_equal(one[idx], two[idx]) is False:
                return False

        return True

    if isinstance(one, dict):
        # we only verify that everything in one is also in two
        # if two has more keys, that's fine
        for key in one:
            if one[key] != two[key]:
                return False

        return True

    return one == two


class Processor:
    def __init__(self):
        self.default_config_name = os.environ.get('PVCBO_DEFAULT_CONFIG_NAME')

        self._batch_client = kubernetes.client.BatchV1Api()
        self._core_client = kubernetes.client.CoreV1Api()
        self._custom_objects = kubernetes.client.CustomObjectsApi()

    @staticmethod
    def _is_bound(pv_or_pvc) -> bool:
        try:
            value = pv_or_pvc['status']['phase']
        except KeyError:
            return False

        return value == 'Bound'

    def on_pvc_created(self, pvc):
        pvc_name = pvc["metadata"]["name"]
        pvc_namespace = pvc["metadata"]["namespace"]
        if self._is_bound(pvc) is False:
            logging.info(f'skipping unbound pvc {pvc_namespace}/{pvc_name}')
            return

        pv_name = pvc['spec']['volumeName']
        pv = self._core_client.read_persistent_volume(pv_name)
        if pv is None:
            logging.error(f'failed to find persistent volume "{pv_name}" for {pvc_namespace}/{pvc_name}')
            return

        self._ensure_cronjob(pvc)

    def on_pvc_modified(self, pvc):
        pvc_name = pvc["metadata"]["name"]
        pvc_namespace = pvc["metadata"]["namespace"]
        if self._is_bound(pvc) is False:
            logging.info(f'skipping unbound pvc {pvc_namespace}/{pvc_name}')
            return

    def on_pvc_deleted(self, pvc):
        self._remove_cronjob(pvc)

    def _ensure_cronjob(self, pvc):
        pvc_name = pvc['metadata']['name']
        pvc_namespace = pvc['metadata']['namespace']

        backup_config_name = pvc['metadata']['annotations'].get(annotations.config_name, self.default_config_name)
        if not backup_config_name:
            logging.warning(f'missing backup config annotation; either add the {annotations.config_name} annotation, or define a default')
            return

        backup_config_namespace, backup_config_name = _parse_config_name(backup_config_name, pvc_namespace)
        backup_config = self._custom_objects.get_namespaced_custom_object(
            'pvcbackup.djeebus.net', 'v1beta1',
            backup_config_namespace,
            'pvcbackupconfigs',
            backup_config_name,
        )
        if backup_config is None:
            logging.warning(f'failed to find backup config "{backup_config_namespace}/{backup_config_name}"')
            return

        new_cron_job = _create_cron_job_resource(backup_config, pvc)
        cron_job = self._batch_client.read_namespaced_cron_job(pvc_name, pvc_namespace)
        if cron_job is None:
            logging.info('cronjob does not exist, creating it')
            self._create_cronjob(new_cron_job)
            logging.info('cronjob created')
        else:
            logging.info('cronjob exists, seeing if it should be updated')
            if _deep_equal(new_cron_job, cron_job) is False:
                logging.info('cronjob needs to be updated')
                self._update_cronjob(new_cron_job, cron_job)
                logging.info('cronjob has been updated')
            else:
                logging.info('cronjob does not need to be updated')

    def _create_cronjob(self, new_cron_job):
        raise NotImplementedError()

    def _update_cronjob(self, cron_job_spec, current_cron_job):
        raise NotImplementedError()

    def _remove_cronjob(self, pvc):
        raise NotImplementedError()
