import Taro from '@tarojs/taro';

const SUBSCRIBE_TEMPLATES = {
  appointmentSuccess: '',
  appointmentReminder: '',
  queueCall: '',
};

export function useSubscribeMessage() {
  const requestSubscribe = async (templateIds: string[]) => {
    try {
      const res = await Taro.requestSubscribeMessage({
        tmplIds: templateIds,
      } as Parameters<typeof Taro.requestSubscribeMessage>[0]);
      return res;
    } catch (error) {
      console.warn('订阅消息授权失败:', error);
      return null;
    }
  };

  const subscribeAppointment = async () => {
    const ids = [
      SUBSCRIBE_TEMPLATES.appointmentSuccess,
      SUBSCRIBE_TEMPLATES.appointmentReminder,
      SUBSCRIBE_TEMPLATES.queueCall,
    ].filter(Boolean);
    if (ids.length > 0) {
      return requestSubscribe(ids);
    }
  };

  return { requestSubscribe, subscribeAppointment };
}
