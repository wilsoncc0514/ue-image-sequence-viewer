import os
import glob
import csv
import tkinter as tk
from tkinter import filedialog, messagebox

def perform_merge(input_folder):
    """执行核心的合并逻辑"""
    file_list = glob.glob(os.path.join(input_folder, "*.csv"))
    if not file_list:
        return False, "选中的文件夹内未找到任何 CSV 文件。"

    # 确定输出路径：与所选文件夹同级，命名为 "文件夹名_merged.csv"
    folder_name = os.path.basename(input_folder)
    parent_dir = os.path.dirname(input_folder)
    output_file = os.path.join(parent_dir, f"{folder_name}_merged.csv")

    all_headers = []
    all_rows = []
    processed_count = 0

    # 第一阶段：收集所有去重的表头，并读取数据
    for file in file_list:
        try:
            with open(file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    for header in reader.fieldnames:
                        if header not in all_headers:
                            all_headers.append(header)
                for row in reader:
                    all_rows.append(row)
            processed_count += 1
        except Exception as e:
            return False, f"读取 {os.path.basename(file)} 时出错: {e}"

    if processed_count == 0:
        return False, "未能成功读取任何文件内容。"

    # 第二阶段：根据汇总后的表头写入新文件
    try:
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_headers)
            writer.writeheader()
            writer.writerows(all_rows)
        
        # 换行格式化成功信息，方便在弹窗中阅读
        success_msg = f"成功合并 {processed_count} 个文件。\n\n保存位置:\n{output_file}"
        return True, success_msg
    except Exception as e:
        return False, f"写入新文件时出错: {e}"

class CSVMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV 批量合并工具")
        
        # 设置窗口大小，并在 macOS 上居中显示
        self.root.geometry("450x220")
        self.root.eval('tk::PlaceWindow . center') 

        self.folder_path = tk.StringVar()

        # UI 布局
        tk.Label(root, text="请选择包含待合并 CSV 文件的文件夹：", font=("Arial", 14)).pack(pady=(25, 10))
        
        frame = tk.Frame(root)
        frame.pack(pady=10)
        
        # 路径显示框
        self.entry = tk.Entry(frame, textvariable=self.folder_path, width=35, state='readonly')
        self.entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # 浏览按钮
        tk.Button(frame, text="浏览...", command=self.select_folder).pack(side=tk.LEFT)

        # 执行按钮
        tk.Button(root, text="开始合并", command=self.start_merge, width=15, height=2).pack(pady=15)

    def select_folder(self):
        # 弹出文件夹选择对话框
        folder = filedialog.askdirectory(title="选择 CSV 文件夹")
        if folder:
            self.folder_path.set(folder)

    def start_merge(self):
        input_folder = self.folder_path.get()
        if not input_folder:
            messagebox.showwarning("提示", "请先点击【浏览】选择一个文件夹。")
            return

        # 禁用主界面，防止重复点击
        self.root.config(cursor="watch")
        self.root.update()

        # 调用合并逻辑
        success, message = perform_merge(input_folder)
        
        # 恢复主界面状态
        self.root.config(cursor="")
        
        # 结果弹窗提示
        if success:
            messagebox.showinfo("合并完成", message)
        else:
            messagebox.showerror("发生错误", message)

if __name__ == "__main__":
    # 初始化 GUI
    root = tk.Tk()
    # macOS 环境下，可以让窗口前置
    os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
    app = CSVMergerApp(root)
    root.mainloop()