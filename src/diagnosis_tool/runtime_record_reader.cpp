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

#include "runtime_record_reader.h"

#include "failure_log_helper.h"

namespace diag {
namespace log_helper {
namespace {
constexpr std::size_t TIMESTAMP_SIZE = sizeof("YYYY-MM-DDTHH:MM:SS") - 1;
constexpr std::size_t TIMESTAMP_DATE_SIZE = sizeof("YYYY-MM-DD") - 1;
constexpr char TIMESTAMP_T_SEPARATOR = 'T';
constexpr char TIMESTAMP_BOUND_SEPARATOR = ' ';
} // namespace

bool RuntimeRecordReader::Feed(std::string_view line)
{
    if (!line.empty() && line.back() == '\r') {
        line.remove_suffix(1);
    }
    // A timestamp at the beginning is a boundary even if the rest of the
    // header is malformed. Never attach another log/trace to the pending one.
    bool startsRecord = IsTimestampTAt(line, 0);
    if (!startsRecord && line.size() >= TIMESTAMP_SIZE && line[TIMESTAMP_DATE_SIZE] == TIMESTAMP_BOUND_SEPARATOR) {
        std::string timestamp(line.substr(0, TIMESTAMP_SIZE));
        timestamp[TIMESTAMP_DATE_SIZE] = TIMESTAMP_T_SEPARATOR;
        startsRecord = IsTimestampTAt(timestamp, 0);
    }
    if (startsRecord) {
        if (!Finish()) {
            return false;
        }
        pending_ = line;
        hasPending_ = true;
    } else if (hasPending_) {
        OwnPending();
        owned_ += "\\n";
        owned_.append(line);
        pending_ = owned_;
    }
    // Orphan continuation lines have no source location or trace to diagnose.
    return true;
}

void RuntimeRecordReader::OwnPending()
{
    if (hasPending_ && !ownsPending_) {
        owned_.assign(pending_);
        pending_ = owned_;
        ownsPending_ = true;
    }
}

bool RuntimeRecordReader::Finish()
{
    const bool result = !hasPending_ || emit_(pending_, ownsPending_);
    hasPending_ = false;
    ownsPending_ = false;
    pending_ = {};
    owned_.clear();
    return result;
}

} // namespace log_helper
} // namespace diag
