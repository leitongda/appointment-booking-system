/**
 * 权限配置
 * @see https://umijs.org/docs/max/access
 */
export default function access(initialState: { currentUser?: API.User } | undefined) {
  const { currentUser } = initialState ?? {};
  
  return {
    canAdmin: currentUser && currentUser.role === 'ADMIN',
    canDoctor: currentUser && currentUser.role === 'DOCTOR',
  };
}

declare namespace API {
  interface User {
    id: string;
    phone: string;
    name: string;
    avatar?: string;
    role: string;
  }
}

