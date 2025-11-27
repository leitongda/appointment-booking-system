import { NavBar, Result, Button, Card } from 'antd-mobile';
import { history, useSearchParams } from 'umi';
import styles from './confirm.less';

const BookingConfirmPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const appointmentNo = searchParams.get('appointmentNo');

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.push('/home')} backArrow={false}>
        预约结果
      </NavBar>
      
      <Result
        status="success"
        title="预约成功"
        description="请按时到院就诊，提前15分钟到达进行签到"
      />

      <Card className={styles.infoCard}>
        <div className={styles.row}>
          <span>预约单号</span>
          <span className={styles.appointmentNo}>{appointmentNo}</span>
        </div>
        <div className={styles.tips}>
          <div className={styles.tipsTitle}>温馨提示</div>
          <ul>
            <li>请携带本人有效身份证件</li>
            <li>就诊当天请提前15分钟到达医院签到</li>
            <li>如需取消预约，请至少提前2小时操作</li>
            <li>无故爽约超过3次将被加入黑名单</li>
          </ul>
        </div>
      </Card>

      <div className={styles.actions}>
        <Button block onClick={() => history.push('/appointment')}>
          查看预约
        </Button>
        <Button block color="primary" onClick={() => history.push('/home')}>
          返回首页
        </Button>
      </div>
    </div>
  );
};

export default BookingConfirmPage;
