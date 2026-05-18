import { Helmet } from 'react-helmet-async';

interface SEOProps {
  title?: string;
  description?: string;
  keywords?: string;
  image?: string;
  url?: string;
  type?: string;
}

const SITE_NAME = '医院挂号系统';
const DEFAULT_DESCRIPTION = '一套完整的 SaaS 多租户医院预约挂号系统，支持多门店、多科室、多医生排班，覆盖机构端、患者端、医生端全场景。';
const DEFAULT_IMAGE = '/og-image.png';
const SITE_URL = 'https://appointment.example.com';

export function SEO({
  title,
  description = DEFAULT_DESCRIPTION,
  keywords = '医院挂号,预约挂号,门诊预约,SaaS,多租户,排班管理',
  image = DEFAULT_IMAGE,
  url,
  type = 'website',
}: SEOProps) {
  const fullTitle = title ? `${title} | ${SITE_NAME}` : SITE_NAME;
  const fullUrl = url ? `${SITE_URL}${url}` : SITE_URL;
  const fullImage = image.startsWith('http') ? image : `${SITE_URL}${image}`;

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={description} />
      <meta name="keywords" content={keywords} />

      {/* Open Graph */}
      <meta property="og:type" content={type} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={fullImage} />
      <meta property="og:url" content={fullUrl} />
      <meta property="og:site_name" content={SITE_NAME} />

      {/* Twitter Card */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={fullImage} />

      <link rel="canonical" href={fullUrl} />
    </Helmet>
  );
}
