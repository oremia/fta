import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import graphviz
import os
import sys
from PIL import Image, ImageTk
import pandas as pd
import re
from fpdf import FPDF
import datetime
import locale
import collections
import threading


class FaultTreeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("故障树分析工具")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f0f8ff')

        # 设置默认字体
        self.default_font = ("Microsoft YaHei", 10)

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
        self.top_event_var = tk.StringVar(value="T")
        ttk.Entry(self.input_frame, textvariable=self.top_event_var, width=20,
                  font=self.default_font).grid(row=0, column=1, padx=5, pady=5)

        # 添加逻辑表达式输入
        ttk.Label(self.input_frame, text="逻辑表达式:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.logic_expr_text = tk.Text(self.input_frame, width=30, height=5, font=self.default_font)
        self.logic_expr_text.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        self.logic_expr_text.insert(tk.END, "T = A and B\nA = C and D\nB = E and F")

        # 添加表达式示例标签
        ttk.Label(self.input_frame, text="格式: '事件 = 表达式' (每行一个定义)",
                  font=(self.default_font[0], 9), foreground="gray").grid(row=2, column=0, columnspan=2, sticky='w',
                                                                          padx=5)

        # 添加Excel导入按钮
        ttk.Button(self.input_frame, text="导入Excel", command=self.import_excel).grid(row=3, column=0, padx=5, pady=5,
                                                                                       sticky='w')

        # 添加导入格式提示
        ttk.Label(self.input_frame,
                  text="Excel格式: 事件名称, 概率 (仅底事件)",
                  font=(self.default_font[0], 8), foreground="gray").grid(row=3, column=1, padx=5, sticky='w')

        ttk.Label(self.input_frame, text="底事件列表:").grid(row=4, column=0, padx=5, pady=5, sticky='nw')

        # 底事件表格
        columns = ("event", "probability")
        self.event_tree = ttk.Treeview(self.input_frame, columns=columns, show="headings", height=5)
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

        # 按钮框架
        btn_frame = ttk.Frame(self.input_frame)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=5)

        ttk.Button(btn_frame, text="添加事件", command=self.add_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="编辑事件", command=self.edit_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除事件", command=self.delete_event).pack(side=tk.LEFT, padx=5)

        # 字体选择
        font_frame = ttk.Frame(self.input_frame)
        font_frame.grid(row=7, column=0, columnspan=2, pady=3, sticky='w')

        ttk.Label(font_frame, text="图形字体:").grid(row=0, column=0, padx=(0, 5))

        self.font_var = tk.StringVar(value="SimHei")
        fonts = ["SimHei", "SimSun", "KaiTi", "Microsoft YaHei", "FangSong"]
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_var, values=fonts, width=15)
        font_combo.grid(row=0, column=1)

        # 分析按钮
        ttk.Button(self.input_frame, text="生成故障树分析",
                   command=self.analyze_fault_tree,
                   style='TButton').grid(row=8, column=0, columnspan=2, pady=5)

        # 保存按钮
        ttk.Button(self.input_frame, text="保存故障树分析",
                   command=self.save_analysis,
                   style='TButton').grid(row=9, column=0, columnspan=2, pady=5)

        # 结果面板内容
        self.graph_frame = ttk.LabelFrame(self.result_frame, text="故障树图形")
        self.graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        result_text_frame = ttk.Frame(self.result_frame)
        result_text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.result_text = tk.Text(result_text_frame, wrap=tk.WORD, height=10,
                                   font=self.default_font)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.result_text.insert(tk.END, "分析结果将显示在这里...")
        self.result_text.configure(state='disabled')

        # 添加字体提示
        ttk.Label(self.input_frame, text="提示: 如果中文显示异常，请尝试更换字体",
                  foreground="red", font=(self.default_font[0], 9)).grid(row=10, column=0, columnspan=2,
                                                                         pady=3)

        # 存储分析结果
        self.analysis_results = {
            "top_event": "",
            "probability": 0.0,
            "minimal_cut_sets": [],
            "structure_description": ""
        }
        self.graph_image_path = "fault_tree.png"
        self.event_hierarchy = {}
        self.event_definitions = {}

        # 进度窗口相关
        self.progress = None
        self.progress_window = None
        self.analysis_thread = None
        self.analysis_canceled = False

        # 添加示例事件
        self.add_example_events()

    def add_example_events(self):
        example_events = [
            ("C", 0.006),
            ("D", 0.005),
            ("E", 0.003),
            ("F", 0.004)
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
            df = pd.read_excel(file_path)
            if df.shape[1] < 1:
                messagebox.showerror("导入错误", "Excel文件必须包含至少一列（事件名称）")
                return

            for item in self.event_tree.get_children():
                self.event_tree.delete(item)

            success_count = 0
            error_rows = []

            for i, row in df.iterrows():
                try:
                    event = str(row.iloc[0]).strip()
                    if not event:
                        raise ValueError("事件名称不能为空")

                    prob = 0.0
                    if df.shape[1] >= 2:
                        prob_value = row.iloc[1]

                        if pd.notna(prob_value):
                            try:
                                prob = float(prob_value)
                            except ValueError:
                                prob = 0.0
                                raise ValueError(f"概率值无效，已设置为0.0: '{prob_value}'")

                            if prob < 0 or prob > 1:
                                raise ValueError(f"概率值必须在0-1之间: {prob}")
                    self.event_tree.insert("", tk.END, values=(event, prob))
                    success_count += 1
                except Exception as e:
                    error_rows.append((i + 1, str(e)))

            if error_rows:
                error_msg = f"成功导入 {success_count} 条记录，以下行导入失败:\n"
                for row_num, error in error_rows:
                    error_msg += f"行 {row_num}: {error}\n"
                messagebox.showwarning("部分导入失败", error_msg)
            else:
                messagebox.showinfo("导入成功", f"成功导入 {success_count} 条记录")

        except Exception as e:
            messagebox.showerror("导入错误", f"导入Excel文件时出错:\n{str(e)}")

    def has_cycle(self, start_event):
        """检测事件定义中是否存在循环依赖"""
        visited = set()
        stack = set()

        def visit(event):
            if event not in self.event_definitions:
                return False

            if event in stack:
                return True
            if event in visited:
                return False

            visited.add(event)
            stack.add(event)

            gate = self.event_definitions[event]
            if 'children' in gate:
                for child in gate['children']:
                    child_name = child['name']
                    # 只检查已定义的事件
                    if child_name in self.event_definitions:
                        if visit(child_name):
                            return True

            stack.remove(event)
            return False

        return visit(start_event)

    def analyze_fault_tree(self):
        # 创建进度窗口
        self.create_progress_window()

        # 在单独的线程中运行分析
        self.analysis_canceled = False
        self.analysis_thread = threading.Thread(target=self.perform_analysis)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()

        # 定期检查线程状态
        self.check_analysis_thread()

    def create_progress_window(self):
        """创建分析进度窗口"""
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("分析中...")
        self.progress_window.geometry("400x150")
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()

        frame = ttk.Frame(self.progress_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="正在分析故障树，请稍候...", font=("Microsoft YaHei", 10)).pack(pady=10)

        self.progress = ttk.Progressbar(frame, orient="horizontal", length=300, mode="indeterminate")
        self.progress.pack(pady=10)
        self.progress.start(10)

        cancel_btn = ttk.Button(frame, text="取消", command=self.cancel_analysis)
        cancel_btn.pack(pady=5)

    def cancel_analysis(self):
        """取消分析过程"""
        self.analysis_canceled = True
        if self.progress_window:
            self.progress_window.destroy()
            self.progress_window = None

        self.result_text.configure(state='normal')
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "分析已取消")
        self.result_text.configure(state='disabled')

    def check_analysis_thread(self):
        """定期检查分析线程状态"""
        if self.analysis_thread.is_alive():
            self.root.after(100, self.check_analysis_thread)
        else:
            if self.progress_window:
                self.progress_window.destroy()
                self.progress_window = None

    def perform_analysis(self):
        """执行实际的分析工作"""
        try:
            # 获取顶事件
            top_event = self.top_event_var.get().strip()
            if not top_event:
                self.root.after(0, lambda: messagebox.showerror("错误", "顶事件名称不能为空"))
                return

            # 获取底事件
            events = {}
            for item in self.event_tree.get_children():
                values = self.event_tree.item(item, 'values')
                event_name = values[0]

                try:
                    prob = float(values[1])
                    if prob < 0 or prob > 1:
                        prob = 0.0
                except ValueError:
                    prob = 0.0

                events[event_name] = prob

            if not events:
                self.root.after(0, lambda: messagebox.showerror("错误", "请添加至少一个底事件"))
                return

            # 获取逻辑表达式
            logic_expr = self.logic_expr_text.get("1.0", tk.END).strip()
            if not logic_expr:
                self.root.after(0, lambda: messagebox.showerror("错误", "逻辑表达式不能为空"))
                return

            # 解析逻辑表达式
            try:
                self.event_definitions = self.parse_event_definitions(logic_expr)
                if top_event not in self.event_definitions:
                    raise ValueError(f"顶事件 '{top_event}' 未在逻辑表达式中定义")
                gate_structure = self.event_definitions[top_event]

                # 检测循环依赖
                if self.has_cycle(top_event):
                    self.root.after(0, lambda: messagebox.showerror("循环依赖错误",
                                                                    "事件定义中存在循环依赖，请检查逻辑表达式"))
                    return

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("解析错误", f"逻辑表达式解析失败:\n{str(e)}"))
                return

            # 检查所有基本事件是否已定义
            missing_events = []
            self.collect_basic_events(gate_structure, events, missing_events)
            if missing_events:
                self.root.after(0, lambda: messagebox.showwarning("缺失事件",
                                                                  f"以下基本事件未在底事件列表中定义: {', '.join(missing_events)}\n请添加这些事件及其概率。"))
                return

            # 生成故障树图形
            self.generate_fault_tree(top_event, events, gate_structure)

            # 计算顶事件概率和最小割集
            self.calculate_results(top_event, events, gate_structure)

        except RecursionError:
            # 处理递归深度错误
            self.root.after(0, self.show_recursion_error)
        except Exception as e:
            self.root.after(0, lambda: self.show_error(f"分析过程中出错:\n{str(e)}"))

    def show_recursion_error(self):
        """显示递归深度错误"""
        self.result_text.configure(state='normal')
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "分析过程中出错: 递归深度超出限制\n\n")
        self.result_text.insert(tk.END, "可能的原因:\n")
        self.result_text.insert(tk.END, "1. 故障树结构太深或太复杂\n")
        self.result_text.insert(tk.END, "2. 逻辑表达式中存在循环引用\n")
        self.result_text.insert(tk.END, "3. 系统递归深度限制不足\n\n")
        self.result_text.insert(tk.END, "解决方案建议:\n")
        self.result_text.insert(tk.END, "- 简化故障树结构\n")
        self.result_text.insert(tk.END, "- 检查逻辑表达式中的循环引用\n")
        self.result_text.configure(state='disabled')

    def collect_basic_events(self, gate, events, missing_events):
        """递归收集所有基本事件"""
        if gate['type'] == 'BASIC':
            if gate['name'] not in events:
                missing_events.append(gate['name'])
        else:
            for child in gate.get('children', []):
                if child['name'] in self.event_definitions:
                    self.collect_basic_events(self.event_definitions[child['name']], events, missing_events)
                else:
                    self.collect_basic_events(child, events, missing_events)

    def parse_event_definitions(self, expr):
        """解析多行事件定义"""
        event_definitions = {}
        lines = expr.splitlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = re.match(r'^\s*(\w+)\s*=\s*(.+)$', line)
            if not match:
                raise ValueError(f"无效的事件定义格式: '{line}'")

            event_name = match.group(1)
            expr_part = match.group(2).strip()
            event_definitions[event_name] = self.parse_expression(expr_part, event_name)

        return event_definitions

    def parse_expression(self, expr, event_name):
        """解析表达式为门结构"""
        expr = re.sub(r'\s+', ' ', expr).strip()

        if expr.startswith("(") and expr.endswith(")"):
            expr = expr[1:-1].strip()

        or_parts = self.split_by_operator(expr, " or ")
        if len(or_parts) > 1:
            return {
                "type": "OR",
                "name": event_name,
                "children": [self.parse_expression(part, f"{event_name}_OR") for part in or_parts]
            }

        and_parts = self.split_by_operator(expr, " and ")
        if len(and_parts) > 1:
            return {
                "type": "AND",
                "name": event_name,
                "children": [self.parse_expression(part, f"{event_name}_AND") for part in and_parts]
            }

        return {
            "type": "BASIC",
            "name": expr
        }

    def split_by_operator(self, expr, operator):
        """按运算符分割表达式"""
        parts = []
        current = []
        paren_count = 0
        tokens = expr.split()

        for token in tokens:
            if token == "(":
                paren_count += 1
            elif token == ")":
                paren_count -= 1

            if paren_count == 0 and token == operator.strip():
                parts.append(" ".join(current))
                current = []
            else:
                current.append(token)

        parts.append(" ".join(current))
        return [p.strip() for p in parts if p.strip()]

    def generate_fault_tree(self, top_event, events, gate_structure):
        """生成故障树图形 - 使用迭代方法替代递归"""
        if self.analysis_canceled:
            return

        font_name = self.font_var.get()

        graph_attr = {
            'rankdir': 'TB',
            'fontname': font_name,
            'fontsize': '12'
        }

        node_attr = {
            'fontname': font_name,
            'fontsize': '10'
        }

        edge_attr = {
            'fontname': font_name,
            'fontsize': '9'
        }

        dot = graphviz.Digraph(comment='Fault Tree',
                               graph_attr=graph_attr,
                               node_attr=node_attr,
                               edge_attr=edge_attr)

        # 使用栈替代递归
        stack = collections.deque()
        self.event_hierarchy = {}
        node_counter = 0

        # 添加顶事件
        dot.node('TOP', f'顶事件: {top_event}',
                 shape='rectangle', style='filled', fillcolor='lightblue')

        # 添加顶部门
        stack.append(('TOP', gate_structure, 0))

        while stack and not self.analysis_canceled:
            parent_id, gate, level = stack.pop()

            # 创建节点ID
            node_id = f"node{node_counter}"
            node_counter += 1
            self.event_hierarchy[gate['name']] = level

            # 创建节点
            if gate['type'] == 'BASIC':
                prob = events.get(gate['name'], 0.0)
                dot.node(node_id, f"{gate['name']}\nP={prob:.4f}",
                         shape='box', style='filled', fillcolor='lightcoral')
            else:
                gate_label = "或门 (OR)" if gate['type'] == 'OR' else "与门 (AND)"
                dot.node(node_id, f"{gate_label}\n{gate['name']}",
                         shape='ellipse', style='filled', fillcolor='lightyellow')

            # 添加边
            dot.edge(parent_id, node_id)

            # 添加子节点到栈中
            if 'children' in gate:
                # 反转子节点列表，以便按顺序处理
                children = list(reversed(gate['children']))
                for child in children:
                    if child['name'] in self.event_definitions:
                        stack.append((node_id, self.event_definitions[child['name']], level + 1))
                    else:
                        stack.append((node_id, child, level + 1))

        # 保存并渲染图形
        try:
            os.environ["LANG"] = "zh_CN.UTF-8"
            os.environ["LC_ALL"] = "zh_CN.UTF-8"

            dot.render('fault_tree', format='png', cleanup=True)

            img = Image.open('fault_tree.png')
            max_width = 800
            max_height = 600
            img.thumbnail((max_width, max_height))
            photo = ImageTk.PhotoImage(img)

            # 在主线程中更新UI
            self.root.after(0, lambda: self.update_graph(photo))

        except Exception as e:
            error_msg = f"无法生成故障树图形: {str(e)}\n\n可能的原因:\n"
            error_msg += "1. 未安装Graphviz或未添加到系统PATH\n"
            error_msg += "2. 系统中缺少指定的中文字体\n"
            error_msg += "3. 文件写入权限问题"
            self.root.after(0, lambda: messagebox.showerror("图形生成错误", error_msg))

    def update_graph(self, photo):
        """在主线程中更新图形显示"""
        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        label = ttk.Label(self.graph_frame, image=photo)
        label.image = photo
        label.pack(padx=10, pady=10)

    def calculate_results(self, top_event, events, gate_structure):
        """计算顶事件概率和最小割集 - 使用迭代方法替代递归"""
        if self.analysis_canceled:
            return

        # 使用迭代方法计算概率
        def calculate_probability_iterative(gate):
            """使用迭代方法计算事件概率"""
            # 后序遍历栈
            stack = []
            # 结果缓存
            cache = {}
            # 访问标记
            visited = set()

            # 初始节点入栈
            stack.append(gate)

            while stack:
                current = stack[-1]

                # 如果当前节点是基本事件，直接计算
                if current['type'] == 'BASIC':
                    cache[current['name']] = events.get(current['name'], 0.0)
                    visited.add(current['name'])
                    stack.pop()
                    continue

                # 如果当前节点在缓存中，直接使用
                if current['name'] in cache:
                    stack.pop()
                    continue

                # 检查所有子节点是否已计算
                all_children_calculated = True
                children_to_process = []

                for child in current.get('children', []):
                    # 如果子节点是已定义的事件，使用定义
                    child_node = self.event_definitions[child['name']] if child[
                                                                              'name'] in self.event_definitions else child

                    if child_node['name'] not in cache:
                        all_children_calculated = False
                        if child_node['name'] not in visited:
                            stack.append(child_node)
                            visited.add(child_node['name'])
                    else:
                        children_to_process.append(cache[child_node['name']])

                # 如果所有子节点都已计算，计算当前节点
                if all_children_calculated:
                    if current['type'] == 'OR':
                        product = 1.0
                        for p in children_to_process:
                            product *= (1 - p)
                        cache[current['name']] = 1 - product
                    elif current['type'] == 'AND':
                        product = 1.0
                        for p in children_to_process:
                            product *= p
                        cache[current['name']] = product
                    else:
                        cache[current['name']] = 0.0
                    stack.pop()

            return cache.get(gate['name'], 0.0)

        # 使用迭代方法计算最小割集
        def find_cut_sets_iterative(gate):
            """使用迭代方法计算最小割集"""
            # 后序遍历栈
            stack = []
            # 结果缓存
            cache = {}
            # 访问标记
            visited = set()

            # 初始节点入栈
            stack.append(gate)

            while stack:
                current = stack[-1]

                # 如果当前节点是基本事件，直接计算
                if current['type'] == 'BASIC':
                    cache[current['name']] = [[current['name']]]
                    visited.add(current['name'])
                    stack.pop()
                    continue

                # 如果当前节点在缓存中，直接使用
                if current['name'] in cache:
                    stack.pop()
                    continue

                # 检查所有子节点是否已计算
                all_children_calculated = True
                children_cut_sets = []

                for child in current.get('children', []):
                    # 如果子节点是已定义的事件，使用定义
                    child_node = self.event_definitions[child['name']] if child[
                                                                              'name'] in self.event_definitions else child

                    if child_node['name'] not in cache:
                        all_children_calculated = False
                        if child_node['name'] not in visited:
                            stack.append(child_node)
                            visited.add(child_node['name'])
                    else:
                        children_cut_sets.append(cache[child_node['name']])

                # 如果所有子节点都已计算，计算当前节点
                if all_children_calculated:
                    if current['type'] == 'OR':
                        result = []
                        for cut_sets in children_cut_sets:
                            result.extend(cut_sets)
                        cache[current['name']] = result
                    elif current['type'] == 'AND':
                        result = []
                        if children_cut_sets:
                            # 从第一个子节点开始
                            result = children_cut_sets[0]
                            for i in range(1, len(children_cut_sets)):
                                new_result = []
                                for cs1 in result:
                                    for cs2 in children_cut_sets[i]:
                                        new_result.append(cs1 + cs2)
                                result = new_result
                        cache[current['name']] = result
                    else:
                        cache[current['name']] = []
                    stack.pop()

            return cache.get(gate['name'], [])

        try:
            # 计算顶事件概率
            p_top = calculate_probability_iterative(gate_structure)

            # 计算最小割集
            all_cut_sets = find_cut_sets_iterative(gate_structure)
            minimal_cut_sets = []

            # 按长度排序以便更有效地找到最小割集
            all_cut_sets.sort(key=len)

            # 转换为集合以进行子集检查
            all_cut_sets_sets = [set(cs) for cs in all_cut_sets]

            # 找出最小割集
            for i, cut_set in enumerate(all_cut_sets_sets):
                is_minimal = True
                for j, existing_set in enumerate(all_cut_sets_sets):
                    if i != j and existing_set.issubset(cut_set) and len(existing_set) < len(cut_set):
                        is_minimal = False
                        break
                if is_minimal:
                    minimal_cut_sets.append(list(cut_set))

            # 保存分析结果
            self.analysis_results = {
                "top_event": top_event,
                "probability": p_top,
                "minimal_cut_sets": minimal_cut_sets,
                "structure_description": {
                    "gate_type": gate_structure['type'],
                    "children_count": len(gate_structure.get('children', [])),
                    "max_depth": max(self.event_hierarchy.values()) if self.event_hierarchy else 0
                }
            }

            # 在主线程中更新结果
            self.root.after(0, lambda: self.update_results(top_event, p_top, minimal_cut_sets, gate_structure))

        except Exception as e:
            # 在主线程中显示错误
            self.root.after(0, lambda: self.show_error(f"分析过程中出错:\n{str(e)}"))

    def update_results(self, top_event, p_top, minimal_cut_sets, gate_structure):
        """在主线程中更新结果文本框"""
        self.result_text.configure(state='normal')
        self.result_text.delete(1.0, tk.END)

        self.result_text.insert(tk.END, f"故障树分析结果\n", 'header')
        self.result_text.insert(tk.END, f"顶事件: {top_event}\n\n")

        self.result_text.insert(tk.END, "1. 顶事件发生概率:\n", 'subheader')
        self.result_text.insert(tk.END, f"   P({top_event}) = {p_top:.12f}\n\n")

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
        self.result_text.insert(tk.END,
                                f"   最大深度: {self.analysis_results['structure_description']['max_depth']}\n")

        # 添加样式标签
        self.result_text.tag_configure('header', font=(self.default_font[0], 12, 'bold'), foreground='navy')
        self.result_text.tag_configure('subheader', font=(self.default_font[0], 10, 'bold'), foreground='darkblue')

        self.result_text.configure(state='disabled')

    def show_error(self, message):
        """在主线程中显示错误"""
        self.result_text.configure(state='normal')
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, message)
        self.result_text.configure(state='disabled')

    def save_analysis(self):
        if not self.analysis_results["top_event"]:
            messagebox.showwarning("保存失败", "请先生成故障树分析结果")
            return

        if not os.path.exists(self.graph_image_path):
            messagebox.showwarning("保存失败", "未找到故障树图形文件")
            return

        default_filename = f"故障树分析_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")],
            initialfile=default_filename
        )

        if not file_path:
            return

        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)

            try:
                if sys.platform.startswith('win'):
                    pdf.add_font("SimSun", "", "C:/Windows/Fonts/simsun.ttc", uni=True)
                    pdf.set_font("SimSun", size=14)
                else:
                    pdf.add_font("SimSun", "", "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", uni=True)
                    pdf.set_font("SimSun", size=14)
            except:
                try:
                    if sys.platform.startswith('win'):
                        pdf.add_font("SimHei", "", "C:/Windows/Fonts/simhei.ttf", uni=True)
                        pdf.set_font("SimHei", size=14)
                    else:
                        pdf.add_font("SimHei", "", "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                                     uni=True)
                        pdf.set_font("SimHei", size=14)
                except:
                    pdf.set_font("Arial", size=14)

            pdf.set_font_size(16)
            pdf.cell(0, 10, "故障树分析报告", ln=True, align='C')
            pdf.ln(10)

            pdf.set_font_size(12)
            pdf.cell(0, 10, f"生成日期: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
            pdf.cell(0, 10, f"顶事件: {self.analysis_results['top_event']}", ln=True)
            pdf.ln(10)

            pdf.set_font_size(14)
            pdf.cell(0, 10, "分析结果", ln=True)
            pdf.set_font_size(12)

            pdf.cell(0, 10,
                     f"1. 顶事件发生概率: P({self.analysis_results['top_event']}) = {self.analysis_results['probability']:.12f}",
                     ln=True)

            pdf.cell(0, 10, "2. 最小割集:", ln=True)
            if self.analysis_results["minimal_cut_sets"]:
                for i, cut_set in enumerate(self.analysis_results["minimal_cut_sets"], 1):
                    pdf.cell(20)
                    pdf.cell(0, 10, f"割集 {i}: {' and '.join(cut_set)}", ln=True)
            else:
                pdf.cell(20)
                pdf.cell(0, 10, "未找到最小割集", ln=True)

            pdf.cell(0, 10, "3. 故障树结构说明:", ln=True)
            pdf.cell(20)
            pdf.cell(0, 10, f"顶事件: {self.analysis_results['top_event']}", ln=True)
            pdf.cell(20)
            pdf.cell(0, 10, f"门类型: {self.analysis_results['structure_description']['gate_type']}", ln=True)
            pdf.cell(20)
            pdf.cell(0, 10, f"子节点数: {self.analysis_results['structure_description']['children_count']}", ln=True)
            pdf.cell(20)
            pdf.cell(0, 10, f"最大深度: {self.analysis_results['structure_description']['max_depth']}", ln=True)

            pdf.ln(10)

            pdf.set_font_size(14)
            pdf.cell(0, 10, "故障树图形", ln=True)
            pdf.ln(5)

            pdf.image(self.graph_image_path, x=10, w=180)

            pdf.output(file_path)
            messagebox.showinfo("保存成功", f"分析报告已保存至: {file_path}")

        except Exception as e:
            messagebox.showerror("保存失败", f"保存分析报告时出错:\n{str(e)}")


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        if locale.getdefaultlocale()[0] is None:
            os.environ["LANG"] = "zh_CN.UTF-8"
    else:
        os.environ["LANG"] = "zh_CN.UTF-8"
        os.environ["LC_ALL"] = "zh_CN.UTF-8"

    root = tk.Tk()
    app = FaultTreeApp(root)
    root.mainloop()