import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import graphviz
from itertools import combinations
import os
import sys
from PIL import Image, ImageTk
import pandas as pd
import re


class FaultTreeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("故障树分析工具")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f0f8ff')

        # 设置默认字体
        self.default_font = ("Microsoft YaHei", 10)  # 使用微软雅黑作为默认字体

        # 设置样式
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f8ff')
        self.style.configure('TButton', font=self.default_font, padding=5)
        self.style.configure('TLabel', background='#f0f8ff', font=self.default_font)
        self.style.configure('Header.TLabel', background='#3a7ca5', foreground='white',
                             font=(self.default_font[0], 12, 'bold'))

        # 创建主框架
        self.main_frame = ttk.Frame(root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧输入面板
        self.input_frame = ttk.LabelFrame(self.main_frame, text="故障树输入", padding=10)
        self.input_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

        # 右侧结果面板
        self.result_frame = ttk.LabelFrame(self.main_frame, text="分析结果", padding=10)
        self.result_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')

        # 配置网格权重
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=2)
        self.main_frame.rowconfigure(0, weight=1)

        # 输入面板内容
        ttk.Label(self.input_frame, text="顶事件名称:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.top_event_var = tk.StringVar(value="系统故障")
        ttk.Entry(self.input_frame, textvariable=self.top_event_var, width=20,
                  font=self.default_font).grid(row=0, column=1, padx=5, pady=5)

        # 添加逻辑表达式输入
        ttk.Label(self.input_frame, text="逻辑表达式:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.logic_expr_text = tk.Text(self.input_frame, width=30, height=3, font=self.default_font)
        self.logic_expr_text.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        self.logic_expr_text.insert(tk.END, "顶事件 = (A and B) or (C and D)")  # 示例表达式

        # 添加表达式示例标签
        ttk.Label(self.input_frame, text="示例: '顶事件 = (A and B) or (C and D)'",
                  font=(self.default_font[0], 9), foreground="gray").grid(row=2, column=0, columnspan=2, sticky='w',
                                                                          padx=5)

        # 添加Excel导入按钮
        ttk.Button(self.input_frame, text="导入Excel", command=self.import_excel).grid(row=3, column=0, padx=5, pady=5,
                                                                                       sticky='w')

        ttk.Label(self.input_frame, text="底事件列表:").grid(row=4, column=0, padx=5, pady=5, sticky='nw')

        # 底事件表格
        columns = ("event", "probability")
        self.event_tree = ttk.Treeview(self.input_frame, columns=columns, show="headings", height=8)
        self.event_tree.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        self.event_tree.heading("event", text="事件名称")
        self.event_tree.heading("probability", text="发生概率")
        self.event_tree.column("event", width=120)
        self.event_tree.column("probability", width=80)

        # 设置表格字体
        style = ttk.Style()
        style.configure("Treeview", font=self.default_font)
        style.configure("Treeview.Heading", font=(self.default_font[0], 10, 'bold'))

        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.input_frame, orient="vertical", command=self.event_tree.yview)
        scrollbar.grid(row=5, column=2, sticky='ns')
        self.event_tree.configure(yscrollcommand=scrollbar.set)

        # 添加示例数据
        self.add_example_events()

        # 按钮框架
        btn_frame = ttk.Frame(self.input_frame)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame, text="添加事件", command=self.add_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="编辑事件", command=self.edit_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除事件", command=self.delete_event).pack(side=tk.LEFT, padx=5)

        # 字体选择
        font_frame = ttk.Frame(self.input_frame)
        font_frame.grid(row=7, column=0, columnspan=2, pady=5, sticky='w')

        ttk.Label(font_frame, text="图形字体:").grid(row=0, column=0, padx=(0, 5))

        self.font_var = tk.StringVar(value="SimHei")  # 默认使用黑体
        fonts = ["SimHei", "SimSun", "KaiTi", "Microsoft YaHei", "FangSong"]
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_var, values=fonts, width=15)
        font_combo.grid(row=0, column=1)

        # 分析按钮
        ttk.Button(self.input_frame, text="生成故障树分析",
                   command=self.analyze_fault_tree,
                   style='TButton').grid(row=8, column=0, columnspan=2, pady=15)

        # 结果面板内容
        # 故障树图形展示
        self.graph_frame = ttk.LabelFrame(self.result_frame, text="故障树图形")
        self.graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 分析结果
        result_text_frame = ttk.Frame(self.result_frame)
        result_text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.result_text = tk.Text(result_text_frame, wrap=tk.WORD, height=10,
                                   font=self.default_font)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 添加示例结果
        self.result_text.insert(tk.END, "分析结果将显示在这里...\n\n")
        self.result_text.insert(tk.END, "1. 顶事件发生概率\n")
        self.result_text.insert(tk.END, "2. 最小割集列表\n")
        self.result_text.insert(tk.END, "3. 故障树结构说明")
        self.result_text.configure(state='disabled')

        # 添加字体提示
        ttk.Label(self.input_frame, text="提示: 如果中文显示异常，请尝试更换字体",
                  foreground="red", font=(self.default_font[0], 9)).grid(row=9, column=0, columnspan=2, pady=5)

    def add_example_events(self):
        example_events = [
            ("A", 0.05),
            ("B", 0.03),
            ("C", 0.02),
            ("D", 0.04),
            ("E", 0.06),
            ("F", 0.01)
        ]

        for event, prob in example_events:
            self.event_tree.insert("", tk.END, values=(event, prob))

    def add_event(self):
        event = simpledialog.askstring("添加底事件", "输入事件名称:")
        if event:
            prob = simpledialog.askfloat("添加底事件", "输入事件发生概率(0-1):",
                                         minvalue=0.0, maxvalue=1.0)
            if prob is not None:
                self.event_tree.insert("", tk.END, values=(event, prob))

    def edit_event(self):
        selected = self.event_tree.selection()
        if not selected:
            messagebox.showwarning("编辑事件", "请先选择一个事件")
            return

        item = selected[0]
        values = self.event_tree.item(item, 'values')

        event = simpledialog.askstring("编辑事件", "修改事件名称:", initialvalue=values[0])
        if event:
            prob = simpledialog.askfloat("编辑事件", "修改事件发生概率(0-1):",
                                         minvalue=0.0, maxvalue=1.0,
                                         initialvalue=float(values[1]))
            if prob is not None:
                self.event_tree.item(item, values=(event, prob))

    def delete_event(self):
        selected = self.event_tree.selection()
        if not selected:
            messagebox.showwarning("删除事件", "请先选择一个事件")
            return
        for item in selected:
            self.event_tree.delete(item)

    def import_excel(self):
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx;*.xls"), ("所有文件", "*.*")]
        )

        if not file_path:
            return

        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)

            # 清除现有数据
            for item in self.event_tree.get_children():
                self.event_tree.delete(item)

            # 添加新数据
            for _, row in df.iterrows():
                event = str(row.iloc[0])  # 第一列为事件名称
                prob = float(row.iloc[1])  # 第二列为概率
                self.event_tree.insert("", tk.END, values=(event, prob))

            messagebox.showinfo("导入成功", f"成功导入 {len(df)} 条记录")

        except Exception as e:
            messagebox.showerror("导入错误", f"导入Excel文件时出错:\n{str(e)}")

    def analyze_fault_tree(self):
        # 获取顶事件
        top_event = self.top_event_var.get()

        # 获取底事件
        events = {}
        for item in self.event_tree.get_children():
            values = self.event_tree.item(item, 'values')
            events[values[0]] = float(values[1])

        if not events:
            messagebox.showerror("错误", "请添加至少一个底事件")
            return

        # 获取逻辑表达式
        logic_expr = self.logic_expr_text.get("1.0", tk.END).strip()

        # 解析逻辑表达式
        try:
            gate_structure = self.parse_logic_expression(logic_expr, top_event)
        except Exception as e:
            messagebox.showerror("解析错误", f"逻辑表达式解析失败:\n{str(e)}")
            return

        # 生成故障树图形
        self.generate_fault_tree(top_event, events, gate_structure)

        # 计算顶事件概率和最小割集
        self.calculate_results(top_event, events, gate_structure)

    def parse_logic_expression(self, expr, top_event_name):
        """解析逻辑表达式为门结构字典"""
        # 移除多余空格
        expr = re.sub(r'\s+', ' ', expr).strip()

        # 检查顶事件名称是否匹配
        if not expr.startswith(f"{top_event_name} = "):
            raise ValueError(f"表达式必须以顶事件名称 '{top_event_name} = ' 开头")

        # 提取表达式部分
        expr_part = expr[len(f"{top_event_name} = "):]

        # 解析门结构
        gate_structure = {"name": top_event_name, "type": "OR", "children": []}

        # 简单解析 - 实际应用中可能需要更复杂的解析器
        if expr_part.startswith("(") and expr_part.endswith(")"):
            expr_part = expr_part[1:-1]

        # 分割顶层OR关系
        or_parts = expr_part.split(' or ')
        if len(or_parts) > 1:
            gate_structure["children"] = [self.parse_gate(part) for part in or_parts]
            return gate_structure

        # 分割顶层AND关系
        and_parts = expr_part.split(' and ')
        if len(and_parts) > 1:
            gate_structure["type"] = "AND"
            gate_structure["children"] = [self.parse_gate(part) for part in and_parts]
            return gate_structure

        # 单个事件
        gate_structure["children"] = [{"type": "BASIC", "name": expr_part}]
        return gate_structure

    def parse_gate(self, expr):
        """解析子表达式为门或基本事件"""
        expr = expr.strip()

        # 如果是括号表达式
        if expr.startswith("(") and expr.endswith(")"):
            expr = expr[1:-1]

            # 检查内部是否包含AND/OR关系
            if ' and ' in expr:
                parts = expr.split(' and ')
                return {
                    "type": "AND",
                    "children": [self.parse_gate(part) for part in parts]
                }
            elif ' or ' in expr:
                parts = expr.split(' or ')
                return {
                    "type": "OR",
                    "children": [self.parse_gate(part) for part in parts]
                }
            else:
                return {"type": "BASIC", "name": expr}

        # 单个事件
        return {"type": "BASIC", "name": expr}

    def generate_fault_tree(self, top_event, events, gate_structure):
        """根据解析的门结构生成故障树图形"""
        # 获取选择的字体
        font_name = self.font_var.get()

        # 创建故障树图形
        graph_attr = {
            'rankdir': 'TB',
            'fontname': font_name,  # 设置图形字体
            'fontsize': '12'
        }

        node_attr = {
            'fontname': font_name,  # 设置节点字体
            'fontsize': '10'
        }

        edge_attr = {
            'fontname': font_name,  # 设置边字体
            'fontsize': '9'
        }

        dot = graphviz.Digraph(comment='Fault Tree',
                               graph_attr=graph_attr,
                               node_attr=node_attr,
                               edge_attr=edge_attr)

        # 递归添加节点和边
        node_counter = {'count': 0}  # 用于生成唯一节点ID

        def add_node(parent_id, gate):
            # 生成唯一节点ID
            node_id = f"node{node_counter['count']}"
            node_counter['count'] += 1

            # 根据门类型设置节点样式
            if gate['type'] == 'BASIC':
                prob = events.get(gate['name'], 0.0)
                dot.node(node_id, f"{gate['name']}\nP={prob:.4f}",
                         shape='box', style='filled', fillcolor='lightcoral')
            else:
                # 门节点
                gate_label = "或门 (OR)" if gate['type'] == 'OR' else "与门 (AND)"
                dot.node(node_id, gate_label,
                         shape='ellipse', style='filled', fillcolor='lightyellow')

            # 添加边
            if parent_id:
                dot.edge(parent_id, node_id)

            # 递归添加子节点
            if 'children' in gate:
                for child in gate['children']:
                    child_id = add_node(node_id, child)

            return node_id

        # 添加顶事件
        dot.node('TOP', f'顶事件: {top_event}',
                 shape='rectangle', style='filled', fillcolor='lightblue')

        # 添加顶部门
        top_gate_id = add_node('TOP', gate_structure)

        # 保存并渲染图形
        try:
            # 设置环境变量确保使用正确的编码
            os.environ["LANG"] = "zh_CN.UTF-8"
            os.environ["LC_ALL"] = "zh_CN.UTF-8"

            # 修复点：移除了 encoding 参数
            dot.render('fault_tree', format='png', cleanup=True)

            # 在GUI中显示图形
            img = Image.open('fault_tree.png')
            img.thumbnail((800, 600))
            photo = ImageTk.PhotoImage(img)

            # 清除旧图像
            for widget in self.graph_frame.winfo_children():
                widget.destroy()

            # 显示新图像
            label = ttk.Label(self.graph_frame, image=photo)
            label.image = photo  # 保持引用
            label.pack(padx=10, pady=10)

        except Exception as e:
            error_msg = f"无法生成故障树图形: {str(e)}\n\n"
            error_msg += "可能的原因:\n"
            error_msg += "1. 未安装Graphviz或未添加到系统PATH\n"
            error_msg += "2. 系统中缺少指定的中文字体\n"
            error_msg += "3. 文件写入权限问题"
            messagebox.showerror("图形生成错误", error_msg)

    def calculate_results(self, top_event, events, gate_structure):
        """计算顶事件概率和最小割集"""

        # 计算顶事件概率
        def calculate_probability(gate):
            if gate['type'] == 'BASIC':
                return events.get(gate['name'], 0.0)

            elif gate['type'] == 'OR':
                p = 1.0
                for child in gate['children']:
                    p *= (1 - calculate_probability(child))
                return 1 - p

            elif gate['type'] == 'AND':
                p = 1.0
                for child in gate['children']:
                    p *= calculate_probability(child)
                return p

        p_top = calculate_probability(gate_structure)

        # 计算最小割集
        def find_cut_sets(gate):
            if gate['type'] == 'BASIC':
                return [[gate['name']]]

            elif gate['type'] == 'OR':
                cut_sets = []
                for child in gate['children']:
                    cut_sets.extend(find_cut_sets(child))
                return cut_sets

            elif gate['type'] == 'AND':
                cut_sets = []
                for child in gate['children']:
                    child_cut_sets = find_cut_sets(child)
                    if not cut_sets:
                        cut_sets = child_cut_sets
                    else:
                        new_cut_sets = []
                        for cs1 in cut_sets:
                            for cs2 in child_cut_sets:
                                new_cut_sets.append(cs1 + cs2)
                        cut_sets = new_cut_sets
                return cut_sets

        # 获取所有割集并最小化
        all_cut_sets = find_cut_sets(gate_structure)
        minimal_cut_sets = []

        # 按长度排序以便最小化
        all_cut_sets.sort(key=len)

        for cut_set in all_cut_sets:
            # 转换为集合以便比较
            cut_set_set = set(cut_set)

            # 检查是否是最小割集
            is_minimal = True
            for existing in minimal_cut_sets:
                if existing.issubset(cut_set_set):
                    is_minimal = False
                    break

            if is_minimal:
                minimal_cut_sets.append(cut_set_set)

        # 转换为列表的列表
        minimal_cut_sets = [list(cs) for cs in minimal_cut_sets]

        # 更新结果文本框
        self.result_text.configure(state='normal')
        self.result_text.delete(1.0, tk.END)

        self.result_text.insert(tk.END, f"故障树分析结果\n", 'header')
        self.result_text.insert(tk.END, f"顶事件: {top_event}\n\n")

        self.result_text.insert(tk.END, "1. 顶事件发生概率:\n", 'subheader')
        self.result_text.insert(tk.END, f"   P({top_event}) = {p_top:.6f}\n\n")

        self.result_text.insert(tk.END, "2. 最小割集:\n", 'subheader')
        if minimal_cut_sets:
            for i, cut_set in enumerate(minimal_cut_sets, 1):
                self.result_text.insert(tk.END, f"   割集 {i}: {' and '.join(cut_set)}\n")
        else:
            self.result_text.insert(tk.END, "   未找到最小割集\n")

        self.result_text.insert(tk.END, "\n3. 故障树结构说明:\n", 'subheader')
        self.result_text.insert(tk.END, f"   顶事件: {top_event}\n")
        self.result_text.insert(tk.END, f"   门类型: {gate_structure['type']}\n")
        self.result_text.insert(tk.END, f"   子节点数: {len(gate_structure.get('children', []))}\n")

        # 添加样式标签
        self.result_text.tag_configure('header', font=(self.default_font[0], 12, 'bold'), foreground='navy')
        self.result_text.tag_configure('subheader', font=(self.default_font[0], 10, 'bold'), foreground='darkblue')

        self.result_text.configure(state='disabled')


if __name__ == "__main__":
    # 设置系统编码为UTF-8
    if sys.platform.startswith('win'):
        import locale

        if locale.getdefaultlocale()[0] is None:
            os.environ["LANG"] = "zh_CN.UTF-8"

    root = tk.Tk()
    app = FaultTreeApp(root)

    root.mainloop()
