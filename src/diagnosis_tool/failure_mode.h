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

#ifndef FAILURE_MODE_H
#define FAILURE_MODE_H

#include <memory>
#include <string>
#include <vector>

namespace diag {
class RootCause {
public:
    RootCause(bool isFinalRootCauseInput, std::string rootCauseInput)
        : isFinalRootCause(isFinalRootCauseInput),
          rootCause(rootCauseInput)
    {
    }
    bool IsFinalRootCause();
    std::string GetRootCause();

private:
    bool isFinalRootCause;
    std::string rootCause;
};

class FailureMode {
public:
    virtual void PrintDesc();
    virtual std::string GetName() const = 0;
    virtual std::string GetValidationMethodDesc() const = 0;
    virtual bool IsValid(const std::vector<std::string> &fields) = 0;
    virtual std::string GetRootCauseDesc() const = 0;
    virtual RootCause AnalyzeRootCause();
    virtual std::string GetFixSuggDesc() const = 0;
    virtual std::string GetId() const = 0;
    void AddSubFailureMode(std::string faiureModeId);
    std::vector<std::string> GetSubFailureModes();

private:
    std::vector<std::string> subFailureModes;
};

} // namespace diag
#endif