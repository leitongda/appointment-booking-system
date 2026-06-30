export const navigation = {
  push(path: string) {
    window.location.href = path;
  },

  replace(path: string) {
    window.location.replace(path);
  },

  back() {
    window.history.back();
  },
};
