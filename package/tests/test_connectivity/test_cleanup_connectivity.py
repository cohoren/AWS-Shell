from _ast import Eq
from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.conncetivity.operations.cleanup import CleanupConnectivityOperation


class TestCleanupConnectivity(TestCase):
    def setUp(self):
        self.vpc_serv = Mock()
        self.key_pair_serv = Mock()
        self.s3_session = Mock()
        self.ec2_session = Mock()
        self.bucket_name = Mock()
        self.reservation_id = Mock()
        self.cleanup_operation = CleanupConnectivityOperation(self.vpc_serv, self.key_pair_serv)

    def test_cleanup(self):
        vpc = self.vpc_serv.find_vpc_for_reservation()

        self.cleanup_operation.cleanup(ec2_session=self.ec2_session,
                                       s3_session=self.s3_session,
                                       bucket_name=self.bucket_name,
                                       reservation_id=self.reservation_id)

        self.assertTrue(self.vpc_serv.find_vpc_for_reservation.called_with(self.ec2_session, self.reservation_id))
        self.assertTrue(self.key_pair_serv.remove_key_pair_for_reservation.called_with(self.s3_session,
                                                                                       self.bucket_name,
                                                                                       self.reservation_id))
        self.assertTrue(self.vpc_serv.delete_all_instances.called_with(vpc))
        self.assertTrue(self.vpc_serv.remove_all_security_groups.called_with(vpc))
        self.assertTrue(self.vpc_serv.remove_all_subnets.called_with(vpc))
        self.assertTrue(self.vpc_serv.remove_all_peering.called_with(vpc))
        self.assertTrue(self.vpc_serv.delete_vpc.called_with(vpc))

    def test_cleanup_no_vpc(self):
        vpc_serv = Mock()
        vpc_serv.find_vpc_for_reservation = Mock(return_value=None)
        result = CleanupConnectivityOperation(vpc_serv, self.key_pair_serv).cleanup(
                          ec2_session=self.ec2_session,
                          s3_session=self.s3_session,
                          bucket_name=self.bucket_name,
                          reservation_id=self.reservation_id)

        self.assertFalse(result['success'])