import { uploadApi } from '@hospital/api';
import { default as SharedImageUpload } from '@hospital/shared/components/ImageUpload';
import type { ImageUploadProps } from '@hospital/shared/components/ImageUpload/types';

const ImageUpload: React.FC<ImageUploadProps> = (props) => (
  <SharedImageUpload
    onUpload={(file, folder) => uploadApi.upload(file, { folder })}
    onTransferUrl={(url, folder) => uploadApi.transfer(url, folder)}
    {...props}
  />
);

export default ImageUpload;
export type { ImageUploadProps } from '@hospital/shared/components/ImageUpload/types';
