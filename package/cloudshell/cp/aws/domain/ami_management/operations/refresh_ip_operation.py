class RefreshIpOperation(object):
    public_ip = "Public IP"

    def __init__(self):
        pass

    def refresh_ip(self, cloudshell_session, ec2_session, deployed_instance_id, private_ip_on_resource,
                   public_ip_on_resource, resource_fullname):
        """
        :param public_ip_on_resource:
        :param resource_fullname:
        :param deployed_instance_id:
        :param private_ip_on_resource:
        :param cloudshell_session: CloudShellAPISession
        :param ec2_session : ec2_session
        """

        deployed_instance = ec2_session.Instance(deployed_instance_id)

        public_ip_on_aws = deployed_instance.public_ip_address
        private_ip_on_aws = deployed_instance.private_ip_address

        if public_ip_on_aws != public_ip_on_resource :
            cloudshell_session.SetAttributeValue(resource_fullname, RefreshIpOperation.public_ip,
                                                 public_ip_on_aws if public_ip_on_aws is not None else "")

        if private_ip_on_aws != private_ip_on_resource:
            cloudshell_session.UpdateResourceAddress(resource_fullname, private_ip_on_aws)
