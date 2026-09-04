/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#ifndef DATABASE_H
#define DATABASE_H

#include <sqlite3.h>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

namespace database {
using namespace std;
enum class OP_RET {
    SUCCESS = 0,
    FAIL = 1,
    NOT_FOUND = 2,
};
using COMP_SYMB = const char *;
constexpr COMP_SYMB EQ = "=";
constexpr COMP_SYMB NEQ = "!=";
constexpr COMP_SYMB LT = "<";
constexpr COMP_SYMB LE = "<=";
constexpr COMP_SYMB GT = ">";
constexpr COMP_SYMB GE = ">=";
constexpr COMP_SYMB IN = " IS NOT ";
using DataMap = unordered_map<string, string>;
using ConditionMap = unordered_map<string, pair<COMP_SYMB, string>>;
using QueryResult = vector<DataMap>;
using TableParams = vector<tuple<string, string, bool, bool>>;

class Database {
public:
    OP_RET OpenDb(string currDbName, bool enableHis);
    // name, type, null, primary_key
    OP_RET CreateTable(string tableName, TableParams createTableParams);
    OP_RET InsertData(string tableName, DataMap data);
    OP_RET UpdateData(string tableName, ConditionMap condition, DataMap content);
    OP_RET DeleteData(string tableName, ConditionMap data);
    OP_RET QueryCurrData(string tableName, ConditionMap data, QueryResult *res);
    OP_RET QueryHisData(string tableName, ConditionMap data, QueryResult *res, int start, int end);
    OP_RET Close();

private:
    sqlite3 *currDb;
    sqlite3 *hisDb;
    string currDbName;
    string hisDbName;
    bool enableHis;
    unordered_map<string, vector<string>> primaryKeysMap;
    unordered_map<string, unordered_map<string, string>> keysMap;
    bool IsValidTable(string tableName);
    bool IsValidKey(string tableName, string key);
    bool AppendConditions(string tableName, ConditionMap conditions, string *sql, vector<string> *binds);
    int CreateTableOp(sqlite3 *db, string tableName, TableParams params, vector<string> primaryKeys);
    int InsertDataOp(sqlite3 *db, string tableName, DataMap data);
    int UpdateDataOp(sqlite3 *db, string tableName, ConditionMap condition, DataMap content);
    int DeleteDataOp(sqlite3 *db, string tableName, ConditionMap data);
    OP_RET DropTable(sqlite3 *db, string tableName);
};
int GetNowTimestamp();
} // namespace database

#endif // DATABASE_H
