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

#ifndef RUNTIME_RECORD_READER_H
#define RUNTIME_RECORD_READER_H

#include <functional>
#include <string>
#include <string_view>
#include <utility>

namespace diag {
namespace log_helper {
// Keep one logical runtime record pending. Borrow mmap/chunk storage until the
// caller is about to reuse it; only continuations and buffer boundaries copy.
class RuntimeRecordReader {
public:
    using Emit = std::function<bool(std::string_view, bool)>;
    explicit RuntimeRecordReader(Emit emit) : emit_(std::move(emit)) {}
    bool Feed(std::string_view line);
    bool Finish();
    void OwnPending();

private:
    Emit emit_;
    std::string_view pending_;
    std::string owned_;
    bool hasPending_ = false;
    bool ownsPending_ = false;
};

} // namespace log_helper
} // namespace diag

#endif // RUNTIME_RECORD_READER_H
