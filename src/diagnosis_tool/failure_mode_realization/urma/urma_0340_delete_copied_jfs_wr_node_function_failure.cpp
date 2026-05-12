#include "urma_0340_delete_copied_jfs_wr_node_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0340DeleteCopiedJfsWrNodeFunctionFailure> g_urma("urma_0340");

bool Urma0340DeleteCopiedJfsWrNodeFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0341"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0340DeleteCopiedJfsWrNodeFunctionFailure::GetName() const
{
    return "delete_copied_jfs_wr_node 函数故障";
}

std::string Urma0340DeleteCopiedJfsWrNodeFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0340DeleteCopiedJfsWrNodeFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0340DeleteCopiedJfsWrNodeFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0340DeleteCopiedJfsWrNodeFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0340DeleteCopiedJfsWrNodeFunctionFailure::GetId() const
{
    return "urma_0340";
}
} // namespace diag
