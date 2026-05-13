#include "urma_0338_delete_copied_jfs_wr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0338DeleteCopiedJfsWrFunctionFailure> g_urma("urma_0338");

bool Urma0338DeleteCopiedJfsWrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0339"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0338DeleteCopiedJfsWrFunctionFailure::GetName() const
{
    return "delete_copied_jfs_wr 函数故障";
}

std::string Urma0338DeleteCopiedJfsWrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0338DeleteCopiedJfsWrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0338DeleteCopiedJfsWrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0338DeleteCopiedJfsWrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0338DeleteCopiedJfsWrFunctionFailure::GetId() const
{
    return "urma_0338";
}
} // namespace diag
