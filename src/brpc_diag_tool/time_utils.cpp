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

#include "time_utils.h"

namespace brpc::time {

bool ParseFixedInt(std::string_view value, std::size_t pos, std::size_t count, int &result)
{
    if (pos + count > value.size()) {
        return false;
    }
    int parsed = 0;
    for (std::size_t i = pos; i < pos + count; ++i) {
        if (value[i] < '0' || value[i] > '9') {
            return false;
        }
        parsed = parsed * NUM_10 + value[i] - '0';
    }
    result = parsed;
    return true;
}

bool BuildUtc8Timestamp(const CivilTime &parsed, std::int64_t &timestamp)
{
    constexpr int daysPerMonth[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    const bool leapYear = parsed.year % 4 == 0 && (parsed.year % 100 != 0 || parsed.year % 400 == 0);
    if (parsed.month < MIN_MONTH || parsed.month > MAX_MONTH || parsed.day < MIN_DAY ||
        parsed.day > daysPerMonth[parsed.month - 1] + (parsed.month == FEBRARY && leapYear ? 1 : 0) ||
        parsed.hour < MIN_HOUR || parsed.hour > MAX_HOUR || parsed.minute < MIN_MINUTE || parsed.minute > MAX_MINUTE ||
        parsed.second < MIN_SECOND || parsed.second > MAX_SECOND || parsed.microsecond < MIN_MICROSECOND ||
        parsed.microsecond >= MICROSECONDS_PER_SECOND) {
        return false;
    }

    const int adjustedYear = parsed.year - (parsed.month <= 2);
    const int era = (adjustedYear >= 0 ? adjustedYear : adjustedYear - 399) / 400;
    const unsigned yearOfEra = static_cast<unsigned>(adjustedYear - era * 400);
    const unsigned monthIndex = static_cast<unsigned>(parsed.month > 2 ? parsed.month - 3 : parsed.month + 9);
    const unsigned dayOfYear = (153 * monthIndex + 2) / 5 + static_cast<unsigned>(parsed.day) - 1;
    const unsigned dayOfEra = yearOfEra * 365 + yearOfEra / 4 - yearOfEra / 100 + dayOfYear;
    const std::int64_t daysSinceEpoch = static_cast<std::int64_t>(era) * 146097 + dayOfEra - 719468;
    const std::int64_t unixSeconds = daysSinceEpoch * 24 * 60 * 60 + parsed.hour * 60 * 60 + parsed.minute * 60 +
                                     parsed.second - UTC8_OFFSET_SECONDS;
    timestamp = unixSeconds * MICROSECONDS_PER_SECOND + parsed.microsecond;
    return true;
}

} // namespace brpc::time
