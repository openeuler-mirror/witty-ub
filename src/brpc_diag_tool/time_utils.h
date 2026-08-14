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

#pragma once

#include <cstddef>
#include <cstdint>
#include <string_view>

namespace brpc::time {

inline constexpr std::int64_t MICROSECONDS_PER_SECOND = 1000000;
inline constexpr std::int64_t UTC8_OFFSET_SECONDS = 8 * 60 * 60;
constexpr int NUM_10 = 10;
constexpr int MIN_MONTH = 1;
constexpr int MAX_MONTH = 12;
constexpr int FEBRARY = 2;
constexpr int MIN_DAY = 1;
constexpr int MIN_HOUR = 0;
constexpr int MAX_HOUR = 23;
constexpr int MIN_MINUTE = 0;
constexpr int MAX_MINUTE = 59;
constexpr int MIN_SECOND = 0;
constexpr int MAX_SECOND = 59;
constexpr int MIN_MICROSECOND = 0;

struct CivilTime {
    int year = 0;
    int month = 0;
    int day = 0;
    int hour = 0;
    int minute = 0;
    int second = 0;
    int microsecond = 0;
};

bool ParseFixedInt(std::string_view value, std::size_t pos, std::size_t count, int &result);
bool BuildUtc8Timestamp(const CivilTime &parsed, std::int64_t &timestamp);

} // namespace brpc::time
