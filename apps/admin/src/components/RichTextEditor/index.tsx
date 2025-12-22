import { useRef } from 'react';
import { Editor } from '@tinymce/tinymce-react';
import type { IAllProps } from '@tinymce/tinymce-react';

// 邮件模板常用变量
export const EMAIL_TEMPLATE_VARIABLES = [
  { label: '患者姓名', value: 'patient_name' },
  { label: '医生姓名', value: 'doctor_name' },
  { label: '科室名称', value: 'department_name' },
  { label: '预约日期', value: 'appointment_date' },
  { label: '预约时间', value: 'appointment_time' },
  { label: '预约编号', value: 'appointment_no' },
  { label: '医院名称', value: 'hospital_name' },
  { label: '医院电话', value: 'hospital_phone' },
];

interface RichTextEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  height?: number;
  placeholder?: string;
  variables?: { label: string; value: string }[];
  disabled?: boolean;
}

// 获取 TinyMCE Editor 类型
type TinyMCEEditorInstance = Parameters<NonNullable<IAllProps['onInit']>>[1];

const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  height = 400,
  placeholder = '请输入内容...',
  variables,
  disabled = false,
}) => {
  const editorRef = useRef<TinyMCEEditorInstance | null>(null);

  const handleEditorChange = (content: string) => {
    onChange?.(content);
  };

  // 根据是否有变量配置来决定工具栏
  const baseToolbar = 'undo redo | blocks | bold italic underline strikethrough | forecolor backcolor | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image table | code preview fullscreen';
  const toolbar = variables?.length ? `${baseToolbar} | insertvariable` : baseToolbar;

  // 获取 TinyMCE API Key
  const apiKey = process.env.TINYMCE_API_KEY || 'no-api-key';

  return (
    <Editor
      tinymceScriptSrc={`https://cdn.tiny.cloud/1/${apiKey}/tinymce/7/tinymce.min.js`}
      onInit={(_evt: unknown, editor: TinyMCEEditorInstance) => {
        editorRef.current = editor;
      }}
      value={value}
      onEditorChange={handleEditorChange}
      disabled={disabled}
      init={{
        height,
        placeholder,
        menubar: false,
        language: 'zh_CN',
        plugins: 'lists link image table code preview fullscreen wordcount',
        toolbar,
        toolbar_mode: 'sliding',
        branding: false,
        promotion: false,
        statusbar: true,
        elementpath: false,
        resize: true,
        content_style: `
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            padding: 12px;
          }
          p { margin: 0 0 10px 0; }
        `,
        setup: (editor: TinyMCEEditorInstance) => {
          // 添加变量插入按钮
          if (variables?.length) {
            editor.ui.registry.addMenuButton('insertvariable', {
              text: '插入变量',
              tooltip: '插入模板变量',
              fetch: (callback: (items: Array<{ type: 'menuitem'; text: string; onAction: () => void }>) => void) => {
                const items = variables.map((v) => ({
                  type: 'menuitem' as const,
                  text: v.label,
                  onAction: () => {
                    editor.insertContent(`<span style="color: #1890ff; font-weight: bold;">{{${v.value}}}</span>&nbsp;`);
                  },
                }));
                callback(items);
              },
            });
          }
        },
      }}
    />
  );
};

export default RichTextEditor;

