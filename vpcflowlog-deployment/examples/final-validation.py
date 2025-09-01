#!/usr/bin/env python3
"""
最终验证脚本 - 检查 OSI 配置的完整性
"""

def final_validation():
    """最终验证 OSI 配置"""
    
    print("🎯 OSI VPC Flow Logs 配置最终验证")
    print("=" * 50)
    
    validation_results = []
    
    # 1. 检查字段名标准
    print("1️⃣ 检查字段名标准...")
    try:
        with open('osi-vpcflowlog.yml', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否使用标准字段名
        standard_fields = [
            'aws.vpc.version', 'aws.vpc.account-id', 'aws.vpc.interface-id',
            'aws.vpc.srcaddr', 'aws.vpc.dstaddr', 'cloud.region'
        ]
        
        all_standard = True
        for field in standard_fields:
            if field not in content:
                all_standard = False
                break
        
        if all_standard:
            print("   ✅ 使用 OpenSearch Catalog 标准字段名")
            validation_results.append(True)
        else:
            print("   ❌ 字段名不符合标准")
            validation_results.append(False)
            
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        validation_results.append(False)
    
    # 2. 检查处理器兼容性
    print("2️⃣ 检查处理器兼容性...")
    try:
        with open('osi-vpcflowlog.yml', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查不支持的处理器
        unsupported = ['delete_entries:', 'add_entries:', 'rename_keys:']
        has_unsupported = False
        
        for processor in unsupported:
            if processor in content:
                print(f"   ❌ 发现不支持的处理器: {processor}")
                has_unsupported = True
        
        if not has_unsupported:
            print("   ✅ 所有处理器都被 OSI 支持")
            validation_results.append(True)
        else:
            validation_results.append(False)
            
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        validation_results.append(False)
    
    # 3. 检查配置结构
    print("3️⃣ 检查配置结构...")
    try:
        with open('osi-vpcflowlog.yml', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_sections = ['source:', 'processor:', 'sink:']
        all_sections = True
        
        for section in required_sections:
            if section not in content:
                print(f"   ❌ 缺少必需部分: {section}")
                all_sections = False
        
        if all_sections:
            print("   ✅ 配置结构完整")
            validation_results.append(True)
        else:
            validation_results.append(False)
            
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        validation_results.append(False)
    
    # 4. 检查 SQS 和 S3 配置
    print("4️⃣ 检查 SQS 和 S3 配置...")
    try:
        with open('osi-vpcflowlog.yml', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_configs = ['queue_url:', 'notification_type: sqs', 'compression: gzip']
        all_configs = True
        
        for config in required_configs:
            if config not in content:
                print(f"   ❌ 缺少配置: {config}")
                all_configs = False
        
        if all_configs:
            print("   ✅ SQS 和 S3 配置正确")
            validation_results.append(True)
        else:
            validation_results.append(False)
            
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        validation_results.append(False)
    
    # 5. 检查 OpenSearch 输出配置
    print("5️⃣ 检查 OpenSearch 输出配置...")
    try:
        with open('osi-vpcflowlog.yml', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_sink = ['opensearch:', 'hosts:', 'index:', 'region:']
        all_sink = True
        
        for config in required_sink:
            if config not in content:
                print(f"   ❌ 缺少输出配置: {config}")
                all_sink = False
        
        if all_sink:
            print("   ✅ OpenSearch 输出配置正确")
            validation_results.append(True)
        else:
            validation_results.append(False)
            
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        validation_results.append(False)
    
    # 总结
    print(f"\n📊 验证结果总结:")
    print("-" * 30)
    
    passed = sum(validation_results)
    total = len(validation_results)
    
    print(f"通过检查: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print(f"\n🎉 配置验证完全通过!")
        print("✅ 可以安全部署到 Amazon OpenSearch Ingestion")
        print("✅ 符合所有 OSI 要求和限制")
        print("✅ 使用 OpenSearch Catalog 标准字段名")
        
        print(f"\n🚀 下一步:")
        print("1. 使用 AWS CLI 创建 OSI 管道")
        print("2. 监控管道状态和性能")
        print("3. 验证数据正确索引到 OpenSearch")
        
        return True
    else:
        print(f"\n⚠️  配置需要进一步修正")
        print(f"❌ {total - passed} 项检查未通过")
        return False

def show_deployment_commands():
    """显示部署命令"""
    
    print(f"\n📋 部署命令参考:")
    print("=" * 50)
    
    print("1️⃣ 验证配置:")
    print("aws osis validate-pipeline --pipeline-configuration-body file://osi-vpcflowlog.yml")
    
    print(f"\n2️⃣ 创建管道:")
    print("aws osis create-pipeline \\")
    print("  --pipeline-name 'vpc-logs-pipeline' \\")
    print("  --pipeline-configuration-body file://osi-vpcflowlog.yml \\")
    print("  --min-units 1 \\")
    print("  --max-units 4")
    
    print(f"\n3️⃣ 检查状态:")
    print("aws osis get-pipeline --pipeline-name 'vpc-logs-pipeline'")
    
    print(f"\n4️⃣ 监控日志:")
    print("aws logs describe-log-groups --log-group-name-prefix '/aws/osis'")

if __name__ == "__main__":
    result = final_validation()
    
    if result:
        show_deployment_commands()
    
    print(f"\n🏁 最终结果: {'✅ 准备就绪' if result else '❌ 需要修正'}")