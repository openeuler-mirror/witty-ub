#include "urma_0196_import_pjetty_port_eid_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0196ImportPjettyPortEidFunctionFailure> g_urma("urma_0196");

bool Urma0196ImportPjettyPortEidFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0197", "urma_0198"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0196ImportPjettyPortEidFunctionFailure::GetName() const
{
    return "import_pjetty_for_port_eid 函数故障";
}

std::string Urma0196ImportPjettyPortEidFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0196ImportPjettyPortEidFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0196ImportPjettyPortEidFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0196ImportPjettyPortEidFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0196ImportPjettyPortEidFunctionFailure::GetId() const
{
    return "urma_0196";
}
} // namespace diag
