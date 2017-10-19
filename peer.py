"""AWS VPC Peering connector."""

import boto3
import botocore
import yaml
REGION = 'eu-central-1'
VERIFY = False
SSL = True

def assume_role(**args):
    client = boto3.client('sts',use_ssl=SSL, verify=VERIFY)
    response = client.assume_role(**args)
    return boto3.Session(region_name='eu-central-1',
        aws_access_key_id=response['Credentials']['AccessKeyId'],
        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
        aws_session_token=response['Credentials']['SessionToken'])

with open('./config.yml', 'r') as file:
    config = yaml.load(file)

for peer in config['peer']:

    from_peer = peer['from']
    to_peer = peer['to']
    from_session =  assume_role(RoleArn=from_peer['role'],
                                RoleSessionName='Peering_from-Session')

    #from_session = boto3.Session(
    #    profile_name=from_peer['profile'],
    #    region_name=REGION
    #)
    print """Peering from VPC {} ({}) """.format(
            from_peer['vpc-id'],
            from_peer['role']
        )
    from_client = from_session.client('ec2',use_ssl=SSL, verify=VERIFY)
    from_resource = from_session.resource('ec2',use_ssl=SSL, verify=VERIFY)
    
    for to in to_peer:
        to_session = assume_role(RoleArn=to['role'],
                                RoleSessionName='Peering_from-Session')
		#= boto3.Session(
        #    profile_name=to['profile'],
        #    region_name=REGION
        #)
        to_client = to_session.client('ec2',use_ssl=SSL, verify=VERIFY)
        to_resource = to_session.resource('ec2',use_ssl=SSL, verify=VERIFY)
        to_account = to_session.client('sts',use_ssl=SSL, verify=VERIFY).get_caller_identity().get('Account')
				
        print """Peering from VPC {} ({}) to {} in {}""".format(
            from_peer['vpc-id'],
            from_peer['role'],
            to['vpc-id'],
            to['role']
        )
        try:
            from_vpc = from_resource.Vpc(
                from_peer['vpc-id']
            )
            to_vpc = to_resource.Vpc(
                to['vpc-id']
            )
            print from_vpc.cidr_block
            print to_vpc.cidr_block
            from_name = [
                n for n in from_vpc.tags if n['Key'] == 'Name'
            ][0]['Value']

            to_name = [
                n for n in to_vpc.tags if n['Key'] == 'Name'
            ][0]['Value']

            response = from_client.create_vpc_peering_connection(
                DryRun=False,
                VpcId=from_peer['vpc-id'],
                PeerVpcId=str(to['vpc-id']),
                PeerOwnerId=str(to_account)
            )

            connectionId = response[
                'VpcPeeringConnection'
            ]['VpcPeeringConnectionId']
            tags = [
                {
                    'Key': 'Name',
                    'Value': '{}---{}'.format(from_name, to_name)
                }
            ]
            from_client.create_tags(
                Resources=[connectionId],
                Tags=tags
            )
            to_client.create_tags(
                Resources=[connectionId],
                Tags=tags
            )
            target = to_client.accept_vpc_peering_connection(
                VpcPeeringConnectionId=connectionId
            )

            for table in from_vpc.route_tables.all():
                print table.create_route(
                    DryRun=False,
                    DestinationCidrBlock=to_vpc.cidr_block,
                    VpcPeeringConnectionId=connectionId
                )
                print "RouteTable {} updated with route".format(table.route_table_id)

            for table in to_vpc.route_tables.all():
                print table.create_route(
                    DryRun=False,
                    DestinationCidrBlock=from_vpc.cidr_block,
                    VpcPeeringConnectionId=connectionId
                )

                print "RouteTable {} updated with route".format(table.route_table_id)

        except Exception as e:
            print e
