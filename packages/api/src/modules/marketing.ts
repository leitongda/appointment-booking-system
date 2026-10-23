import request from '../request';

/**
 * 海报小程序码请求参数
 */
export interface PosterQrcodeParams {
  /** 小程序码 scene 参数（医生 UUID 去连字符的 32 位十六进制，微信 scene 上限 32 字符；落地页解析后还原为医生ID） */
  scene: string;
  /** 小程序页面路径（如 packageBooking/pages/doctor/detail，须为 app.json 已发布的页面） */
  page: string;
}

/**
 * 海报小程序码响应（契约：{ image }，image 为小程序码图片，可能是 data URL 或 http 地址）
 */
export interface PosterQrcodeResult {
  image: string;
}

/**
 * 营销相关接口
 */
export const marketingApi = {
  /**
   * 获取海报用小程序码
   * GET /marketing/poster-qrcode?scene=&page=
   */
  getPosterQrcode: (params: PosterQrcodeParams): Promise<PosterQrcodeResult> => {
    return request.get('/marketing/poster-qrcode', {
      params: {
        scene: params.scene,
        page: params.page,
      },
    });
  },
};

/**
 * 获取海报用小程序码（独立导出，便于按需引入）
 * GET /marketing/poster-qrcode?scene=&page=
 */
export const getPosterQrcode = (params: PosterQrcodeParams): Promise<PosterQrcodeResult> => {
  return marketingApi.getPosterQrcode(params);
};
