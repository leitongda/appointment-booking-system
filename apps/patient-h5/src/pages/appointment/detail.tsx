import { NavBar, Card, Steps, Button, Dialog } from 'antd-mobile';
import { history, useParams } from 'umi';
import styles from './detail.less';

const { Step } = Steps;

const AppointmentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const handleCancel = async () => {
    const result = await Dialog.confirm({ content: '确定要取消预约吗？' });
    if (result) {
      // TODO: 调用取消 API
    }
  };

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>预约详情</NavBar>

      <Card title="预约信息" className={styles.card}>
        <div className={styles.row}><span>预约单号</span><span>YY20241127001</span></div>
        <div className={styles.row}><span>预约日期</span><span>2024-11-28</span></div>
        <div className={styles.row}><span>就诊时段</span><span>上午 第5号</span></div>
        <div className={styles.row}><span>挂号费</span><span className={styles.fee}>¥50.00</span></div>
      </Card>

      <Card title="就诊人信息" className={styles.card}>
        <div className={styles.row}><span>姓名</span><span>张三</span></div>
        <div className={styles.row}><span>手机号</span><span>138****8888</span></div>
      </Card>

      <Card title="医生信息" className={styles.card}>
        <div className={styles.row}><span>医生</span><span>张医生</span></div>
        <div className={styles.row}><span>职称</span><span>主任医师</span></div>
        <div className={styles.row}><span>科室</span><span>心内科</span></div>
      </Card>

      <Card title="就诊进度" className={styles.card}>
        <Steps current={1} direction="vertical">
          <Step title="已预约" description="2024-11-27 10:00" />
          <Step title="已签到" description="等待签到" />
          <Step title="就诊中" description="" />
          <Step title="已完成" description="" />
        </Steps>
      </Card>

      <div className={styles.footer}>
        <Button block onClick={handleCancel}>取消预约</Button>
        <Button block color="primary">签到</Button>
      </div>
    </div>
  );
};

export default AppointmentDetailPage;

