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

#define MODULE_NAME "DATABASE"

#include "database.h"
#include <sqlite3.h>
#include <algorithm>
#include <cctype>
#include <chrono>
#include <iostream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
#include "logger.h"

namespace database {
using namespace std;
constexpr uint32_t IND_ZERO = 0;
constexpr uint32_t IND_ONE = 1;
constexpr uint32_t IND_TWO = 2;
constexpr uint32_t IND_THREE = 3;
constexpr const char *UPDATE_TIMESTAMP = "update_timestamp";
constexpr const char *EXPIRE_TIMESTAMP = "expire_timestamp";

bool IsSafeIdentifier(const string &identifier)
{
    if (identifier.empty() || (!isalpha(static_cast<unsigned char>(identifier[0])) && identifier[0] != '_')) {
        return false;
    }
    for (size_t i = 1; i < identifier.size(); ++i) {
        unsigned char character = identifier[i];
        if (!isalnum(character) && character != '_') {
            return false;
        }
    }
    return true;
}

bool IsValidComparison(COMP_SYMB comparison)
{
    if (comparison == nullptr) {
        return false;
    }
    const string value(comparison);
    return value == EQ || value == NEQ || value == LT || value == LE || value == GT || value == GE || value == IN;
}

bool IsValidColumnType(const string &type)
{
    return type == "TEXT" || type == "INTEGER" || type == "REAL" || type == "BLOB" || type == "NUMERIC";
}

int PrepareStatement(sqlite3 *db, const string &sql, const vector<string> &binds, sqlite3_stmt **statement)
{
    int rc = sqlite3_prepare_v2(db, sql.c_str(), -1, statement, nullptr);
    if (rc != SQLITE_OK) {
        cout << "prepare statement error: " << sqlite3_errmsg(db) << endl;
        return rc;
    }
    for (size_t i = 0; i < binds.size(); ++i) {
        rc = sqlite3_bind_text(*statement, static_cast<int>(i + 1), binds[i].c_str(), -1, SQLITE_TRANSIENT);
        if (rc != SQLITE_OK) {
            cout << "bind data error: " << sqlite3_errmsg(db) << endl;
            sqlite3_finalize(*statement);
            *statement = nullptr;
            return rc;
        }
    }
    return SQLITE_OK;
}

int ExecutePrepared(sqlite3 *db, const string &sql, const vector<string> &binds, const char *operation)
{
    sqlite3_stmt *statement = nullptr;
    int rc = PrepareStatement(db, sql, binds, &statement);
    if (rc != SQLITE_OK) {
        return rc;
    }
    rc = sqlite3_step(statement);
    if (rc != SQLITE_DONE) {
        cout << operation << " data error: " << sqlite3_errmsg(db) << endl;
        sqlite3_finalize(statement);
        return rc;
    }
    rc = sqlite3_finalize(statement);
    return rc == SQLITE_OK ? SQLITE_OK : rc;
}

OP_RET QueryPrepared(sqlite3 *db, const string &sql, const vector<string> &binds, QueryResult *res)
{
    sqlite3_stmt *statement = nullptr;
    int rc = PrepareStatement(db, sql, binds, &statement);
    if (rc != SQLITE_OK) {
        return OP_RET::FAIL;
    }
    while ((rc = sqlite3_step(statement)) == SQLITE_ROW) {
        unordered_map<string, string> row;
        for (int i = 0; i < sqlite3_column_count(statement); ++i) {
            const unsigned char *value = sqlite3_column_text(statement, i);
            row[sqlite3_column_name(statement, i)] = value == nullptr ? "NULL" : reinterpret_cast<const char *>(value);
        }
        res->push_back(row);
    }
    if (rc != SQLITE_DONE) {
        cout << "query data error: " << sqlite3_errmsg(db) << endl;
    }
    int finalizeRc = sqlite3_finalize(statement);
    return rc == SQLITE_DONE && finalizeRc == SQLITE_OK ? OP_RET::SUCCESS : OP_RET::FAIL;
}

int GetNowTimestamp()
{
    auto time = chrono::system_clock::now();
    int timestamp = chrono::duration_cast<chrono::milliseconds>(time.time_since_epoch()).count();
    return timestamp;
}

bool Database::IsValidTable(string tableName)
{
    return IsSafeIdentifier(tableName) && keysMap.find(tableName) != keysMap.end();
}

bool Database::IsValidKey(string tableName, string key)
{
    auto table = keysMap.find(tableName);
    return IsSafeIdentifier(key) && table != keysMap.end() && table->second.find(key) != table->second.end();
}

bool Database::AppendConditions(string tableName, ConditionMap conditions, string *sql, vector<string> *binds)
{
    size_t index = 0;
    for (const auto &condition : conditions) {
        if (!IsValidKey(tableName, condition.first) || !IsValidComparison(condition.second.first)) {
            cout << "invalid query condition" << endl;
            return false;
        }
        if (index++ != 0) {
            *sql += " AND ";
        }
        *sql += condition.first + string(condition.second.first) + "?";
        binds->push_back(condition.second.second);
    }
    return true;
}
OP_RET Database::OpenDb(string currDbName, bool enableHis)
{
    this->currDbName = currDbName;
    this->enableHis = enableHis;
    int rc1 = sqlite3_open(currDbName.c_str(), &currDb);
    int rc2 = 0;
    if (enableHis) {
        hisDbName = currDbName + "_history";
        rc2 = sqlite3_open(hisDbName.c_str(), &hisDb);
    }
    if (rc1 || rc2) {
        return OP_RET::FAIL;
    } else {
        return OP_RET::SUCCESS;
    }
}
int Database::CreateTableOp(sqlite3 *db, string tableName, TableParams params, vector<string> primaryKeys)
{
    char *errMsg;
    string sql = "CREATE TABLE IF NOT EXISTS " + tableName + " (";
    for (int i = 0; i < params.size(); i++) {
        sql += get<IND_ZERO>(params[i]) + " " + get<IND_ONE>(params[i]);
        sql += get<IND_TWO>(params[i]) ? " NOT NULL" : " DEFAULT NULL";

        if (i != params.size() - 1) {
            sql += ", ";
        }
    }
    if (!primaryKeys.empty()) {
        sql += ", PRIMARY KEY (";
        for (int i = 0; i < primaryKeys.size(); i++) {
            sql += ((i == 0 ? "" : ", ") + primaryKeys[i]);
        }
        sql += ")";
    }
    sql += ");";
    LOG_DEBUG << "execute SQL on table: " << tableName;
    int rc = sqlite3_exec(db, sql.c_str(), NULL, NULL, &errMsg);
    if (rc != SQLITE_OK) {
        cout << "create table error: " << errMsg << endl;
    }
    sqlite3_free(errMsg);
    return rc;
}

// void Database::CreateTable(string tableName, vector<tuple<string, string, bool, bool>> createTableParams) {
//     return;
// }
// createTableParams: name, type, not null, primary key
OP_RET Database::CreateTable(string tableName, TableParams createTableParams)
{
    if (!IsSafeIdentifier(tableName) || createTableParams.empty()) {
        cout << "invalid table definition" << endl;
        return OP_RET::FAIL;
    }

    vector<string> primaryKeys;
    unordered_map<string, string> keys;
    for (const auto &param : createTableParams) {
        const string &columnName = get<IND_ZERO>(param);
        const string &columnType = get<IND_ONE>(param);
        if (!IsSafeIdentifier(columnName) || !IsValidColumnType(columnType) || columnName == UPDATE_TIMESTAMP ||
            columnName == EXPIRE_TIMESTAMP || keys.find(columnName) != keys.end()) {
            cout << "invalid table definition" << endl;
            return OP_RET::FAIL;
        }
        keys[columnName] = columnType;
        if (get<IND_THREE>(param)) {
            primaryKeys.push_back(columnName);
        }
    }

    TableParams params = createTableParams;
    params.push_back(make_tuple(UPDATE_TIMESTAMP, "INTEGER", true, false));
    int rc1 = CreateTableOp(currDb, tableName, params, primaryKeys);
    int rc2 = SQLITE_OK;
    if (enableHis) {
        // in his db, UPDATE_TIMESTAMP is primary key
        params[params.size() - 1] = make_tuple(UPDATE_TIMESTAMP, "INTEGER", true, true);
        params.push_back(make_tuple(EXPIRE_TIMESTAMP, "INTEGER", false, false));
        vector<string> historyPrimaryKeys = primaryKeys;
        historyPrimaryKeys.push_back(UPDATE_TIMESTAMP);
        rc2 = CreateTableOp(hisDb, tableName, params, historyPrimaryKeys);
    }
    if (rc1 != SQLITE_OK || rc2 != SQLITE_OK) {
        return OP_RET::FAIL;
    }
    keys[UPDATE_TIMESTAMP] = "INTEGER";
    if (enableHis) {
        keys[EXPIRE_TIMESTAMP] = "INTEGER";
    }
    keysMap[tableName] = std::move(keys);
    primaryKeysMap[tableName] = std::move(primaryKeys);
    return OP_RET::SUCCESS;
}

OP_RET Database::QueryCurrData(string tableName, ConditionMap data, QueryResult *res)
{
    res->clear();
    if (!IsValidTable(tableName)) {
        cout << "invalid table name: " << tableName << endl;
        return OP_RET::FAIL;
    }
    string sql = "SELECT * FROM " + tableName;
    vector<string> binds;
    if (!data.empty()) {
        sql += " WHERE ";
    }
    if (!AppendConditions(tableName, data, &sql, &binds)) {
        return OP_RET::FAIL;
    }
    sql += ";";
    LOG_DEBUG << "execute SQL on table: " << tableName;
    return QueryPrepared(currDb, sql, binds, res);
}

OP_RET Database::QueryHisData(string tableName, ConditionMap data, QueryResult *res, int start, int end)
{
    res->clear();
    if (!IsValidTable(tableName)) {
        cout << "invalid table name: " << tableName << endl;
        return OP_RET::FAIL;
    }
    string sql = "SELECT * FROM " + tableName + " WHERE ";
    vector<string> binds;
    if (!AppendConditions(tableName, data, &sql, &binds)) {
        return OP_RET::FAIL;
    }
    if (!data.empty()) {
        sql += " AND ";
    }
    sql += string(UPDATE_TIMESTAMP) + " <= ? AND (" + EXPIRE_TIMESTAMP + " IS NULL OR " + EXPIRE_TIMESTAMP + " >= ?);";
    binds.push_back(to_string(end));
    binds.push_back(to_string(start));
    LOG_DEBUG << "execute SQL on table: " << tableName;
    return QueryPrepared(hisDb, sql, binds, res);
}

int Database::UpdateDataOp(sqlite3 *db, string tableName, ConditionMap condition, DataMap content)
{
    if (!IsValidTable(tableName) || content.empty() || condition.empty()) {
        cout << "invalid update parameters" << endl;
        return SQLITE_MISUSE;
    }
    string sql = "UPDATE " + tableName + " SET ";
    vector<string> binds;
    for (auto it = content.begin(); it != content.end(); ++it) {
        if (!IsValidKey(tableName, it->first)) {
            cout << "invalid column name: " << it->first << endl;
            return SQLITE_MISUSE;
        }
        if (it != content.begin()) {
            sql += ", ";
        }
        sql += it->first + " = ?";
        binds.push_back(it->second);
    }
    sql += " WHERE ";
    if (!AppendConditions(tableName, condition, &sql, &binds)) {
        return SQLITE_MISUSE;
    }
    sql += ";";
    LOG_DEBUG << "execute SQL on table: " << tableName;
    return ExecutePrepared(db, sql, binds, "update");
}

OP_RET Database::UpdateData(string tableName, ConditionMap condition, DataMap content)
{
    int timestamp = GetNowTimestamp();
    content[UPDATE_TIMESTAMP] = to_string(timestamp);
    int rc = UpdateDataOp(currDb, tableName, condition, content);
    if (rc != SQLITE_OK) {
        return OP_RET::FAIL;
    }
    if (enableHis) {
        unordered_map<string, string> expireContent;
        expireContent[EXPIRE_TIMESTAMP] = to_string(timestamp);
        rc = UpdateDataOp(hisDb, tableName, condition, expireContent);
        if (rc != SQLITE_OK) {
            return OP_RET::FAIL;
        }
        vector<unordered_map<string, string>> queryRes;
        OP_RET rc2 = QueryCurrData(tableName, condition, &queryRes);
        if (rc2 == OP_RET::FAIL) {
            return OP_RET::FAIL;
        }
        for (int i = 0; i < queryRes.size(); i++) {
            unordered_map<string, string> res = queryRes[i];
            rc = InsertDataOp(hisDb, tableName, res);
            if (rc != SQLITE_OK) {
                return OP_RET::FAIL;
            }
        }
    }
    return OP_RET::SUCCESS;
}

int Database::InsertDataOp(sqlite3 *db, string tableName, DataMap data)
{
    if (!IsValidTable(tableName) || data.empty()) {
        cout << "invalid insert parameters" << endl;
        return SQLITE_MISUSE;
    }
    vector<pair<string, string>> insertData(data.begin(), data.end());
    string sql = "INSERT INTO " + tableName + "(";
    vector<string> binds;
    for (size_t i = 0; i < insertData.size(); ++i) {
        if (!IsValidKey(tableName, insertData[i].first)) {
            cout << "invalid column name: " << insertData[i].first << endl;
            return SQLITE_MISUSE;
        }
        if (i != 0) {
            sql += ",";
        }
        sql += insertData[i].first;
    }
    sql += ") VALUES(";
    for (size_t i = 0; i < insertData.size(); ++i) {
        if (i != 0) {
            sql += ",";
        }
        sql += "?";
        binds.push_back(insertData[i].second);
    }
    sql += ");";
    LOG_DEBUG << "execute SQL on table: " << tableName;
    return ExecutePrepared(db, sql, binds, "insert");
}

OP_RET Database::InsertData(string tableName, DataMap data)
{
    // if the primary key already exists, update
    if (!IsValidTable(tableName)) {
        cout << "invalid table name: " << tableName << endl;
        return OP_RET::FAIL;
    }
    unordered_map<string, pair<COMP_SYMB, string>> queryMap;
    unordered_map<string, string> contentMap;
    for (auto it : data) {
        if (find(primaryKeysMap[tableName].begin(), primaryKeysMap[tableName].end(), it.first) !=
            primaryKeysMap[tableName].end()) {
            queryMap[it.first] = make_pair(EQ, it.second);
        } else {
            contentMap[it.first] = it.second;
        }
    }
    vector<unordered_map<string, string>> queryRes;
    OP_RET qrc = Database::QueryCurrData(tableName, queryMap, &queryRes);
    if (qrc == OP_RET::FAIL) {
        return OP_RET::FAIL;
    }
    if (queryRes.size() > 0) {
        return Database::UpdateData(tableName, queryMap, contentMap);
    }
    // else, insert
    int timestamp = GetNowTimestamp();
    data[UPDATE_TIMESTAMP] = to_string(timestamp);
    int rc = InsertDataOp(currDb, tableName, data);
    if (rc != SQLITE_OK) {
        return OP_RET::FAIL;
    }
    if (enableHis) {
        int rc2 = InsertDataOp(hisDb, tableName, data);
        if (rc2 != SQLITE_OK) {
            return OP_RET::FAIL;
        }
    }
    return OP_RET::SUCCESS;
}

int Database::DeleteDataOp(sqlite3 *db, string tableName, ConditionMap data)
{
    if (!IsValidTable(tableName) || data.empty()) {
        cout << "invalid delete parameters" << endl;
        return SQLITE_MISUSE;
    }
    string sql = "DELETE FROM " + tableName + " WHERE ";
    vector<string> binds;
    if (!AppendConditions(tableName, data, &sql, &binds)) {
        return SQLITE_MISUSE;
    }
    sql += ";";
    LOG_DEBUG << "execute SQL on table: " << tableName;
    return ExecutePrepared(db, sql, binds, "delete");
}

// delete a line in curr db, and expire the corresponding line in his db
OP_RET Database::DeleteData(string tableName, ConditionMap data)
{
    int rc = DeleteDataOp(currDb, tableName, data);
    if (rc != SQLITE_OK) {
        return OP_RET::FAIL;
    }
    if (enableHis) {
        int timestamp = GetNowTimestamp();
        unordered_map<string, string> content;
        content[EXPIRE_TIMESTAMP] = to_string(timestamp);
        int rc2 = UpdateDataOp(hisDb, tableName, data, content);
        if (rc2 != SQLITE_OK) {
            return OP_RET::FAIL;
        }
    }
    return OP_RET::SUCCESS;
}

OP_RET Database::DropTable(sqlite3 *db, string tableName)
{
    if (!IsSafeIdentifier(tableName)) {
        cout << "invalid table name: " << tableName << endl;
        return OP_RET::FAIL;
    }
    cout << "dropping " << tableName << endl;
    char *errMsg;
    string sql = "DROP TABLE IF EXISTS " + tableName + ";";
    int rc = sqlite3_exec(db, sql.c_str(), NULL, NULL, &errMsg);
    if (rc != SQLITE_OK) {
        cout << "drop table error: " << tableName << " " << errMsg << endl;
        sqlite3_free(errMsg);
        return OP_RET::FAIL;
    } else {
        return OP_RET::SUCCESS;
    }
}

OP_RET Database::Close()
{
    cout << "closing db" << endl;
    int rc1 = sqlite3_close(currDb);
    int rc2 = 0;
    if (enableHis) {
        rc2 = sqlite3_close(hisDb);
    }
    currDb = nullptr;
    hisDb = nullptr;
    if (rc1 || rc2) {
        return OP_RET::FAIL;
    }
    return OP_RET::SUCCESS;
}
} // namespace database
