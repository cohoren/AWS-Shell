

class DeleteAMIOperation(object):
    def __init__(self, instance_service, ec2_storage_service, security_group_service):
        """
        :param instance_service:
        :param EC2StorageService ec2_storage_service:
        :param SecurityGroupService security_group_service:
        """
        self.instance_service = instance_service
        self.ec2_storage_service = ec2_storage_service
        self.security_group_service = security_group_service

    def delete_instance(self, logger, ec2_session, instance_id):
        """
        Will terminate the instance
        :param logger: Logger
        :type logger: logging.Logger
        :param ec2_session: ec2 session
        :param instance_id: the id if the instance
        :type instance_id: str
        :return:
        """
        logger.info('Loading ami instance: {0}'.format(instance_id))
        instance = self.instance_service.get_instance_by_id(ec2_session, instance_id)

        logger.info('Terminating ami instance: {0}'.format(instance_id))
        instance = self.instance_service.terminate_instance(instance)
        logger.info('Ami instance: {0}, Terminated'.format(instance_id))

        logger.info('Deleting security groups for ami instance: {0}'.format(instance_id))
        self.security_group_service.delete_all_security_groups_of_instance(instance)
        return True
