import { useEffect, useRef, useState } from 'react';
import '@wangeditor/editor/dist/css/style.css';
import { Editor, Toolbar } from '@wangeditor/editor-for-react';
import {
  Boot,
  IDomEditor,
  IDropPanelMenu,
  IEditorConfig,
  IToolbarConfig,
} from '@wangeditor/editor';

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

// 变量插入菜单的 key
const INSERT_VARIABLE_MENU_KEY = 'insertVariable';

// 是否已注册自定义菜单
let isMenuRegistered = false;

// 创建变量插入菜单类
function createInsertVariableMenuClass(
  variables: { label: string; value: string }[],
) {
  class InsertVariableMenu implements IDropPanelMenu {
    title: string;
    tag: string;
    showDropPanel: boolean;
    private $panel: HTMLElement | null = null;
    private currentEditor: IDomEditor | null = null;

    constructor() {
      this.title = '插入变量';
      this.tag = 'button';
      this.showDropPanel = true;
    }

    isActive(): boolean {
      return false;
    }

    getValue(): string | boolean {
      return '';
    }

    isDisabled(editor: IDomEditor): boolean {
      return editor.isDisabled();
    }

    exec(): void {
      // DropPanel menu 不需要实现 exec
    }

    getPanelContentElem(editor: IDomEditor): HTMLElement {
      this.currentEditor = editor;

      // 如果已有缓存的面板，直接返回
      if (this.$panel) {
        return this.$panel;
      }

      // 创建面板容器
      const $panel = document.createElement('div');
      $panel.style.cssText =
        'padding: 8px 0; min-width: 120px; max-height: 300px; overflow-y: auto;';

      // 创建变量列表
      variables.forEach((variable) => {
        const $item = document.createElement('div');
        $item.innerText = variable.label;
        $item.style.cssText = `
          padding: 8px 16px;
          cursor: pointer;
          font-size: 14px;
          color: #333;
          transition: background-color 0.2s;
        `;

        $item.addEventListener('mouseenter', () => {
          $item.style.backgroundColor = '#f5f5f5';
        });

        $item.addEventListener('mouseleave', () => {
          $item.style.backgroundColor = 'transparent';
        });

        $item.addEventListener('click', () => {
          if (this.currentEditor) {
            // 插入变量占位符（带样式）
            this.currentEditor.dangerouslyInsertHtml(
              `<span style="color: #1890ff; font-weight: bold;">{{${variable.value}}}</span>&nbsp;`,
            );
          }
        });

        $panel.appendChild($item);
      });

      this.$panel = $panel;
      return $panel;
    }
  }

  return InsertVariableMenu;
}

// 注册变量插入菜单
function registerVariableMenu(
  variables: { label: string; value: string }[],
): void {
  if (isMenuRegistered) return;

  const InsertVariableMenuClass = createInsertVariableMenuClass(variables);

  Boot.registerMenu({
    key: INSERT_VARIABLE_MENU_KEY,
    factory() {
      return new InsertVariableMenuClass();
    },
  });

  isMenuRegistered = true;
}

const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  height = 400,
  placeholder = '请输入内容...',
  variables,
  disabled = false,
}) => {
  const [editor, setEditor] = useState<IDomEditor | null>(null);
  const isInitialMount = useRef(true);

  // 注册变量菜单（如果有变量配置）
  useEffect(() => {
    if (variables?.length && !isMenuRegistered) {
      registerVariableMenu(variables);
    }
  }, [variables]);

  // 工具栏配置
  const toolbarConfig: Partial<IToolbarConfig> = {
    toolbarKeys: [
      'undo',
      'redo',
      '|',
      'headerSelect',
      '|',
      'bold',
      'italic',
      'underline',
      'through',
      '|',
      'color',
      'bgColor',
      '|',
      'justifyLeft',
      'justifyCenter',
      'justifyRight',
      'justifyJustify',
      '|',
      'bulletedList',
      'numberedList',
      'todo',
      '|',
      'indent',
      'delIndent',
      '|',
      'insertLink',
      'insertImage',
      'insertTable',
      '|',
      'codeBlock',
      'divider',
      '|',
      'fullScreen',
      // 如果有变量配置，添加变量插入菜单
      ...(variables?.length ? ['|', INSERT_VARIABLE_MENU_KEY] : []),
    ],
  };

  // 编辑器配置
  const editorConfig: Partial<IEditorConfig> = {
    placeholder,
    readOnly: disabled,
    MENU_CONF: {},
  };

  // 及时销毁 editor
  useEffect(() => {
    return () => {
      if (editor === null || editor === undefined) return;
      editor.destroy();
      setEditor(null);
    };
  }, [editor]);

  // 处理内容变化
  const handleChange = (newEditor: IDomEditor) => {
    // 跳过初始化时的 onChange 调用
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    const html = newEditor.getHtml();
    // 如果内容为空段落，返回空字符串
    const isEmpty = html === '<p><br></p>' || html === '<p></p>';
    onChange?.(isEmpty ? '' : html);
  };

  return (
    <div
      style={{
        border: '1px solid #d9d9d9',
        borderRadius: '6px',
        overflow: 'hidden',
      }}
    >
      <Toolbar
        editor={editor}
        defaultConfig={toolbarConfig}
        mode="default"
        style={{
          borderBottom: '1px solid #d9d9d9',
          backgroundColor: '#fafafa',
        }}
      />
      <Editor
        defaultConfig={editorConfig}
        value={value}
        onCreated={setEditor}
        onChange={handleChange}
        mode="default"
        style={{ height: `${height}px`, overflowY: 'hidden' }}
      />
    </div>
  );
};

export default RichTextEditor;
