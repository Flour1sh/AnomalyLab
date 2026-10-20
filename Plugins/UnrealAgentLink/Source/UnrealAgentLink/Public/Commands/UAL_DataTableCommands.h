#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/**
 * 数据表（DataTable）的读和改。
 *
 * ## 为什么单独做，不让模型写 Python
 *
 * Python 也改得动表，但每次都得现写：字段名拼错是跑到一半才报，蓝图结构体的
 * 字段真名带 GUID 后缀（`Damage_2_8F3A...`）根本猜不出来，改到一半出错时前面
 * 改过的行已经留在表里了。这里把这三件事收进引擎侧：
 *
 *   - 列名按编辑器里显示的名字认，写错给「你是不是想写 XXX」；
 *   - 值走 `UALPropertyPath`（ImportText），类型不对当场拒；
 *   - 一批改动要么全成要么全不动，并且整批是 agent 撤销栈上的一步。
 *
 * ## 有源文件的表
 *
 * 从 CSV / JSON 导入的表，在编辑器里改完、下次重新导入就被源文件盖掉。
 * 两条命令都回 `source_file`，让上层在动手前先跟用户说清楚。不替用户去改源文件。
 */
class FUAL_DataTableCommands
{
public:
	static void RegisterCommands(TMap<FString, TFunction<void(const TSharedPtr<FJsonObject>&, const FString)>>& CommandMap);

	/**
	 * datatable.describe —— 表有哪些列、哪些行、指定行的值。
	 *
	 * 请求: { asset_path, rows?: [行名], columns?: [列名], offset?: 0, limit?: 20 }
	 *   rows 省略时按 offset/limit 取一段；columns 省略时给全部列
	 * 响应: { ok, asset_path, row_struct: { name, path, user_defined }, row_count,
	 *         columns: [{ name, type, enum_values? }],
	 *         row_names, row_names_truncated,
	 *         rows: { 行名: { 列名: 值 } },
	 *         unknown_rows?: [{ name, suggestions }], unknown_columns?: [...],
	 *         source_file?, source_file_exists?, composite?, parent_tables? }
	 */
	static void Handle_Describe(const TSharedPtr<FJsonObject>& Payload, const FString RequestId);

	/**
	 * datatable.edit —— 一批改动，按顺序执行，任何一条失败整批还原。
	 *
	 * 请求: { asset_path, ops: [
	 *           { op: "set",    row, values: { 列名或路径: 值 } },
	 *           { op: "add",    row, copy_from?, values? },
	 *           { op: "remove", row },
	 *           { op: "rename", row, new_name } ] }
	 * 响应: { ok, asset_path, applied, row_count, rows: { 行名: { 写过的列: 回读值 } },
	 *         removed?: [...], renamed?: [{ from, to }], source_file?, package }
	 * 失败: 400，message 指明第几条、哪一行、哪一列、为什么；表保持原样
	 */
	static void Handle_Edit(const TSharedPtr<FJsonObject>& Payload, const FString RequestId);
};
