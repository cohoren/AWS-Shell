

class CleanupConnectivityOperation(object):
    def __init__(self, vpc_service, key_pair_service):
        """
        :param vpc_service: VPC Service
        :type vpc_service: cloudshell.cp.aws.domain.services.ec2.vpc.VPCService
        :param key_pair_service: Security Group Service
        :type key_pair_service: cloudshell.cp.aws.domain.services.ec2.keypair.KeyPairService
        """
        self.vpc_service = vpc_service
        self.key_pair_service = key_pair_service

    def cleanup(self, logger, ec2_session, s3_session, bucket_name, reservation_id):
        """
        Will clean all the connectivity for the given reservation, also terminate stale deployed AMIs
        :param logger: Logger
        :type logger: logging.Logger
        :param ec2_session: EC2 Resource
        :param s3_session: S3 Resource
        :param bucket_name: The bucket in S3
        :type bucket_name: str
        :param reservation_id: The reservation id
        :type reservation_id: str
        :return:
        """
        logger.info('loading vpc for reservation: {0}, in the bucket: {1}'.format(reservation_id, bucket_name))
        vpc = self.vpc_service.find_vpc_for_reservation(ec2_session, reservation_id)
        if not vpc:
            logger.error('No VPC was created for this reservation: {0}'.format(reservation_id))
            raise ValueError('No VPC was created for this reservation')

        logger.info('Deleting key pair for reservation: {0}'.format(reservation_id))
        self.key_pair_service.remove_key_pair_for_reservation(s3_session, bucket_name, reservation_id)

        logger.info('Deleting all the instances for reservation: {0}'.format(reservation_id))
        self.vpc_service.delete_all_instances(vpc)

        logger.info('Deleting all the security groups for reservation: {0}'.format(reservation_id))
        self.vpc_service.remove_all_security_groups(vpc)

        logger.info('Deleting all the subnets for reservation: {0}'.format(reservation_id))
        self.vpc_service.remove_all_subnets(vpc)

        logger.info('Deleting all the peerings for reservation: {0}'.format(reservation_id))
        self.vpc_service.remove_all_peering(vpc)

        logger.info('Deleting all the vpc for reservation: {0}'.format(reservation_id))
        self.vpc_service.delete_vpc(vpc)