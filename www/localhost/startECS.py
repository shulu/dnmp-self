#!/usr/bin/env python3
# coding=utf-8
import json
import time
import traceback

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkecs.request.v20140526.RunInstancesRequest import RunInstancesRequest
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
import subprocess
import sys


RUNNING_STATUS = 'Running'
CHECK_INTERVAL = 3
CHECK_TIMEOUT = 240
# 实例的资源规格
INSTANCE_TYPE ={
    "4":"ecs.ic5.xlarge",
    "8":"ecs.ic5.2xlarge",
    "12":"ecs.ic5.3xlarge",
}

class AliyunRunInstancesExample(object):
    def __init__(self):
        self.access_id = ''
        self.access_secret = ''

        # 是否只预检此次请求。true：发送检查请求，不会创建实例，也不会产生费用；false：发送正常请求，通过检查后直接创建实例，并直接产生费用
        self.dry_run = False
        # 实例所属的地域ID
        self.region_id = 'cn-hangzhou'
        # 实例的资源规格
        self.instance_type = ''
        # 实例的计费方式
        self.instance_charge_type = 'PostPaid'
        # 镜像ID
        self.image_id = 'm-bp1aijx8hx1f2yirvtak'
        # 指定新创建实例所属于的安全组ID
        self.security_group_id = 'sg-bp1cat2x56tt1yhqkbkq'
        # 购买资源的时长
        self.period = 1
        # 购买资源的时长单位
        self.period_unit = 'Hourly'
        # 实例所属的可用区编号
        self.zone_id = 'cn-hangzhou-h'
        # 网络计费类型
        self.internet_charge_type = 'PayByTraffic'
        # 虚拟交换机ID
        self.vswitch_id = 'vsw-bp1ms3h3cmx7va9lexsoa'
        # 实例名称
        self.instance_name = 'package-tmp.dy.server'
        # 是否使用镜像预设的密码
        self.password_inherit = True
        # 指定创建ECS实例的数量
        self.amount = 1
        # 公网出带宽最大值
        self.internet_max_bandwidth_out = 0
        # 云服务器的主机名
        self.host_name = 'package-tmp-dy-server'
        # 是否为实例名称和主机名添加有序后缀
        self.unique_suffix = True
        self.io_optimized = 'optimized'
        # 系统盘大小
        self.system_disk_size = '40'
        # 系统盘的磁盘种类
        self.system_disk_category = 'cloud_essd'
        # 性能级别
        self.system_disk_performance_level = 'PL0'


    def run(self, params):
        self.instance_type = INSTANCE_TYPE[str(params['vCPU_number'])]
        self.client = AcsClient(self.access_id, self.access_secret, self.region_id)

        try:
            ids = self.run_instances()
            self._check_instances_status(ids)
            # run d
        except ClientException as e:
            print('Fail. Something with your connection with Aliyun go incorrect.'
                  ' Code: {code}, Message: {msg}'
                  .format(code=e.error_code, msg=e.message))
        except ServerException as e:
            print('Fail. Business error.'
                  ' Code: {code}, Message: {msg}'
                  .format(code=e.error_code, msg=e.message))
        except Exception:
            print('Unhandled error')
            print(traceback.format_exc())

    def run_instances(self):
        """
        调用创建实例的API，得到实例ID后继续查询实例状态
        :return:instance_ids 需要检查的实例ID
        """
        request = RunInstancesRequest()

        request.set_DryRun(self.dry_run)

        request.set_InstanceType(self.instance_type)
        request.set_InstanceChargeType(self.instance_charge_type)
        request.set_ImageId(self.image_id)
        request.set_SecurityGroupId(self.security_group_id)
        # request.set_ResourceGroupId(self.resource_group_id)
        request.set_Period(self.period)
        request.set_PeriodUnit(self.period_unit)
        request.set_ZoneId(self.zone_id)
        request.set_InternetChargeType(self.internet_charge_type)
        request.set_VSwitchId(self.vswitch_id)
        request.set_InstanceName(self.instance_name)
        request.set_PasswordInherit(self.password_inherit)
        request.set_Amount(self.amount)
        request.set_InternetMaxBandwidthOut(self.internet_max_bandwidth_out)
        request.set_UniqueSuffix(self.unique_suffix)
        request.set_IoOptimized(self.io_optimized)
        # request.set_SpotStrategy(self.spot_strategy)
        # request.set_AutoReleaseTime(self.auto_release_time)
        request.set_SystemDiskSize(self.system_disk_size)
        request.set_SystemDiskCategory(self.system_disk_category)

        body = self.client.do_action_with_exception(request)
        data = json.loads(body)
        instance_ids = data['InstanceIdSets']['InstanceIdSet']
        print('Success. Instance creation succeed. InstanceIds: {}'.format(', '.join(instance_ids)))
        return instance_ids

    def do_check_instances_status(self,instance_ids):
        self._check_instances_status([instance_ids])

    def _check_instances_status(self, instance_ids):
        """
        每3秒中检查一次实例的状态，超时时间设为3分钟.
        :param instance_ids 需要检查的实例ID
        :return:
        """
        start = time.time()
        while True:
            request = DescribeInstancesRequest()
            request.set_InstanceIds(json.dumps(instance_ids))
            body = self.client.do_action_with_exception(request)
            data = json.loads(body)
            for instance in data['Instances']['Instance']:
                if RUNNING_STATUS in instance['Status']:
                    instance_ids.remove(instance['InstanceId'])
                    print('Instance boot successfully: {}'.format(instance['InstanceId']))
                    ip = instance['VpcAttributes']['PrivateIpAddress']['IpAddress'][0]
                    print('IP:'+ip)
                    time.sleep(30)
                    cmd = subprocess.Popen('sh ./release-prod.sh '+ip+' && ssh -o StrictHostKeyChecking=no root@'+ip+' "echo \'*/1 * * * * /bin/sh /data/www/packages.duoyuhudong.com/fgamepack.sh\' > /tmp/crontab && crontab /tmp/crontab" && sed -i "/^'+ip+'/d" ~/.ssh/known_hosts',
                                                  stdin=subprocess.PIPE, stderr=sys.stderr, close_fds=True,stdout=sys.stdout, universal_newlines=True, shell=True,
                                                  bufsize=1)
                    cmd.communicate()
            if not instance_ids:
                print('Instances all boot successfully')
                break

            if time.time() - start > CHECK_TIMEOUT:
                print('Instances boot failed within {timeout}s: {ids}'
                      .format(timeout=CHECK_TIMEOUT, ids=', '.join(instance_ids)))
                break

            time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    cpu = sys.argv[1]
    if INSTANCE_TYPE.__contains__(str(cpu)) is False:
        print("input vcpu number:4,8,12")
        exit()
    params = {'vCPU_number':cpu}
    AliyunRunInstancesExample().run(params)

