import { uploadApi } from '@hospital/api';
import SharedImageUpload from '@hospital/shared/components/ImageUpload';
import type { ImageUploadProps } from '@hospital/shared/components/ImageUpload';

const ImageUpload = (props: ImageUploadProps) => (
  <SharedImageUpload
    onUpload={(file: File, folder?: string) => uploadApi.upload(file, { folder })}
    onTransferUrl={(url: string, folder?: string) => uploadApi.transfer(url, folder)}
    {...props}
  />
);

export default ImageUpload;
export type { ImageUploadProps } from '@hospital/shared/components/ImageUpload';
