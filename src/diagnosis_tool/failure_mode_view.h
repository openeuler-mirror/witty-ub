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

#ifndef FAILURE_MODE_VIEW_H
#define FAILURE_MODE_VIEW_H

#include <memory>
#include <string>
#include <unordered_set>

#include "rack_error.h"
#include "failure_mode_controller.h"

namespace diag {
struct FailureModeViewNodeData {
    std::string id;
    std::string name;
    std::string cause;
    std::string suggestion;
    std::string validation;
    int hitCount;
    std::unordered_map<std::string, std::shared_ptr<FailureLogInfo>> traceIdToFailureLogInfo;

    explicit FailureModeViewNodeData(const FailureModeController &controller);
};

class FailureModeViewNode final {
public:
    explicit FailureModeViewNode(FailureModeViewNodeData &&data);
    ~FailureModeViewNode() = default;

    const FailureModeViewNodeData &GetData() const;
    void AddSubNode(const FailureModeViewNode &subNode);
    const std::vector<FailureModeViewNode> &GetSubNodes() const;

private:
    FailureModeViewNodeData data_;
    std::vector<FailureModeViewNode> subNodes_;
};

class FailureModeView final {
public:
    RackResult Build(
        const std::unordered_set<std::string> &rootFailureModes,
        const std::unordered_map<std::string, FailureModeController> &failureModeIdToController,
        const std::unordered_map<std::string, std::vector<std::shared_ptr<FailureLogInfo>>> &traceIdToFailureLogInfos);
    RackResult Dump(const std::string &outputDir = "") const;

private:
    RackResult BuildSubTree(FailureModeViewNode &parentNode, const std::string &parentFailureModeId,
                            const std::unordered_map<std::string, FailureModeController> &failureModeIdToController,
                            std::unordered_set<std::string> &path);

private:
    std::vector<FailureModeViewNode> roots_;
    std::unordered_map<std::string, std::vector<std::shared_ptr<FailureLogInfo>>> traceIdToFailureLogInfos_;
};
} // namespace diag

#endif // FAILURE_MODE_VIEW_H