import { View, Text, ScrollView } from '@tarojs/components';
import { useRouter } from '@tarojs/taro';
import { useApplyThemeNavigationBar } from '../../../../utils/theme';
import './index.less';

const AgreementPage = () => {
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { type } = router.params;
  
  const isPrivacy = type === 'privacy';
  
  return (
    <View className="agreement-page">
      <ScrollView scrollY className="content">
        {isPrivacy ? (
          <View className="agreement-content">
            <Text className="title">隐私政策</Text>
            <Text className="update-time">更新日期：2025年1月1日</Text>
            <Text className="update-time">生效日期：2025年1月1日</Text>
            
            <View className="section">
              <Text className="section-title">引言</Text>
              <Text className="paragraph">
                欢迎使用医院挂号系统（以下简称"本应用"）。我们非常重视您的个人信息和隐私保护。本隐私政策旨在向您说明我们如何收集、使用、存储和保护您的个人信息。请您仔细阅读本隐私政策，如您对本隐私政策有任何疑问，可通过本政策中的联系方式与我们联系。
              </Text>
            </View>

            <View className="section">
              <Text className="section-title">一、我们收集的信息</Text>
              <Text className="paragraph">
                为了向您提供预约挂号服务，我们可能会收集以下信息：
              </Text>
              <Text className="list-item">1. 账号信息：手机号码、微信授权信息</Text>
              <Text className="list-item">2. 就诊人信息：姓名、身份证号、手机号、性别、与账号持有人关系</Text>
              <Text className="list-item">3. 预约信息：预约科室、医生、时间等就诊相关信息</Text>
              <Text className="list-item">4. 设备信息：设备型号、操作系统版本等</Text>
            </View>

            <View className="section">
              <Text className="section-title">二、信息的使用</Text>
              <Text className="paragraph">
                我们收集的信息将用于以下目的：
              </Text>
              <Text className="list-item">1. 提供预约挂号、就诊提醒等核心服务</Text>
              <Text className="list-item">2. 验证您的身份，确保账号安全</Text>
              <Text className="list-item">3. 改进我们的产品和服务</Text>
              <Text className="list-item">4. 向您发送服务通知和提醒</Text>
            </View>

            <View className="section">
              <Text className="section-title">三、信息的存储与保护</Text>
              <Text className="paragraph">
                我们采取严格的数据安全措施保护您的个人信息，包括但不限于加密存储、访问控制、安全审计等。您的个人信息将存储在中国境内的安全服务器上。
              </Text>
            </View>

            <View className="section">
              <Text className="section-title">四、信息的共享</Text>
              <Text className="paragraph">
                除以下情况外，我们不会与第三方共享您的个人信息：
              </Text>
              <Text className="list-item">1. 获得您的明确同意</Text>
              <Text className="list-item">2. 根据法律法规的要求</Text>
              <Text className="list-item">3. 与医院进行必要的就诊信息对接</Text>
            </View>

            <View className="section">
              <Text className="section-title">五、您的权利</Text>
              <Text className="paragraph">
                您有权访问、更正、删除您的个人信息，也可以撤回您的授权同意。如需行使这些权利，请通过本应用的设置页面操作或联系我们的客服。
              </Text>
            </View>

            <View className="section">
              <Text className="section-title">六、联系我们</Text>
              <Text className="paragraph">
                如您对本隐私政策有任何疑问、意见或建议，请通过以下方式与我们联系：
              </Text>
              <Text className="list-item">客服电话：400-888-8888</Text>
              <Text className="list-item">客服邮箱：privacy@hospital.com</Text>
            </View>
          </View>
        ) : (
          <View className="agreement-content">
            <Text className="title">用户协议</Text>
            <Text className="update-time">更新日期：2025年1月1日</Text>
            <Text className="update-time">生效日期：2025年1月1日</Text>
            
            <View className="section">
              <Text className="section-title">总则</Text>
              <Text className="paragraph">
                欢迎您使用医院挂号系统。在使用本应用之前，请您仔细阅读本用户协议。您使用本应用即表示您已阅读并同意接受本协议的所有条款。
              </Text>
            </View>

            <View className="section">
              <Text className="section-title">一、服务内容</Text>
              <Text className="paragraph">
                本应用为用户提供以下服务：
              </Text>
              <Text className="list-item">1. 在线预约挂号服务</Text>
              <Text className="list-item">2. 就诊人信息管理</Text>
              <Text className="list-item">3. 就诊记录查询</Text>
              <Text className="list-item">4. 预约提醒通知</Text>
              <Text className="list-item">5. 其他相关医疗健康服务</Text>
            </View>

            <View className="section">
              <Text className="section-title">二、用户注册与账号</Text>
              <Text className="paragraph">
                2.1 用户应提供真实、准确、完整的注册信息，并及时更新。
              </Text>
              <Text className="paragraph">
                2.2 用户应妥善保管账号和密码，因账号和密码泄露造成的损失由用户自行承担。
              </Text>
              <Text className="paragraph">
                2.3 用户不得将账号转让或借用给他人使用。
              </Text>
            </View>

            <View className="section">
              <Text className="section-title">三、用户行为规范</Text>
              <Text className="paragraph">
                用户在使用本应用时，应遵守以下规范：
              </Text>
              <Text className="list-item">1. 遵守国家法律法规</Text>
              <Text className="list-item">2. 不得利用本应用从事违法活动</Text>
              <Text className="list-item">3. 不得干扰本应用的正常运行</Text>
              <Text className="list-item">4. 按时就诊，如需取消请提前操作</Text>
              <Text className="list-item">5. 尊重医务人员，维护就诊秩序</Text>
            </View>

            <View className="section">
              <Text className="section-title">四、预约规则</Text>
              <Text className="paragraph">
                4.1 用户预约成功后，请按预约时间到达医院就诊。
              </Text>
              <Text className="paragraph">
                4.2 如需取消预约，请至少提前24小时操作。
              </Text>
              <Text className="paragraph">
                4.3 多次爽约可能影响您后续的预约权限。
              </Text>
            </View>

            <View className="section">
              <Text className="section-title">五、免责声明</Text>
              <Text className="paragraph">
                5.1 本应用仅提供预约挂号服务，不提供医疗诊断服务。
              </Text>
              <Text className="paragraph">
                5.2 因不可抗力或第三方原因导致的服务中断，我们不承担责任。
              </Text>
              <Text className="paragraph">
                5.3 用户因违反本协议造成的损失由用户自行承担。
              </Text>
            </View>

            <View className="section">
              <Text className="section-title">六、协议修订</Text>
              <Text className="paragraph">
                我们有权根据需要修订本协议，修订后的协议将在本应用公布。您继续使用本应用即表示您接受修订后的协议。
              </Text>
            </View>

            <View className="section">
              <Text className="section-title">七、联系方式</Text>
              <Text className="paragraph">
                如您对本协议有任何疑问，请通过以下方式联系我们：
              </Text>
              <Text className="list-item">客服电话：400-888-8888</Text>
              <Text className="list-item">客服邮箱：support@hospital.com</Text>
            </View>
          </View>
        )}
      </ScrollView>
    </View>
  );
};

export default AgreementPage;
