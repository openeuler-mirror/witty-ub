#include "urma_0199_import_pjetty_primary_eid_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0199ImportPjettyPrimaryEidFunctionFailure> g_urma("urma_0199");

bool Urma0199ImportPjettyPrimaryEidFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0200", "urma_0201", "urma_0202"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0199ImportPjettyPrimaryEidFunctionFailure::GetName() const
{
    return "import_pjetty_for_primary_eid 函数故障";
}

std::string Urma0199ImportPjettyPrimaryEidFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0199ImportPjettyPrimaryEidFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0199ImportPjettyPrimaryEidFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0199ImportPjettyPrimaryEidFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0199ImportPjettyPrimaryEidFunctionFailure::GetId() const
{
    return "urma_0199";
}
} // namespace diag
