import jsonpickle


# from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.common.driver_helper import CloudshellDriverHelper
from cloudshell.cp.aws.domain.ami_management.operations.delete_operation import DeleteAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.deploy_operation import DeployAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.power_operation import PowerOperation
from cloudshell.cp.aws.domain.conncetivity.operations.cleanup import CleanupConnectivityOperation
from cloudshell.cp.aws.domain.conncetivity.operations.prepare import PrepareConnectivityOperation
from cloudshell.cp.aws.domain.deployed_app.operations.app_ports_operation import DeployedAppPortsOperation
from cloudshell.cp.aws.domain.services.ec2.instance import InstanceService
from cloudshell.cp.aws.domain.services.ec2.ebs import EC2StorageService
from cloudshell.cp.aws.domain.services.ec2.instance_credentials import InstanceCredentialsService
from cloudshell.cp.aws.domain.services.ec2.keypair import KeyPairService
from cloudshell.cp.aws.domain.services.ec2.security_group import SecurityGroupService
from cloudshell.cp.aws.domain.services.ec2.subnet import SubnetService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService
from cloudshell.cp.aws.domain.services.parsers.aws_model_parser import AWSModelsParser
from cloudshell.cp.aws.domain.services.parsers.command_result_parser import CommandResultsParser
from cloudshell.cp.aws.domain.services.parsers.custom_param_extractor import VmCustomParamsExtractor
from cloudshell.cp.aws.domain.services.s3.bucket import S3BucketService
from cloudshell.cp.aws.domain.services.session_providers.aws_session_provider import AWSSessionProvider
from cloudshell.cp.aws.domain.services.waiters.instance import InstanceWaiter
from cloudshell.cp.aws.domain.services.waiters.password import PasswordWaiter
from cloudshell.cp.aws.domain.services.waiters.subnet import SubnetWaiter
from cloudshell.cp.aws.domain.services.waiters.vpc import VPCWaiter
from cloudshell.cp.aws.domain.services.waiters.vpc_peering import VpcPeeringConnectionWaiter


class AWSShell(object):
    def __init__(self):
        self.command_result_parser = CommandResultsParser()
        self.cloudshell_context_factory = CloudShellContextFactory()
        self.tag_service = TagService()
        self.ec2_instance_waiter = InstanceWaiter()
        self.instance_service = InstanceService(self.tag_service, self.ec2_instance_waiter)
        self.ec2_storage_service = EC2StorageService()
        self.model_parser = AWSModelsParser()
        self.cloudshell_session_helper = CloudshellDriverHelper()
        self.aws_session_manager = AWSSessionProvider()
        self.password_waiter = PasswordWaiter()
        self.vm_custom_params_extractor = VmCustomParamsExtractor()
        self.ami_credentials_service = InstanceCredentialsService(self.password_waiter)
        self.security_group_service = SecurityGroupService()
        self.subnet_waiter = SubnetWaiter()
        self.subnet_service = SubnetService(self.tag_service, self.subnet_waiter)
        self.s3_service = S3BucketService()
        self.vpc_peering_waiter = VpcPeeringConnectionWaiter()
        self.key_pair_service = KeyPairService(self.s3_service)
        self.vpc_waiter = VPCWaiter()

        self.vpc_service = VPCService(tag_service=self.tag_service,
                                      subnet_service=self.subnet_service,
                                      instance_service=self.instance_service,
                                      vpc_waiter=self.vpc_waiter,
                                      vpc_peering_waiter=self.vpc_peering_waiter,
                                      sg_service=self.security_group_service)
        self.prepare_connectivity_operation = \
            PrepareConnectivityOperation(vpc_service=self.vpc_service,
                                         security_group_service=self.security_group_service,
                                         key_pair_service=self.key_pair_service,
                                         tag_service=self.tag_service)

        self.deploy_ami_operation = DeployAMIOperation(instance_service=self.instance_service,
                                                       ami_credential_service=self.ami_credentials_service,
                                                       security_group_service=self.security_group_service,
                                                       tag_service=self.tag_service,
                                                       vpc_service=self.vpc_service,
                                                       key_pair_service=self.key_pair_service,
                                                       subnet_service=self.subnet_service)

        self.power_management_operation = PowerOperation(instance_service=self.instance_service,
                                                         instance_waiter=self.ec2_instance_waiter)

        self.delete_ami_operation = DeleteAMIOperation(instance_service=self.instance_service,
                                                       ec2_storage_service=self.ec2_storage_service,
                                                       security_group_service=self.security_group_service)

        self.clean_up_operation = CleanupConnectivityOperation(vpc_service=self.vpc_service,
                                                               key_pair_service=self.key_pair_service)

        self.deployed_app_ports_operation = DeployedAppPortsOperation(self.vm_custom_params_extractor)

    def cleanup_connectivity(self, command_context):
        with get_logger_for_driver(command_context) as logger:
            with self.cloudshell_context_factory.create(command_context) as cloudshell_context:
                logger.info('parsing data model')
                aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)

                logger.info('getting aws api sessions')
                ec2_session = self.aws_session_manager.get_ec2_session(logger, cloudshell_context, aws_ec2_resource_model)
                s3_session = self.aws_session_manager.get_s3_session(logger, cloudshell_context, aws_ec2_resource_model)

                logger.info('starting clean up connectivity')
                self.clean_up_operation.cleanup(logger=logger,
                                                ec2_session=ec2_session,
                                                s3_session=s3_session,
                                                bucket_name=aws_ec2_resource_model.key_pairs_location,
                                                reservation_id=command_context.reservation.reservation_id)

    def prepare_connectivity(self, command_context, request):
        """
        Will create a vpc for the reservation and will peer it with the management vpc
        :param command_context: The Command Context
        :param request: The json request
        :type request: str
        :return:
        """
        with get_logger_for_driver(command_context) as logger:
            with self.cloudshell_context_factory.create(command_context) as cloudshell_context:
                logger.info('parsing data model')
                aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)

                logger.info('getting aws api sessions')
                ec2_session = self.aws_session_manager.get_ec2_session(logger, cloudshell_context, aws_ec2_resource_model)
                s3_session = self.aws_session_manager.get_s3_session(logger, cloudshell_context, aws_ec2_resource_model)

                # parse request
                logger.info('parsing prepare connectivity request')
                prepare_connectivity_request = DeployDataHolder(jsonpickle.decode(request))
                prepare_connectivity_request = getattr(prepare_connectivity_request, 'driverRequest', None)
                if not prepare_connectivity_request:
                    logger.error('Invalid prepare connectivity request')
                    raise ValueError('Invalid prepare connectivity request')

                logger.info('Preparing connectivity')
                results = self.prepare_connectivity_operation.prepare_connectivity(
                        logger=logger,
                        ec2_session=ec2_session,
                        s3_session=s3_session,
                        reservation_id=command_context.reservation.reservation_id,
                        aws_ec2_datamodel=aws_ec2_resource_model,
                        request=prepare_connectivity_request)

                return self.command_result_parser.set_command_result({'driverResponse': {'actionResults': results}})

    def deploy_ami(self, command_context, deployment_request):
        """
        Will deploy Amazon Image on the cloud provider
        """
        with get_logger_for_driver(command_context) as logger:
            with self.cloudshell_context_factory.create(command_context) as cloudshell_context:
                logger.info('parsing data model')
                aws_ami_deployment_model, name = self.model_parser.convert_to_deployment_resource_model(deployment_request)

                logger.info('parsing deployment request request')
                aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)

                logger.info('getting aws api sessions')
                ec2_session = self.aws_session_manager.get_ec2_session(logger, cloudshell_context, aws_ec2_resource_model)
                s3_session = self.aws_session_manager.get_s3_session(logger, cloudshell_context, aws_ec2_resource_model)

                reservation_id = command_context.reservation.reservation_id

                logger.info('Deploying AMI')
                deploy_data = self.deploy_ami_operation.deploy(logger=logger,
                                                               ec2_session=ec2_session,
                                                               s3_session=s3_session,
                                                               name=name,
                                                               reservation_id=reservation_id,
                                                               aws_ec2_cp_resource_model=aws_ec2_resource_model,
                                                               ami_deployment_model=aws_ami_deployment_model)

                return self.command_result_parser.set_command_result(deploy_data)

    def power_on_ami(self, command_context):
        """
        Will power on the ami
        :param command_context: RemoteCommandContext
        :return:
        """
        with get_logger_for_driver(command_context) as logger:
            with self.cloudshell_context_factory.create(command_context) as cloudshell_context:
                logger.info('parsing data model')
                aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)

                resource = command_context.remote_endpoints[0]
                data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

                logger.info('getting aws api sessions')
                ec2_session = self.aws_session_manager.get_ec2_session(logger, cloudshell_context, aws_ec2_resource_model)

                logger.info('Powering on ami')
                result = self.power_management_operation.power_on(logger, ec2_session, data_holder.vmdetails.uid)
                cloudshell_context.SetResourceLiveStatus(resource.fullname, "Online", "Active")
                return self.command_result_parser.set_command_result(result)

    def power_off_ami(self, command_context):
        """
        Will power on the ami
        :param command_context: RemoteCommandContext
        :return:
        """
        with get_logger_for_driver(command_context) as logger:
            with self.cloudshell_context_factory.create(command_context) as cloudshell_context:
                logger.info('parsing data model')
                aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
                resource = command_context.remote_endpoints[0]
                data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

                logger.info('getting aws api sessions')
                ec2_session = self.aws_session_manager.get_ec2_session(logger, cloudshell_context, aws_ec2_resource_model)

                logger.info('Powering off ami')
                result = self.power_management_operation.power_off(logger, ec2_session, data_holder.vmdetails.uid)
                cloudshell_context.SetResourceLiveStatus(resource.fullname, "Offline", "Powered Off")
                return self.command_result_parser.set_command_result(result)

    def delete_ami(self, command_context, delete_resource=True):
        """
        Will delete the ami instance
        :param bool delete_resource:
        :param command_context: RemoteCommandContext
        :return:
        """
        with get_logger_for_driver(command_context) as logger:
            with self.cloudshell_context_factory.create(command_context) as cloudshell_context:
                logger.info('parsing data model')
                aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
                resource = command_context.remote_endpoints[0]
                data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

                logger.info('getting aws api sessions')
                ec2_session = self.aws_session_manager.get_ec2_session(logger, cloudshell_context, aws_ec2_resource_model)

                logger.info('Terminating off ami')
                result = self.delete_ami_operation.delete_instance(logger, ec2_session, data_holder.vmdetails.uid)

                # todo this is temporary for the demo
                if delete_resource:
                    cloudshell_context.DeleteResource(resourceFullPath=resource.fullname)

                return self.command_result_parser.set_command_result(result)

    def get_application_ports(self, command_context):
        """
        Will return the application ports in a nicely formated manner
        :param command_context: RemoteCommandContext
        :return:
        """
        with get_logger_for_driver(command_context) as logger:
            logger.info('parsing data model')
            resource = command_context.remote_endpoints[0]
            data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

            logger.info('getting application ports')
            return self.deployed_app_ports_operation.get_formatted_deployed_app_ports(logger,
                                                                                      data_holder.vmdetails.vmCustomParams)