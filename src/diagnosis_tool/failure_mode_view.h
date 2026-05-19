#ifndef FAILURE_MODE_VIEW_H
#define FAILURE_MODE_VIEW_H

#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "rack_error.h"
#include "failure_mode_controller.h"

namespace diag {
class FailureModeViewNode {
public:
    FailureModeViewNode(const std::string &id, const std::string &name, const std::string &cause,
                        const std::string &suggestion, const std::string &validation, int hitCount,
                        std::vector<FailureLogInfo> logInfos);
    FailureModeViewNode &AddSubFailureModeNode(FailureModeViewNode subFailureModeNode);
    const std::string &GetId() const;
    const std::string &GetName() const;
    const std::string &GetCause() const;
    const std::string &GetSuggestion() const;
    const std::string &GetValidation() const;
    int GetHitCount() const;
    const std::vector<FailureLogInfo> &GetLogInfos() const;
    const std::vector<FailureModeViewNode> &GetSubFailureModeNodes() const;

private:
    std::string id_;
    std::string name_;
    std::string cause_;
    std::string suggestion_;
    std::string validation_;
    int hitCount_;

    std::vector<FailureLogInfo> logInfos_;

    std::vector<FailureModeViewNode> subFailureModeNodes_;
};

class FailureModeView final {
public:
    RackResult Build(const std::unordered_set<std::string> &rootFailureModes,
                     std::unordered_map<std::string, FailureModeController> &failureModeIdToController);
    RackResult Dump() const;

private:
    RackResult BuildSubTree(FailureModeViewNode &parentNode, const std::string &parentFailureModeId,
                            std::unordered_map<std::string, FailureModeController> &failureModeIdToController,
                            std::unordered_set<std::string> &path);

    std::vector<FailureModeViewNode> roots;
};
} // namespace diag

#endif
