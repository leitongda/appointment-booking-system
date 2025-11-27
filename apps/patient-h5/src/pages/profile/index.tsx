import { List, Image, Button } from 'antd-mobile';
import { history } from 'umi';
import { RightOutline, UserOutline, FileOutline, MessageOutline, QuestionCircleOutline, SetOutline } from 'antd-mobile-icons';
import styles from './index.less';

const ProfilePage: React.FC = () => {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Image src="" width={64} height={64} fit="cover" style={{ borderRadius: '50%', background: '#eee' }} />
        <div className={styles.userInfo}>
          <div className={styles.userName}>张三</div>
          <div className={styles.userPhone}>138****8888</div>
        </div>
      </div>

      <List className={styles.list}>
        <List.Item prefix={<UserOutline />} onClick={() => history.push('/profile/patient')} arrow>就诊人管理</List.Item>
        <List.Item prefix={<FileOutline />} onClick={() => history.push('/records')} arrow>就诊记录</List.Item>
        <List.Item prefix={<MessageOutline />} arrow>消息通知</List.Item>
      </List>

      <List className={styles.list}>
        <List.Item prefix={<QuestionCircleOutline />} arrow>意见反馈</List.Item>
        <List.Item prefix={<SetOutline />} arrow>设置</List.Item>
      </List>

      <div className={styles.logout}>
        <Button block>退出登录</Button>
      </div>
    </div>
  );
};

export default ProfilePage;

