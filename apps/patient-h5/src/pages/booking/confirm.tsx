import { NavBar, Result, Button } from 'antd-mobile';
import { history } from 'umi';
import styles from './confirm.less';

const BookingConfirmPage: React.FC = () => {
  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.push('/home')}>预约结果</NavBar>
      <Result
        status="success"
        title="预约成功"
        description="请按时到院就诊，提前15分钟签到"
      />
      <div className={styles.actions}>
        <Button block onClick={() => history.push('/appointment')}>查看预约</Button>
        <Button block color="primary" onClick={() => history.push('/home')}>返回首页</Button>
      </div>
    </div>
  );
};

export default BookingConfirmPage;

