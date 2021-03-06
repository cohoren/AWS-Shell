from unittest import TestCase
from mock import Mock

from cloudshell.cp.aws.domain.ami_management.operations.refresh_ip_operation import RefreshIpOperation


class TestRefreshIpOperation(TestCase):
    def setUp(self):
        self.ec2_session = Mock()
        self.refresh_ip_operation = RefreshIpOperation()
        self.instance = Mock()
        self.cloudshell_session = Mock()

        self.cloudshell_session.SetAttributeValue = Mock()
        self.cloudshell_session.UpdateResourceAddress = Mock()

        self.ec2_session = Mock()

    def test_delete_operation(self):
        instance_id = "some instance id"
        current_private_ip = "1.0.0.0"
        current_public_ip = "2.0.0.0"
        resource_name = "deployed resource"
        instance = Mock()
        instance.private_ip_address = "1.0.0.1"
        instance.public_ip_address = "2.0.0.1"

        self.ec2_session.Instance = Mock(return_value=instance)

        self.refresh_ip_operation.refresh_ip(cloudshell_session=self.cloudshell_session,
                                             ec2_session=self.ec2_session,
                                             deployed_instance_id=instance_id,
                                             public_ip_on_resource=current_public_ip,
                                             private_ip_on_resource=current_private_ip,
                                             resource_fullname=resource_name)

        self.cloudshell_session.UpdateResourceAddress.assert_called_with(resource_name, instance.private_ip_address)

        self.cloudshell_session.SetAttributeValue.assert_called_with(resource_name, 'Public IP',
                                                                     instance.public_ip_address)
